-- Increase watchlist limit from 30 to 50
ALTER TABLE users ALTER COLUMN max_stocks SET DEFAULT 50;

-- Update existing users who have the previous default of 30
UPDATE users SET max_stocks = 50 WHERE max_stocks = 30;