-- ============================================================
-- MSI Factory Database Schema for MS SQL Server
-- Version: 3.0
-- Created: 2024-09-15
-- Updated: 2025-09-16
-- Description: Complete MS SQL Server schema for MSI Factory system
--              with GitFlow, JFrog integration, and comprehensive MSI configuration
-- ============================================================

-- Create database if it doesn't exist
IF NOT EXISTS (SELECT * FROM sys.databases WHERE name = 'MSIFactory')
BEGIN
    CREATE DATABASE MSIFactory;
END
GO

USE MSIFactory;
GO

-- ============================================================
-- CORE TABLES
-- ============================================================

-- ============================================================
-- USERS TABLE
-- Stores user account information and authentication data
-- ============================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='users' AND xtype='U')
CREATE TABLE users (
    user_id INT PRIMARY KEY IDENTITY(1,1),
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    domain VARCHAR(20) DEFAULT 'COMPANY',
    first_name VARCHAR(50) NOT NULL,
    middle_name VARCHAR(50),
    last_name VARCHAR(50) NOT NULL,
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'inactive', 'denied')),
    role VARCHAR(20) DEFAULT 'user' CHECK (role IN ('user', 'admin')),
    created_date DATETIME DEFAULT GETDATE(),
    approved_date DATETIME,
    approved_by VARCHAR(50),
    last_login DATETIME,
    login_count INT DEFAULT 0,
    is_active BIT DEFAULT 1
);
GO

-- ============================================================
-- PROJECTS TABLE
-- Stores project information and configuration
-- ============================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='projects' AND xtype='U')
CREATE TABLE projects (
    project_id INT PRIMARY KEY IDENTITY(1,1),
    project_guid UNIQUEIDENTIFIER DEFAULT NEWID(),
    project_name VARCHAR(100) NOT NULL,
    project_key VARCHAR(20) UNIQUE NOT NULL,
    description TEXT,
    project_type VARCHAR(20) NOT NULL CHECK (project_type IN ('WebApp', 'Service', 'Website', 'Desktop', 'API')),
    owner_team VARCHAR(100) NOT NULL,
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'maintenance', 'archived')),
    color_primary VARCHAR(7) DEFAULT '#2c3e50',
    color_secondary VARCHAR(7) DEFAULT '#3498db',
    
    -- Artifact Repository Configuration
    artifact_source_type VARCHAR(50),  -- http, ftp, jfrog, nexus
    artifact_url VARCHAR(500),
    artifact_username VARCHAR(100),
    artifact_password VARCHAR(100),  -- Should be encrypted in production
    
    -- Metadata
    created_date DATETIME DEFAULT GETDATE(),
    created_by VARCHAR(50) NOT NULL,
    updated_date DATETIME DEFAULT GETDATE(),
    updated_by VARCHAR(50),
    is_active BIT DEFAULT 1
);
GO

-- ============================================================
-- COMPONENTS TABLE
-- Stores component information for multi-component projects
-- ============================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='components' AND xtype='U')
CREATE TABLE components (
    component_id INT PRIMARY KEY IDENTITY(1,1),
    component_guid UNIQUEIDENTIFIER DEFAULT NEWID(),
    unique_guid UNIQUEIDENTIFIER DEFAULT NEWID(),  -- For folder naming
    project_id INT NOT NULL,
    component_name VARCHAR(100) NOT NULL,
    component_type VARCHAR(20) NOT NULL CHECK (component_type IN ('webapp', 'website', 'service', 'scheduler', 'api', 'desktop', 'library')),
    framework VARCHAR(20) NOT NULL CHECK (framework IN ('netframework', 'netcore', 'react', 'angular', 'python', 'static', 'vue', 'nodejs')),
    artifact_source VARCHAR(255),
    
    -- GitFlow Branch Tracking
    branch_name VARCHAR(100),
    polling_enabled BIT DEFAULT 1,
    last_poll_time DATETIME,
    last_artifact_version VARCHAR(100),
    last_download_path VARCHAR(500),
    last_extract_path VARCHAR(500),
    last_artifact_time DATETIME,
    
    -- Metadata
    created_date DATETIME DEFAULT GETDATE(),
    created_by VARCHAR(50) NOT NULL,
    FOREIGN KEY (project_id) REFERENCES projects(project_id) ON DELETE CASCADE
);
GO

