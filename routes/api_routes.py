"""API routes for stock data endpoints."""

import logging
from typing import Any

from flask import Blueprint, current_app, jsonify, request

from utils.rate_limiter import UserRateLimiter
from utils.validators import ValidationError, validate_period, validate_ticker_symbol

logger = logging.getLogger("StockAlerts.API")

api_bp = Blueprint("api", __name__)

# Legacy functions removed - now handled by StockService


@api_bp.route("/data/<ticker>/<period>")
def get_stock_data(ticker: str, period: str) -> Any:
    """
    Get complete stock data and trading stats for a specific ticker and period.

    This endpoint now combines chart data and trading intelligence to reduce API calls.

    Args:
        ticker: Stock ticker symbol (e.g., AAPL, TSLA)
        period: Time period (1y, 3y, 5y, max)

    Returns:
        JSON response with combined stock data and trading stats or error message
    """
    # Log request with client info for security monitoring
    client_ip = request.environ.get("HTTP_X_FORWARDED_FOR", request.remote_addr)
    logger.info(
        f"Combined stock data request from {client_ip}: ticker={ticker}, period={period}"
    )

    stock_service = getattr(current_app, "stock_service", None)
    if not stock_service:
        logger.error("Stock service not available")
        return jsonify({"error": "Stock service not available"}), 500

    user_rate_limiter = UserRateLimiter(stock_service.db_manager)
    if client_ip:
        can_proceed, rate_limit_reason = user_rate_limiter.can_user_make_request(client_ip)
    else:
        can_proceed, rate_limit_reason = False, "Could not determine client IP"
    
    if not can_proceed:
        logger.warning(f"Rate limit exceeded for {client_ip}: {rate_limit_reason}")
        return jsonify({"error": rate_limit_reason}), 429
    
    # Record the user request
    if client_ip:
        user_rate_limiter.record_user_request(client_ip, f"/data/{ticker}/{period}")

    try:
        # Validate ticker symbol with enhanced security checks
        is_valid_ticker, validated_ticker = validate_ticker_symbol(ticker)
        if not is_valid_ticker:
            logger.warning(
                f"Invalid ticker from {client_ip}: {ticker} - {validated_ticker}"
            )
            return jsonify({"error": f"Invalid ticker symbol: {validated_ticker}"}), 400

        # Validate period parameter
        is_valid_period, validated_period = validate_period(period)
        if not is_valid_period:
            logger.warning(
                f"Invalid period from {client_ip}: {period} - {validated_period}"
            )
            return jsonify({"error": f"Invalid period: {validated_period}"}), 400

        # Get stock service from app context
        stock_service = getattr(current_app, "stock_service", None)
        if stock_service is None:
            logger.error("Stock service not available")
            return jsonify({"error": "Stock service not available"}), 500

        # Get combined data (chart + trading stats)
        result, status_code = stock_service.get_combined_data(
            validated_ticker, validated_period
        )

        # Log successful request
        if status_code == 200:
            logger.info(
                f"Successful combined data request for {validated_ticker}/{validated_period} from {client_ip}"
            )
        else:
            logger.warning(
                f"Stock service error for {validated_ticker}/{validated_period}: {result.get('error', 'Unknown error')}"
            )

        return jsonify(result), status_code

    except ValidationError as e:
        logger.warning(f"Validation error from {client_ip}: {e.message}")
        return jsonify({"error": f"Validation error: {e.message}"}), 400
    except Exception as e:
        logger.error(
            f"Unexpected error processing request from {client_ip}: {e}", exc_info=True
        )
        return jsonify({"error": "Internal server error"}), 500


# Removed redundant /trading-stats endpoint - functionality now integrated into /data endpoint


@api_bp.route("/api-usage")
def get_api_usage() -> Any:
    """
    Get API usage statistics for monitoring rate limits.
    
    Returns:
        JSON response with current API usage statistics
    """
    try:
        # Get rate limiter instance
        stock_service = getattr(current_app, "stock_service", None)
        if stock_service is None:
            return jsonify({"error": "Stock service not available"}), 500
            
        rate_limiter = stock_service.rate_limiter
        
        # Get usage statistics
        usage_stats = rate_limiter.get_usage_stats("tiingo")
        
        return jsonify({
            "status": "success",
            "tiingo_api_usage": usage_stats,
            "limits": {
                "hourly_limit": 50,
                "daily_limit": 1000,
                "safe_hourly_limit": 48,
                "safe_daily_limit": 980
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting API usage stats: {e}", exc_info=True)
        return jsonify({"error": "Failed to get usage statistics"}), 500
