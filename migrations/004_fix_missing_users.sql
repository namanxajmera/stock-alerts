-- Fix missing users in production - sync with existing watchlist data
-- This ensures users with watchlists can receive notifications

-- Insert any users that exist in watchlist_items but not in users table
INSERT INTO users (id, name, notification_enabled, max_stocks, created_at)
SELECT DISTINCT 
    user_id,
    'User_' || user_id as name,
    TRUE as notification_enabled,
    50 as max_stocks,
    NOW() as created_at
FROM watchlist_items wi
WHERE NOT EXISTS (
    SELECT 1 FROM users u WHERE u.id = wi.user_id
);

-- Enable notifications for any existing users who might have it disabled
UPDATE users SET notification_enabled = TRUE WHERE notification_enabled = FALSE;