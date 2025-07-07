-- Add position tracking to watchlist items
-- This allows users to mark stocks as "owned" vs "watched"

-- Add is_owned column to watchlist_items table
ALTER TABLE watchlist_items ADD COLUMN is_owned BOOLEAN DEFAULT FALSE;

-- Add index for position queries
CREATE INDEX idx_watchlist_owned ON watchlist_items(user_id, is_owned);

-- Update the active_watchlists view to include ownership status
DROP VIEW IF EXISTS active_watchlists;
CREATE VIEW active_watchlists AS
SELECT 
    w.user_id,
    u.name as user_name,
    w.symbol,
    w.is_owned,
    w.alert_threshold_low,
    w.alert_threshold_high,
    w.last_alerted_at,
    sc.last_price,
    sc.ma_200
FROM watchlist_items w
JOIN users u ON w.user_id = u.id
LEFT JOIN stock_cache sc ON w.symbol = sc.symbol
WHERE u.notification_enabled = TRUE;

-- Add configuration for position tracking
INSERT INTO config (key, value, description) VALUES
    ('position_tracking_enabled', 'true', 'Enable position vs watchlist tracking'),
    ('show_position_alerts_first', 'true', 'Show owned positions first in alert batches');