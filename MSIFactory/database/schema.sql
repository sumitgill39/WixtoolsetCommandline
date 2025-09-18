-- ============================================================
-- MSI Factory Database Schema
-- Version: 1.0
-- Created: 2024-09-14
-- Description: Complete database schema for MSI Factory system
-- ============================================================

-- Enable foreign key constraints
PRAGMA foreign_keys = ON;

-- ============================================================
-- USERS TABLE
-- Stores user account information and authentication data
-- ============================================================
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    domain VARCHAR(20) DEFAULT 'COMPANY',
    first_name VARCHAR(50) NOT NULL,
    middle_name VARCHAR(50),
    last_name VARCHAR(50) NOT NULL,
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'inactive', 'denied')),
    role VARCHAR(20) DEFAULT 'user' CHECK (role IN ('user', 'admin')),
    created_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    approved_date DATETIME,
    approved_by VARCHAR(50),
    last_login DATETIME,
    login_count INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT 1,
    FOREIGN KEY (approved_by) REFERENCES users(username)
);

-- ============================================================
-- PROJECTS TABLE
-- Stores project information and configuration
-- ============================================================
CREATE TABLE IF NOT EXISTS projects (
    project_id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_name VARCHAR(100) NOT NULL,
    project_key VARCHAR(20) UNIQUE NOT NULL,
    description TEXT,
    project_type VARCHAR(20) NOT NULL CHECK (project_type IN ('WebApp', 'Service', 'Website', 'Desktop', 'API')),
    owner_team VARCHAR(100) NOT NULL,
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'maintenance', 'archived')),
    color_primary VARCHAR(7) DEFAULT '#2c3e50',
    color_secondary VARCHAR(7) DEFAULT '#3498db',
    created_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(50) NOT NULL,
    updated_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_by VARCHAR(50),
    is_active BOOLEAN DEFAULT 1,
    FOREIGN KEY (created_by) REFERENCES users(username),
    FOREIGN KEY (updated_by) REFERENCES users(username)
);

-- ============================================================
-- PROJECT_ENVIRONMENTS TABLE
-- Stores available environments for each project
-- ============================================================
CREATE TABLE IF NOT EXISTS project_environments (
    env_id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    environment_name VARCHAR(20) NOT NULL CHECK (environment_name IN ('DEV', 'QA', 'UAT', 'PREPROD', 'PROD', 'SIT', 'DR')),
    environment_description VARCHAR(100),
    is_active BOOLEAN DEFAULT 1,
    created_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(project_id) ON DELETE CASCADE,
    UNIQUE(project_id, environment_name)
);

-- ============================================================
-- USER_PROJECTS TABLE
-- Many-to-many relationship between users and projects
-- ============================================================
CREATE TABLE IF NOT EXISTS user_projects (
    up_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    project_id INTEGER NOT NULL,
    access_level VARCHAR(20) DEFAULT 'user' CHECK (access_level IN ('user', 'admin', 'readonly')),
    granted_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    granted_by VARCHAR(50) NOT NULL,
    is_active BOOLEAN DEFAULT 1,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (project_id) REFERENCES projects(project_id) ON DELETE CASCADE,
    FOREIGN KEY (granted_by) REFERENCES users(username),
    UNIQUE(user_id, project_id)
);

-- ============================================================
-- ACCESS_REQUESTS TABLE
-- Stores user access requests for projects
-- ============================================================
CREATE TABLE IF NOT EXISTS access_requests (
    request_id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(50) NOT NULL,
    email VARCHAR(100) NOT NULL,
    first_name VARCHAR(50) NOT NULL,
    middle_name VARCHAR(50),
    last_name VARCHAR(50) NOT NULL,
    project_id INTEGER NOT NULL,
    reason TEXT,
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'denied')),
    requested_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    processed_date DATETIME,
    processed_by VARCHAR(50),
    denial_reason TEXT,
    FOREIGN KEY (project_id) REFERENCES projects(project_id),
    FOREIGN KEY (processed_by) REFERENCES users(username)
);