-- ============================================================
-- PROJECT_ENVIRONMENTS TABLE
-- Stores environment configurations for projects
-- ============================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='project_environments' AND xtype='U')
CREATE TABLE project_environments (
    env_id INT PRIMARY KEY IDENTITY(1,1),
    project_id INT NOT NULL,
    environment_name VARCHAR(20) NOT NULL,
    environment_description VARCHAR(100),
    servers TEXT,  -- Comma-separated list of servers
    region VARCHAR(50),
    is_active BIT DEFAULT 1,
    created_date DATETIME DEFAULT GETDATE(),
    FOREIGN KEY (project_id) REFERENCES projects(project_id) ON DELETE CASCADE
);
GO

-- ============================================================
-- GITFLOW & ARTIFACT POLLING TABLES
-- ============================================================

-- ============================================================
-- BRANCH_MAPPINGS TABLE
-- GitFlow branch to repository path mappings
-- ============================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='branch_mappings' AND xtype='U')
CREATE TABLE branch_mappings (
    mapping_id INT IDENTITY(1,1) PRIMARY KEY,
    project_id INT,
    branch_pattern VARCHAR(100),
    repository_path VARCHAR(200),
    environment_type VARCHAR(50), -- dev, qa, staging, prod
    auto_deploy BIT DEFAULT 0,
    created_date DATETIME DEFAULT GETDATE(),
    FOREIGN KEY (project_id) REFERENCES projects(project_id)
);
GO

-- Insert default GitFlow patterns
IF NOT EXISTS (SELECT * FROM branch_mappings WHERE branch_pattern = 'develop')
BEGIN
    INSERT INTO branch_mappings (project_id, branch_pattern, repository_path, environment_type, auto_deploy)
    VALUES 
        (NULL, 'develop', '/snapshots/develop', 'dev', 1),
        (NULL, 'master', '/releases/stable', 'prod', 0),
        (NULL, 'main', '/releases/stable', 'prod', 0),
        (NULL, 'feature/*', '/feature-builds', 'dev', 1),
        (NULL, 'release/*', '/release-candidates', 'staging', 1),
        (NULL, 'hotfix/*', '/hotfixes', 'prod', 0);
END
GO

-- ============================================================
-- ARTIFACT_HISTORY TABLE
-- Tracks all downloaded artifacts
-- ============================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='artifact_history' AND xtype='U')
CREATE TABLE artifact_history (
    history_id INT IDENTITY(1,1) PRIMARY KEY,
    component_id INT,
    artifact_version VARCHAR(100),
    download_path VARCHAR(500),
    extract_path VARCHAR(500),
    download_time DATETIME,
    branch_name VARCHAR(100),
    artifact_size BIGINT,
    artifact_hash VARCHAR(100),
    FOREIGN KEY (component_id) REFERENCES components(component_id)
);
GO

-- Create indexes only if they don't exist
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_artifact_history_component' AND object_id = OBJECT_ID('artifact_history'))
    CREATE INDEX idx_artifact_history_component ON artifact_history(component_id);

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_artifact_history_time' AND object_id = OBJECT_ID('artifact_history'))
    CREATE INDEX idx_artifact_history_time ON artifact_history(download_time);
GO

-- ============================================================
-- POLLING_CONFIG TABLE
-- Component-specific polling settings
-- ============================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='polling_config' AND xtype='U')
CREATE TABLE polling_config (
    config_id INT IDENTITY(1,1) PRIMARY KEY,
    component_id INT UNIQUE,
    jfrog_repository VARCHAR(200),
    artifact_path_pattern VARCHAR(500),
    polling_interval_seconds INT DEFAULT 60,
    enabled BIT DEFAULT 1,
    last_successful_poll DATETIME,
    consecutive_failures INT DEFAULT 0,
    max_retries INT DEFAULT 3,
    created_date DATETIME DEFAULT GETDATE(),
    updated_date DATETIME DEFAULT GETDATE(),
    FOREIGN KEY (component_id) REFERENCES components(component_id)
);
GO

-- ============================================================
-- MSI CONFIGURATION TABLES
-- ============================================================

