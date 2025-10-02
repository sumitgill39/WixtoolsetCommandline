-- MSI Factory Role-Based Authorization System Update
-- This script adds PowerUser role and creates permission management system

-- Step 1: Update users table to support PowerUser role
ALTER TABLE users DROP CONSTRAINT IF EXISTS CK__users__role;
ALTER TABLE users ADD CONSTRAINT CK__users__role
CHECK (role IN ('user', 'admin', 'poweruser'));

-- Step 2: Create permissions table for fine-grained access control
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[user_permissions]') AND type in (N'U'))
BEGIN
    CREATE TABLE user_permissions (
        permission_id INT PRIMARY KEY IDENTITY(1,1),
        permission_name VARCHAR(100) NOT NULL UNIQUE,
        permission_description VARCHAR(255),
        module_name VARCHAR(50) NOT NULL, -- components, projects, users, msi, cmdb
        action_type VARCHAR(50) NOT NULL, -- create, read, update, delete, enable_disable
        is_active BIT DEFAULT 1,
        created_date DATETIME DEFAULT GETDATE()
    );
END;

-- Step 3: Create role_permissions mapping table
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[role_permissions]') AND type in (N'U'))
BEGIN
    CREATE TABLE role_permissions (
        role_permission_id INT PRIMARY KEY IDENTITY(1,1),
        role_name VARCHAR(20) NOT NULL,
        permission_id INT NOT NULL,
        is_granted BIT DEFAULT 1,
        created_date DATETIME DEFAULT GETDATE(),
        FOREIGN KEY (permission_id) REFERENCES user_permissions(permission_id),
        UNIQUE(role_name, permission_id)
    );
END;

-- Step 4: Insert core permissions
INSERT INTO user_permissions (permission_name, permission_description, module_name, action_type) VALUES
-- Component Management Permissions
('component_create', 'Create new components', 'components', 'create'),
('component_read', 'View component details', 'components', 'read'),
('component_update', 'Update component information', 'components', 'update'),
('component_delete', 'Delete components (soft delete)', 'components', 'delete'),
('component_enable_disable', 'Enable or disable components', 'components', 'enable_disable'),

-- Project Management Permissions
('project_create', 'Create new projects', 'projects', 'create'),
('project_read', 'View project details', 'projects', 'read'),
('project_update', 'Update project information', 'projects', 'update'),
('project_delete', 'Delete projects', 'projects', 'delete'),

-- User Management Permissions
('user_create', 'Create new users', 'users', 'create'),
('user_read', 'View user details', 'users', 'read'),
('user_update', 'Update user information', 'users', 'update'),
('user_delete', 'Delete users', 'users', 'delete'),
('user_role_manage', 'Manage user roles and permissions', 'users', 'role_manage'),

-- MSI Generation Permissions
('msi_generate', 'Generate MSI packages', 'msi', 'create'),
('msi_configure', 'Configure MSI settings', 'msi', 'update'),
('msi_view', 'View MSI status and logs', 'msi', 'read'),

-- CMDB Management Permissions
('cmdb_create', 'Create CMDB entries', 'cmdb', 'create'),
('cmdb_read', 'View CMDB information', 'cmdb', 'read'),
('cmdb_update', 'Update CMDB entries', 'cmdb', 'update'),
('cmdb_delete', 'Delete CMDB entries', 'cmdb', 'delete'),

-- System Administration Permissions
('system_logs', 'View system logs', 'system', 'read'),
('system_settings', 'Manage system settings', 'system', 'update');

-- Step 5: Assign permissions to roles

-- USER ROLE (Read-only access)
INSERT INTO role_permissions (role_name, permission_id)
SELECT 'user', permission_id FROM user_permissions
WHERE action_type = 'read';

-- POWERUSER ROLE (Technical Project Managers - Component CRUD + some project access)
INSERT INTO role_permissions (role_name, permission_id)
SELECT 'poweruser', permission_id FROM user_permissions
WHERE permission_name IN (
    'component_create', 'component_read', 'component_update', 'component_delete', 'component_enable_disable',
    'project_read', 'project_update',
    'msi_generate', 'msi_configure', 'msi_view',
    'cmdb_read', 'cmdb_update'
);

-- ADMIN ROLE (Full access to everything)
INSERT INTO role_permissions (role_name, permission_id)
SELECT 'admin', permission_id FROM user_permissions;

-- Step 6: Create audit table for permission changes
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[user_permission_audit]') AND type in (N'U'))
BEGIN
    CREATE TABLE user_permission_audit (
        audit_id INT PRIMARY KEY IDENTITY(1,1),
        user_id INT NOT NULL,
        old_role VARCHAR(20),
        new_role VARCHAR(20),
        changed_by VARCHAR(50),
        change_reason VARCHAR(255),
        change_date DATETIME DEFAULT GETDATE(),
        FOREIGN KEY (user_id) REFERENCES users(user_id)
    );
END;

-- Step 7: Insert sample PowerUser (Technical Project Manager)
-- Check if PowerUser doesn't already exist before inserting
IF NOT EXISTS (SELECT 1 FROM users WHERE username = 'tech.pm' OR email = 'tech.pm@msifactory.com')
BEGIN
    INSERT INTO users (username, email, first_name, last_name, role, status, is_active)
    VALUES ('tech.pm', 'tech.pm@msifactory.com', 'Technical', 'Project Manager', 'poweruser', 'approved', 1);
    PRINT 'PowerUser "tech.pm" created successfully';
END
ELSE
BEGIN
    PRINT 'PowerUser already exists, skipping creation';
END

-- Optional: Create additional PowerUsers (uncomment and modify as needed)
-- IF NOT EXISTS (SELECT 1 FROM users WHERE username = 'dev.lead')
-- BEGIN
--     INSERT INTO users (username, email, first_name, last_name, role, status, is_active)
--     VALUES ('dev.lead', 'dev.lead@msifactory.com', 'Development', 'Lead', 'poweruser', 'approved', 1);
-- END

-- Step 8: Create view for easy permission checking
GO
CREATE OR ALTER VIEW v_user_permissions AS
SELECT
    u.user_id,
    u.username,
    u.role,
    up.permission_name,
    up.module_name,
    up.action_type,
    up.permission_description
FROM users u
JOIN role_permissions rp ON u.role = rp.role_name
JOIN user_permissions up ON rp.permission_id = up.permission_id
WHERE u.is_active = 1 AND rp.is_granted = 1 AND up.is_active = 1;

GO
-- Step 9: Create function to check user permissions
CREATE OR ALTER FUNCTION dbo.CheckUserPermission(
    @username VARCHAR(50),
    @permission_name VARCHAR(100)
)
RETURNS BIT
AS
BEGIN
    DECLARE @hasPermission BIT = 0;

    SELECT @hasPermission = 1
    FROM v_user_permissions
    WHERE username = @username AND permission_name = @permission_name;

    RETURN ISNULL(@hasPermission, 0);
END;

GO

-- Verification queries
SELECT 'Role Distribution' as Info, role, COUNT(*) as count FROM users GROUP BY role;
SELECT 'Total Permissions' as Info, COUNT(*) as count FROM user_permissions;
SELECT 'Role Permission Mappings' as Info, role_name, COUNT(*) as permission_count FROM role_permissions GROUP BY role_name;

PRINT 'Role-based authorization system successfully updated!';
PRINT 'Roles: user (read-only), poweruser (component CRUD), admin (full access)';