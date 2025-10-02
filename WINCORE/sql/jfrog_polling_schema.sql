-- ==============================================
-- JFrog Polling System Database Schema Update
-- Add SSP API Integration Support
-- ==============================================

-- Add SSP configuration table
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[ssp_config]') AND type in (N'U'))
BEGIN
    CREATE TABLE [dbo].[ssp_config](
        [config_id] [int] IDENTITY(1,1) PRIMARY KEY,
        [api_url] [nvarchar](500) NOT NULL,
        [api_token] [nvarchar](500) NOT NULL,
        [last_updated] [datetime] NOT NULL DEFAULT GETDATE(),
        [created_date] [datetime] NOT NULL DEFAULT GETDATE()
    )
    PRINT 'Created SSP configuration table'
END
GO

-- Update jfrog_system_config table to add new columns
IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.COLUMNS 
    WHERE TABLE_NAME = 'jfrog_system_config' AND COLUMN_NAME = 'config_description')
BEGIN
    ALTER TABLE [dbo].[jfrog_system_config]
    ADD [config_description] [nvarchar](500) NULL
    PRINT 'Added config_description column to jfrog_system_config'
END

IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.COLUMNS 
    WHERE TABLE_NAME = 'jfrog_system_config' AND COLUMN_NAME = 'last_updated')
BEGIN
    ALTER TABLE [dbo].[jfrog_system_config]
    ADD [last_updated] [datetime] NOT NULL DEFAULT GETDATE()
    PRINT 'Added last_updated column to jfrog_system_config'
END
GO

-- Update existing JFrog URL configuration
UPDATE [dbo].[jfrog_system_config]
SET [config_description] = 'JFrog Base URL for artifact monitoring'
WHERE [config_key] = 'JFrogBaseURL'
GO

-- Remove old username/password entries since they'll be managed by SSP
UPDATE [dbo].[jfrog_system_config]
SET [is_enabled] = 0,
    [config_description] = 'Deprecated - Now managed via SSP'
WHERE [config_key] IN ('SVCJFROGUSR', 'SVCJFROGPAS')
GO

-- Add SSP environment settings if not exist
IF NOT EXISTS (SELECT 1 FROM [dbo].[jfrog_system_config] WHERE [config_key] = 'SSP_ENV')
BEGIN
    INSERT INTO [dbo].[jfrog_system_config]
    ([config_key], [config_value], [is_enabled], [config_description], [created_by])
    VALUES
    ('SSP_ENV', 'PROD', 1, 'SSP API Environment', 'system')
END

IF NOT EXISTS (SELECT 1 FROM [dbo].[jfrog_system_config] WHERE [config_key] = 'SSP_APP_NAME')
BEGIN
    INSERT INTO [dbo].[jfrog_system_config]
    ([config_key], [config_value], [is_enabled], [config_description], [created_by])
    VALUES
    ('SSP_APP_NAME', 'WINCORE', 1, 'Application Name for SSP API', 'system')
END
GO

PRINT 'Schema update completed successfully'
GO