-- ============================================================
-- MSI_CONFIGURATIONS TABLE
-- Comprehensive MSI and deployment configuration per component
-- ============================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='msi_configurations' AND xtype='U')
CREATE TABLE msi_configurations (
    config_id INT IDENTITY(1,1) PRIMARY KEY,
    component_id INT UNIQUE NOT NULL,
    
    -- Basic MSI Properties
    unique_id UNIQUEIDENTIFIER DEFAULT NEWID(),
    app_name VARCHAR(255),
    app_version VARCHAR(50) DEFAULT '1.0.0.0',
    auto_increment_version BIT DEFAULT 1,
    manufacturer VARCHAR(255),
    upgrade_code UNIQUEIDENTIFIER,
    product_code UNIQUEIDENTIFIER,
    install_folder VARCHAR(500),
    
    -- Target Configuration
    target_server VARCHAR(255),
    target_environment VARCHAR(50), -- DEV, QA, UAT, PROD
    
    -- Component Type Specific
    component_type VARCHAR(50), -- WebApp, API, Service, Desktop
    
    -- IIS Configuration for WebApp/API
    iis_website_name VARCHAR(255),
    iis_app_path VARCHAR(255), -- Virtual directory path
    iis_app_pool_name VARCHAR(255),
    iis_port INT,
    iis_binding_info TEXT, -- JSON for complex bindings
    parent_website VARCHAR(255), -- For APIs under websites
    parent_webapp VARCHAR(255), -- For APIs under webapps
    
    -- App Pool Configuration
    app_pool_identity VARCHAR(100), -- ApplicationPoolIdentity, LocalSystem, etc
    app_pool_dotnet_version VARCHAR(20), -- v4.0, No Managed Code
    app_pool_pipeline_mode VARCHAR(20), -- Integrated, Classic
    app_pool_enable_32bit BIT DEFAULT 0,
    app_pool_start_mode VARCHAR(20), -- OnDemand, AlwaysRunning
    app_pool_idle_timeout INT DEFAULT 20,
    app_pool_recycling_schedule VARCHAR(500),
    
    -- Advanced IIS Settings
    enable_preload BIT DEFAULT 0,
    enable_anonymous_auth BIT DEFAULT 1,
    enable_windows_auth BIT DEFAULT 0,
    custom_headers TEXT, -- JSON format
    connection_strings TEXT, -- Encrypted JSON
    app_settings TEXT, -- Encrypted JSON
    
    -- Windows Service Configuration (for Service type)
    service_name VARCHAR(255),
    service_display_name VARCHAR(255),
    service_description TEXT,
    service_start_type VARCHAR(50), -- Automatic, Manual, Disabled
    service_account VARCHAR(255),
    service_password VARCHAR(500), -- Encrypted
    service_dependencies VARCHAR(500),
    
    -- MSI Features and Components
    features TEXT, -- JSON array of features
    registry_entries TEXT, -- JSON for registry modifications
    environment_variables TEXT, -- JSON for env vars
    shortcuts TEXT, -- JSON for shortcuts configuration
    
    -- Pre/Post Installation Scripts
    pre_install_script TEXT,
    post_install_script TEXT,
    pre_uninstall_script TEXT,
    post_uninstall_script TEXT,
    
    -- File System Permissions
    folder_permissions TEXT, -- JSON for ACL settings
    
    -- Metadata
    created_date DATETIME DEFAULT GETDATE(),
    created_by VARCHAR(100),
    updated_date DATETIME DEFAULT GETDATE(),
    updated_by VARCHAR(100),
    is_template BIT DEFAULT 0,
    template_name VARCHAR(100),
    
    FOREIGN KEY (component_id) REFERENCES components(component_id)
);
GO

-- Create indexes only if they don't exist
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_msi_config_component' AND object_id = OBJECT_ID('msi_configurations'))
    CREATE INDEX idx_msi_config_component ON msi_configurations(component_id);

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_msi_config_env' AND object_id = OBJECT_ID('msi_configurations'))
    CREATE INDEX idx_msi_config_env ON msi_configurations(target_environment);
GO

