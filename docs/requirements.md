# Stock Analytics Dashboard - Simple Requirements

## 1. Data Requirements

### 1.1 Stock Data
- Use Yahoo Finance API (yfinance) to fetch historical daily data
- Required data points:
  - Daily closing prices
  - Trading volume (optional display)
- Fetch complete history for the stock

### 1.2 Calculations
Sequence of calculations:
1. Calculate 200-day moving average (MA) from closing prices
2. Calculate absolute difference: (Closing Price - 200-day MA)
3. Calculate percent difference: ((Closing Price - 200-day MA) / 200-day MA) * 100
4. Calculate percentile bands:
   - 5th percentile of percent differences
   - 95th percentile of percent differences

## 2. Frontend Requirements

### 2.1 User Interface
- Single page web application
- Clean, minimal design
- Stock ticker input field
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
- Flask server with two routes:
  - GET /: Serves the main page
  - GET /data/<ticker>: Returns JSON stock data

### 3.2 Frontend (HTML/CSS/JS)
- index.html: Basic structure and Plotly.js integration
- style.css: Minimal styling for modern look
- main.js: Handle user input and chart rendering

### 3.3 Data Flow
1. User enters stock ticker
2. JavaScript makes API call to Flask backend
3. Backend fetches and processes stock data
4. Frontend renders both charts

## 4. Error Handling

### 4.1 Basic Error Cases
- Invalid ticker symbols
- No data available
- Network errors

## 5. Future Improvements
(To be considered after basic implementation)
- Additional technical indicators
- More interactive features
- Enhanced styling
- Mobile responsiveness 