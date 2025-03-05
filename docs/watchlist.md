# Watchlist Feature Documentation

## Overview
Simple watchlist system that alerts users when stocks hit 5th/95th percentile thresholds. Each user has their own watchlist file, and the system checks these stocks every Sunday, sending Telegram alerts when significant price movements are detected.

## Components

### 1. Configuration Files

#### User Watchlists
```yaml
# config/watchlists/<telegram_id>.yaml
name: "John Doe"  # User's Telegram name
stocks:
  - AAPL
  - GOOGL
  - MSFT
last_notified: "2024-03-10"  # Track last notification time
```

#### Stock Cache
```yaml
# config/cache/stocks.yaml
AAPL:
  last_check: "2024-03-10"
  price_history:
    - date: "2024-03-10"
      price: 175.34
      percentile: 95.2
  ma_200: 168.45
```

#### Bot Configuration
```yaml
# config/bot.yaml
telegram_token: "your_bot_token"
check_day: "sunday"
check_time: "18:00"
percentile_thresholds:
  low: 5
  high: 95
```

#### System Logs
```yaml
# config/logs.yaml
last_run: "2024-03-10T18:00:00Z"
errors:
  - timestamp: "2024-03-10T18:01:23Z"
    error: "Failed to fetch AAPL data"
    user_id: "123456789"
successes:
  - timestamp: "2024-03-10T18:00:05Z"
    stock: "GOOGL"
    users_notified: 3
```

### 2. Telegram Bot Service
```python
from telegram.ext import Application, CommandHandler
from pathlib import Path
import yaml
from datetime import datetime

class AlertBot:
    def __init__(self, config_path: str = "config/bot.yaml"):
        # Load bot configuration
        self.config = yaml.safe_load(Path(config_path).read_text())
        self.app = Application.builder().token(self.config["telegram_token"]).build()
        self.watchlist_dir = Path("config/watchlists")
        self.cache_file = Path("config/cache/stocks.yaml")
        self.log_file = Path("config/logs.yaml")
        
    async def send_alert(self, 
                        user_id: str, 
                        symbol: str, 
                        price: float, 
                        percentile: float) -> bool:
        """Send alert message when stock hits threshold"""
        message = f"""
🚨 Stock Alert: {symbol}
Stock in your watchlist has hit a significant threshold!

Symbol: {symbol}
Current Price: ${price:.2f}
Current Percentile: {percentile:.1f}%
        """
        try:
            await self.app.bot.send_message(chat_id=user_id, text=message)
            self._log_success(symbol, user_id)
            return True
        except Exception as e:
            self._log_error(f"Failed to send alert: {e}", user_id)
            return False

    def get_user_stocks(self, user_id: str) -> list:
        """Get stocks for a specific user"""
        config_file = self.watchlist_dir / f"{user_id}.yaml"
        if not config_file.exists():
            return []
        
        config = yaml.safe_load(config_file.read_text())
        return config.get("stocks", [])

    def _log_success(self, symbol: str, user_id: str):
        """Log successful notification"""
        logs = yaml.safe_load(self.log_file.read_text())
        logs["successes"].append({
            "timestamp": datetime.utcnow().isoformat(),
            "stock": symbol,
            "user_id": user_id
        })
        self.log_file.write_text(yaml.dump(logs))

    def _log_error(self, error: str, user_id: str):
        """Log error"""
        logs = yaml.safe_load(self.log_file.read_text())
        logs["errors"].append({
            "timestamp": datetime.utcnow().isoformat(),
            "error": error,
            "user_id": user_id
        })
        self.log_file.write_text(yaml.dump(logs))
```

### 3. Weekly Checker Script
```python
import yaml
from pathlib import Path
from datetime import datetime

async def check_all_watchlists(bot: AlertBot):
    """Weekly check of all users' watchlists (runs every Sunday)"""
    # Update last run time
    logs = yaml.safe_load(Path("config/logs.yaml").read_text())
    logs["last_run"] = datetime.utcnow().isoformat()
    Path("config/logs.yaml").write_text(yaml.dump(logs))
    
    # Load stock cache
    cache = yaml.safe_load(Path("config/cache/stocks.yaml").read_text())
    
    # Process each user's watchlist
    for config_file in Path("config/watchlists").glob("*.yaml"):
        user_id = config_file.stem
        user_config = yaml.safe_load(config_file.read_text())
        stocks = user_config.get("stocks", [])
        
        for symbol in stocks:
            try:
                # Check cache first
                if symbol in cache and _is_cache_valid(cache[symbol]):
                    data = cache[symbol]
                else:
                    # Use existing stock data function and update cache
                    data = get_stock_data(symbol)
                    cache[symbol] = {
                        "last_check": datetime.utcnow().isoformat(),
                        "price": data.price,
                        "percentile": data.percentile,
                        "ma_200": data.ma_200
                    }
                
                # Check thresholds
                if data["percentile"] <= bot.config["percentile_thresholds"]["low"] or \
                   data["percentile"] >= bot.config["percentile_thresholds"]["high"]:
                    await bot.send_alert(
                        user_id,
                        symbol,
                        data["price"],
                        data["percentile"]
                    )
                
            except Exception as e:
                bot._log_error(f"Error checking {symbol}: {e}", user_id)
    
    # Save updated cache
    Path("config/cache/stocks.yaml").write_text(yaml.dump(cache))

def _is_cache_valid(data: dict, max_age_hours: int = 24) -> bool:
    """Check if cached data is still valid"""
    last_check = datetime.fromisoformat(data["last_check"])
    age = datetime.utcnow() - last_check
    return age.total_seconds() < max_age_hours * 3600
```

