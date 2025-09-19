-- ============================================================
-- Fix for system_logs table - Add missing created_date column
-- ============================================================

USE MSIFactory;
GO

-- Check if system_logs table exists and add created_date column if missing
IF EXISTS (SELECT * FROM sysobjects WHERE name='system_logs' AND xtype='U')
BEGIN
    IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.COLUMNS
                   WHERE TABLE_NAME = 'system_logs' AND COLUMN_NAME = 'created_date')
    BEGIN
        ALTER TABLE system_logs ADD created_date DATETIME DEFAULT GETDATE();
        PRINT 'Added created_date column to system_logs table';
    END
    ELSE
    BEGIN
        PRINT 'created_date column already exists in system_logs table';
    END

    -- Now create the index if it doesn't exist
    IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_system_logs_date' AND object_id = OBJECT_ID('system_logs'))
    BEGIN
        CREATE INDEX idx_system_logs_date ON system_logs(created_date);
        PRINT 'Created index idx_system_logs_date on system_logs table';
    END
    ELSE
    BEGIN
        PRINT 'Index idx_system_logs_date already exists';
    END
END
ELSE
BEGIN
    PRINT 'system_logs table does not exist';
END
GO

PRINT '============================================================';
PRINT 'System Logs Fix Complete';
PRINT '============================================================';