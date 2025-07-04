"""
Admin service for handling admin panel operations.

This service provides admin-related functionality including:
- Admin panel data retrieval
- Database queries for admin operations
- HTML generation for admin interface
"""

import logging
from typing import Dict, Any, List, Optional

import psycopg2.extras


class AdminService:
    """Service class for admin operations."""
    
    def __init__(self, db_manager: Any) -> None:
        """
        Initialize the AdminService.
        
        Args:
            db_manager: Database manager instance for database operations
        """
        self.db_manager = db_manager
        self.logger = logging.getLogger("StockAlerts.AdminService")
        
    def get_admin_data(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Retrieve all admin panel data from the database.
        
        Returns:
            Dictionary containing users, watchlist, alerts, cache, and config data
            
        Raises:
            Exception: If database operations fail
        """
        try:
            with self.db_manager._get_connection() as conn:
                cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

                # Users
                cursor.execute("SELECT * FROM users")
                users = cursor.fetchall()

                # Watchlist items
                cursor.execute("SELECT * FROM watchlist_items ORDER BY user_id, symbol")
                watchlist = cursor.fetchall()

                # Alert history (last 50)
                cursor.execute("SELECT * FROM alert_history ORDER BY sent_at DESC LIMIT 50")
                alerts = cursor.fetchall()

                # Stock cache
                cursor.execute("SELECT * FROM stock_cache ORDER BY last_check DESC")
                cache = cursor.fetchall()

                # Config (filter out sensitive data)
                cursor.execute("SELECT * FROM config WHERE key != 'telegram_token'")
                config = cursor.fetchall()

                return {
                    "users": users,
                    "watchlist": watchlist,
                    "alerts": alerts,
                    "cache": cache,
                    "config": config
                }
                
        except Exception as e:
            self.logger.error(f"Error retrieving admin data: {e}", exc_info=True)
            raise
            
    def generate_admin_panel_html(self, data: Dict[str, List[Dict[str, Any]]]) -> str:
        """
        Generate HTML for the admin panel.
        
        Args:
            data: Dictionary containing admin data from get_admin_data()
            
        Returns:
            HTML string for the admin panel
        """
        users = data["users"]
        watchlist = data["watchlist"]
        alerts = data["alerts"]
        cache = data["cache"]
        config = data["config"]
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Admin Panel</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
                h2 {{ color: #333; cursor: pointer; user-select: none; }}
                h2:hover {{ background-color: #f5f5f5; }}
                .count {{ color: #666; font-size: 14px; }}
                .section {{ border: 1px solid #ddd; margin: 10px 0; }}
                .section-header {{ background-color: #f8f9fa; padding: 10px; }}
                .section-content {{ padding: 10px; display: block; }}
                .collapsed {{ display: none; }}
                .toggle {{ font-size: 18px; margin-right: 10px; }}
            </style>
            <script>
                function toggleSection(id) {{
                    const content = document.getElementById(id);
                    const toggle = document.getElementById(id + '-toggle');
                    if (content.classList.contains('collapsed')) {{
                        content.classList.remove('collapsed');
                        toggle.textContent = '▼';
                    }} else {{
                        content.classList.add('collapsed');
                        toggle.textContent = '▶';
                    }}
                }}
            </script>
        </head>
        <body>
            <h1>Database Admin Panel</h1>

            <div class="section">
                <div class="section-header" onclick="toggleSection('users')">
                    <span id="users-toggle" class="toggle">▼</span>
                    <strong>Users</strong> <span class="count">({len(users)} total)</span>
                </div>
                <div id="users" class="section-content">
                    <table>
                        <tr><th>ID</th><th>Name</th><th>Joined</th><th>Max Stocks</th><th>Notifications</th></tr>
                        {''.join([f"<tr><td>{u['id']}</td><td>{u['name']}</td><td>{u['joined_at']}</td><td>{u['max_stocks']}</td><td>{'✓' if u['notification_enabled'] else '✗'}</td></tr>" for u in users])}
                    </table>
                </div>
            </div>

            <div class="section">
                <div class="section-header" onclick="toggleSection('watchlist')">
                    <span id="watchlist-toggle" class="toggle">▼</span>
                    <strong>Watchlist Items</strong> <span class="count">({len(watchlist)} total)</span>
                </div>
                <div id="watchlist" class="section-content">
                    <table>
                        <tr><th>User ID</th><th>Symbol</th><th>Added</th><th>Low Threshold</th><th>High Threshold</th></tr>
                        {''.join([f"<tr><td>{w['user_id']}</td><td>{w['symbol']}</td><td>{w['added_at']}</td><td>{w['alert_threshold_low']}</td><td>{w['alert_threshold_high']}</td></tr>" for w in watchlist])}
                    </table>
                </div>
            </div>

            <div class="section">
                <div class="section-header" onclick="toggleSection('alerts')">
                    <span id="alerts-toggle" class="toggle">▼</span>
                    <strong>Alert History</strong> <span class="count">({len(alerts)} recent)</span>
                </div>
                <div id="alerts" class="section-content">
                    <table>
                        <tr><th>User ID</th><th>Symbol</th><th>Price</th><th>Percentile</th><th>Status</th><th>Sent At</th></tr>
                        {''.join([f"<tr><td>{a['user_id']}</td><td>{a['symbol']}</td><td>${a['price']:.2f}</td><td>{a['percentile']:.1f}%</td><td>{a['status']}</td><td>{a['sent_at']}</td></tr>" for a in alerts])}
                    </table>
                </div>
            </div>

            <div class="section">
                <div class="section-header" onclick="toggleSection('cache')">
                    <span id="cache-toggle" class="toggle">▼</span>
                    <strong>Stock Cache</strong> <span class="count">({len(cache)} cached)</span>
                </div>
                <div id="cache" class="section-content">
                    <table>
                        <tr><th>Symbol</th><th>Last Price</th><th>MA200</th><th>Last Check</th></tr>
                        {''.join([f"<tr><td>{c['symbol']}</td><td>{'${:.2f}'.format(c['last_price']) if c['last_price'] else 'N/A'}</td><td>{'${:.2f}'.format(c['ma_200']) if c['ma_200'] else 'N/A'}</td><td>{c['last_check']}</td></tr>" for c in cache])}
                    </table>
                </div>
            </div>

            <div class="section">
                <div class="section-header" onclick="toggleSection('config')">
                    <span id="config-toggle" class="toggle">▼</span>
                    <strong>Configuration</strong> <span class="count">({len(config)} settings)</span>
                </div>
                <div id="config" class="section-content">
                    <table>
                        <tr><th>Key</th><th>Value</th><th>Description</th></tr>
                        {''.join([f"<tr><td>{cfg['key']}</td><td>{cfg['value']}</td><td>{cfg['description'] or ''}</td></tr>" for cfg in config])}
                    </table>
                </div>
            </div>
        </body>
        </html>
        """
        
        return html
    
    def trigger_stock_check(self) -> None:
        """
        Trigger a manual stock check operation.
        
        Raises:
            Exception: If stock check fails
        """
        try:
            self.logger.info("Stock check triggered manually via AdminService")
            
            # Import and run the periodic checker
            from periodic_checker import PeriodicChecker
            
            checker = PeriodicChecker()
            checker.check_watchlists()
            
            self.logger.info("Stock check completed successfully")
            
        except Exception as e:
            self.logger.error(f"Error in stock check: {e}", exc_info=True)
            raise