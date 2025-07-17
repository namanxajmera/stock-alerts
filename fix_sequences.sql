-- Fix sequence synchronization issues
-- This script resets all sequences to be in sync with their respective tables

-- Fix alert_history sequence
SELECT setval('alert_history_id_seq', COALESCE((SELECT MAX(id) FROM alert_history), 1), true);

-- Fix logs sequence (if exists)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_class WHERE relname = 'logs_id_seq') THEN
        PERFORM setval('logs_id_seq', COALESCE((SELECT MAX(id) FROM logs), 1), true);
    END IF;
END $$;

-- Verify the sequences are set correctly
SELECT 'alert_history_id_seq' as sequence_name, last_value FROM alert_history_id_seq;

-- Show current max IDs for verification
SELECT 'alert_history max id' as table_info, MAX(id) as max_id FROM alert_history;
SELECT 'logs max id' as table_info, COALESCE(MAX(id), 0) as max_id FROM logs;