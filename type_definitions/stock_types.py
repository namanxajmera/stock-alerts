"""
Type definitions for stock-related data structures.

This module contains all type definitions related to stock data, metrics,
and financial calculations used throughout the application.
"""

from typing import Dict, List, Optional, Union, Any, TypedDict, Tuple
from datetime import datetime
from decimal import Decimal
import pandas as pd


class StockPricePoint(TypedDict):
    """Individual stock price data point."""
    date: str
    price: float
    volume: Optional[int]


class PercentileData(TypedDict):
    """Percentile data for stock price analysis."""
    p16: float  # 16th percentile
    p84: float  # 84th percentile
    
    
class MovingAverage(TypedDict):
    """Moving average data."""
    ma_200: Optional[float]
    ma_50: Optional[float]
    ma_20: Optional[float]


class StockMetrics(TypedDict):
    """Comprehensive stock metrics."""
    current_price: float
    previous_close: Optional[float]
    ma_200: Optional[float]
    pct_diff: Optional[float]  # Percentage difference from MA200
    percentiles: PercentileData
    historical_min: Optional[float]
    historical_max: Optional[float]


class StockData(TypedDict):
    """Complete stock data structure."""
    symbol: str
    dates: List[str]
    prices: List[Optional[float]]
    ma_200: List[Optional[float]]
    pct_diff: List[Optional[float]]
    percentiles: PercentileData
    previous_close: Optional[float]


class TiingoResponse(TypedDict):
    """Response structure from Tiingo API."""
    date: str
    close: float
    high: float
    low: float
    open: float
    volume: int
    adjClose: float
    adjHigh: float
    adjLow: float
    adjOpen: float
    adjVolume: int
    divCash: float
    splitFactor: float


class StockCache(TypedDict):
    """Cached stock data structure."""
    symbol: str
    last_check: datetime
    last_price: Optional[float]
    ma_200: Optional[float]
    data_json: str
    
    
class TimeSeriesData(TypedDict):
    """Time series data point for caching."""
    price: Optional[float]
    ma_200: Optional[float]
    pct_diff: Optional[float]


class CacheData(TypedDict):
    """Complete cache data structure."""
    price: float
    ma_200: Optional[float]
    percentiles: PercentileData
    previous_close: Optional[float]
    time_series: Dict[str, TimeSeriesData]
    last_updated: str


class HistoricalData(TypedDict):
    """Historical stock data structure."""
    dates: List[str]
    prices: List[float]
    volumes: List[int]
    
    
class AlertTrigger(TypedDict):
    """Alert trigger data structure."""
    symbol: str
    current_price: float
    current_pct_diff: float
    percentile_16: float
    percentile_84: float
    trigger_type: str  # 'low' or 'high'
    

# Type aliases for commonly used types
StockSymbol = str
Price = Union[float, Decimal]
Percentage = float
DataFrameType = pd.DataFrame
OptionalPrice = Optional[Price]
OptionalPercentage = Optional[Percentage]

# Database row types
StockCacheRow = Dict[str, Any]
WatchlistRow = Dict[str, Any]
AlertHistoryRow = Dict[str, Any]