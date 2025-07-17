-- Fix sequence synchronization issues in production
-- This migration resets all sequences to be in sync with their respective tables

-- Fix alert_history sequence (only if it exists)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_class WHERE relname = 'alert_history_id_seq') THEN
        PERFORM setval('alert_history_id_seq', GREATEST(COALESCE((SELECT MAX(id) FROM alert_history), 1), 1), true);
        INSERT INTO logs (timestamp, log_type, message) 
        VALUES (NOW(), 'migration', 'Fixed alert_history_id_seq to ' || currval('alert_history_id_seq'));
    ELSE
        INSERT INTO logs (timestamp, log_type, message) 
        VALUES (NOW(), 'migration', 'alert_history_id_seq does not exist, skipping sequence fix');
    END IF;
END $$;

-- Fix logs sequence (if exists)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_class WHERE relname = 'logs_id_seq') THEN
        PERFORM setval('logs_id_seq', GREATEST(COALESCE((SELECT MAX(id) FROM logs), 1), 1), true);
        INSERT INTO logs (timestamp, log_type, message) 
        VALUES (NOW(), 'migration', 'Fixed logs_id_seq to ' || currval('logs_id_seq'));
    ELSE
        INSERT INTO logs (timestamp, log_type, message) 
        VALUES (NOW(), 'migration', 'logs_id_seq does not exist, skipping sequence fix');
    END IF;
END $$;