-- ============================================================
-- COMPONENTS TABLE
-- Stores individual components within projects
-- ============================================================
CREATE TABLE IF NOT EXISTS components (
    component_id INTEGER PRIMARY KEY AUTOINCREMENT,
    component_guid UNIQUEIDENTIFIER NOT NULL DEFAULT NEWID(),
    project_id INTEGER NOT NULL,
    component_name VARCHAR(100) NOT NULL,
    component_type VARCHAR(20) NOT NULL CHECK (component_type IN ('webapp', 'website', 'service', 'scheduler', 'api', 'desktop')),
    framework VARCHAR(20) NOT NULL CHECK (framework IN ('netframework', 'netcore', 'react', 'angular', 'python', 'static', 'vue')),
    artifact_source VARCHAR(255),
    deployment_script TEXT,
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'maintenance')),
    created_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(50) NOT NULL,
    updated_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_by VARCHAR(50),
    is_active BIT DEFAULT 1,
    FOREIGN KEY (project_id) REFERENCES projects(project_id) ON DELETE CASCADE,
    FOREIGN KEY (created_by) REFERENCES users(username),
    FOREIGN KEY (updated_by) REFERENCES users(username),
    UNIQUE(project_id, component_name)
);

-- ============================================================
-- COMPONENT_ENVIRONMENTS TABLE
-- Stores environment-specific settings for each component
-- ============================================================
CREATE TABLE IF NOT EXISTS component_environments (
    comp_env_id INTEGER PRIMARY KEY AUTOINCREMENT,
    component_id INTEGER NOT NULL,
    environment_name VARCHAR(20) NOT NULL CHECK (environment_name IN ('DEV', 'QA', 'UAT', 'PREPROD', 'PROD', 'SIT', 'DR')),
    install_path VARCHAR(255) NOT NULL,
    server_list TEXT, -- JSON array of servers for this component in this environment
    service_account_type VARCHAR(20) DEFAULT 'LocalSystem' CHECK (service_account_type IN ('LocalSystem', 'NetworkService', 'CustomUser')),
    service_account_username VARCHAR(100),
    app_pool_name VARCHAR(100),
    port_number INTEGER,
    ssl_enabled BIT DEFAULT 0,
    config_overrides TEXT, -- JSON object for environment-specific configurations
    is_active BIT DEFAULT 1,
    created_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (component_id) REFERENCES components(component_id) ON DELETE CASCADE,
    UNIQUE(component_id, environment_name)
);

-- ============================================================
-- MSI_BUILDS TABLE (Updated for component-level builds)
-- Stores MSI generation build history
-- ============================================================
CREATE TABLE IF NOT EXISTS msi_builds (
    build_id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id VARCHAR(50) UNIQUE NOT NULL,
    project_id INTEGER NOT NULL,
    component_id INTEGER, -- NULL for project-level builds, populated for component builds
    user_id INTEGER NOT NULL,
    component_type VARCHAR(20) NOT NULL,
    environments TEXT NOT NULL, -- JSON array of environments
    build_status VARCHAR(20) DEFAULT 'queued' CHECK (build_status IN ('queued', 'in_progress', 'completed', 'failed', 'cancelled')),
    start_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    end_time DATETIME,
    build_duration INTEGER, -- in seconds
    build_log TEXT,
    output_files TEXT, -- JSON array of generated files
    error_message TEXT,
    build_version VARCHAR(20),
    created_by VARCHAR(50) NOT NULL,
    FOREIGN KEY (project_id) REFERENCES projects(project_id),
    FOREIGN KEY (component_id) REFERENCES components(component_id),
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    FOREIGN KEY (created_by) REFERENCES users(username)
);

-- ============================================================
-- SYSTEM_LOGS TABLE
-- Stores system activity and audit logs
-- ============================================================
CREATE TABLE IF NOT EXISTS system_logs (
    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
    log_type VARCHAR(20) NOT NULL CHECK (log_type IN ('INFO', 'WARNING', 'ERROR', 'SECURITY', 'AUDIT')),
    event_type VARCHAR(50) NOT NULL,
    username VARCHAR(50),
    ip_address VARCHAR(45),
    user_agent TEXT,
    event_data TEXT, -- JSON data
    message TEXT NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    session_id VARCHAR(100),
    FOREIGN KEY (username) REFERENCES users(username)
);

-- ============================================================
-- USER_SESSIONS TABLE
-- Stores user session information
-- ============================================================
CREATE TABLE IF NOT EXISTS user_sessions (
    session_id VARCHAR(100) PRIMARY KEY,
    user_id INTEGER NOT NULL,
    username VARCHAR(50) NOT NULL,
    ip_address VARCHAR(45),
    user_agent TEXT,
    login_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_activity DATETIME DEFAULT CURRENT_TIMESTAMP,
    logout_time DATETIME,
    is_active BOOLEAN DEFAULT 1,
    session_data TEXT, -- JSON data
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    FOREIGN KEY (username) REFERENCES users(username)
);

