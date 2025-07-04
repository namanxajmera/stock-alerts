"""
Type definitions for the Stock Alerts application.

This module provides comprehensive type definitions for all major components
of the stock alerts system, including database models, API responses, and
business logic data structures.
"""

from .stock_types import (
    StockData,
    StockMetrics,
    PercentileData,
    StockCache,
    TiingoResponse,
    StockPricePoint,
    HistoricalData,
    MovingAverage,
    AlertTrigger,
)

from .user_types import (
    User,
    WatchlistItem,
    AlertHistory,
    UserProfile,
    NotificationSettings,
)

from .api_types import (
    APIResponse,
    ErrorResponse,
    SuccessResponse,
    WebhookUpdate,
    TelegramMessage,
    TelegramUser,
    StockDataRequest,
    StockDataResponse,
    HealthCheckResponse,
    AdminPanelData,
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