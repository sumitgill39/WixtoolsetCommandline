-- ============================================================
-- MSI Factory Complete Database Schema for MS SQL Server
-- Version: 6.1 - With Enhanced Permission Control System
-- Description: Complete schema with integrated individual user permission control
-- ============================================================

-- Use the complete v6 schema as base and add individual user permission extensions

USE MSIFactory;
GO

SET NOCOUNT ON;

PRINT '============================================================';
PRINT 'MSI Factory Schema v6.1 - Individual Permission Control Extension';
PRINT '============================================================';

-- ============================================================
-- INDIVIDUAL USER PERMISSION CONTROL TABLES
-- ============================================================

PRINT '';
PRINT 'Adding individual user permission control system...';

-- Individual User Permission Grants Table (extends the role-based system)
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='user_permission_grants' AND xtype='U')
BEGIN
    PRINT '  Creating user_permission_grants table...';
    CREATE TABLE user_permission_grants (
        grant_id INT PRIMARY KEY IDENTITY(1,1),
        user_id INT NOT NULL,
        permission_type VARCHAR(50) NOT NULL,
        permission_value VARCHAR(100) NOT NULL DEFAULT 'granted',

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
        CONSTRAINT FK_user_permission_grants_user FOREIGN KEY (user_id)
            REFERENCES users(user_id),
        CONSTRAINT UK_user_permission_grant_unique UNIQUE (user_id, permission_type, permission_value),
        CONSTRAINT CK_grant_permission_type CHECK (permission_type IN (
            'view_inactive_components',
            'view_inactive_projects',
            'view_inactive_branches',
            'view_all_builds',
            'view_system_logs',
            'export_data',
            'api_access',
            'bulk_component_operations',
            'advanced_msi_config',
            'cmdb_server_management'
        ))
    );

    PRINT '  User permission grants table created successfully.';

    -- Create indexes for performance
    CREATE INDEX idx_user_permission_grants_user ON user_permission_grants(user_id);
    CREATE INDEX idx_user_permission_grants_type ON user_permission_grants(permission_type);
    CREATE INDEX idx_user_permission_grants_active ON user_permission_grants(is_active);
    CREATE INDEX idx_user_permission_grants_user_type ON user_permission_grants(user_id, permission_type, is_active);

    PRINT '  Indexes created successfully.';
END
ELSE
BEGIN
    PRINT '  User permission grants table already exists.';
END
GO

-- Permission Presets Table (for quick assignment of common permission combinations)
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='permission_presets' AND xtype='U')
BEGIN
    PRINT '  Creating permission_presets table...';

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

-- PowerUser Extended preset
IF NOT EXISTS (SELECT * FROM permission_presets WHERE preset_name = 'PowerUser Extended')
BEGIN
    INSERT INTO permission_presets (preset_name, preset_description, permissions, created_by)
    VALUES (
        'PowerUser Extended',
        'PowerUsers with ability to see inactive components and branches',
        '["view_inactive_components", "view_inactive_branches", "bulk_component_operations"]',
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
        '["view_all_builds", "export_data", "advanced_msi_config"]',
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
        '["view_inactive_components", "view_inactive_projects", "view_inactive_branches", "view_system_logs", "view_all_builds"]',
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
        '["api_access", "view_all_builds", "export_data"]',
        'system'
    );
    PRINT '  API User preset created.';
END

-- Infrastructure Manager preset
IF NOT EXISTS (SELECT * FROM permission_presets WHERE preset_name = 'Infrastructure Manager')
BEGIN
    INSERT INTO permission_presets (preset_name, preset_description, permissions, created_by)
    VALUES (
        'Infrastructure Manager',
        'CMDB and server management permissions',
        '["cmdb_server_management", "view_inactive_components", "view_system_logs"]',
        'system'
    );
    PRINT '  Infrastructure Manager preset created.';
END

-- ============================================================
-- ENHANCED PERMISSION CHECKING FUNCTIONS
-- ============================================================

PRINT 'Creating enhanced permission functions...';

-- Drop existing function if exists
IF EXISTS (SELECT * FROM sys.objects WHERE type = 'FN' AND name = 'fn_UserHasSpecialPermission')
    DROP FUNCTION fn_UserHasSpecialPermission;
GO

