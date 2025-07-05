"""
Type definitions for the Stock Alerts application.

This module provides comprehensive type definitions for all major components
of the stock alerts system, including database models, API responses, and
business logic data structures.
"""

from .api_types import (
    AdminPanelData,
    APIResponse,
    ErrorResponse,
    HealthCheckResponse,
    StockDataRequest,
    StockDataResponse,
    SuccessResponse,
    TelegramMessage,
    TelegramUser,
    WebhookUpdate,
)
from .stock_types import (
    AlertTrigger,
    HistoricalData,
    MovingAverage,
    PercentileData,
    StockCache,
    StockData,
    StockMetrics,
    StockPricePoint,
    TiingoResponse,
)
from .user_types import (
    AlertHistory,
    NotificationSettings,
    User,
    UserProfile,
    WatchlistItem,
)

__all__ = [
    # Stock types
    "StockData",
    "StockMetrics",
    "PercentileData",
    "StockCache",
    "TiingoResponse",
    "StockPricePoint",
    "HistoricalData",
    "MovingAverage",
    "AlertTrigger",
    # User types
    "User",
    "WatchlistItem",
    "AlertHistory",
    "UserProfile",
    "NotificationSettings",
    # API types
    "APIResponse",
    "ErrorResponse",
    "SuccessResponse",
    "WebhookUpdate",
    "TelegramMessage",
    "TelegramUser",
    "StockDataRequest",
    "StockDataResponse",
    "HealthCheckResponse",
    "AdminPanelData",
]
