"""
Type definitions for API-related data structures.

This module contains all type definitions related to API requests, responses,
Telegram webhook handling, and external service integrations.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, TypedDict, Union


class APIResponse(TypedDict):
    """Base API response structure."""

    status: str
    message: Optional[str]
    data: Optional[Any]


class ErrorResponse(TypedDict):
    """Error response structure."""

    error: str
    details: Optional[str]
    code: Optional[int]


class SuccessResponse(TypedDict):
    """Success response structure."""

    status: str
    message: str
    data: Optional[Any]


class StockDataRequest(TypedDict):
    """Stock data request parameters."""

    symbol: str
    period: str  # '1y', '3y', '5y', 'max'


class StockDataResponse(TypedDict):
    """Stock data API response."""

    dates: List[str]
    prices: List[Optional[float]]
    ma_200: List[Optional[float]]
    pct_diff: List[Optional[float]]
    percentiles: Dict[str, float]
    previous_close: Optional[float]


class HealthCheckResponse(TypedDict):
    """Health check response structure."""

    status: str
    timestamp: str
    services: Dict[str, str]
    error: Optional[str]


class TelegramUser(TypedDict):
    """Telegram user data structure."""

    id: int
    is_bot: bool
    first_name: str
    last_name: Optional[str]
    username: Optional[str]
    language_code: Optional[str]


class TelegramChat(TypedDict):
    """Telegram chat data structure."""

    id: int
    type: str
    title: Optional[str]
    username: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]


class TelegramMessage(TypedDict):
    """Telegram message data structure."""

    message_id: int
    from_user: TelegramUser  # 'from' is a reserved keyword
    chat: TelegramChat
    date: int
    text: Optional[str]
    entities: Optional[List[Dict[str, Any]]]


class WebhookUpdate(TypedDict):
    """Telegram webhook update structure."""

    update_id: int
    message: Optional[TelegramMessage]
    edited_message: Optional[TelegramMessage]
    channel_post: Optional[TelegramMessage]
    edited_channel_post: Optional[TelegramMessage]


class TelegramSendMessagePayload(TypedDict):
    """Telegram send message API payload."""

    chat_id: Union[int, str]
    text: str
    parse_mode: Optional[str]
    disable_web_page_preview: Optional[bool]
    disable_notification: Optional[bool]
    reply_to_message_id: Optional[int]


class TelegramAPIResponse(TypedDict):
    """Telegram API response structure."""

    ok: bool
    result: Optional[Any]
    description: Optional[str]
    error_code: Optional[int]


class AdminPanelData(TypedDict):
    """Admin panel data structure."""

    users: List[Dict[str, Any]]
    watchlist: List[Dict[str, Any]]
    alerts: List[Dict[str, Any]]
    cache: List[Dict[str, Any]]
    config: List[Dict[str, Any]]


class LogEntry(TypedDict):
    """Log entry structure."""

    timestamp: datetime
    log_type: str
    message: str
    user_id: Optional[str]
    symbol: Optional[str]


class DatabaseConfig(TypedDict):
    """Database configuration."""

    key: str
    value: str
    description: Optional[str]
    created_at: datetime
    updated_at: datetime


class ValidationResult(TypedDict):
    """Validation result structure."""

    is_valid: bool
    message: str
    validated_value: Optional[str]


class AlertContext(TypedDict):
    """Alert context information."""

    user_id: str
    symbol: str
    current_price: float
    current_pct_diff: float
    percentile_16: float
    percentile_84: float
    trigger_type: str


class CacheHit(TypedDict):
    """Cache hit information."""

    symbol: str
    last_check: datetime
    data_age_hours: float
    is_fresh: bool


class APIError(TypedDict):
    """API error details."""

    error_type: str
    error_code: Optional[int]
    error_message: str
    timestamp: datetime
    endpoint: Optional[str]


class RateLimitInfo(TypedDict):
    """Rate limit information."""

    limit: int
    remaining: int
    reset_time: datetime
    window_seconds: int


class ExternalAPIConfig(TypedDict):
    """External API configuration."""

    service_name: str
    api_key: str
    base_url: str
    timeout_seconds: int
    max_retries: int


# Type aliases for commonly used types
HTTPStatusCode = int
HTTPMethod = str
RequestHeaders = Dict[str, str]
RequestParams = Dict[str, Union[str, int, float, bool]]
ResponseData = Dict[str, Any]
JSONData = Dict[str, Any]
APIKey = str
SecretToken = str

# Flask-specific types
FlaskResponse = Tuple[Union[str, Dict[str, Any]], int]
FlaskRequest = Any  # flask.Request type
FlaskHeaders = Dict[str, str]
