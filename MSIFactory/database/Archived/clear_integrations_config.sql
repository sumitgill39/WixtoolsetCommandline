-- Clear integrations_config table
-- This will remove all integration configurations to start fresh

-- Clear all data from integrations_config table
DELETE FROM [dbo].[integrations_config];

-- Reset identity if needed (optional)
-- DBCC CHECKIDENT('[dbo].[integrations_config]', RESEED, 0);

-- Verify table is empty
SELECT COUNT(*) as RecordCount FROM [dbo].[integrations_config];

PRINT 'integrations_config table cleared successfully';