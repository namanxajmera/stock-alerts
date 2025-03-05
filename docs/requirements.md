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
  - /settings - View and update alert preferences
  - /thresholds <ticker> <low> <high> - Set custom thresholds for a stock
- Clear, user-friendly responses
- Error handling with informative messages

### 3.2 Periodic Analysis
- Run based on user preferences (default: every Sunday)
- Check each stock in users' watchlists
- Analyze if stock hit user-defined percentile thresholds
- Send alerts for significant movements via Telegram
- Update user's last notification time and alert history

### 3.3 Data Storage
- Use SQLite database for data persistence
- Store user preferences, watchlists, and alert history
- Implement proper indexing for common queries
- Handle data validation and consistency with constraints
- Provide a robust data access layer

## 4. Technical Implementation

### 4.1 Backend (app.py)
- Flask server with routes:
  - GET /: Serves the main page
  - GET /data/<ticker>/<period>: Returns JSON stock data
  - POST /webhook: Telegram webhook endpoint
- Telegram bot integration
- CORS support for cross-origin requests
- Custom JSON encoder for handling NaN/Infinity values
- Colored console logging for debugging

### 4.2 Frontend (HTML/CSS/JS)
- index.html: Basic structure and Plotly.js integration
- style.css: Minimal styling for modern look
- main.js: Handle user input and chart rendering

### 4.3 Bot Handler (bot_handler.py)
- Implement command handlers
- Process incoming messages
- Interact with the database to manage user preferences and watchlists
- Send notifications

### 4.4 Database Manager (db_manager.py)
- Define database schema and migrations
- Provide methods for CRUD operations on users, watchlists, and alerts
- Handle database connection and error cases
- Implement efficient querying with indexing

### 4.5 Periodic Checker (weekly_checker.py)
- Query the database for active users and their watchlists
- Fetch and analyze stock data based on user preferences
- Send alerts via the Telegram bot for significant movements
- Update user's last notification time and alert history

### 4.6 Data Flow
1. Website:
   - User enters stock ticker and selects period
   - JavaScript makes API call to Flask backend
   - Backend fetches and processes stock data
   - Frontend renders both charts
2. Alert System:
   - User interacts with bot via commands
   - Bot handler updates user preferences and watchlists in the database
   - Periodic checker analyzes stocks and sends alerts
   - Bot sends notifications for significant movements

### 4.7 Implementation Steps

#### [X] Step 1: Database Setup (1-2 hours)
1. Design the database schema
2. Create SQLite database and tables
3. Implement database migration scripts
4. Test database connectivity and queries

#### [X] Step 2: Frontend Implementation (2-3 hours)
1. Set up basic UI structure
2. Implement chart rendering
3. Add user interactions
4. Style components

#### [X] Step 3: Telegram Bot Setup (2-3 hours)
1. Create bot via BotFather
2. Implement command handlers
3. Set up webhook
4. Test basic interactions

#### Step 4: Backend Integration (3-4 hours)
1. Implement Flask routes and request handling
2. Integrate Telegram bot with the backend
3. Implement database access layer
4. Test end-to-end flow

#### Step 5: Periodic Checker (2-3 hours)
1. Implement the periodic checker logic
2. Query the database for active users and watchlists
3. Analyze stock data and send alerts
4. Update user notification history

#### Step 6: Testing & Deployment (2-3 hours)
1. Perform comprehensive testing of all components
2. Handle edge cases and error scenarios
3. Optimize database queries and indexing
4. Deploy the application to a production environment

Total Estimated Time: 12-18 hours

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
- SQL query errors
- Constraint violations
- Migration failures

## 6. Future Improvements
(To be considered after basic implementation)
- Additional technical indicators
- More interactive features
- Enhanced styling
- Mobile responsiveness
- Multiple watchlists per user
- Advanced analytics commands
- Inline keyboard menus
- Scheduled reports
- Multi-language support
- Redis caching for performance
- Request queue for multiple connections
- Multi-stock comparison
- Ticker symbol search
- Web interface for watchlist management 