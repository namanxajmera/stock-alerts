# Stock Analytics Dashboard - Simple Requirements

## 1. Data Requirements

### 1.1 Stock Data
- Use Yahoo Finance API (yfinance) to fetch historical daily data
- Required data points:
  - Daily closing prices
  - Trading volume (optional display)
- Support multiple time periods (1y, 3y, 5y, max)
- Fetch complete history for calculations
- Filter data based on selected period

### 1.2 Calculations
Sequence of calculations:
1. Calculate 200-day moving average (MA) from closing prices
2. Calculate absolute difference: (Closing Price - 200-day MA)
3. Calculate percent difference: ((Closing Price - 200-day MA) / 200-day MA) * 100
4. Calculate percentile bands:
   - 5th percentile of percent differences
   - 95th percentile of percent differences
5. Handle NaN/Infinity values in calculations

## 2. Frontend Requirements

### 2.1 User Interface
- Single page web application
- Clean, minimal design
- Stock ticker input field
- Period selection dropdown (1y, 3y, 5y, max)
- Two charts stacked vertically

### 2.2 Charts
- Main Chart:
  - Line plot of daily closing prices
  - Overlay of 200-day moving average
  - Basic tooltips on hover
- Sub Chart:
  - Line plot of percent difference from MA
  - Horizontal lines for percentile bands
  - Synchronized with main chart

## 3. Alert System Requirements

### 3.1 Telegram Bot Interface
- Command-based interaction
- Support for the following commands:
  - /start - Initialize bot and show help
  - /add <ticker> - Add stock to watchlist
  - /remove <ticker> - Remove stock from watchlist
  - /list - Show current watchlist
  - /help - Display available commands
- Clear, user-friendly responses
- Error handling with informative messages

### 3.2 Weekly Analysis
- Run every Sunday
- Check each stock in users' watchlists
- Analyze if stock hit 5th or 95th percentile in the last week
- Send alerts for significant movements via Telegram

## 4. Technical Implementation

### 4.1 Backend (app.py)
- Flask server with routes:
  - GET /: Serves the main page
  - GET /data/<ticker>/<period>: Returns JSON stock data
  - POST /watchlist/add: Add stock to watchlist
  - POST /watchlist/remove: Remove from watchlist
  - GET /watchlist: Get watchlist items
  - POST /webhook: Telegram webhook endpoint
- Telegram bot integration
- CORS support for cross-origin requests
- Custom JSON encoder for handling NaN/Infinity values
- Colored console logging for debugging

### 4.2 Frontend (HTML/CSS/JS)
- index.html: Basic structure and Plotly.js integration
- style.css: Minimal styling for modern look
- main.js: Handle user input and chart rendering

### 4.3 Bot Handler
- Implement command handlers
- Process incoming messages
- Manage user watchlists
- Send notifications

### 4.4 Data Flow
1. Website:
   - User enters stock ticker and selects period
   - JavaScript makes API call to Flask backend
   - Backend fetches and processes stock data
   - Frontend renders both charts
2. Alert System:
   - User interacts with bot via commands
   - Backend processes commands and updates watchlist
   - Weekly scheduler triggers analysis
   - Bot sends alerts for significant movements

### 4.5 Implementation Steps

#### Step 1: Database Setup (1-2 hours)
1. Create Supabase account and project
2. Set up database connection
3. Create watchlist table with user_id field
4. Test connection from Flask

#### Step 2: Frontend Implementation (2-3 hours)
1. Set up basic UI structure
2. Implement chart rendering
3. Add user interactions
4. Style components

#### Step 3: Telegram Bot Setup (2-3 hours)
1. Create bot via BotFather
2. Implement command handlers
3. Set up webhook
4. Test basic interactions

#### Step 4: Watchlist Management (2-3 hours)
1. Create WatchlistDB class
2. Implement CRUD operations
3. Add API endpoints and command handlers
4. Test with real users

#### Step 5: Weekly Analysis (2-3 hours)
1. Create analysis function
2. Set up weekly scheduler
3. Implement alert logic
4. Test notification flow

#### Step 6: Testing & Deploy (1-2 hours)
1. Test all components
2. Add error handling
3. Deploy updates
4. Monitor initial alerts

Total Estimated Time: 10-16 hours

## 5. Error Handling

### 5.1 Basic Error Cases
- Invalid ticker symbols
- Invalid period selection
- No data available
- Invalid commands
- Network errors
- NaN/Infinity value handling
- Rate limiting
- Database connection issues

## 6. Future Improvements
(To be considered after basic implementation)
- Additional technical indicators
- More interactive features
- Enhanced styling
- Mobile responsiveness
- Custom alert thresholds
- Multiple watchlists per user
- Advanced analytics commands
- Inline keyboard menus
- Scheduled reports
- Multi-language support
- Redis caching for performance
- Request queue for multiple connections
- Multi-stock comparison
- Ticker symbol search 