## Bot Commands

### Command Handlers
```python
async def start(update, context):
    """Welcome message and help"""
    user_id = str(update.effective_user.id)
    config_file = Path("config/watchlists") / f"{user_id}.yaml"
    
    if not config_file.exists():
        # Create empty watchlist for new user
        config_file.parent.mkdir(parents=True, exist_ok=True)
        config = {
            "name": update.effective_user.full_name,
            "stocks": [],
            "last_notified": datetime.utcnow().isoformat()
        }
        config_file.write_text(yaml.dump(config))
    
    await update.message.reply_text(
        "Welcome to Stock Alerts Bot! 📈\n\n"
        "I'll send you alerts every Sunday when stocks in your watchlist "
        "hit significant price thresholds (5th or 95th percentile).\n\n"
        "Commands:\n"
        "/add <ticker> - Add stock to your watchlist\n"
        "/remove <ticker> - Remove stock from watchlist\n"
        "/list - Show your watchlist"
    )

async def add_stock(update, context):
    """Add stock to user's watchlist"""
    if not context.args:
        await update.message.reply_text("Please provide a ticker symbol: /add AAPL")
        return
    
    user_id = str(update.effective_user.id)
    symbol = context.args[0].upper()
    config_file = Path("config/watchlists") / f"{user_id}.yaml"
    
    try:
        config = yaml.safe_load(config_file.read_text())
        if symbol not in config["stocks"]:
            config["stocks"].append(symbol)
            config_file.write_text(yaml.dump(config))
            await update.message.reply_text(f"Added {symbol} to your watchlist!")
        else:
            await update.message.reply_text(f"{symbol} is already in your watchlist!")
    except Exception as e:
        await update.message.reply_text(f"Failed to add {symbol}: {str(e)}")

async def remove_stock(update, context):
    """Remove stock from user's watchlist"""
    if not context.args:
        await update.message.reply_text("Please provide a ticker symbol: /remove AAPL")
        return
    
    user_id = str(update.effective_user.id)
    symbol = context.args[0].upper()
    config_file = Path("config/watchlists") / f"{user_id}.yaml"
    
    try:
        config = yaml.safe_load(config_file.read_text())
        if symbol in config["stocks"]:
            config["stocks"].remove(symbol)
            config_file.write_text(yaml.dump(config))
            await update.message.reply_text(f"Removed {symbol} from your watchlist!")
        else:
            await update.message.reply_text(f"{symbol} is not in your watchlist!")
    except Exception as e:
        await update.message.reply_text(f"Failed to remove {symbol}: {str(e)}")

async def list_stocks(update, context):
    """Show user's watchlist"""
    user_id = str(update.effective_user.id)
    config_file = Path("config/watchlists") / f"{user_id}.yaml"
    
    try:
        config = yaml.safe_load(config_file.read_text())
        stocks = config.get("stocks", [])
        if stocks:
            await update.message.reply_text(
                "📊 Your Watchlist:\n\n" + 
                "\n".join(f"• {symbol}" for symbol in stocks)
            )
        else:
            await update.message.reply_text(
                "Your watchlist is empty! Use /add <ticker> to add stocks."
            )
    except Exception as e:
        await update.message.reply_text("Failed to fetch your watchlist.")
```

## File Structure
```
config/
  ├── bot.yaml           # Bot configuration
  ├── logs.yaml          # System logs
  ├── cache/
  │   └── stocks.yaml    # Stock data cache
  └── watchlists/        # User watchlists
      ├── 123456789.yaml # One file per user
      └── 987654321.yaml
```

## Error Handling
- Invalid symbols are logged but don't stop processing
- Telegram sending failures are logged but continue with other users
- YAML parsing errors are caught and reported to users
- Missing user config files are created automatically
- Cache invalidation after 24 hours
- All errors and successes are logged for debugging

## Future Improvements
- Add support for custom percentile thresholds per user
- Allow users to set their preferred alert time
- Add more alert conditions
- Support inline keyboard menus
- Add scheduled reports per user
- Add data retention policies for logs and cache
- Implement backup system for YAML files 