-- ============================================================
-- SYSTEM_SETTINGS TABLE
-- Stores system configuration and settings
-- ============================================================
CREATE TABLE IF NOT EXISTS system_settings (
    setting_id INTEGER PRIMARY KEY AUTOINCREMENT,
    setting_key VARCHAR(50) UNIQUE NOT NULL,
    setting_value TEXT NOT NULL,
    setting_type VARCHAR(20) DEFAULT 'string' CHECK (setting_type IN ('string', 'integer', 'boolean', 'json')),
    description TEXT,
    category VARCHAR(30) DEFAULT 'general',
    is_encrypted BOOLEAN DEFAULT 0,
    created_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_by VARCHAR(50),
    FOREIGN KEY (updated_by) REFERENCES users(username)
);

-- ============================================================
-- APPLICATIONS TABLE (Legacy support)
-- Maintains compatibility with existing application structure
-- ============================================================
CREATE TABLE IF NOT EXISTS applications (
    app_id INTEGER PRIMARY KEY AUTOINCREMENT,
    app_short_key VARCHAR(20) UNIQUE NOT NULL,
    app_name VARCHAR(100) NOT NULL,
    description TEXT,
    owner_team VARCHAR(100) NOT NULL,
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'inactive')),
    created_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT 1
);

-- ============================================================
-- INDEXES FOR PERFORMANCE
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_status ON users(status);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);

CREATE INDEX IF NOT EXISTS idx_projects_key ON projects(project_key);
CREATE INDEX IF NOT EXISTS idx_projects_status ON projects(status);
CREATE INDEX IF NOT EXISTS idx_projects_type ON projects(project_type);

CREATE INDEX IF NOT EXISTS idx_user_projects_user ON user_projects(user_id);
CREATE INDEX IF NOT EXISTS idx_user_projects_project ON user_projects(project_id);

CREATE INDEX IF NOT EXISTS idx_access_requests_status ON access_requests(status);
CREATE INDEX IF NOT EXISTS idx_access_requests_username ON access_requests(username);

CREATE INDEX IF NOT EXISTS idx_components_project ON components(project_id);
CREATE INDEX IF NOT EXISTS idx_components_guid ON components(component_guid);
CREATE INDEX IF NOT EXISTS idx_components_type ON components(component_type);
CREATE INDEX IF NOT EXISTS idx_components_status ON components(status);

CREATE INDEX IF NOT EXISTS idx_comp_env_component ON component_environments(component_id);
CREATE INDEX IF NOT EXISTS idx_comp_env_environment ON component_environments(environment_name);

CREATE INDEX IF NOT EXISTS idx_msi_builds_project ON msi_builds(project_id);
CREATE INDEX IF NOT EXISTS idx_msi_builds_component ON msi_builds(component_id);
CREATE INDEX IF NOT EXISTS idx_msi_builds_user ON msi_builds(user_id);
CREATE INDEX IF NOT EXISTS idx_msi_builds_status ON msi_builds(build_status);
CREATE INDEX IF NOT EXISTS idx_msi_builds_job_id ON msi_builds(job_id);

CREATE INDEX IF NOT EXISTS idx_system_logs_type ON system_logs(log_type);
CREATE INDEX IF NOT EXISTS idx_system_logs_event ON system_logs(event_type);
CREATE INDEX IF NOT EXISTS idx_system_logs_username ON system_logs(username);
CREATE INDEX IF NOT EXISTS idx_system_logs_timestamp ON system_logs(timestamp);

CREATE INDEX IF NOT EXISTS idx_user_sessions_username ON user_sessions(username);
CREATE INDEX IF NOT EXISTS idx_user_sessions_active ON user_sessions(is_active);

-- ============================================================
-- TRIGGERS FOR AUTOMATIC UPDATES
-- ============================================================

-- Update projects.updated_date when project is modified
CREATE TRIGGER trigger_projects_updated
    ON projects
    AFTER UPDATE
AS
BEGIN
    UPDATE projects 
    SET updated_date = GETDATE() 
    WHERE project_id IN (SELECT project_id FROM inserted);
END;

-- Update components.updated_date when component is modified
CREATE TRIGGER trigger_components_updated
    ON components
    AFTER UPDATE