-- ============================================================
-- MSI_ENVIRONMENT_CONFIGS TABLE
-- Environment-specific configuration overrides
-- ============================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='msi_environment_configs' AND xtype='U')
CREATE TABLE msi_environment_configs (
    env_config_id INT IDENTITY(1,1) PRIMARY KEY,
    config_id INT NOT NULL,
    environment VARCHAR(50) NOT NULL,
    
    -- Environment-specific overrides
    target_server VARCHAR(255),
    install_folder VARCHAR(500),
    iis_website_name VARCHAR(255),
    iis_app_pool_name VARCHAR(255),
    iis_port INT,
    connection_strings TEXT,
    app_settings TEXT,
    service_account VARCHAR(255),
    
    -- Environment-specific metadata
    approved_by VARCHAR(100),
    approval_date DATETIME,
    notes TEXT,
    
    FOREIGN KEY (config_id) REFERENCES msi_configurations(config_id),
    UNIQUE(config_id, environment)
);
GO

-- Create index only if it doesn't exist
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_env_config' AND object_id = OBJECT_ID('msi_environment_configs'))
    CREATE INDEX idx_env_config ON msi_environment_configs(config_id, environment);
GO

-- ============================================================
-- IIS_ADVANCED_CONFIGS TABLE
-- Advanced IIS configuration settings
-- ============================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='iis_advanced_configs' AND xtype='U')
CREATE TABLE iis_advanced_configs (
    iis_config_id INT IDENTITY(1,1) PRIMARY KEY,
    config_id INT NOT NULL,
    
    -- URL Rewrite Rules
    url_rewrite_rules TEXT,
    
    -- MIME Types
    custom_mime_types TEXT, -- JSON format
    
    -- Compression Settings
    enable_static_compression BIT DEFAULT 1,
    enable_dynamic_compression BIT DEFAULT 0,
    compression_level INT DEFAULT 7,
    
    -- Caching Settings
    enable_kernel_cache BIT DEFAULT 1,
    enable_output_cache BIT DEFAULT 0,
    cache_control_custom VARCHAR(255),
    
    -- Request Filtering
    max_allowed_content_length BIGINT,
    max_url_length INT,
    max_query_string INT,
    file_extensions_denied TEXT,
    verbs_denied TEXT,
    
    -- Session State
    session_state_mode VARCHAR(50), -- InProc, StateServer, SQLServer
    session_timeout INT DEFAULT 20,
    cookie_settings TEXT, -- JSON
    
    -- Error Pages
    custom_error_pages TEXT, -- JSON format
    detailed_errors BIT DEFAULT 0,
    
    -- Logging
    log_file_directory VARCHAR(500),
    log_fields VARCHAR(500),
    log_period VARCHAR(50),
    
    -- SSL Settings
    require_ssl BIT DEFAULT 0,
    ssl_flags VARCHAR(100),
    client_cert_mode VARCHAR(50),
    
    FOREIGN KEY (config_id) REFERENCES msi_configurations(config_id)
);
GO

-- ============================================================
-- MSI_VERSION_HISTORY TABLE
-- Version tracking and release management
-- ============================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='msi_version_history' AND xtype='U')
CREATE TABLE msi_version_history (
    version_id INT IDENTITY(1,1) PRIMARY KEY,
    component_id INT NOT NULL,
    version_number VARCHAR(50) NOT NULL,
    build_number INT,
    product_code UNIQUEIDENTIFIER,
    msi_file_path VARCHAR(500),
    msi_file_size BIGINT,
    msi_file_hash VARCHAR(100),
    
    -- Build Information
    build_date DATETIME,
    build_by VARCHAR(100),
    build_machine VARCHAR(100),
    source_branch VARCHAR(100),
    source_commit VARCHAR(100),
    
    -- Deployment Information
    deployed_environments TEXT, -- JSON array
    deployment_notes TEXT,
    
    -- Status
    status VARCHAR(50), -- Draft, Testing, Released, Deprecated
    release_date DATETIME,
    deprecated_date DATETIME,
    
    FOREIGN KEY (component_id) REFERENCES components(component_id)
);
GO

-- Create index only if it doesn't exist
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_version_history' AND object_id = OBJECT_ID('msi_version_history'))
    CREATE INDEX idx_version_history ON msi_version_history(component_id, version_number);
GO

