-- Fix sequence synchronization issues in production
-- This migration resets all sequences to be in sync with their respective tables

-- Fix alert_history sequence
SELECT setval('alert_history_id_seq', GREATEST(COALESCE((SELECT MAX(id) FROM alert_history), 1), 1), true);

-- Fix logs sequence (if exists)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_class WHERE relname = 'logs_id_seq') THEN
        PERFORM setval('logs_id_seq', GREATEST(COALESCE((SELECT MAX(id) FROM logs), 1), 1), true);
    END IF;
END $$;

-- Log the results for verification
DO $$
DECLARE
    alert_seq_val bigint;
    alert_max_id bigint;
    logs_seq_val bigint;
    logs_max_id bigint;
BEGIN
    -- Get alert_history info
    SELECT last_value INTO alert_seq_val FROM alert_history_id_seq;
    SELECT COALESCE(MAX(id), 0) INTO alert_max_id FROM alert_history;
    
    -- Log alert_history sequence fix
    INSERT INTO logs (timestamp, log_type, message) 
    VALUES (NOW(), 'migration', 'Fixed alert_history_id_seq to ' || alert_seq_val || ', max table id: ' || alert_max_id);
    
    -- Get logs info if sequence exists
    IF EXISTS (SELECT 1 FROM pg_class WHERE relname = 'logs_id_seq') THEN
        SELECT last_value INTO logs_seq_val FROM logs_id_seq;
        SELECT COALESCE(MAX(id), 0) INTO logs_max_id FROM logs;
        
        INSERT INTO logs (timestamp, log_type, message) 
        VALUES (NOW(), 'migration', 'Fixed logs_id_seq to ' || logs_seq_val || ', max table id: ' || logs_max_id);
    END IF;
END $$;