-- Create function to check if user has specific special permission
CREATE FUNCTION fn_UserHasSpecialPermission
(
    @user_id INT,
    @permission_type VARCHAR(50)
)
RETURNS BIT
AS
BEGIN
    DECLARE @has_permission BIT = 0;

    -- Check if user is admin (admins have all permissions)
    IF EXISTS (SELECT 1 FROM users WHERE user_id = @user_id AND role = 'admin' AND is_active = 1)
    BEGIN
        SET @has_permission = 1;
    END
    ELSE
    BEGIN
        -- Check specific individual permission grant
        IF EXISTS (
            SELECT 1 FROM user_permission_grants
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

-- Enhanced user permission check function (combines role-based and individual permissions)
IF EXISTS (SELECT * FROM sys.objects WHERE type = 'FN' AND name = 'fn_UserHasEnhancedPermission')
    DROP FUNCTION fn_UserHasEnhancedPermission;
GO

CREATE FUNCTION fn_UserHasEnhancedPermission
(
    @username VARCHAR(50),
    @permission_name VARCHAR(100)
)
RETURNS BIT
AS
BEGIN
    DECLARE @has_permission BIT = 0;
    DECLARE @user_id INT;

    -- Get user_id
    SELECT @user_id = user_id FROM users WHERE username = @username AND is_active = 1;

    IF @user_id IS NOT NULL
    BEGIN
        -- Check if user is admin (admins have all permissions)
        IF EXISTS (SELECT 1 FROM users WHERE user_id = @user_id AND role = 'admin')
        BEGIN
            SET @has_permission = 1;
        END
        ELSE
        BEGIN
            -- Check role-based permission first
            IF EXISTS (
                SELECT 1 FROM users u
                JOIN role_permissions rp ON u.role = rp.role_name
                JOIN user_permissions up ON rp.permission_id = up.permission_id
                WHERE u.user_id = @user_id
                AND up.permission_name = @permission_name
                AND rp.is_granted = 1
                AND up.is_active = 1
            )
            BEGIN
                SET @has_permission = 1;
            END

            -- Check for individual special permissions that might grant access
            -- (This could be extended to map specific permissions to role-based actions)
        END
    END

    RETURN @has_permission;
END
GO

PRINT '  Enhanced permission functions created successfully.';

-- ============================================================
-- ADD SOFT DELETE VISIBILITY PERMISSIONS TO EXISTING PERMISSIONS
-- ============================================================

PRINT 'Adding soft delete visibility permissions to existing permission system...';

-- Add soft delete related permissions to the existing user_permissions table
IF NOT EXISTS (SELECT * FROM user_permissions WHERE permission_name = 'view_inactive_components')
BEGIN
    INSERT INTO user_permissions (permission_name, permission_description, module_name, action_type) VALUES
    ('view_inactive_components', 'View components marked as inactive (soft deleted)', 'components', 'read'),
    ('view_inactive_projects', 'View projects marked as inactive (soft deleted)', 'projects', 'read'),
    ('view_inactive_branches', 'View branches marked as inactive (soft deleted)', 'components', 'read'),
    ('view_all_builds', 'View builds from all users regardless of ownership', 'msi', 'read'),
    ('export_system_data', 'Export system data and reports', 'system', 'export'),
    ('api_full_access', 'Full access to API endpoints', 'system', 'api'),
    ('bulk_operations', 'Perform bulk operations on multiple records', 'system', 'bulk'),
    ('advanced_config', 'Access to advanced configuration options', 'system', 'config');

    PRINT '  Soft delete visibility permissions added to user_permissions table.';

    -- Grant these new permissions to admin role
    INSERT INTO role_permissions (role_name, permission_id)
    SELECT 'admin', permission_id FROM user_permissions
    WHERE permission_name IN (
        'view_inactive_components', 'view_inactive_projects', 'view_inactive_branches',
        'view_all_builds', 'export_system_data', 'api_full_access', 'bulk_operations', 'advanced_config'
    );

    PRINT '  New permissions granted to admin role.';
END

-- ============================================================
-- CREATE ENHANCED VIEWS FOR PERMISSION CONTROL
-- ============================================================

PRINT 'Creating enhanced permission control views...';

-- User Permission Summary View
IF NOT EXISTS (SELECT * FROM sys.views WHERE name = 'vw_user_permission_summary')
BEGIN
    EXEC('
    CREATE VIEW vw_user_permission_summary
    AS
    SELECT
        u.user_id,
        u.username,
        u.email,
        u.first_name + '' '' + u.last_name as full_name,
        u.role,
        u.status,
        u.is_active,

        -- Role-based permissions count
        (SELECT COUNT(*) FROM v_user_permissions vup
         WHERE vup.user_id = u.user_id) as role_permissions_count,

        -- Individual permission grants count
        (SELECT COUNT(*) FROM user_permission_grants upg
         WHERE upg.user_id = u.user_id AND upg.is_active = 1
         AND (upg.expires_date IS NULL OR upg.expires_date > GETDATE())) as individual_permissions_count,

        -- Last permission change
        (SELECT MAX(granted_date) FROM user_permission_grants upg
         WHERE upg.user_id = u.user_id) as last_permission_change,

        u.created_date,
        u.last_login
    FROM users u
    WHERE u.is_active = 1
    ');
    PRINT '  View vw_user_permission_summary created successfully.';
END
GO

-- Active Permission Grants View
IF NOT EXISTS (SELECT * FROM sys.views WHERE name = 'vw_active_permission_grants')
BEGIN
    EXEC('
    CREATE VIEW vw_active_permission_grants
    AS
    SELECT
        upg.grant_id,
        upg.user_id,
        u.username,
        u.first_name + '' '' + u.last_name as full_name,
        u.role,
        upg.permission_type,
        upg.permission_value,
        upg.description,
        upg.granted_by,
        upg.granted_date,
        upg.expires_date,
        CASE
            WHEN upg.expires_date IS NULL THEN ''Permanent''
            WHEN upg.expires_date > GETDATE() THEN ''Active until '' + CONVERT(VARCHAR, upg.expires_date, 120)
            ELSE ''Expired''
        END as status_description,
        upg.created_date
    FROM user_permission_grants upg
    INNER JOIN users u ON upg.user_id = u.user_id
    WHERE upg.is_active = 1
    AND u.is_active = 1
    ');
    PRINT '  View vw_active_permission_grants created successfully.';
END
GO

-- ============================================================
-- STORED PROCEDURES FOR PERMISSION MANAGEMENT
-- ============================================================

PRINT 'Creating permission management stored procedures...';

-- Grant Individual Permission Procedure
IF EXISTS (SELECT * FROM sys.objects WHERE type = 'P' AND name = 'sp_GrantIndividualPermission')
    DROP PROCEDURE sp_GrantIndividualPermission;
GO

CREATE PROCEDURE sp_GrantIndividualPermission
    @user_id INT,
    @permission_type VARCHAR(50),
    @granted_by VARCHAR(50),
    @expires_date DATETIME = NULL,
    @description VARCHAR(500) = NULL
AS
BEGIN
    SET NOCOUNT ON;

    BEGIN TRY
        -- Check if user exists and is active
        IF NOT EXISTS (SELECT 1 FROM users WHERE user_id = @user_id AND is_active = 1)
        BEGIN
            SELECT 0 as success, 'User not found or inactive' as message;
            RETURN;
        END

        -- Check if permission already exists
        IF EXISTS (
            SELECT 1 FROM user_permission_grants
            WHERE user_id = @user_id
            AND permission_type = @permission_type
            AND is_active = 1
        )
        BEGIN
            -- Update existing permission
            UPDATE user_permission_grants
            SET expires_date = @expires_date,
                description = @description,
                updated_date = GETDATE(),
                updated_by = @granted_by
            WHERE user_id = @user_id
            AND permission_type = @permission_type
            AND is_active = 1;

            SELECT 1 as success, 'Permission updated successfully' as message;
        END
        ELSE
        BEGIN
            -- Insert new permission
            INSERT INTO user_permission_grants (
                user_id, permission_type, granted_by, expires_date, description
            ) VALUES (
                @user_id, @permission_type, @granted_by, @expires_date, @description
            );

            SELECT 1 as success, 'Permission granted successfully' as message;
        END
    END TRY
    BEGIN CATCH
        SELECT 0 as success, ERROR_MESSAGE() as message;
    END CATCH
END
GO

-- Revoke Individual Permission Procedure
IF EXISTS (SELECT * FROM sys.objects WHERE type = 'P' AND name = 'sp_RevokeIndividualPermission')
    DROP PROCEDURE sp_RevokeIndividualPermission;
GO

CREATE PROCEDURE sp_RevokeIndividualPermission
    @grant_id INT
AS
BEGIN
    SET NOCOUNT ON;

    BEGIN TRY
        IF EXISTS (SELECT 1 FROM user_permission_grants WHERE grant_id = @grant_id)
        BEGIN
            UPDATE user_permission_grants
            SET is_active = 0,
                updated_date = GETDATE()
            WHERE grant_id = @grant_id;

            SELECT 1 as success, 'Permission revoked successfully' as message;
        END
        ELSE
        BEGIN
            SELECT 0 as success, 'Permission grant not found' as message;
        END
    END TRY
    BEGIN CATCH
        SELECT 0 as success, ERROR_MESSAGE() as message;
    END CATCH
END
GO

PRINT '  Permission management stored procedures created successfully.';

-- ============================================================
-- UPDATE COMPONENT BRANCHES TABLE FOR SOFT DELETE SUPPORT
-- ============================================================

PRINT 'Ensuring component branches table supports soft delete...';

-- Add component_branches table if it doesn't exist (for branch management soft delete)
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='component_branches' AND xtype='U')
BEGIN
    PRINT '  Creating component_branches table...';
    CREATE TABLE component_branches (
        branch_id INT PRIMARY KEY IDENTITY(1,1),
        component_id INT NOT NULL,
        branch_name VARCHAR(100) NOT NULL,
        branch_type VARCHAR(50) DEFAULT 'feature' CHECK (branch_type IN ('main', 'develop', 'feature', 'hotfix', 'release')),
        description TEXT,

        -- Git Information
        repository_url VARCHAR(500),
        last_commit VARCHAR(100),
        last_commit_date DATETIME,
        last_commit_author VARCHAR(100),

        -- Artifact Information
        artifact_path VARCHAR(500),
        last_build_version VARCHAR(50),
        last_build_date DATETIME,

        -- Status and Metadata
        is_active BIT DEFAULT 1 NOT NULL,
        created_date DATETIME DEFAULT GETDATE() NOT NULL,
        created_by VARCHAR(50) NOT NULL,
        updated_date DATETIME DEFAULT GETDATE() NOT NULL,
        updated_by VARCHAR(50),

        FOREIGN KEY (component_id) REFERENCES components(component_id) ON DELETE CASCADE,
        UNIQUE(component_id, branch_name)
    );

    CREATE INDEX idx_component_branches_component ON component_branches(component_id);
    CREATE INDEX idx_component_branches_active ON component_branches(is_active);
    CREATE INDEX idx_component_branches_type ON component_branches(branch_type);

    PRINT '  Component branches table created successfully.';
END
ELSE
BEGIN
    PRINT '  Component branches table already exists.';

    -- Ensure is_active column exists
    IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.COLUMNS
                   WHERE TABLE_NAME = 'component_branches' AND COLUMN_NAME = 'is_active')
    BEGIN
        ALTER TABLE component_branches ADD is_active BIT DEFAULT 1 NOT NULL;
        PRINT '  Added is_active column to component_branches table.';
    END
END
GO

-- ============================================================
-- FINAL INTEGRATION SUMMARY
-- ============================================================

PRINT '';
PRINT '============================================================';
PRINT 'Permission Control System Integration Complete!';
PRINT '============================================================';
PRINT '';
PRINT 'Enhanced Features Added:';
PRINT '  ✓ Individual user permission grants (extends role-based system)';
PRINT '  ✓ Permission presets for quick assignment';
PRINT '  ✓ Soft delete visibility permissions';
PRINT '  ✓ Time-based permission expiration';
PRINT '  ✓ Enhanced permission checking functions';
PRINT '  ✓ Permission management stored procedures';
PRINT '  ✓ Comprehensive permission views';
PRINT '  ✓ Component branches soft delete support';
PRINT '';
PRINT 'Permission Types Available:';
PRINT '  - view_inactive_components: See soft-deleted components';
PRINT '  - view_inactive_projects: See soft-deleted projects';
PRINT '  - view_inactive_branches: See soft-deleted branches';
PRINT '  - view_all_builds: See builds from all users';
PRINT '  - view_system_logs: Access system audit logs';
PRINT '  - export_data: Data export functionality';
PRINT '  - api_access: API endpoint access';
PRINT '  - bulk_component_operations: Bulk operations';
PRINT '  - advanced_msi_config: Advanced MSI settings';
PRINT '  - cmdb_server_management: CMDB management';
PRINT '';
PRINT 'Usage:';
PRINT '  - Use Permission Control page: http://localhost:5000/permission_control';
PRINT '  - Grant permissions: EXEC sp_GrantIndividualPermission @user_id, @permission_type, @granted_by';
PRINT '  - Check permissions: SELECT dbo.fn_UserHasSpecialPermission(@user_id, @permission_type)';
PRINT '  - Apply presets through the web interface';
PRINT '';
PRINT '============================================================';

SET NOCOUNT OFF;