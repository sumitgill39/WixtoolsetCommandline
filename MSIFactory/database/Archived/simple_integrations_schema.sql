-- ============================================================
-- Simple Integrations Configuration Schema for MSI Factory
-- Version: 2.0 (Simplified - No Stored Procedures)
-- Description: Creates basic integration configuration table only
-- ============================================================

USE MSIFactory;
GO

SET NOCOUNT ON;

PRINT '============================================================';
PRINT 'Creating Simple Integrations Configuration Schema...';
PRINT '============================================================';

-- ============================================================
-- CREATE INTEGRATIONS CONFIG TABLE (NO api_key column)
-- ============================================================

IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='integrations_config' AND xtype='U')
BEGIN
    PRINT 'Creating integrations_config table...';

    CREATE TABLE integrations_config (
        config_id INT PRIMARY KEY IDENTITY(1,1),
        integration_type VARCHAR(50) NOT NULL,
        integration_name VARCHAR(100) NOT NULL,

        -- Common Integration Attributes (NO api_key)
        base_url VARCHAR(500) NOT NULL,
        username VARCHAR(100),
        password VARCHAR(255),
        token VARCHAR(500),

        -- Authentication Configuration (NO api_key auth)
        auth_type VARCHAR(20) NOT NULL DEFAULT 'username_password'
            CHECK (auth_type IN ('username_password', 'token', 'basic_auth')),

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

        -- Constraints (SIMPLIFIED)
        CONSTRAINT UK_integrations_type_name UNIQUE (integration_type, integration_name),
        CONSTRAINT CK_integrations_base_url_format CHECK (
            base_url LIKE 'http://%' OR base_url LIKE 'https://%'
        ),
        CONSTRAINT CK_integrations_timeout CHECK (timeout_seconds > 0 AND timeout_seconds <= 300),
        CONSTRAINT CK_integrations_retry CHECK (retry_count >= 0 AND retry_count <= 10),
        CONSTRAINT CK_integrations_auth_requirements CHECK (
            (auth_type = 'username_password' AND username IS NOT NULL AND password IS NOT NULL) OR
            (auth_type = 'token' AND token IS NOT NULL) OR
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
-- CREATE INDEXES FOR PERFORMANCE
-- ============================================================

PRINT 'Creating indexes for integrations table...';

-- Primary indexes for integrations_config
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_integrations_type')
    CREATE INDEX idx_integrations_type ON integrations_config(integration_type);

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_integrations_enabled')
    CREATE INDEX idx_integrations_enabled ON integrations_config(is_enabled);

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_integrations_type_enabled')
    CREATE INDEX idx_integrations_type_enabled ON integrations_config(integration_type, is_enabled);

PRINT 'Indexes created successfully.';
GO

-- ============================================================
-- INSERT SAMPLE DATA
-- ============================================================

PRINT 'Inserting sample integration configurations...';

-- Insert sample JFrog configuration (NO api_key)
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
-- FINAL VALIDATION
-- ============================================================

PRINT 'Running final validation...';

-- Check table counts
SELECT
    'integrations_config' as table_name,
    COUNT(*) as record_count
FROM integrations_config;

PRINT '';
PRINT '============================================================';
PRINT 'Simple Integrations Configuration Schema Complete!';
PRINT '============================================================';
PRINT '';
PRINT 'Features:';
PRINT '  ✓ Simple table structure (NO stored procedures)';
PRINT '  ✓ Direct SQL queries only';
PRINT '  ✓ No api_key column dependencies';
PRINT '  ✓ Support for JFrog, ServiceNow, and Vault';
PRINT '  ✓ Basic indexing for performance';
PRINT '  ✓ Simplified authentication constraints';
PRINT '';
PRINT 'Ready for simple integration management!';
PRINT '============================================================';

SET NOCOUNT OFF;