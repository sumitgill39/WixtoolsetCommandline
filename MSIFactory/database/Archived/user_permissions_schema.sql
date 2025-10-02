-- ============================================================
-- User Permissions Control Schema for MSI Factory
-- Version: 1.0
-- Description: Creates flexible permission control system for viewing soft-deleted records
-- ============================================================

USE MSIFactory;
GO

SET NOCOUNT ON;

PRINT '============================================================';
PRINT 'Creating User Permissions Control Schema...';
PRINT '============================================================';

-- ============================================================
-- CREATE USER PERMISSIONS TABLE
-- ============================================================

IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='user_permissions' AND xtype='U')
BEGIN
    PRINT 'Creating user_permissions table...';

    CREATE TABLE user_permissions (
        permission_id INT PRIMARY KEY IDENTITY(1,1),
        user_id INT NOT NULL,
        permission_type VARCHAR(50) NOT NULL,
        permission_value VARCHAR(100) NOT NULL,

        -- Permission Details
        description VARCHAR(500),
        granted_by VARCHAR(50) NOT NULL,
        granted_date DATETIME DEFAULT GETDATE() NOT NULL,

        -- Expiration Control
        expires_date DATETIME,
        is_active BIT DEFAULT 1 NOT NULL,

        -- Audit Fields
        created_date DATETIME DEFAULT GETDATE() NOT NULL,
        updated_date DATETIME DEFAULT GETDATE() NOT NULL,
        updated_by VARCHAR(50),

        -- Constraints
        CONSTRAINT FK_user_permissions_user FOREIGN KEY (user_id)
            REFERENCES users(user_id),
        CONSTRAINT UK_user_permission_unique UNIQUE (user_id, permission_type, permission_value),
        CONSTRAINT CK_permission_type CHECK (permission_type IN (
            'view_inactive_components',
            'view_inactive_projects',
            'view_inactive_branches',
            'view_all_builds',
            'view_system_logs',
            'export_data',
            'api_access'
        ))
    );

    PRINT '  User permissions table created successfully.';

    -- Create indexes for performance
    CREATE INDEX idx_user_permissions_user ON user_permissions(user_id);
    CREATE INDEX idx_user_permissions_type ON user_permissions(permission_type);
    CREATE INDEX idx_user_permissions_active ON user_permissions(is_active);
    CREATE INDEX idx_user_permissions_user_type ON user_permissions(user_id, permission_type, is_active);

    PRINT '  Indexes created successfully.';
END
ELSE
BEGIN
    PRINT '  User permissions table already exists.';
END
GO

-- ============================================================
-- CREATE PERMISSION PRESETS TABLE
-- ============================================================

IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='permission_presets' AND xtype='U')
BEGIN
    PRINT 'Creating permission_presets table...';

    CREATE TABLE permission_presets (
        preset_id INT PRIMARY KEY IDENTITY(1,1),
        preset_name VARCHAR(100) NOT NULL UNIQUE,
        preset_description VARCHAR(500),

        -- Preset Permissions (JSON array of permission_type values)
        permissions TEXT NOT NULL,

        -- Metadata
        created_by VARCHAR(50) NOT NULL,
        created_date DATETIME DEFAULT GETDATE() NOT NULL,
        updated_by VARCHAR(50),
        updated_date DATETIME DEFAULT GETDATE() NOT NULL,
        is_active BIT DEFAULT 1 NOT NULL
    );

    PRINT '  Permission presets table created successfully.';
END
ELSE
BEGIN
    PRINT '  Permission presets table already exists.';
END
GO

-- ============================================================
-- INSERT DEFAULT PERMISSION PRESETS
-- ============================================================

PRINT 'Inserting default permission presets...';

