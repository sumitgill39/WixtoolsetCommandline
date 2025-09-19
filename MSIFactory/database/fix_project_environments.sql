-- ============================================================
-- Fix project_environments table identity column issue
-- ============================================================

USE MSIFactory;
GO

-- Check if environment_id column exists and remove it if it's causing issues
IF EXISTS (SELECT * FROM INFORMATION_SCHEMA.COLUMNS
           WHERE TABLE_NAME = 'project_environments' AND COLUMN_NAME = 'environment_id')
BEGIN
    -- Check if it's an identity column
    IF EXISTS (SELECT * FROM sys.identity_columns
               WHERE object_id = OBJECT_ID('project_environments') AND name = 'environment_id')
    BEGIN
        PRINT 'Removing duplicate identity column environment_id...';

        -- We'll use env_id as the primary identity column
        -- Add a computed column or alias if needed for compatibility
        ALTER TABLE project_environments DROP COLUMN environment_id;

        PRINT 'Fixed: Removed duplicate identity column environment_id';
        PRINT 'Note: env_id serves as the primary identity column';
    END
    ELSE
    BEGIN
        PRINT 'environment_id exists but is not an identity column - no action needed';
    END
END
ELSE
BEGIN
    PRINT 'environment_id column does not exist - no action needed';
END
GO

-- Verify the table structure
PRINT '';
PRINT 'Current project_environments table structure:';
SELECT
    COLUMN_NAME,
    DATA_TYPE,
    IS_NULLABLE,
    COLUMNPROPERTY(OBJECT_ID('project_environments'), COLUMN_NAME, 'IsIdentity') as IS_IDENTITY
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_NAME = 'project_environments'
ORDER BY ORDINAL_POSITION;

PRINT '';
PRINT '============================================================';
PRINT 'Project Environments Table Fix Complete';
PRINT '============================================================';