AS
BEGIN
    UPDATE components 
    SET updated_date = GETDATE() 
    WHERE component_id IN (SELECT component_id FROM inserted);
END;

-- Update user.login_count on successful login
CREATE TRIGGER trigger_user_login_count
    ON user_sessions
    AFTER INSERT
AS
BEGIN
    UPDATE users 
    SET login_count = login_count + 1,
        last_login = i.login_time
    FROM users u
    INNER JOIN inserted i ON u.user_id = i.user_id;
END;

-- Auto-approve user when first project is granted
CREATE TRIGGER trigger_user_auto_approve
    ON user_projects
    AFTER INSERT
AS
BEGIN
    UPDATE users 
    SET status = 'approved',
        approved_date = GETDATE(),
        approved_by = i.granted_by
    FROM users u
    INNER JOIN inserted i ON u.user_id = i.user_id
    WHERE u.status = 'pending';
END;

-- ============================================================
-- INITIAL DATA INSERTION
-- ============================================================

-- Insert default admin user
IF NOT EXISTS (SELECT 1 FROM users WHERE username = 'admin')
BEGIN
    INSERT INTO users (
        username, email, first_name, middle_name, last_name, 
        status, role, approved_date, approved_by
    ) VALUES (
        'admin', 'admin@company.com', 'System', '', 'Administrator', 
        'approved', 'admin', GETDATE(), 'system'
    );
END;

-- Insert default regular user
IF NOT EXISTS (SELECT 1 FROM users WHERE username = 'john.doe')
BEGIN
    INSERT INTO users (
        username, email, first_name, middle_name, last_name, 
        status, role, approved_date, approved_by
    ) VALUES (
        'john.doe', 'john.doe@company.com', 'John', 'M', 'Doe', 
        'approved', 'user', GETDATE(), 'admin'
    );
END;

-- Insert default projects
IF NOT EXISTS (SELECT 1 FROM projects WHERE project_key = 'WEBAPP01')
BEGIN
    INSERT INTO projects (
        project_name, project_key, description, project_type, owner_team,
        color_primary, color_secondary, created_by
    ) VALUES (
        'Customer Portal Web Application', 'WEBAPP01',
        'Customer-facing web portal for service requests and account management',
        'WebApp', 'Customer Experience Team',
        '#2c3e50', '#3498db', 'admin'
    );
END;

IF NOT EXISTS (SELECT 1 FROM projects WHERE project_key = 'PORTAL')
BEGIN
    INSERT INTO projects (
        project_name, project_key, description, project_type, owner_team,
        color_primary, color_secondary, created_by
    ) VALUES (
        'Employee Portal Website', 'PORTAL',
        'Internal employee self-service portal for HR and IT services',
        'Website', 'HR Technology',
        '#27ae60', '#2ecc71', 'admin'
    );
END;

IF NOT EXISTS (SELECT 1 FROM projects WHERE project_key = 'DATASYNC')
BEGIN
    INSERT INTO projects (
        project_name, project_key, description, project_type, owner_team,
        color_primary, color_secondary, created_by
    ) VALUES (
        'Data Synchronization Service', 'DATASYNC',
        'Background service for synchronizing data between systems',
        'Service', 'Integration Team',
        '#e74c3c', '#c0392b', 'admin'
    );
END;

-- Insert default environments for projects
INSERT INTO project_environments (project_id, environment_name, environment_description)
SELECT p.project_id, env.name, env.description
FROM projects p
CROSS JOIN (
    SELECT 'DEV' as name, 'Development Environment' as description
    UNION SELECT 'QA', 'Quality Assurance Environment'
    UNION SELECT 'UAT', 'User Acceptance Testing'
    UNION SELECT 'PROD', 'Production Environment'
    UNION SELECT 'PREPROD', 'Pre-Production Environment'
    UNION SELECT 'SIT', 'System Integration Testing'
    UNION SELECT 'DR', 'Disaster Recovery Environment'
) env
WHERE NOT EXISTS (
    SELECT 1 FROM project_environments pe2 
    WHERE pe2.project_id = p.project_id AND pe2.environment_name = env.name
);

-- Grant admin user access to all projects
INSERT INTO user_projects (user_id, project_id, access_level, granted_by)
SELECT u.user_id, p.project_id, 'admin', 'system'
FROM users u, projects p
WHERE u.username = 'admin'
AND NOT EXISTS (
    SELECT 1 FROM user_projects up2 
    WHERE up2.user_id = u.user_id AND up2.project_id = p.project_id
);

