-- ============================================================
-- Integrations Configuration Schema for MSI Factory
-- Version: 1.0
-- Description: Creates centralized integration configuration table
-- Author: MSI Factory Team
-- ============================================================

USE MSIFactory;
GO

SET NOCOUNT ON;

PRINT '============================================================';
PRINT 'Creating Integrations Configuration Schema...';
PRINT '============================================================';

-- ============================================================
-- CREATE INTEGRATIONS CONFIG TABLE
-- ============================================================

IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='integrations_config' AND xtype='U')
BEGIN
    PRINT 'Creating integrations_config table...';

    CREATE TABLE integrations_config (
        config_id INT PRIMARY KEY IDENTITY(1,1),
        integration_type VARCHAR(50) NOT NULL,
        integration_name VARCHAR(100) NOT NULL,

        -- Common Integration Attributes
        base_url VARCHAR(500) NOT NULL,
        username VARCHAR(100),
        password VARCHAR(255),
        token VARCHAR(500),
        api_key VARCHAR(500),

        -- Authentication Configuration
        auth_type VARCHAR(20) NOT NULL DEFAULT 'username_password'
            CHECK (auth_type IN ('username_password', 'token', 'api_key', 'basic_auth')),

        -- Integration Specific Settings (JSON)
        additional_config TEXT,

        -- Status and Validation
        is_enabled BIT DEFAULT 1 NOT NULL,
        is_validated BIT DEFAULT 0,
        last_test_date DATETIME,
        last_test_result VARCHAR(20) CHECK (last_test_result IN ('success', 'failed', 'pending') OR last_test_result IS NULL),
        last_test_message TEXT,

        -- Connection Settings
        timeout_seconds INT DEFAULT 30,
        retry_count INT DEFAULT 3,
        ssl_verify BIT DEFAULT 1,

        -- Audit Attributes
        created_date DATETIME DEFAULT GETDATE() NOT NULL,
        created_by VARCHAR(50) NOT NULL,
        updated_date DATETIME DEFAULT GETDATE() NOT NULL,
        updated_by VARCHAR(50) NOT NULL,
        version_number INT DEFAULT 1,

        -- Security and Compliance
        encryption_enabled BIT DEFAULT 1,
        last_password_change DATETIME,
        password_expires_date DATETIME,

        -- Usage Tracking
        last_used_date DATETIME,
        usage_count INT DEFAULT 0,

        -- Constraints
        CONSTRAINT UK_integrations_type_name UNIQUE (integration_type, integration_name),
        CONSTRAINT CK_integrations_base_url_format CHECK (
            base_url LIKE 'http://%' OR base_url LIKE 'https://%'
        ),
        CONSTRAINT CK_integrations_timeout CHECK (timeout_seconds > 0 AND timeout_seconds <= 300),
        CONSTRAINT CK_integrations_retry CHECK (retry_count >= 0 AND retry_count <= 10),
        CONSTRAINT CK_integrations_auth_requirements CHECK (
            (auth_type = 'username_password' AND username IS NOT NULL AND password IS NOT NULL) OR
            (auth_type = 'token' AND token IS NOT NULL) OR
            (auth_type = 'api_key' AND api_key IS NOT NULL) OR
            (auth_type = 'basic_auth' AND username IS NOT NULL AND password IS NOT NULL)
        )
    );

    PRINT '  Integrations config table created successfully.';
END
ELSE
BEGIN
    PRINT '  Integrations config table already exists.';
END
GO

-- ============================================================
-- CREATE INTEGRATION AUDIT LOG TABLE
-- ============================================================

IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='integrations_audit_log' AND xtype='U')
BEGIN
    PRINT 'Creating integrations_audit_log table...';

    CREATE TABLE integrations_audit_log (
        audit_id INT PRIMARY KEY IDENTITY(1,1),
        config_id INT NOT NULL,
        integration_type VARCHAR(50) NOT NULL,
        integration_name VARCHAR(100) NOT NULL,

        -- Audit Action Details
        action_type VARCHAR(50) NOT NULL CHECK (action_type IN (
            'created', 'updated', 'deleted', 'enabled', 'disabled',
            'test_connection', 'password_changed', 'token_renewed'
        )),
        action_description TEXT,

        -- Change Tracking
        field_name VARCHAR(100),
        old_value TEXT,
        new_value TEXT,

        -- Request Context
        request_ip VARCHAR(45),
        user_agent TEXT,
        session_id VARCHAR(100),

        -- Audit Metadata
        audit_date DATETIME DEFAULT GETDATE() NOT NULL,
        performed_by VARCHAR(50) NOT NULL,
        performed_by_role VARCHAR(20),

        -- Result Tracking
        action_result VARCHAR(20) CHECK (action_result IN ('success', 'failed', 'warning')),
        error_message TEXT,

        FOREIGN KEY (config_id) REFERENCES integrations_config(config_id) ON DELETE CASCADE
    );

    PRINT '  Integrations audit log table created successfully.';
END
ELSE
BEGIN
    PRINT '  Integrations audit log table already exists.';
END
GO

-- ============================================================
-- CREATE INDEXES FOR PERFORMANCE
-- ============================================================

PRINT 'Creating indexes for integrations tables...';

-- Primary indexes for integrations_config
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_integrations_type')
    CREATE INDEX idx_integrations_type ON integrations_config(integration_type);

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_integrations_enabled')
    CREATE INDEX idx_integrations_enabled ON integrations_config(is_enabled);

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_integrations_type_enabled')
    CREATE INDEX idx_integrations_type_enabled ON integrations_config(integration_type, is_enabled);

-- Indexes for integrations_audit_log
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_audit_config_id')
    CREATE INDEX idx_audit_config_id ON integrations_audit_log(config_id);

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_audit_date')
    CREATE INDEX idx_audit_date ON integrations_audit_log(audit_date);

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_audit_action_type')
    CREATE INDEX idx_audit_action_type ON integrations_audit_log(action_type);

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_audit_performed_by')
    CREATE INDEX idx_audit_performed_by ON integrations_audit_log(performed_by);

PRINT 'Indexes created successfully.';
GO

-- ============================================================
-- CREATE STORED PROCEDURES
-- ============================================================

PRINT 'Creating stored procedures for integration management...';

-- Procedure to get integration configuration
IF EXISTS (SELECT * FROM sys.objects WHERE type = 'P' AND name = 'sp_GetIntegrationConfig')
    DROP PROCEDURE sp_GetIntegrationConfig;
GO

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
        -- Get specific configuration
        SELECT
            config_id, integration_type, integration_name, base_url,
            username, password, token, api_key, auth_type,
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

-- Procedure to update integration usage
IF EXISTS (SELECT * FROM sys.objects WHERE type = 'P' AND name = 'sp_UpdateIntegrationUsage')
    DROP PROCEDURE sp_UpdateIntegrationUsage;
GO

CREATE PROCEDURE sp_UpdateIntegrationUsage
    @config_id INT
AS
BEGIN
    SET NOCOUNT ON;

    UPDATE integrations_config
    SET last_used_date = GETDATE(),
        usage_count = usage_count + 1
    WHERE config_id = @config_id;
END
GO

-- Procedure to log audit actions
IF EXISTS (SELECT * FROM sys.objects WHERE type = 'P' AND name = 'sp_LogIntegrationAudit')
    DROP PROCEDURE sp_LogIntegrationAudit;
GO

CREATE PROCEDURE sp_LogIntegrationAudit
    @config_id INT,
    @action_type VARCHAR(50),
    @performed_by VARCHAR(50),
    @action_description TEXT = NULL,
    @field_name VARCHAR(100) = NULL,
    @old_value TEXT = NULL,
    @new_value TEXT = NULL,
    @action_result VARCHAR(20) = 'success',
    @error_message TEXT = NULL
AS
BEGIN
    SET NOCOUNT ON;

    DECLARE @integration_type VARCHAR(50), @integration_name VARCHAR(100);

    -- Get integration details
    SELECT @integration_type = integration_type, @integration_name = integration_name
    FROM integrations_config WHERE config_id = @config_id;

    -- Insert audit record
    INSERT INTO integrations_audit_log (
        config_id, integration_type, integration_name, action_type,
        action_description, field_name, old_value, new_value,
        performed_by, action_result, error_message
    )
    VALUES (
        @config_id, @integration_type, @integration_name, @action_type,
        @action_description, @field_name, @old_value, @new_value,
        @performed_by, @action_result, @error_message
    );
