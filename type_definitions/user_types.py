"""
Type definitions for user-related data structures.

This module contains all type definitions related to users, watchlists,
alerts, and user management functionality.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, TypedDict, Union


class User(TypedDict):
    """User data structure."""

    id: str  # Telegram user ID as string
    name: str
    joined_at: datetime
    max_stocks: int
    notification_enabled: bool
    last_notified: Optional[datetime]


class UserProfile(TypedDict):
    """Extended user profile information."""

    id: str
    name: str
    username: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    joined_at: datetime
    max_stocks: int
    notification_enabled: bool
    last_notified: Optional[datetime]
    total_alerts_sent: int
    total_watchlist_items: int


class NotificationSettings(TypedDict):
    """User notification preferences."""

    enabled: bool
    last_notified: Optional[datetime]
    frequency_limit: int  # Minutes between notifications
    alert_types: List[str]  # Types of alerts to receive


class WatchlistItem(TypedDict):
    """Watchlist item data structure."""

    user_id: str
    symbol: str
    added_at: datetime
    alert_threshold_low: Optional[float]
    alert_threshold_high: Optional[float]


class AlertHistory(TypedDict):
    """Alert history data structure."""

    id: int
    user_id: str
    symbol: str
    price: float
    percentile: float
    status: str  # 'sent', 'failed', 'pending'
    error_message: Optional[str]
    sent_at: datetime


class WatchlistItemWithPrice(TypedDict):
    """Watchlist item with current price information."""

    symbol: str
    alert_threshold_low: Optional[float]
    alert_threshold_high: Optional[float]
    last_price: Optional[float]
    ma_200: Optional[float]


class UserStats(TypedDict):
    """User statistics."""

    total_users: int
    active_users: int
    total_watchlist_items: int
    total_alerts_sent: int
    most_watched_stocks: List[Dict[str, Union[str, int]]]


class AlertSummary(TypedDict):
    """Alert summary for user."""

    total_alerts: int
    successful_alerts: int
    failed_alerts: int
    recent_alerts: List[AlertHistory]


# Type aliases for commonly used types
UserId = str
UserName = str
TelegramUserId = int
UserDict = Dict[str, Any]
WatchlistDict = Dict[str, Any]
AlertDict = Dict[str, Any]

# Database row types
UserRow = Dict[str, Any]
WatchlistItemRow = Dict[str, Any]
AlertHistoryRow = Dict[str, Any]
UserStatsRow = Dict[str, Any]