-- ============================================================
-- MSI_CONFIG_TEMPLATES TABLE
-- Reusable configuration templates
-- ============================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='msi_config_templates' AND xtype='U')
CREATE TABLE msi_config_templates (
    template_id INT IDENTITY(1,1) PRIMARY KEY,
    template_name VARCHAR(100) UNIQUE NOT NULL,
    template_description TEXT,
    component_type VARCHAR(50),
    
    -- Template Configuration (JSON)
    configuration TEXT NOT NULL,
    
    -- Metadata
    is_default BIT DEFAULT 0,
    created_date DATETIME DEFAULT GETDATE(),
    created_by VARCHAR(100),
    
    CHECK (component_type IN ('WebApp', 'API', 'Service', 'Desktop', 'Library'))
);
GO

-- Insert default templates
IF NOT EXISTS (SELECT * FROM msi_config_templates WHERE template_name = 'Default WebApp')
BEGIN
    INSERT INTO msi_config_templates (template_name, template_description, component_type, configuration, is_default)
    VALUES 
    ('Default WebApp', 'Standard web application configuration', 'WebApp', 
     '{"app_pool_dotnet_version":"v4.0","app_pool_pipeline_mode":"Integrated","enable_32bit":false}', 1),
    
    ('Default API', 'Standard API configuration', 'API',
     '{"app_pool_dotnet_version":"No Managed Code","app_pool_pipeline_mode":"Integrated","enable_preload":true}', 1),
    
    ('Default Service', 'Standard Windows service configuration', 'Service',
     '{"service_start_type":"Automatic","service_account":"LocalSystem"}', 1);
END
GO

-- ============================================================
-- BUILD & DEPLOYMENT TABLES
-- ============================================================

-- ============================================================
-- MSI_BUILD_QUEUE TABLE
-- Queue for MSI build tasks
-- ============================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='msi_build_queue' AND xtype='U')
CREATE TABLE msi_build_queue (
    queue_id INT IDENTITY(1,1) PRIMARY KEY,
    component_id INT,
    project_id INT,
    source_path VARCHAR(500),
    status VARCHAR(50),
    queued_time DATETIME,
    start_time DATETIME,
    end_time DATETIME,
    error_message TEXT,
    msi_output_path VARCHAR(500),
    build_log TEXT,
    priority INT DEFAULT 5,
    FOREIGN KEY (component_id) REFERENCES components(component_id),
    FOREIGN KEY (project_id) REFERENCES projects(project_id)
);
GO

-- Create indexes only if they don't exist
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_build_queue_status' AND object_id = OBJECT_ID('msi_build_queue'))
    CREATE INDEX idx_build_queue_status ON msi_build_queue(status);

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_build_queue_time' AND object_id = OBJECT_ID('msi_build_queue'))
    CREATE INDEX idx_build_queue_time ON msi_build_queue(queued_time);
GO

-- ============================================================
-- MSI_BUILDS TABLE
-- Stores MSI build history and status
-- ============================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='msi_builds' AND xtype='U')
CREATE TABLE msi_builds (
    build_id INT PRIMARY KEY IDENTITY(1,1),
    project_id INT NOT NULL,
    component_id INT,
    environment_name VARCHAR(50) NOT NULL,
    build_version VARCHAR(50),
    build_status VARCHAR(20) DEFAULT 'pending' CHECK (build_status IN ('pending', 'building', 'success', 'failed', 'cancelled')),
    msi_file_path VARCHAR(500),
    build_log TEXT,
    build_started DATETIME DEFAULT GETDATE(),
    build_completed DATETIME,
    built_by VARCHAR(50) NOT NULL,
    FOREIGN KEY (project_id) REFERENCES projects(project_id) ON DELETE CASCADE,
    FOREIGN KEY (component_id) REFERENCES components(component_id)
);
GO

-- ============================================================
-- ACCESS CONTROL & AUDIT TABLES
-- ============================================================

-- ============================================================
-- USER_PROJECTS TABLE
-- Stores user access permissions for projects
-- ============================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='user_projects' AND xtype='U')
CREATE TABLE user_projects (
    user_project_id INT PRIMARY KEY IDENTITY(1,1),
    user_id INT NOT NULL,
    project_id INT NOT NULL,
    access_level VARCHAR(20) DEFAULT 'read' CHECK (access_level IN ('read', 'write', 'admin')),
    granted_date DATETIME DEFAULT GETDATE(),
    granted_by VARCHAR(50),
    is_active BIT DEFAULT 1,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (project_id) REFERENCES projects(project_id) ON DELETE CASCADE
);
GO

