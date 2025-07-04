"""
Stock service for handling stock data operations.

This service encapsulates all stock-related business logic including:
- Fetching data from Tiingo API
- Calculating technical indicators and metrics
- Caching and data management
"""

import os
import json
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Tuple, Optional, List

import pandas as pd
import numpy as np
import pytz
import requests


class StockService:
    """Service class for stock data operations."""
    
    def __init__(self, db_manager: Any = None) -> None:
        """
        Initialize the StockService.
        
        Args:
            db_manager: Database manager instance for caching operations
        """
        self.db_manager = db_manager
        self.logger = logging.getLogger("StockAlerts.StockService")
        
    def fetch_tiingo_data(self, ticker_symbol: str) -> Optional[pd.DataFrame]:
        """
        Fetch data from Tiingo API using direct REST calls.
        
        Args:
            ticker_symbol: Stock ticker symbol to fetch data for
            
        Returns:
            DataFrame with Date index and Close prices, or None if no data
            
        Raises:
            ValueError: If API token is not configured
            Exception: If API request fails
        """
        try:
            # Get API token from environment
            api_token = os.getenv("TIINGO_API_TOKEN")
            if not api_token:
                raise ValueError("TIINGO_API_TOKEN not found in environment variables")

            self.logger.info(f"Fetching Tiingo data for {ticker_symbol}")

            # Calculate start date for maximum historical data (30+ years available)
            end_date = datetime.now()
            start_date = end_date - timedelta(days=30 * 365)  # 30 years ago

            # Build the REST API URL as per Tiingo docs
            url = f"https://api.tiingo.com/tiingo/daily/{ticker_symbol}/prices"

            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Token {api_token}",
            }

            params = {
                "startDate": start_date.strftime("%Y-%m-%d"),
                "endDate": end_date.strftime("%Y-%m-%d"),
            }

            self.logger.info(
                f"Making request to: {url} with dates {params['startDate']} to {params['endDate']}"
            )

            # Make the API request
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()

            data = response.json()

            if not data:
                self.logger.warning(f"No data returned from Tiingo for {ticker_symbol}")
                return None

            # Convert JSON response to DataFrame
            df = pd.DataFrame(data)

            # Convert Tiingo format to match expected format
            # Tiingo returns: date, close, high, low, open, volume, adjClose, adjHigh, adjLow, adjOpen, adjVolume, divCash, splitFactor
            # Use adjusted prices which incorporate split and dividend adjustments per CRSP methodology

            # Use split-adjusted prices for accurate historical charts
            column_mapping = {
                "date": "Date",
                "adjClose": "Close",
            }

            # Select and rename only the columns we need
            df_filtered = df[list(column_mapping.keys())].rename(columns=column_mapping)

            # Convert date string to datetime and set as index
            df_filtered["Date"] = pd.to_datetime(df_filtered["Date"])
            df_filtered.set_index("Date", inplace=True)

            # Sort by date (oldest first)
            df_filtered = df_filtered.sort_index()

            self.logger.info(
                f"Successfully fetched {len(df_filtered)} data points for {ticker_symbol} from Tiingo"
            )
            return df_filtered

        except Exception as e:
            self.logger.error(f"Error fetching data from Tiingo for {ticker_symbol}: {e}")
            raise

    def calculate_metrics(self, ticker_symbol: str, period: str = "5y") -> Tuple[Dict[str, Any], int]:
        """
        Calculate stock metrics including MA and percentiles with caching and retry logic.
        
        Args:
            ticker_symbol: Stock ticker symbol
            period: Time period for data (1y, 3y, 5y, max)
            
        Returns:
            Tuple of (result_dict, status_code)
        """
        try:
            self.logger.info(f"Processing request for {ticker_symbol} with period {period}")

            valid_periods = ["1y", "3y", "5y", "max"]
            if period not in valid_periods:
                return {
                    "error": f"Invalid period. Must be one of: {', '.join(valid_periods)}"
                }, 400

            # Check if database manager is available
            if self.db_manager is None:
                self.logger.warning("Database manager not available, skipping cache")
                cached_data = None
            else:
                # Check cache first (1 hour cache)
                cache_hours = int(os.getenv("CACHE_HOURS", 1))
                cached_data = self.db_manager.get_fresh_cache(
                    ticker_symbol, max_age_hours=cache_hours
                )

            if cached_data and cached_data.get("data_json"):
                self.logger.info(f"Cache hit for {ticker_symbol}")
                try:
                    cache_data = json.loads(cached_data["data_json"])
                    
                    # Check if we have complete time series data in cache
                    if "time_series" in cache_data and cache_data["time_series"]:
                        self.logger.info(f"Using complete cached time series data for {ticker_symbol}")
                        time_series = cache_data["time_series"]
                        
                        # Filter cached data by period
                        if period != "max":
                            years = int(period[:-1])
                            start_date = datetime.now(pytz.utc) - timedelta(days=years * 365)
                            # Filter time series data by date
                            filtered_series = {
                                date: data for date, data in time_series.items()
                                if pd.to_datetime(date).tz_localize('UTC') >= start_date
                            }
                        else:
                            filtered_series = time_series
                        
                        # Convert back to the expected format
                        dates = sorted(filtered_series.keys())
                        prices = [filtered_series[date]["price"] for date in dates]
                        ma_200 = [filtered_series[date]["ma_200"] for date in dates]
                        pct_diff = [filtered_series[date]["pct_diff"] for date in dates]
                        
                        result = {
                            "dates": dates,
                            "prices": prices,
                            "ma_200": ma_200,
                            "pct_diff": pct_diff,
                            "percentiles": cache_data["percentiles"],
                            "previous_close": cache_data.get("previous_close"),
                        }
                        
                        return result, 200
                    else:
                        self.logger.info(f"Cached data for {ticker_symbol} missing time series, fetching fresh data")
                        
                except (json.JSONDecodeError, KeyError) as e:
                    self.logger.warning(f"Invalid cached data for {ticker_symbol}: {e}")
                    # Continue to fetch fresh data

            # Fetch fresh data from Tiingo API
            try:
                complete_data = self.fetch_tiingo_data(ticker_symbol)

                if complete_data is None or complete_data.empty:
                    return {"error": "No data available for this ticker symbol"}, 404

            except Exception as e:
                self.logger.error(f"Failed to fetch data from Tiingo for {ticker_symbol}: {e}")
                return {"error": "Unable to fetch stock data. Please try again later."}, 500

            # Calculate technical indicators
            complete_data["MA200"] = complete_data["Close"].rolling(window=200).mean()
            complete_data["pct_diff"] = (
                (complete_data["Close"] - complete_data["MA200"]) / complete_data["MA200"]
            ) * 100

            valid_pct_diff = complete_data["pct_diff"].dropna()
            if len(valid_pct_diff) < 20:
                return {
                    "error": "Insufficient data for meaningful analysis (need at least 20 data points)"
                }, 400

            percentile_16th = np.percentile(valid_pct_diff, 16)
            percentile_84th = np.percentile(valid_pct_diff, 84)

            previous_close = (
                complete_data["Close"].iloc[-2] if len(complete_data) >= 2 else None
            )
            current_price = complete_data["Close"].iloc[-1]
            current_ma_200 = complete_data["MA200"].iloc[-1]

            # Filter data by period
            if period != "max":
                years = int(period[:-1])
                start_date = datetime.now(pytz.utc) - timedelta(days=years * 365)
                # Ensure index is timezone-aware for comparison
                if complete_data.index.tz is None:
                    complete_data.index = complete_data.index.tz_localize("UTC")
                data = complete_data[complete_data.index >= start_date]
            else:
                data = complete_data

            # Prepare result - convert NaN to None for valid JSON
            def clean_for_json(series: Any) -> List[Any]:
                """Convert pandas series to list with NaN/inf converted to None"""
                # Replace inf/-inf with NaN, then convert to list and replace NaN with None
                cleaned = series.replace([np.inf, -np.inf], np.nan)
                result = cleaned.tolist()
                # Replace any remaining NaN values with None for valid JSON
                return [None if pd.isna(x) else x for x in result]

            result = {
                "dates": data.index.strftime("%Y-%m-%d").tolist(),
                "prices": clean_for_json(data["Close"]),
                "ma_200": clean_for_json(data["MA200"]),
                "pct_diff": clean_for_json(data["pct_diff"]),
                "percentiles": {"p16": percentile_16th, "p84": percentile_84th},
                "previous_close": previous_close,
            }

            # Update cache with fresh data including complete time series
            time_series_data = {}
            for i, date in enumerate(complete_data.index):
                time_series_data[date.strftime("%Y-%m-%d")] = {
                    "price": float(complete_data["Close"].iloc[i]) if not pd.isna(complete_data["Close"].iloc[i]) else None,
                    "ma_200": float(complete_data["MA200"].iloc[i]) if not pd.isna(complete_data["MA200"].iloc[i]) else None,
                    "pct_diff": float(complete_data["pct_diff"].iloc[i]) if not pd.isna(complete_data["pct_diff"].iloc[i]) else None,
                }
            
            cache_data = {
                "price": float(current_price),
                "ma_200": float(current_ma_200) if not pd.isna(current_ma_200) else None,
                "percentiles": {"p16": percentile_16th, "p84": percentile_84th},
                "previous_close": previous_close,
                "time_series": time_series_data,
                "last_updated": datetime.now().isoformat(),
            }

            # Update cache if database manager is available
            if self.db_manager is not None:
                self.db_manager.update_stock_cache(
                    symbol=ticker_symbol,
                    price=float(current_price),
                    ma_200=float(current_ma_200) if not pd.isna(current_ma_200) else None,
                    data_json=json.dumps(cache_data),
                )
            else:
                self.logger.warning(f"Skipping cache update for {ticker_symbol} - database not available")

            # Add small delay to be respectful to Yahoo Finance
            time.sleep(0.5)

            self.logger.info(
                f"Successfully processed {ticker_symbol} with {len(data)} data points"
            )
            return result, 200

        except Exception as e:
            error_msg = f"Unexpected error processing {ticker_symbol}: {e}"
            self.logger.error(error_msg, exc_info=True)
            return {"error": "An unexpected error occurred. Please try again later."}, 500