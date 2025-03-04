# Watchlist Feature Documentation

## Overview
Simple watchlist system that alerts users when stocks hit 5th/95th percentile thresholds. The system periodically checks stock prices and sends email alerts when significant price movements are detected.

## Components

### 1. Database Interface
```python
class WatchlistDB:
    def __init__(self, database_url):
        self.db_url = database_url
        
    async def add_stock(self, symbol: str, email: str) -> dict:
        """Add stock to watchlist if not already present"""
        
    async def remove_stock(self, symbol: str, email: str) -> bool:
        """Remove stock from watchlist"""
        
    async def get_all_stocks(self) -> list:
        """Get all watched stocks"""
        
    async def update_stock_status(self, symbol: str, 
                                price: float, 
                                percentile: float) -> bool:
        """Update last check information"""
```

### 2. Email Service
```python
from resend import Resend

class AlertEmailer:
    def __init__(self, api_key: str):
        self.resend = Resend(api_key)
        
    async def send_alert(self, 
                        email: str, 
                        symbol: str, 
                        price: float, 
                        percentile: float) -> bool:
        """Send alert email when stock hits threshold"""
        return await self.resend.emails.send({
            "from": "alerts@yourdomain.com",
            "to": email,
            "subject": f"Stock Alert: {symbol}",
            "html": f"""
                <h2>Stock Alert: {symbol}</h2>
                <p>Your watched stock has hit a threshold!</p>
                <ul>
                    <li>Symbol: {symbol}</li>
                    <li>Current Price: ${price:.2f}</li>
                    <li>Current Percentile: {percentile:.1f}%</li>
                </ul>
            """
        })
```

### 3. Stock Checker
```python
async def check_watchlist(db: WatchlistDB, 
                         emailer: AlertEmailer):
    """Periodic check of watchlist stocks"""
    stocks = await db.get_all_stocks()
    
    for stock in stocks:
        try:
            # Use existing stock data function
            data = get_stock_data(stock.symbol)
            
            # Check thresholds
            if data.percentile <= 5 or data.percentile >= 95:
                await emailer.send_alert(
                    stock.email,
                    stock.symbol,
                    data.price,
                    data.percentile
                )
            
            # Update last check
            await db.update_stock_status(
                stock.symbol,
                data.price,
                data.percentile
            )
            
        except Exception as e:
            print(f"Error checking {stock.symbol}: {e}")
```

## API Routes

### Add to Watchlist
```python
@app.post("/watchlist/add")
async def add_to_watchlist():
    """Add stock to watchlist"""
    data = request.json
    try:
        await db.add_stock(
            symbol=data["symbol"].upper(),
            email=data["email"]
        )
        return {"status": "added"}
    except Exception as e:
        return {"error": str(e)}, 400
```

### Remove from Watchlist
```python
@app.post("/watchlist/remove")
async def remove_from_watchlist():
    """Remove stock from watchlist"""
    data = request.json
    success = await db.remove_stock(
        symbol=data["symbol"].upper(),
        email=data["email"]
    )
    return {"status": "removed" if success else "not found"}
```

### Get Watchlist
```python
@app.get("/watchlist")
async def get_watchlist():
    """Get all stocks in watchlist"""
    stocks = await db.get_all_stocks()
    return {"watchlist": stocks}
```

## Error Handling
- Invalid symbols return 400 error
- Database errors return 500 error
- Email sending failures are logged but don't stop processing
- Duplicate watchlist entries are ignored

## Future Improvements
- Add support for custom percentile thresholds
- Implement watchlist groups
- Add more alert conditions
- Support multiple notification channels 