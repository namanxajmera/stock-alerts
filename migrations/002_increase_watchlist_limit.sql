-- Increase default watchlist limit from 20 to 30
ALTER TABLE users ALTER COLUMN max_stocks SET DEFAULT 30;

-- Update existing users who still have the old default
UPDATE users SET max_stocks = 30 WHERE max_stocks = 20;