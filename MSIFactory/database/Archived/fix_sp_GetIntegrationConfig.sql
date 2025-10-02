-- ============================================================
-- Fix sp_GetIntegrationConfig - Remove api_key column reference
-- ============================================================

USE MSIFactory;
GO

PRINT 'Updating sp_GetIntegrationConfig to remove api_key column reference...';

-- Drop existing procedure
IF EXISTS (SELECT * FROM sys.objects WHERE type = 'P' AND name = 'sp_GetIntegrationConfig')
    DROP PROCEDURE sp_GetIntegrationConfig;
GO

-- Recreate procedure without api_key column
CREATE PROCEDURE sp_GetIntegrationConfig
    @integration_type VARCHAR(50),
    @integration_name VARCHAR(100) = NULL
AS
BEGIN
    SET NOCOUNT ON;

    IF @integration_name IS NULL
    BEGIN
        -- Get all configurations for the integration type
        SELECT
            config_id, integration_type, integration_name, base_url,
            username, auth_type, is_enabled, is_validated,
            last_test_date, last_test_result, last_test_message,
            timeout_seconds, retry_count, ssl_verify,
            created_date, updated_date, last_used_date, usage_count
        FROM integrations_config
        WHERE integration_type = @integration_type
        ORDER BY integration_name;
    END
    ELSE
    BEGIN
        -- Get specific configuration (api_key column removed)
        SELECT
            config_id, integration_type, integration_name, base_url,
            username, password, token, auth_type,
            additional_config, is_enabled, is_validated,
            last_test_date, last_test_result, last_test_message,
            timeout_seconds, retry_count, ssl_verify,
            created_date, updated_date, last_used_date, usage_count
        FROM integrations_config
        WHERE integration_type = @integration_type
        AND integration_name = @integration_name;
    END
END
GO

PRINT 'sp_GetIntegrationConfig updated successfully - api_key column reference removed';