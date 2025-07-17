"""
Stock service for handling stock data operations.

This service encapsulates all stock-related business logic including:
- Fetching data from Tiingo API
- Calculating technical indicators and metrics
- Caching and data management
"""

import json
import logging
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Tuple, Union

import numpy as np

import pandas as pd
import pytz

from database import DatabaseManager
from utils.config import config
from utils.rate_limiter import RateLimiter
from utils.tiingo_client import TiingoClient


class StockService:
    """Service class for stock data operations."""

    def __init__(self, db_manager: DatabaseManager) -> None:
        """
        Initialize the StockService.

        Args:
            db_manager: Database manager instance for caching operations
        """
        self.db_manager = db_manager
        self.logger = logging.getLogger("StockAlerts.StockService")
        
        # Initialize rate limiter and Tiingo client with rate limiting
        self.rate_limiter = RateLimiter(db_manager)
        self.tiingo_client = TiingoClient(self.rate_limiter)

    def get_stock_data(
        self, symbol: str, period: str
    ) -> Union[Dict[str, Any], pd.DataFrame]:
        """
        Get stock data for a given symbol and period.

        Args:
            symbol: Stock symbol (e.g., 'AAPL')
            period: Time period ('1y', '3y', '5y', 'max')

        Returns:
            Dictionary containing stock data and analysis

        Raises:
            Exception: If data fetching fails
        """
        try:
            self.logger.info(f"Fetching stock data for {symbol} ({period})")

            # Check cache first
            cache_hours = config.CACHE_HOURS
            cached_data = self.db_manager.get_fresh_cache(symbol, cache_hours)

            if cached_data:
                self.logger.info(f"Using cached data for {symbol}")
                data = json.loads(cached_data["data_json"])
                return self._filter_data_by_period(data, period)

            # Fetch from Tiingo API
            return self._fetch_from_tiingo(symbol, period)

        except Exception as e:
            self.logger.error(
                f"Error fetching stock data for {symbol}: {e}", exc_info=True
            )
            raise

    def _filter_data_by_period(
        self, data: Dict[str, Any], period: str
    ) -> Dict[str, Any]:
        """
        Filter cached data by the requested period.

        Args:
            data: Complete cached data
            period: Requested time period

        Returns:
            Filtered data dictionary
        """
        if period == "max" or "time_series" not in data:
            return data

        # Calculate cutoff date
        years = int(period[:-1])
        cutoff_date = datetime.now() - timedelta(days=years * 365)

        # Filter time series data
        time_series = data["time_series"]
        filtered_series = {
            date: series_data
            for date, series_data in time_series.items()
            if pd.to_datetime(date) >= cutoff_date
        }

        # Convert to the expected format
        dates = sorted(filtered_series.keys())
        prices = [filtered_series[date]["price"] for date in dates]
        ma_200 = [filtered_series[date]["ma_200"] for date in dates]
        pct_diff = [filtered_series[date]["pct_diff"] for date in dates]

        return {
            "dates": dates,
            "prices": prices,
            "ma_200": ma_200,
            "pct_diff": pct_diff,
            "percentiles": data["percentiles"],
            "previous_close": data.get("previous_close"),
        }

    def _fetch_from_tiingo(self, symbol: str, period: str) -> pd.DataFrame:
        """
        Fetch stock data from Tiingo API using the centralized client.

        Args:
            symbol: Stock symbol
            period: Time period

        Returns:
            Processed pandas DataFrame
        """
        data = self.tiingo_client.fetch_historical_data(symbol, period)
        if data is None:
            raise ValueError(f"No data returned for {symbol}")
        return data

    def calculate_metrics(
        self, ticker_symbol: str, period: str = "5y"
    ) -> Tuple[Dict[str, Any], int]:
        """
        Calculate stock metrics including MA and percentiles with caching and retry logic.

        Args:
            ticker_symbol: Stock ticker symbol
            period: Time period for data (1y, 3y, 5y, max)

        Returns:
            Tuple of (result_dict, status_code)
        """
        try:
            self.logger.info(
                f"Processing request for {ticker_symbol} with period {period}"
            )

            valid_periods = ["1y", "3y", "5y", "max"]
            if period not in valid_periods:
                return {
                    "error": f"Invalid period. Must be one of: {', '.join(valid_periods)}"
                }, 400

            # Check cache first (1 hour cache)
            cache_hours = config.CACHE_HOURS
            cached_data = self.db_manager.get_fresh_cache(
                ticker_symbol, max_age_hours=cache_hours
            )

            if cached_data and cached_data.get("data_json"):
                self.logger.info(f"Cache hit for {ticker_symbol}")
                try:
                    cache_data = json.loads(cached_data["data_json"])

                    # Check if we have complete time series data in cache
                    if "time_series" in cache_data and cache_data["time_series"]:
                        self.logger.info(
                            f"Using complete cached time series data for {ticker_symbol}"
                        )
                        time_series = cache_data["time_series"]

                        # Filter cached data by period
                        if period != "max":
                            years = int(period[:-1])
                            start_date = datetime.now(pytz.utc) - timedelta(
                                days=years * 365
                            )
                            # Filter time series data by date
                            filtered_series = {
                                date: data
                                for date, data in time_series.items()
                                if pd.to_datetime(date).tz_localize("UTC") >= start_date
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
                        self.logger.info(
                            f"Cached data for {ticker_symbol} missing time series, fetching fresh data"
                        )

                except (json.JSONDecodeError, KeyError) as e:
                    self.logger.warning(f"Invalid cached data for {ticker_symbol}: {e}")
                    # Continue to fetch fresh data

            # Fetch fresh data from Tiingo API
            try:
                complete_data = self._fetch_from_tiingo(
                    ticker_symbol, "max"
                )  # Always fetch max data for complete analysis

                if complete_data is None or complete_data.empty:
                    return {"error": "No data available for this ticker symbol"}, 404

            except Exception as e:
                self.logger.error(
                    f"Failed to fetch data from Tiingo for {ticker_symbol}: {e}"
                )
                return {
                    "error": "Unable to fetch stock data. Please try again later."
                }, 500

            # Calculate technical indicators
            complete_data["MA200"] = complete_data["Close"].rolling(window=200).mean()
            complete_data["pct_diff"] = (
                (complete_data["Close"] - complete_data["MA200"])
                / complete_data["MA200"]
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
                """Convert pandas series to list with NaN/inf converted to None."""
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
                    "price": (
                        float(complete_data["Close"].iloc[i])
                        if not pd.isna(complete_data["Close"].iloc[i])
                        else None
                    ),
                    "ma_200": (
                        float(complete_data["MA200"].iloc[i])
                        if not pd.isna(complete_data["MA200"].iloc[i])
                        else None
                    ),
                    "pct_diff": (
                        float(complete_data["pct_diff"].iloc[i])
                        if not pd.isna(complete_data["pct_diff"].iloc[i])
                        else None
                    ),
                }

            cache_data = {
                "price": float(current_price),
                "ma_200": (
                    float(current_ma_200) if not pd.isna(current_ma_200) else None
                ),
                "percentiles": {"p16": percentile_16th, "p84": percentile_84th},
                "previous_close": previous_close,
                "time_series": time_series_data,
                "last_updated": datetime.now().isoformat(),
            }

            # Update cache
            self.db_manager.update_stock_cache(
                symbol=ticker_symbol,
                price=float(current_price),
                ma_200=float(current_ma_200) if not pd.isna(current_ma_200) else None,
                data_json=json.dumps(cache_data),
            )

            # Add small delay to be respectful to Yahoo Finance
            time.sleep(0.5)

            self.logger.info(
                f"Successfully processed {ticker_symbol} with {len(data)} data points"
            )
            return result, 200

        except Exception as e:
            error_msg = f"Unexpected error processing {ticker_symbol}: {e}"
            self.logger.error(error_msg, exc_info=True)
            return {
                "error": "An unexpected error occurred. Please try again later."
            }, 500

    def calculate_trading_stats(
        self, ticker_symbol: str, period: str = "5y"
    ) -> Tuple[Dict[str, Any], int]:
        """
        Calculate trading intelligence statistics for a stock.

        This includes:
        - Alert frequency (how often price hits extreme levels)
        - Fear/Greed zones (days spent in different percentiles)
        - Opportunity analysis (average prices during different conditions)
        - Time analysis (duration of oversold/overbought periods)

        Args:
            ticker_symbol: Stock ticker symbol
            period: Time period for analysis (1y, 3y, 5y, max)

        Returns:
            Tuple of (stats_dict, status_code)
        """
        try:
            self.logger.info(
                f"Calculating trading stats for {ticker_symbol} with period {period}"
            )

            # Check cache first
            cache_hours = config.CACHE_HOURS
            cached_stats = self.db_manager.get_fresh_trading_stats_cache(
                ticker_symbol, period, cache_hours
            )

            if cached_stats:
                self.logger.info(
                    f"Using cached trading stats for {ticker_symbol}/{period}"
                )
                return json.loads(cached_stats["stats_json"]), 200

            # First get the stock data
            stock_data, status = self.calculate_metrics(ticker_symbol, period)
            if status != 200:
                return stock_data, status

            # Extract data for analysis
            dates = stock_data["dates"]
            prices = [p for p in stock_data["prices"] if p is not None]
            pct_diff = [p for p in stock_data["pct_diff"] if p is not None]
            percentiles = stock_data["percentiles"]

            if not prices or not pct_diff:
                return {"error": "Insufficient data for trading analysis"}, 400

            # Calculate trading intelligence metrics
            p16 = percentiles["p16"]
            p84 = percentiles["p84"]
            current_price = prices[-1] if prices else 0

            # 1. Alert Analysis - Count extreme movements
            extreme_fear_count = sum(1 for p in pct_diff if p <= p16)
            extreme_greed_count = sum(1 for p in pct_diff if p >= p84)
            total_alerts = extreme_fear_count + extreme_greed_count

            # 2. Fear/Greed Zone Analysis
            total_days = len(pct_diff)
            fear_days = extreme_fear_count
            greed_days = extreme_greed_count
            neutral_days = total_days - fear_days - greed_days

            fear_percentage = (fear_days / total_days * 100) if total_days > 0 else 0
            greed_percentage = (greed_days / total_days * 100) if total_days > 0 else 0

            # 3. Opportunity Analysis - Average prices during different conditions
            fear_prices = []
            greed_prices = []
            neutral_prices = []

            for i, p in enumerate(pct_diff):
                if i < len(prices):
                    price = prices[i]
                    if p <= p16:
                        fear_prices.append(price)
                    elif p >= p84:
                        greed_prices.append(price)
                    else:
                        neutral_prices.append(price)

            avg_fear_price = np.mean(fear_prices) if fear_prices else 0
            avg_greed_price = np.mean(greed_prices) if greed_prices else 0
            avg_neutral_price = np.mean(neutral_prices) if neutral_prices else 0

            # 4. Time Analysis - Calculate streaks
            fear_streaks = self._calculate_streaks(pct_diff, lambda x: x <= p16)
            greed_streaks = self._calculate_streaks(pct_diff, lambda x: x >= p84)

            avg_fear_duration = float(np.mean(fear_streaks)) if fear_streaks else 0.0
            avg_greed_duration = float(np.mean(greed_streaks)) if greed_streaks else 0.0
            max_fear_duration = int(max(fear_streaks)) if fear_streaks else 0
            max_greed_duration = int(max(greed_streaks)) if greed_streaks else 0

            # 5. Current Analysis
            current_pct_diff = pct_diff[-1] if pct_diff else 0
            current_zone = "neutral"
            if current_pct_diff <= p16:
                current_zone = "fear"
            elif current_pct_diff >= p84:
                current_zone = "greed"

            # 6. Opportunity Score (how good the current opportunity is)
            # Lower prices relative to fear zone average = higher opportunity
            opportunity_score = 0
            if avg_fear_price > 0:
                if current_zone == "fear":
                    # In fear zone - calculate how good this opportunity is
                    opportunity_score = int(
                        min(
                            100,
                            max(
                                0,
                                (avg_fear_price - current_price) / avg_fear_price * 100
                                + 50,
                            ),
                        )
                    )
                elif current_zone == "greed":
                    # In greed zone - selling opportunity
                    opportunity_score = int(
                        min(
                            100,
                            max(
                                0,
                                (current_price - avg_greed_price)
                                / avg_greed_price
                                * 100
                                + 50,
                            ),
                        )
                        if avg_greed_price > 0
                        else 0
                    )
                else:
                    # Neutral zone
                    opportunity_score = 50

            # Prepare results
            result = {
                "symbol": ticker_symbol,
                "period": period,
                "analysis_period": {
                    "start_date": dates[0] if dates else None,
                    "end_date": dates[-1] if dates else None,
                    "total_days": total_days,
                },
                "alert_analysis": {
                    "total_alerts": total_alerts,
                    "extreme_fear_alerts": extreme_fear_count,
                    "extreme_greed_alerts": extreme_greed_count,
                    "alert_frequency": (
                        f"{total_alerts / total_days * 100:.1f}%"
                        if total_days > 0
                        else "0%"
                    ),
                },
                "zone_analysis": {
                    "fear_zone": {
                        "days": fear_days,
                        "percentage": f"{fear_percentage:.1f}%",
                        "avg_price": (
                            round(avg_fear_price, 2) if avg_fear_price > 0 else None
                        ),
                        "avg_duration": (
                            round(avg_fear_duration, 1) if avg_fear_duration > 0 else 0
                        ),
                        "max_duration": max_fear_duration,
                    },
                    "greed_zone": {
                        "days": greed_days,
                        "percentage": f"{greed_percentage:.1f}%",
                        "avg_price": (
                            round(avg_greed_price, 2) if avg_greed_price > 0 else None
                        ),
                        "avg_duration": (
                            round(avg_greed_duration, 1)
                            if avg_greed_duration > 0
                            else 0
                        ),
                        "max_duration": max_greed_duration,
                    },
                    "neutral_zone": {
                        "days": neutral_days,
                        "percentage": f"{100 - fear_percentage - greed_percentage:.1f}%",
                        "avg_price": (
                            round(avg_neutral_price, 2)
                            if avg_neutral_price > 0
                            else None
                        ),
                    },
                },
                "current_analysis": {
                    "price": round(current_price, 2),
                    "zone": current_zone,
                    "pct_from_ma200": round(current_pct_diff, 2),
                    "opportunity_score": round(opportunity_score, 1),
                },
                "opportunity_insights": {
                    "vs_fear_avg": (
                        round(
                            (current_price - avg_fear_price) / avg_fear_price * 100, 1
                        )
                        if avg_fear_price > 0
                        else None
                    ),
                    "vs_greed_avg": (
                        round(
                            (current_price - avg_greed_price) / avg_greed_price * 100, 1
                        )
                        if avg_greed_price > 0
                        else None
                    ),
                    "vs_neutral_avg": (
                        round(
                            (current_price - avg_neutral_price)
                            / avg_neutral_price
                            * 100,
                            1,
                        )
                        if avg_neutral_price > 0
                        else None
                    ),
                },
            }

            self.logger.info(
                f"Successfully calculated trading stats for {ticker_symbol}"
            )

            # Cache the computed results
            try:
                result_json = json.dumps(result)
                self.db_manager.update_trading_stats_cache(
                    ticker_symbol, period, result_json
                )
            except Exception as cache_error:
                self.logger.warning(
                    f"Failed to cache trading stats for {ticker_symbol}/{period}: {cache_error}"
                )

            return result, 200

        except Exception as e:
            error_msg = f"Error calculating trading stats for {ticker_symbol}: {e}"
            self.logger.error(error_msg, exc_info=True)
            return {
                "error": "Failed to calculate trading statistics. Please try again later."
            }, 500

    def _calculate_streaks(self, data: List[float], condition_func: Any) -> List[int]:
        """
        Calculate consecutive streaks where condition is true.

        Args:
            data: List of values to analyze
            condition_func: Function that returns True/False for each value

        Returns:
            List of streak lengths
        """
        streaks = []
        current_streak = 0

        for value in data:
            if condition_func(value):
                current_streak += 1
            else:
                if current_streak > 0:
                    streaks.append(current_streak)
                    current_streak = 0

        # Don't forget the last streak if it ends at the data end
        if current_streak > 0:
            streaks.append(current_streak)

        return streaks

    def get_combined_data(
        self, ticker_symbol: str, period: str
    ) -> Tuple[Dict[str, Any], int]:
        """
        Get combined stock data and trading stats in a single call.

        This method eliminates the need for separate API calls by returning
        both chart data and trading intelligence in one response.
        It optimizes performance by sharing computation between stock data and trading stats.

        Args:
            ticker_symbol: Stock ticker symbol
            period: Time period ('1y', '3y', '5y', 'max')

        Returns:
            Tuple of (combined_data_dict, status_code)
        """
        try:
            # Check if we have cached trading stats first
            cache_hours = config.CACHE_HOURS
            cached_stats = self.db_manager.get_fresh_trading_stats_cache(
                ticker_symbol, period, cache_hours
            )

            # Get stock metrics
            stock_data, status_code = self.calculate_metrics(ticker_symbol, period)

            if status_code != 200:
                return stock_data, status_code

            # Use cached trading stats if available, otherwise compute
            if cached_stats:
                self.logger.info(
                    f"Using cached trading stats for combined data {ticker_symbol}/{period}"
                )
                trading_stats = json.loads(cached_stats["stats_json"])
            else:
                # Compute trading stats using the same stock data we already have
                trading_stats, stats_status_code = (
                    self._compute_trading_stats_from_stock_data(
                        ticker_symbol, period, stock_data
                    )
                )

                if stats_status_code != 200:
                    return trading_stats, stats_status_code

                # Cache the computed stats
                try:
                    result_json = json.dumps(trading_stats)
                    self.db_manager.update_trading_stats_cache(
                        ticker_symbol, period, result_json
                    )
                except Exception as cache_error:
                    self.logger.warning(
                        f"Failed to cache trading stats for {ticker_symbol}/{period}: {cache_error}"
                    )

            # Combine both datasets
            combined_data = {"stock_data": stock_data, "trading_stats": trading_stats}

            return combined_data, 200

        except Exception as e:
            self.logger.error(
                f"Error getting combined data for {ticker_symbol}/{period}: {e}",
                exc_info=True,
            )
            return {"error": "Failed to get combined data"}, 500

    def _compute_trading_stats_from_stock_data(
        self, ticker_symbol: str, period: str, stock_data: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], int]:
        """
        Compute trading stats from already-processed stock data.

        This method avoids duplicate data processing by reusing the stock data
        that was already computed for the charts.

        Args:
            ticker_symbol: Stock ticker symbol
            period: Time period
            stock_data: Already-processed stock data dictionary

        Returns:
            Tuple of (stats_dict, status_code)
        """
        try:
            # Extract data from the already-processed stock data
            prices = [p for p in stock_data["prices"] if p is not None]
            pct_diff = [p for p in stock_data["pct_diff"] if p is not None]
            percentiles = stock_data["percentiles"]

            if not prices or not pct_diff:
                return {"error": "Insufficient data for trading analysis"}, 400

            # Calculate trading intelligence metrics
            p16 = percentiles["p16"]
            p84 = percentiles["p84"]
            current_price = prices[-1] if prices else 0

            # 1. Alert Analysis - Count extreme movements
            extreme_fear_count = sum(1 for p in pct_diff if p <= p16)
            extreme_greed_count = sum(1 for p in pct_diff if p >= p84)
            total_alerts = extreme_fear_count + extreme_greed_count

            # 2. Fear/Greed Zone Analysis
            total_days = len(pct_diff)
            fear_days = extreme_fear_count
            greed_days = extreme_greed_count
            neutral_days = total_days - fear_days - greed_days

            fear_percentage = (fear_days / total_days * 100) if total_days > 0 else 0
            greed_percentage = (greed_days / total_days * 100) if total_days > 0 else 0

            # 3. Average Prices in Different Zones
            fear_prices = []
            greed_prices = []
            neutral_prices = []

            for i, p in enumerate(pct_diff):
                if i < len(prices):
                    price = prices[i]
                    if p <= p16:
                        fear_prices.append(price)
                    elif p >= p84:
                        greed_prices.append(price)
                    else:
                        neutral_prices.append(price)

            avg_fear_price = np.mean(fear_prices) if fear_prices else 0
            avg_greed_price = np.mean(greed_prices) if greed_prices else 0
            avg_neutral_price = np.mean(neutral_prices) if neutral_prices else 0

            # 4. Streak Analysis
            fear_streaks = self._calculate_streaks(pct_diff, lambda x: x <= p16)
            greed_streaks = self._calculate_streaks(pct_diff, lambda x: x >= p84)

            max_fear_streak = int(max(fear_streaks)) if fear_streaks else 0
            max_greed_streak = int(max(greed_streaks)) if greed_streaks else 0
            avg_fear_streak = float(np.mean(fear_streaks)) if fear_streaks else 0.0
            avg_greed_streak = float(np.mean(greed_streaks)) if greed_streaks else 0.0

            # 5. Build the result
            result = {
                "alert_analysis": {
                    "total_alerts": total_alerts,
                    "fear_alerts": extreme_fear_count,
                    "greed_alerts": extreme_greed_count,
                },
                "zone_analysis": {
                    "fear_zone": {
                        "days": fear_days,
                        "percentage": f"{fear_percentage:.1f}%",
                        "avg_price": round(avg_fear_price, 2),
                    },
                    "greed_zone": {
                        "days": greed_days,
                        "percentage": f"{greed_percentage:.1f}%",
                        "avg_price": round(avg_greed_price, 2),
                    },
                    "neutral_zone": {
                        "days": neutral_days,
                        "percentage": f"{100 - fear_percentage - greed_percentage:.1f}%",
                        "avg_price": round(avg_neutral_price, 2),
                    },
                },
                "streak_analysis": {
                    "fear_streaks": {
                        "max": max_fear_streak,
                        "avg": round(avg_fear_streak, 1),
                        "count": len(fear_streaks),
                    },
                    "greed_streaks": {
                        "max": max_greed_streak,
                        "avg": round(avg_greed_streak, 1),
                        "count": len(greed_streaks),
                    },
                },
                "current_analysis": {
                    "price": current_price,
                    "pct_diff": pct_diff[-1] if pct_diff else 0,
                    "percentile_16": p16,
                    "percentile_84": p84,
                },
                "opportunity_insights": {
                    "vs_fear_avg": (
                        round(
                            (current_price - avg_fear_price) / avg_fear_price * 100, 1
                        )
                        if avg_fear_price > 0
                        else None
                    ),
                    "vs_greed_avg": (
                        round(
                            (current_price - avg_greed_price) / avg_greed_price * 100, 1
                        )
                        if avg_greed_price > 0
                        else None
                    ),
                    "vs_neutral_avg": (
                        round(
                            (current_price - avg_neutral_price)
                            / avg_neutral_price
                            * 100,
                            1,
                        )
                        if avg_neutral_price > 0
                        else None
                    ),
                },
            }

            return result, 200

        except Exception as e:
            self.logger.error(
                f"Error computing trading stats from stock data for {ticker_symbol}/{period}: {e}",
                exc_info=True,
            )
            return {"error": "Failed to compute trading statistics"}, 500
