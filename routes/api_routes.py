"""API routes for stock data endpoints."""
import logging
from typing import Any
from flask import Blueprint, jsonify, current_app
from utils.validators import validate_ticker_symbol

logger = logging.getLogger("StockAlerts.API")

api_bp = Blueprint('api', __name__)

# Legacy functions removed - now handled by StockService

@api_bp.route("/data/<ticker>/<period>")
def get_stock_data(ticker: str, period: str) -> Any:
    """Get stock data for a specific ticker and period."""
    logger.info(f"Request for ticker: {ticker}, period: {period}")
    
    # Validate ticker symbol
    is_valid, validated_ticker = validate_ticker_symbol(ticker)
    if not is_valid:
        return jsonify({"error": validated_ticker}), 400
    
    # Get stock service from app context
    stock_service = getattr(current_app, 'stock_service', None)
    if stock_service is None:
        return jsonify({"error": "Stock service not available"}), 500
    
    result, status_code = stock_service.calculate_metrics(validated_ticker, period)
    return jsonify(result), status_code