-- PowerUser preset
IF NOT EXISTS (SELECT * FROM permission_presets WHERE preset_name = 'PowerUser Extended')
BEGIN
    INSERT INTO permission_presets (preset_name, preset_description, permissions, created_by)
    VALUES (
        'PowerUser Extended',
        'PowerUsers with ability to see inactive components and branches',
        '["view_inactive_components", "view_inactive_branches"]',
        'system'
    );
    PRINT '  PowerUser Extended preset created.';
END

-- Developer preset
IF NOT EXISTS (SELECT * FROM permission_presets WHERE preset_name = 'Developer')
BEGIN
    INSERT INTO permission_presets (preset_name, preset_description, permissions, created_by)
    VALUES (
        'Developer',
        'Developers with build and export permissions',
        '["view_all_builds", "export_data"]',
        'system'
    );
    PRINT '  Developer preset created.';
END

-- Auditor preset
IF NOT EXISTS (SELECT * FROM permission_presets WHERE preset_name = 'Auditor')
BEGIN
    INSERT INTO permission_presets (preset_name, preset_description, permissions, created_by)
    VALUES (
        'Auditor',
        'Auditors with full read access including inactive records',
        '["view_inactive_components", "view_inactive_projects", "view_inactive_branches", "view_system_logs"]',
        'system'
    );
    PRINT '  Auditor preset created.';
END

-- API User preset
IF NOT EXISTS (SELECT * FROM permission_presets WHERE preset_name = 'API User')
BEGIN
    INSERT INTO permission_presets (preset_name, preset_description, permissions, created_by)
    VALUES (
        'API User',
        'Service accounts with API access',
        '["api_access", "view_all_builds"]',
        'system'
    );
    PRINT '  API User preset created.';
END

-- ============================================================
-- CREATE HELPER FUNCTIONS
-- ============================================================

PRINT 'Creating helper functions...';

-- Drop existing function if exists
IF EXISTS (SELECT * FROM sys.objects WHERE type = 'FN' AND name = 'fn_UserHasPermission')
    DROP FUNCTION fn_UserHasPermission;
GO

-- Create function to check if user has specific permission
CREATE FUNCTION fn_UserHasPermission
(
    @user_id INT,
    @permission_type VARCHAR(50)
)
RETURNS BIT
AS
BEGIN
    DECLARE @has_permission BIT = 0;

    -- Check if user is admin (admins have all permissions)
    IF EXISTS (SELECT 1 FROM users WHERE user_id = @user_id AND role = 'admin')
    BEGIN
        SET @has_permission = 1;
    END
    ELSE
    BEGIN
        -- Check specific permission
        IF EXISTS (
            SELECT 1 FROM user_permissions
            WHERE user_id = @user_id
            AND permission_type = @permission_type
            AND is_active = 1
            AND (expires_date IS NULL OR expires_date > GETDATE())
        )
        BEGIN
            SET @has_permission = 1;
        END
    END

    RETURN @has_permission;
END
GO

PRINT '  Helper functions created successfully.';

-- ============================================================
-- FINAL VALIDATION
-- ============================================================

PRINT '';
PRINT 'Running final validation...';

-- Check table counts
SELECT 'user_permissions' as table_name, COUNT(*) as record_count FROM user_permissions
UNION ALL
SELECT 'permission_presets', COUNT(*) FROM permission_presets;

PRINT '';
PRINT '============================================================';
PRINT 'User Permissions Control Schema Complete!';
PRINT '============================================================';
PRINT '';
PRINT 'Features:';
PRINT '  ✓ Flexible permission system for individual users';
PRINT '  ✓ Permission presets for common role combinations';
PRINT '  ✓ Time-based permission expiration';
PRINT '  ✓ Helper function for permission checks';
PRINT '  ✓ Full audit trail support';
PRINT '';
PRINT 'Usage:';
PRINT '  - Grant permission: INSERT INTO user_permissions...';
PRINT '  - Check permission: SELECT dbo.fn_UserHasPermission(@user_id, @permission_type)';
PRINT '  - Apply preset: Use stored procedure or application logic';
PRINT '';
PRINT '============================================================';

SET NOCOUNT OFF;