-- Grant john.doe access to specific projects
INSERT INTO user_projects (user_id, project_id, access_level, granted_by)
SELECT u.user_id, p.project_id, 'user', 'admin'
FROM users u, projects p
WHERE u.username = 'john.doe' AND p.project_key IN ('WEBAPP01', 'PORTAL')
AND NOT EXISTS (
    SELECT 1 FROM user_projects up2 
    WHERE up2.user_id = u.user_id AND up2.project_id = p.project_id
);

-- Insert legacy applications for compatibility
IF NOT EXISTS (SELECT 1 FROM applications WHERE app_short_key = 'WEBAPP01')
BEGIN
    INSERT INTO applications (app_short_key, app_name, description, owner_team)
    VALUES ('WEBAPP01', 'Customer Portal Web App', 'Customer-facing web portal', 'Customer Experience');
END;

IF NOT EXISTS (SELECT 1 FROM applications WHERE app_short_key = 'PORTAL')
BEGIN
    INSERT INTO applications (app_short_key, app_name, description, owner_team)
    VALUES ('PORTAL', 'Employee Portal Website', 'Employee self-service portal', 'HR Technology');
END;

IF NOT EXISTS (SELECT 1 FROM applications WHERE app_short_key = 'DATASYNC')
BEGIN
    INSERT INTO applications (app_short_key, app_name, description, owner_team)
    VALUES ('DATASYNC', 'Data Synchronization Service', 'Background data sync service', 'Integration Team');
END;

-- Insert default system settings
MERGE system_settings AS target
USING (VALUES 
    ('app_name', 'CelerDeploy', 'string', 'Application name displayed in UI', 'general'),
    ('app_version', '1.0.0', 'string', 'Current application version', 'general'),
    ('max_concurrent_builds', '5', 'integer', 'Maximum number of concurrent MSI builds', 'build'),
    ('build_timeout_minutes', '30', 'integer', 'Build timeout in minutes', 'build'),
    ('enable_audit_logging', 'true', 'boolean', 'Enable detailed audit logging', 'security'),
    ('session_timeout_hours', '8', 'integer', 'User session timeout in hours', 'security'),
    ('auto_approve_users', 'false', 'boolean', 'Automatically approve new user registrations', 'security')
) AS source (setting_key, setting_value, setting_type, description, category)
ON target.setting_key = source.setting_key
WHEN NOT MATCHED THEN
    INSERT (setting_key, setting_value, setting_type, description, category)
    VALUES (source.setting_key, source.setting_value, source.setting_type, source.description, source.category);

-- ============================================================
-- VIEWS FOR COMMON QUERIES
-- ============================================================

-- User summary view with project count
CREATE VIEW IF NOT EXISTS v_user_summary AS
SELECT 
    u.user_id,
    u.username,
    u.email,
    u.first_name || ' ' || u.last_name as full_name,
    u.role,
    u.status,
    u.login_count,
    u.last_login,
    COUNT(up.project_id) as project_count,
    u.created_date
FROM users u
LEFT JOIN user_projects up ON u.user_id = up.user_id AND up.is_active = 1
GROUP BY u.user_id;

-- Project summary view with user count
CREATE VIEW IF NOT EXISTS v_project_summary AS
SELECT 
    p.project_id,
    p.project_name,
    p.project_key,
    p.project_type,
    p.owner_team,
    p.status,
    COUNT(up.user_id) as user_count,
    COUNT(mb.build_id) as build_count,
    p.created_date
FROM projects p
LEFT JOIN user_projects up ON p.project_id = up.project_id AND up.is_active = 1
LEFT JOIN msi_builds mb ON p.project_id = mb.project_id
GROUP BY p.project_id;

-- Build history view with user, project, and component details
CREATE VIEW v_build_history AS
SELECT 
    mb.build_id,
    mb.job_id,
    p.project_name,
    p.project_key,
    c.component_name,
    c.component_guid,
    u.username,
    u.first_name + ' ' + u.last_name as user_name,
    mb.component_type,
    mb.environments,
    mb.build_status,
    mb.start_time,
    mb.end_time,
    mb.build_duration,
    mb.build_version
FROM msi_builds mb
JOIN projects p ON mb.project_id = p.project_id
LEFT JOIN components c ON mb.component_id = c.component_id
JOIN users u ON mb.user_id = u.user_id;

