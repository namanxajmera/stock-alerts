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

## 3. Technical Implementation

### 3.1 Backend (app.py)
- Flask server with routes:
  - GET /: Serves the main page
  - GET /data/<ticker>/<period>: Returns JSON stock data
  - POST /watchlist/add: Add stock to watchlist
  - POST /watchlist/remove: Remove from watchlist
  - GET /watchlist: Get watchlist items
- CORS support for cross-origin requests
- Custom JSON encoder for handling NaN/Infinity values
- Colored console logging for debugging

### 3.2 Frontend (HTML/CSS/JS)
- index.html: Basic structure and Plotly.js integration
- style.css: Minimal styling for modern look
- main.js: Handle user input and chart rendering

### 3.3 Data Flow
1. User enters stock ticker and selects period
2. JavaScript makes API call to Flask backend
3. Backend fetches and processes stock data
4. Frontend renders both charts
5. Periodic checker runs hourly for watchlist alerts

### 3.4 Implementation Steps

#### Step 1: Database Setup (1-2 hours)
1. Create Supabase account and project
2. Set up database connection
3. Create watchlist table
4. Test connection from Flask

#### Step 2: Watchlist API (2-3 hours)
1. Create WatchlistDB class
2. Implement CRUD operations
3. Add API endpoints
4. Test with Postman/curl

#### Step 3: Email Integration (1-2 hours)
1. Create Resend.com account
2. Set up AlertEmailer class
3. Create email template
4. Test email sending

#### Step 4: Alert Checker (2-3 hours)
1. Create check_watchlist function
2. Set up periodic task scheduler
3. Implement alert logic
4. Test full alert flow

#### Step 5: UI Integration (2-3 hours)
1. Add watchlist section to UI
2. Create add/remove forms
3. Display current watchlist
4. Add loading states

#### Step 6: Testing & Deploy (1-2 hours)
1. Test all components
2. Add error handling
3. Deploy updates
4. Monitor initial alerts

Total Estimated Time: 9-15 hours

## 4. Error Handling

### 4.1 Basic Error Cases
- Invalid ticker symbols
- Invalid period selection
- No data available
- Network errors
- NaN/Infinity value handling

## 5. Future Improvements
(To be considered after basic implementation)
- Additional technical indicators
- More interactive features
- Enhanced styling
- Mobile responsiveness
- Redis caching for performance
- Request queue for multiple connections
- Multi-stock comparison
- Ticker symbol search 