-- ============================================================
-- SYSTEM_LOGS TABLE
-- Comprehensive audit trail and system logging
-- ============================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='system_logs' AND xtype='U')
CREATE TABLE system_logs (
    log_id INT PRIMARY KEY IDENTITY(1,1),
    log_level VARCHAR(10) NOT NULL CHECK (log_level IN ('INFO', 'WARNING', 'ERROR', 'DEBUG')),
    log_category VARCHAR(50) NOT NULL,
    message TEXT NOT NULL,
    username VARCHAR(50),
    ip_address VARCHAR(45),
    user_agent TEXT,
    additional_data TEXT,
    created_date DATETIME DEFAULT GETDATE()
);
GO

-- ============================================================
-- USER_SESSIONS TABLE
-- Active session management
-- ============================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='user_sessions' AND xtype='U')
CREATE TABLE user_sessions (
    session_id VARCHAR(100) PRIMARY KEY,
    user_id INT NOT NULL,
    username VARCHAR(50) NOT NULL,
    login_time DATETIME DEFAULT GETDATE(),
    last_activity DATETIME DEFAULT GETDATE(),
    ip_address VARCHAR(45),
    user_agent TEXT,
    is_active BIT DEFAULT 1,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);
GO

-- ============================================================
-- LEGACY/COMPATIBILITY TABLES
-- ============================================================

-- ============================================================
-- COMPONENT_ENVIRONMENTS TABLE
-- Stores environment-specific component configurations
-- ============================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='component_environments' AND xtype='U')
CREATE TABLE component_environments (
    config_id INT PRIMARY KEY IDENTITY(1,1),
    component_id INT NOT NULL,
    environment_id INT NOT NULL,
    artifact_url VARCHAR(500),
    deployment_path VARCHAR(255),
    configuration_json TEXT,
    is_active BIT DEFAULT 1,
    created_date DATETIME DEFAULT GETDATE(),
    FOREIGN KEY (component_id) REFERENCES components(component_id) ON DELETE NO ACTION,
    FOREIGN KEY (environment_id) REFERENCES project_environments(env_id) ON DELETE NO ACTION
);
GO

-- ============================================================
-- INDEXES FOR PERFORMANCE
-- ============================================================
-- Create indexes only if they don't exist
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_users_username' AND object_id = OBJECT_ID('users'))
    CREATE INDEX idx_users_username ON users(username);

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_users_email' AND object_id = OBJECT_ID('users'))
    CREATE INDEX idx_users_email ON users(email);

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_projects_key' AND object_id = OBJECT_ID('projects'))
    CREATE INDEX idx_projects_key ON projects(project_key);

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_components_project' AND object_id = OBJECT_ID('components'))
    CREATE INDEX idx_components_project ON components(project_id);

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_components_branch' AND object_id = OBJECT_ID('components'))
    CREATE INDEX idx_components_branch ON components(branch_name);

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_system_logs_date' AND object_id = OBJECT_ID('system_logs'))
    CREATE INDEX idx_system_logs_date ON system_logs(created_date);

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_user_sessions_user' AND object_id = OBJECT_ID('user_sessions'))
    CREATE INDEX idx_user_sessions_user ON user_sessions(user_id);
GO

-- ============================================================
-- SAMPLE DATA
-- Insert default users and sample data
-- ============================================================

-- Insert default admin user
IF NOT EXISTS (SELECT * FROM users WHERE username = 'admin')
INSERT INTO users (username, email, first_name, last_name, status, role, created_date, approved_date, approved_by, is_active)
VALUES ('admin', 'admin@company.com', 'System', 'Administrator', 'approved', 'admin', GETDATE(), GETDATE(), 'system', 1);

-- Insert sample regular user
IF NOT EXISTS (SELECT * FROM users WHERE username = 'john.doe')
INSERT INTO users (username, email, first_name, last_name, status, role, created_date, approved_date, approved_by, is_active)
VALUES ('john.doe', 'john.doe@company.com', 'John', 'Doe', 'approved', 'user', GETDATE(), GETDATE(), 'admin', 1);

