"""Admin routes for database management and manual operations."""

import logging
from typing import Any, Tuple, Union

from flask import Blueprint, Response, current_app, jsonify, render_template, request

from utils.validators import ValidationError, validate_api_key

logger = logging.getLogger("StockAlerts.Admin")

admin_bp = Blueprint("admin", __name__)

# Legacy authentication functions removed - now handled by AuthService


@admin_bp.route("/admin", methods=["GET"])
def admin_panel() -> Any:
    """Admin panel endpoint with authentication."""
    # Get auth service from app context
    auth_service = getattr(current_app, "auth_service", None)
    if auth_service is None:
        return "<h1>Error</h1><p>Authentication service not available</p>", 500

    # Check authentication
    auth_result = auth_service.check_admin_auth()
    if auth_result is not True:
        return auth_result  # Return the authentication error response

    admin_service = getattr(current_app, "admin_service", None)
    if admin_service is None:
        return "<h1>Error</h1><p>Admin service not available</p>", 500

    try:
        # Get admin data using the service
        admin_data = admin_service.get_admin_data()

        # Render template with admin data (secure HTML escaping)
        return render_template("admin.html", **admin_data)

    except Exception as e:
        logger.error(f"Admin panel error: {e}", exc_info=True)
        return f"<h1>Error</h1><p>{e}</p>", 500


@admin_bp.route("/admin/check", methods=["POST"])
def trigger_stock_check() -> Tuple[Response, int]:
    """
    Endpoint to manually trigger stock checking with enhanced validation.

    Requires valid API key authentication and additional security checks.
    """
    # Log admin access attempt for security monitoring
    client_ip = request.environ.get("HTTP_X_FORWARDED_FOR", request.remote_addr)
    logger.info(f"Admin stock check request from {client_ip}")

    try:
        # Get auth service from app context
        auth_service = getattr(current_app, "auth_service", None)
        if auth_service is None:
            logger.error("Authentication service not available for admin endpoint")
            return (
                jsonify(
                    {
                        "status": "error",
                        "message": "Authentication service not available",
                    }
                ),
                500,
            )

        # Enhanced API key validation
        api_key = request.headers.get("X-API-Key")
        if not api_key:
            logger.warning(
                f"Admin endpoint access attempt without API key from {client_ip}"
            )
            return jsonify({"status": "error", "message": "API key required"}), 401

        # Validate API key format first
        is_valid_format, validated_key = validate_api_key(api_key)
        if not is_valid_format:
            logger.warning(f"Invalid API key format from {client_ip}: {validated_key}")
            return (
                jsonify({"status": "error", "message": "Invalid API key format"}),
                401,
            )

        # Validate API key against configured value
        is_valid_auth, error_msg = auth_service.validate_admin_api_key(validated_key)
        if not is_valid_auth:
            logger.warning(f"Invalid API key from {client_ip}: {error_msg}")
            return jsonify({"status": "error", "message": error_msg}), (
                401 if error_msg == "Unauthorized" else 503
            )

        # Get admin service
        admin_service = getattr(current_app, "admin_service", None)
        if admin_service is None:
            logger.error("Admin service not available")
            return (
                jsonify({"status": "error", "message": "Admin service not available"}),
                500,
            )

        # Execute stock check with proper logging
        logger.info(f"Executing manual stock check triggered by {client_ip}")
        admin_service.trigger_stock_check()
        logger.info(f"Manual stock check completed successfully for {client_ip}")

        return (
            jsonify(
                {
                    "status": "success",
                    "message": "Stock check completed successfully",
                    "timestamp": "now",  # Could add actual timestamp
                }
            ),
            200,
        )

    except ValidationError as e:
        logger.warning(
            f"Validation error in admin endpoint from {client_ip}: {e.message}"
        )
        return (
            jsonify({"status": "error", "message": f"Validation error: {e.message}"}),
            400,
        )
    except Exception as e:
        logger.error(
            f"Unexpected error in admin stock check from {client_ip}: {e}",
            exc_info=True,
        )
        return jsonify({"status": "error", "message": "Internal server error"}), 500
