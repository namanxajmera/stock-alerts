-- Migration: Add trading stats cache table
-- This table will store pre-computed trading statistics per ticker+period
-- to eliminate the need for recalculating complex stats on each request

CREATE TABLE IF NOT EXISTS trading_stats_cache (
    id SERIAL PRIMARY KEY,
    symbol TEXT NOT NULL,
    period TEXT NOT NULL,
    stats_json TEXT NOT NULL,
    last_updated TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    -- Composite unique constraint for symbol+period
    UNIQUE(symbol, period)
);

-- Index for efficient lookups
CREATE INDEX IF NOT EXISTS idx_trading_stats_symbol_period ON trading_stats_cache(symbol, period);
CREATE INDEX IF NOT EXISTS idx_trading_stats_updated ON trading_stats_cache(last_updated);