-- Insert sample project with components
IF NOT EXISTS (SELECT * FROM projects WHERE project_key = 'DEMO01')
BEGIN
    INSERT INTO projects (project_name, project_key, description, project_type, owner_team, status, 
                         artifact_source_type, artifact_url, created_by)
    VALUES ('Demo E-commerce Platform', 'DEMO01', 
            'Complete e-commerce solution with multiple components', 'WebApp', 'Development Team', 'active',
            'jfrog', 'https://artifactory.example.com/artifactory', 'admin');
    
    DECLARE @project_id INT = SCOPE_IDENTITY();
    
    -- Insert components for the demo project
    INSERT INTO components (project_id, component_name, component_type, framework, 
                           artifact_source, branch_name, created_by)
    VALUES 
        (@project_id, 'Web Frontend', 'webapp', 'react', 
         'artifactory://frontend-builds', 'develop', 'admin'),
        (@project_id, 'API Backend', 'api', 'netcore', 
         'artifactory://api-builds', 'develop', 'admin'),
        (@project_id, 'Background Service', 'service', 'netframework', 
         'artifactory://service-builds', 'master', 'admin');
    
    -- Insert environments with dynamic naming support
    INSERT INTO project_environments (project_id, environment_name, environment_description, servers, region)
    VALUES 
        (@project_id, 'DEV1', 'Development Environment 1', 'DEVSERVER01,DEVSERVER02', 'US-EAST'),
        (@project_id, 'DEV2', 'Development Environment 2', 'DEVSERVER03', 'US-WEST'),
        (@project_id, 'QA1', 'Quality Assurance Environment 1', 'QASERVER01', 'US-EAST'),
        (@project_id, 'UAT1', 'User Acceptance Testing', 'UATSERVER01', 'EU-WEST'),
        (@project_id, 'PROD_USA', 'Production USA Environment', 'PRODSERVER01,PRODSERVER02,PRODSERVER03', 'US-EAST'),
        (@project_id, 'PROD_EU', 'Production Europe Environment', 'EUPRODSERVER01,EUPRODSERVER02', 'EU-CENTRAL');
END
GO

-- ============================================================
-- STORED PROCEDURES FOR COMMON OPERATIONS
-- ============================================================

-- Get next version number for a component
IF EXISTS (SELECT * FROM sys.objects WHERE type = 'P' AND name = 'sp_GetNextVersion')
    DROP PROCEDURE sp_GetNextVersion
GO

CREATE PROCEDURE sp_GetNextVersion
    @component_id INT,
    @next_version VARCHAR(50) OUTPUT
AS
BEGIN
    DECLARE @current_version VARCHAR(50)
    
    SELECT TOP 1 @current_version = version_number
    FROM msi_version_history
    WHERE component_id = @component_id
    ORDER BY version_id DESC
    
    IF @current_version IS NULL
        SET @next_version = '1.0.0.0'
    ELSE
    BEGIN
        -- Parse and increment version
        DECLARE @major INT, @minor INT, @build INT, @revision INT
        
        SET @major = PARSENAME(@current_version, 4)
        SET @minor = PARSENAME(@current_version, 3)
        SET @build = PARSENAME(@current_version, 2)
        SET @revision = PARSENAME(@current_version, 1) + 1
        
        IF @revision > 9999
        BEGIN
            SET @revision = 0
            SET @build = @build + 1
        END
        
        SET @next_version = CAST(@major AS VARCHAR) + '.' + 
                           CAST(@minor AS VARCHAR) + '.' + 
                           CAST(@build AS VARCHAR) + '.' + 
                           CAST(@revision AS VARCHAR)
    END
END
GO

-- ============================================================
-- FINAL SETUP
-- ============================================================
PRINT '============================================================'
PRINT 'MSI Factory database schema v3.0 created successfully'
PRINT 'Features included:'
PRINT '  ✓ Core user and project management'
PRINT '  ✓ Multi-component support with unique GUIDs'
PRINT '  ✓ Dynamic environment configurations'
PRINT '  ✓ GitFlow branch tracking'
PRINT '  ✓ JFrog artifact polling'
PRINT '  ✓ Comprehensive MSI configuration'
PRINT '  ✓ IIS and Windows Service settings'
PRINT '  ✓ Version history and templates'
PRINT '  ✓ Build queue management'
PRINT '  ✓ Audit logging and session management'
PRINT '============================================================'
GO