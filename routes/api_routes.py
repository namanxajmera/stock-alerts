"""API routes for stock data endpoints."""

import logging
from typing import Any

from flask import Blueprint, current_app, jsonify, request

from utils.validators import ValidationError, validate_period, validate_ticker_symbol

logger = logging.getLogger("StockAlerts.API")

api_bp = Blueprint("api", __name__)

# Legacy functions removed - now handled by StockService


@api_bp.route("/data/<ticker>/<period>")
def get_stock_data(ticker: str, period: str) -> Any:
    """
    Get stock data for a specific ticker and period with enhanced validation.

    Args:
        ticker: Stock ticker symbol (e.g., AAPL, TSLA)
        period: Time period (1y, 3y, 5y, max)

    Returns:
        JSON response with stock data or error message
    """
    # Log request with client info for security monitoring
    client_ip = request.environ.get("HTTP_X_FORWARDED_FOR", request.remote_addr)
    logger.info(
        f"Stock data request from {client_ip}: ticker={ticker}, period={period}"
    )

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

        # Process request with validated inputs
        result, status_code = stock_service.calculate_metrics(
            validated_ticker, validated_period
        )

        # Log successful request
        if status_code == 200:
            logger.info(
                f"Successful data request for {validated_ticker}/{validated_period} from {client_ip}"
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


@api_bp.route("/trading-stats/<ticker>/<period>")
def get_trading_stats(ticker: str, period: str) -> Any:
    """
    Get trading intelligence stats for a specific ticker and period.

    Returns historical alert patterns, fear/greed metrics, and opportunity analysis.

    Args:
        ticker: Stock ticker symbol (e.g., AAPL, TSLA)
        period: Time period (1y, 3y, 5y, max)

    Returns:
        JSON response with trading intelligence data or error message
    """
    # Log request with client info
    client_ip = request.environ.get("HTTP_X_FORWARDED_FOR", request.remote_addr)
    logger.info(
        f"Trading stats request from {client_ip}: ticker={ticker}, period={period}"
    )

    try:
        # Validate inputs using same validation logic
        is_valid_ticker, validated_ticker = validate_ticker_symbol(ticker)
        if not is_valid_ticker:
            logger.warning(
                f"Invalid ticker from {client_ip}: {ticker} - {validated_ticker}"
            )
            return jsonify({"error": f"Invalid ticker symbol: {validated_ticker}"}), 400

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

        # Calculate trading intelligence stats
        result, status_code = stock_service.calculate_trading_stats(
            validated_ticker, validated_period
        )

        # Log result
        if status_code == 200:
            logger.info(
                f"Successful trading stats for {validated_ticker}/{validated_period} from {client_ip}"
            )
        else:
            logger.warning(
                f"Trading stats error for {validated_ticker}/{validated_period}: {result.get('error', 'Unknown error')}"
            )

        return jsonify(result), status_code

    except ValidationError as e:
        logger.warning(f"Validation error from {client_ip}: {e.message}")
        return jsonify({"error": f"Validation error: {e.message}"}), 400
    except Exception as e:
        logger.error(
            f"Unexpected error processing trading stats from {client_ip}: {e}",
            exc_info=True,
        )
        return jsonify({"error": "Internal server error"}), 500