END
GO

PRINT 'Stored procedures created successfully.';
GO

-- ============================================================
-- INSERT SAMPLE DATA
-- ============================================================

PRINT 'Inserting sample integration configurations...';

-- Insert sample JFrog configuration
IF NOT EXISTS (SELECT * FROM integrations_config WHERE integration_type = 'jfrog' AND integration_name = 'Primary JFrog')
BEGIN
    INSERT INTO integrations_config (
        integration_type, integration_name, base_url, username, password,
        auth_type, is_enabled, timeout_seconds, retry_count,
        created_by, updated_by
    )
    VALUES (
        'jfrog', 'Primary JFrog', 'https://your-company.jfrog.io/artifactory',
        'jfrog_user', 'encrypted_password_placeholder',
        'username_password', 1, 30, 3,
        'system', 'system'
    );
    PRINT '  Sample JFrog configuration created.';
END

-- Insert sample ServiceNow configuration
IF NOT EXISTS (SELECT * FROM integrations_config WHERE integration_type = 'servicenow' AND integration_name = 'Primary ServiceNow')
BEGIN
    INSERT INTO integrations_config (
        integration_type, integration_name, base_url, username, password,
        auth_type, is_enabled, timeout_seconds, retry_count,
        created_by, updated_by
    )
    VALUES (
        'servicenow', 'Primary ServiceNow', 'https://your-instance.service-now.com',
        'servicenow_user', 'encrypted_password_placeholder',
        'username_password', 0, 45, 3,
        'system', 'system'
    );
    PRINT '  Sample ServiceNow configuration created.';
END

-- Insert sample HashiCorp Vault configuration
IF NOT EXISTS (SELECT * FROM integrations_config WHERE integration_type = 'vault' AND integration_name = 'Primary Vault')
BEGIN
    INSERT INTO integrations_config (
        integration_type, integration_name, base_url, token,
        auth_type, is_enabled, timeout_seconds, retry_count,
        created_by, updated_by
    )
    VALUES (
        'vault', 'Primary Vault', 'https://vault.your-company.com:8200',
        'hvs.encrypted_token_placeholder',
        'token', 0, 20, 2,
        'system', 'system'
    );
    PRINT '  Sample HashiCorp Vault configuration created.';
END

-- ============================================================
-- UPDATE STATISTICS
-- ============================================================

PRINT 'Updating statistics...';

UPDATE STATISTICS integrations_config;
UPDATE STATISTICS integrations_audit_log;

-- ============================================================
-- FINAL VALIDATION
-- ============================================================

PRINT 'Running final validation...';

-- Check table counts
SELECT
    'integrations_config' as table_name,
    COUNT(*) as record_count
FROM integrations_config

UNION ALL

SELECT
    'integrations_audit_log' as table_name,
    COUNT(*) as record_count
FROM integrations_audit_log;

PRINT '';
PRINT '============================================================';
PRINT 'Integrations Configuration Schema Installation Complete!';
PRINT '============================================================';
PRINT '';
PRINT 'Features Added:';
PRINT '  ✓ Centralized integration configuration management';
PRINT '  ✓ Support for ServiceNow (username/password)';
PRINT '  ✓ Support for HashiCorp Vault (token-based)';
PRINT '  ✓ Support for JFrog Artifactory (username/password)';
PRINT '  ✓ Flexible authentication methods';
PRINT '  ✓ Comprehensive audit logging';
PRINT '  ✓ Connection testing and validation';
PRINT '  ✓ Usage tracking and monitoring';
PRINT '  ✓ Security and encryption support';
PRINT '  ✓ Performance optimized indexes';
PRINT '  ✓ Stored procedures for common operations';
PRINT '';
PRINT 'Database ready for Centralized Integration Management!';
PRINT '============================================================';

SET NOCOUNT OFF;