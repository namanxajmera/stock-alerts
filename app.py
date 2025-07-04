import os
import atexit
from typing import Tuple, Any
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(".env")


def setup_directories() -> None:
    """Create necessary directories if they don't exist."""
    os.makedirs("logs", exist_ok=True)
    os.makedirs("db", exist_ok=True)
    os.makedirs("static/js", exist_ok=True)


setup_directories()

from flask import (
    Flask,
    render_template,
    send_from_directory,
)
from flask_cors import CORS
from db_manager import DatabaseManager
from webhook_handler import WebhookHandler
import logging
import mimetypes

# Import utilities
from utils.json_encoder import CustomJSONEncoder
from utils.scheduler import setup_scheduler
from utils.config import config

# Import route blueprints
from routes.api_routes import api_bp
from routes.webhook_routes import webhook_bp
from routes.admin_routes import admin_bp
from routes.health_routes import health_bp

# Import services
from services import StockService, AuthService, AdminService


def setup_logging() -> Any:
    """Configure logging for the application."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler("logs/stock_alerts.log"),
            logging.StreamHandler(),
        ],
    )
    return logging.getLogger("StockAlerts.App")


logger = setup_logging()
mimetypes.add_type("application/javascript", ".js")


# Create Flask app first so gunicorn can always find it
app = Flask(__name__)
app.json_encoder = CustomJSONEncoder  # type: ignore
CORS(app)

# Initialize other components
db_manager = None
webhook_handler = None
stock_service = None
auth_service = None
admin_service = None

logger.info("Starting application initialization...")

# Log configuration summary (without sensitive values)
config_summary = config.get_config_summary()
logger.info(f"Configuration loaded: {config_summary}")

logger.info("Initializing database manager...")
db_manager = DatabaseManager(config.DATABASE_URL)

# Register cleanup function for database connection pool
atexit.register(lambda: db_manager.close_pool() if db_manager else None)
logger.info("Database manager initialized successfully with connection pooling")

logger.info("Initializing webhook handler...")
webhook_handler = WebhookHandler(
    db_manager,
    config.TELEGRAM_BOT_TOKEN,
    config.TELEGRAM_WEBHOOK_SECRET,
)
logger.info("Webhook handler initialized successfully")

logger.info("Initializing service layer...")
stock_service = StockService(db_manager)
auth_service = AuthService()
admin_service = AdminService(db_manager)
logger.info("Service layer initialized successfully")

logger.info("Application initialization completed successfully")

# Store components in app context for blueprints to access
app.db_manager = db_manager  # type: ignore
app.webhook_handler = webhook_handler  # type: ignore
app.stock_service = stock_service  # type: ignore
app.auth_service = auth_service  # type: ignore
app.admin_service = admin_service  # type: ignore

# Setup scheduler
scheduler = setup_scheduler()

# Register blueprints
app.register_blueprint(api_bp)
app.register_blueprint(webhook_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(health_bp)


@app.route("/")
def index() -> str:
    return render_template("index.html")


@app.route("/static/js/<path:filename>")
def serve_js(filename: str) -> Any:
    return send_from_directory("static/js", filename, mimetype="application/javascript")


@app.errorhandler(404)
def not_found(error: Any) -> Tuple[Any, int]:
    from flask import jsonify
    return jsonify({"error": "Not Found"}), 404


@app.errorhandler(500)
def server_error(error: Any) -> Tuple[Any, int]:
    from flask import jsonify
    logger.error(f"Server Error: {error}", exc_info=True)
    return jsonify({"error": "Internal Server Error"}), 500


@app.errorhandler(403)
def forbidden(error: Any) -> Tuple[Any, int]:
    from flask import jsonify
    return jsonify({"error": "Forbidden"}), 403


if __name__ == "__main__":
    try:
        logger.info(f"Starting Stock Analytics Dashboard server on port {config.PORT}...")
        logger.info("Flask app routes registered successfully")
        app.run(debug=config.DEBUG, host="0.0.0.0", port=config.PORT)
    except Exception as e:
        logger.critical(f"Failed to start server: {e}", exc_info=True)
        import traceback
        traceback.print_exc()
        raise