"""Health check routes for monitoring application status."""
import logging
from flask import Blueprint, jsonify, current_app

logger = logging.getLogger("StockAlerts.Health")

health_bp = Blueprint('health', __name__)


@health_bp.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint for monitoring application status."""
    try:
        logger.info("Health check endpoint called")
        
        # Get database manager from app context
        db_manager = getattr(current_app, 'db_manager', None)
        
        if db_manager is None:
            logger.error("Health check failed: Database manager not initialized")
            return jsonify({"status": "unhealthy", "error": "Database manager not initialized"}), 500
        
        db_manager.get_config("telegram_token")
        logger.info("Health check database test passed")
        return jsonify({"status": "healthy"}), 200
    except Exception as e:
        logger.error(f"Health check failed: {e}", exc_info=True)
        return jsonify({"status": "unhealthy", "error": str(e)}), 500