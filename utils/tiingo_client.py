"""
Centralized Tiingo API client for stock data fetching.

This module provides a unified interface for fetching stock data from the Tiingo API,
centralizing request handling, retry logic, and error handling.
"""

import logging
import random
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import pandas as pd
import requests
from requests.exceptions import ConnectionError, HTTPError, RequestException, Timeout

from utils.config import config

logger = logging.getLogger("StockAlerts.TiingoClient")


class TiingoClient:
    """Centralized client for Tiingo API operations."""

    def __init__(self) -> None:
        """Initialize the Tiingo client."""
        self.logger = logging.getLogger("StockAlerts.TiingoClient")
        self.api_token = config.TIINGO_API_TOKEN

        if not self.api_token:
            raise ValueError("TIINGO_API_TOKEN not configured")

    def fetch_historical_data(
        self, symbol: str, period: str = "2y", max_retries: int = 3
    ) -> Optional[pd.DataFrame]:
        """
        Fetch historical stock data from Tiingo API.

        Args:
            symbol: Stock symbol (e.g., 'AAPL')
            period: Time period ('1y', '2y', '3y', '5y', 'max')
            max_retries: Maximum number of retry attempts

        Returns:
            DataFrame with historical stock data or None if failed
        """
        # Calculate date range
        end_date = datetime.now()
        if period == "1y":
            start_date = end_date - timedelta(days=365)
        elif period == "2y":
            start_date = end_date - timedelta(days=730)
        elif period == "3y":
            start_date = end_date - timedelta(days=1095)
        elif period == "5y":
            start_date = end_date - timedelta(days=1825)
        else:  # max
            start_date = end_date - timedelta(days=3650)  # 10 years max

        # Build API request
        url = f"https://api.tiingo.com/tiingo/daily/{symbol}/prices"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Token {self.api_token}",
        }
        params = {
            "startDate": start_date.strftime("%Y-%m-%d"),
            "endDate": end_date.strftime("%Y-%m-%d"),
        }

        # Retry logic with exponential backoff
        for attempt in range(max_retries):
            try:
                self.logger.info(
                    f"Fetching Tiingo data for {symbol} (attempt {attempt + 1}/{max_retries})"
                )

                response = requests.get(url, headers=headers, params=params, timeout=30)
                response.raise_for_status()

                data = response.json()

                if not data:
                    self.logger.warning(f"No data available for {symbol}")
                    return None

                # Process the data
                return self._process_tiingo_data(symbol, data)

            except HTTPError as e:
                if e.response.status_code == 429:
                    # Rate limit exceeded
                    self.logger.warning(
                        f"Rate limit exceeded for {symbol}, attempt {attempt + 1}/{max_retries}"
                    )
                    if attempt < max_retries - 1:
                        backoff_time = (2**attempt) + random.uniform(0, 1)
                        self.logger.info(f"Backing off for {backoff_time:.2f} seconds")
                        time.sleep(backoff_time)
                        continue
                elif e.response.status_code == 404:
                    self.logger.error(f"Symbol {symbol} not found in Tiingo")
                    return None
                elif e.response.status_code >= 500:
                    # Server error, retry
                    self.logger.warning(
                        f"Server error for {symbol}: {e.response.status_code}, attempt {attempt + 1}/{max_retries}"
                    )
                    if attempt < max_retries - 1:
                        backoff_time = (2**attempt) + random.uniform(0, 1)
                        self.logger.info(f"Backing off for {backoff_time:.2f} seconds")
                        time.sleep(backoff_time)
                        continue
                else:
                    # Client error, don't retry
                    self.logger.error(
                        f"Client error for {symbol}: {e.response.status_code} - {e}"
                    )
                    return None

            except (ConnectionError, Timeout) as e:
                self.logger.warning(
                    f"Network error for {symbol}: {e}, attempt {attempt + 1}/{max_retries}"
                )
                if attempt < max_retries - 1:
                    backoff_time = (2**attempt) + random.uniform(0, 1)
                    self.logger.info(f"Backing off for {backoff_time:.2f} seconds")
                    time.sleep(backoff_time)
                    continue

            except RequestException as e:
                self.logger.error(f"Request exception for {symbol}: {e}")
                return None

            except Exception as e:
                self.logger.error(f"Unexpected error fetching data for {symbol}: {e}")
                return None

        self.logger.error(
            f"Failed to fetch data for {symbol} after {max_retries} attempts"
        )
        return None

    def _process_tiingo_data(
        self, symbol: str, tiingo_data: List[Dict[str, Any]]
    ) -> pd.DataFrame:
        """
        Process raw Tiingo API data into a standardized pandas DataFrame.

        Args:
            symbol: Stock symbol
            tiingo_data: Raw data from Tiingo API

        Returns:
            Processed pandas DataFrame with standardized columns
        """
        if not tiingo_data:
            raise ValueError(f"No data received for {symbol}")

        # Convert to DataFrame
        df = pd.DataFrame(tiingo_data)

        # Ensure we have the required columns
        required_columns = ["date", "adjClose"]
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            # Check for alternative column names
            if "close" in df.columns:
                df["adjClose"] = df["close"]
            else:
                raise ValueError(f"Missing required columns: {missing_columns}")

        # Standardize column names
        column_mapping = {
            "date": "Date",
            "adjClose": "Close",
            "open": "Open",
            "high": "High",
            "low": "Low",
            "volume": "Volume",
        }

        # Select and rename available columns
        available_columns = {k: v for k, v in column_mapping.items() if k in df.columns}
        df_processed = df[list(available_columns.keys())].rename(
            columns=available_columns
        )

        # Convert date to datetime and set as index
        df_processed["Date"] = pd.to_datetime(df_processed["Date"])
        df_processed.set_index("Date", inplace=True)

        # Sort by date (oldest first)
        df_processed.sort_index(inplace=True)

        # Ensure we have Close column
        if "Close" not in df_processed.columns:
            raise ValueError("Close price data not available")

        self.logger.info(f"Processed {len(df_processed)} data points for {symbol}")
        return df_processed
