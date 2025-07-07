-- Fix foreign key constraint that prevents removing watchlist items with alert history
-- The alert_history should not prevent removal of watchlist items

-- Drop the problematic foreign key constraint
ALTER TABLE alert_history DROP CONSTRAINT IF EXISTS alert_history_user_id_symbol_fkey;

-- Add a more flexible foreign key constraint that only references users table
-- Alert history should be preserved even if watchlist items are removed
ALTER TABLE alert_history DROP CONSTRAINT IF EXISTS alert_history_user_id_fkey;
ALTER TABLE alert_history ADD CONSTRAINT alert_history_user_id_fkey 
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;

-- Add index for better performance on alert history queries
CREATE INDEX IF NOT EXISTS idx_alert_history_user_symbol ON alert_history(user_id, symbol);