"""Admin routes for database management and manual operations."""
import logging
from typing import Tuple, Union
from flask import Blueprint, request, jsonify, current_app, Response

logger = logging.getLogger("StockAlerts.Admin")

admin_bp = Blueprint('admin', __name__)

# Legacy authentication functions removed - now handled by AuthService

@admin_bp.route("/admin", methods=["GET"])
def admin_panel() -> Union[str, Tuple[str, int]]:
    """Admin panel endpoint with authentication."""
    # Get auth service from app context  
    auth_service = getattr(current_app, 'auth_service', None)
    if auth_service is None:
        return "<h1>Error</h1><p>Authentication service not available</p>", 500
    
    # Apply authentication using the service
    @auth_service.require_admin_auth  # type: ignore
    def _admin_panel() -> Union[str, Tuple[str, int]]:
        admin_service = getattr(current_app, 'admin_service', None)
        if admin_service is None:
            return "<h1>Error</h1><p>Admin service not available</p>", 500
        
        try:
            # Get admin data using the service
            admin_data = admin_service.get_admin_data()
            
            # Generate HTML using the service
            html = admin_service.generate_admin_panel_html(admin_data)
            
            return html  # type: ignore
        except Exception as e:
            logger.error(f"Admin panel error: {e}", exc_info=True)
            return f"<h1>Error</h1><p>{e}</p>", 500
    
    return _admin_panel()  # type: ignore


@admin_bp.route("/admin/check", methods=["POST"])
def trigger_stock_check() -> Tuple[Response, int]:
    """Endpoint to manually trigger stock checking (secured with API key)."""
    # Get auth service from app context
    auth_service = getattr(current_app, 'auth_service', None)
    if auth_service is None:
        return jsonify({"status": "error", "message": "Authentication service not available"}), 500
    
    # Validate API key
    api_key = request.headers.get('X-API-Key')
    is_valid, error_msg = auth_service.validate_admin_api_key(api_key)
    if not is_valid:
        return jsonify({"status": "error", "message": error_msg}), 401 if error_msg == "Unauthorized" else 503
    
    try:
        admin_service = getattr(current_app, 'admin_service', None)
        if admin_service is None:
            return jsonify({"status": "error", "message": "Admin service not available"}), 500
        
        # Use AdminService to trigger the stock check
        admin_service.trigger_stock_check()
        
        return jsonify({"status": "success", "message": "Stock check completed"}), 200
        
    except Exception as e:
        logger.error(f"Error in stock check: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500