-- ============================================================
-- VERSION TRACKING
-- ============================================================
MERGE system_settings AS target
USING (VALUES ('database_schema_version', '2.0', 'string', 'Current database schema version', 'system'))
AS source (setting_key, setting_value, setting_type, description, category)
ON target.setting_key = source.setting_key
WHEN MATCHED THEN
    UPDATE SET setting_value = source.setting_value, updated_date = GETDATE()
WHEN NOT MATCHED THEN
    INSERT (setting_key, setting_value, setting_type, description, category)
    VALUES (source.setting_key, source.setting_value, source.setting_type, source.description, source.category);

-- ============================================================
-- INSERT SAMPLE COMPONENTS FOR EXISTING PROJECTS
-- ============================================================

-- Add sample components for Customer Portal (WEBAPP01)
INSERT INTO components (project_id, component_name, component_type, framework, artifact_source, created_by)
SELECT p.project_id, 'Customer Portal Web App', 'webapp', 'react', 'https://artifacts.company.com/WEBAPP01/webapp', 'admin'
FROM projects p 
WHERE p.project_key = 'WEBAPP01'
AND NOT EXISTS (SELECT 1 FROM components c WHERE c.project_id = p.project_id AND c.component_name = 'Customer Portal Web App');

INSERT INTO components (project_id, component_name, component_type, framework, artifact_source, created_by)
SELECT p.project_id, 'Customer Portal API', 'api', 'netcore', 'https://artifacts.company.com/WEBAPP01/api', 'admin'
FROM projects p 
WHERE p.project_key = 'WEBAPP01'
AND NOT EXISTS (SELECT 1 FROM components c WHERE c.project_id = p.project_id AND c.component_name = 'Customer Portal API');

-- Add sample components for Employee Portal (PORTAL)
INSERT INTO components (project_id, component_name, component_type, framework, artifact_source, created_by)
SELECT p.project_id, 'Employee Portal Website', 'website', 'angular', 'https://artifacts.company.com/PORTAL/website', 'admin'
FROM projects p 
WHERE p.project_key = 'PORTAL'
AND NOT EXISTS (SELECT 1 FROM components c WHERE c.project_id = p.project_id AND c.component_name = 'Employee Portal Website');

-- Add sample components for Data Sync (DATASYNC)
INSERT INTO components (project_id, component_name, component_type, framework, artifact_source, created_by)
SELECT p.project_id, 'Data Sync Service', 'service', 'netcore', 'https://artifacts.company.com/DATASYNC/service', 'admin'
FROM projects p 
WHERE p.project_key = 'DATASYNC'
AND NOT EXISTS (SELECT 1 FROM components c WHERE c.project_id = p.project_id AND c.component_name = 'Data Sync Service');

INSERT INTO components (project_id, component_name, component_type, framework, artifact_source, created_by)
SELECT p.project_id, 'Data Sync Scheduler', 'scheduler', 'netframework', 'https://artifacts.company.com/DATASYNC/scheduler', 'admin'
FROM projects p 
WHERE p.project_key = 'DATASYNC'
AND NOT EXISTS (SELECT 1 FROM components c WHERE c.project_id = p.project_id AND c.component_name = 'Data Sync Scheduler');

-- Add sample component environments for all components
INSERT INTO component_environments (component_id, environment_name, install_path, server_list, service_account_type)
SELECT c.component_id, env.name, env.path, env.servers, env.service_account
FROM components c
CROSS JOIN (
    SELECT 'DEV' as name, 'C:\inetpub\wwwroot\' + c2.component_name + '_dev' as path, '["dev-web01.company.com"]' as servers, 'NetworkService' as service_account
    UNION SELECT 'QA', 'C:\inetpub\wwwroot\' + c2.component_name + '_qa', '["qa-web01.company.com"]', 'NetworkService'
    UNION SELECT 'UAT', 'C:\inetpub\wwwroot\' + c2.component_name + '_uat', '["uat-web01.company.com"]', 'NetworkService'
    UNION SELECT 'PROD', 'C:\inetpub\wwwroot\' + c2.component_name, '["prod-web01.company.com", "prod-web02.company.com"]', 'CustomUser'
) env
CROSS JOIN components c2
WHERE c.component_id = c2.component_id
AND NOT EXISTS (
    SELECT 1 FROM component_environments ce 
    WHERE ce.component_id = c.component_id AND ce.environment_name = env.name
);

-- ============================================================
-- SCHEMA COMPLETE
-- ============================================================