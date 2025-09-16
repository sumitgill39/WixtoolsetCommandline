-- ============================================================
-- MSI Factory Complete Baseline Database Schema for MS SQL Server
-- Version: 4.0
-- Created: 2024-09-15
-- Updated: 2025-09-16
-- Description: Complete production-ready MS SQL Server baseline schema for MSI Factory system
--              with GitFlow, JFrog integration, comprehensive MSI configuration,
--              enhanced error handling, validation, and performance optimizations
-- 
-- USAGE:
-- This script is designed to be run on a fresh SQL Server instance to create
-- the complete MSI Factory database. It can be safely re-run without data loss.
-- ============================================================

SET NOCOUNT ON;
GO

-- ============================================================
-- ENVIRONMENT VALIDATION
-- ============================================================
PRINT 'MSI Factory Baseline Schema v4.0 - Starting Installation...'
PRINT 'Checking SQL Server environment...'

-- Check SQL Server version
DECLARE @sql_version VARCHAR(50) = @@VERSION;
DECLARE @version_year INT = 
    CASE 
        WHEN @sql_version LIKE '%2019%' THEN 2019
        WHEN @sql_version LIKE '%2017%' THEN 2017
        WHEN @sql_version LIKE '%2016%' THEN 2016
        WHEN @sql_version LIKE '%2014%' THEN 2014
        WHEN @sql_version LIKE '%2012%' THEN 2012
        ELSE 2008
    END;

IF @version_year < 2012
BEGIN
    PRINT 'ERROR: SQL Server 2012 or later is required. Current version not supported.';
    RAISERROR('Unsupported SQL Server version', 16, 1);
    RETURN;
END

PRINT 'SQL Server version check passed: ' + CAST(@version_year AS VARCHAR(4));

-- ============================================================
-- DATABASE CREATION WITH ENHANCED SETTINGS
-- ============================================================
IF NOT EXISTS (SELECT * FROM sys.databases WHERE name = 'MSIFactory')
BEGIN
    PRINT 'Creating MSIFactory database...';
    CREATE DATABASE MSIFactory;
    PRINT 'Database MSIFactory created successfully.';
END
ELSE
BEGIN
    PRINT 'Database MSIFactory already exists. Continuing with schema updates...';
END
GO

USE MSIFactory;
GO

-- ============================================================
-- DATABASE CONFIGURATION
-- ============================================================
PRINT 'Configuring database settings...';

-- Set database options for better performance and reliability
ALTER DATABASE MSIFactory SET RECOVERY SIMPLE;
ALTER DATABASE MSIFactory SET AUTO_SHRINK OFF;
ALTER DATABASE MSIFactory SET AUTO_CREATE_STATISTICS ON;
ALTER DATABASE MSIFactory SET AUTO_UPDATE_STATISTICS ON;
ALTER DATABASE MSIFactory SET PAGE_VERIFY CHECKSUM;

PRINT 'Database configuration completed.'
GO

-- ============================================================
-- CORE TABLES
-- ============================================================

PRINT 'Creating core tables...';

-- ============================================================
-- USERS TABLE
-- Stores user account information and authentication data
-- ============================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='users' AND xtype='U')
BEGIN
    PRINT 'Creating users table...';
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
    is_active BIT DEFAULT 1,
    password_hash VARCHAR(255), -- For future use
    password_salt VARCHAR(255), -- For future use
    last_password_change DATETIME,
    failed_login_attempts INT DEFAULT 0,
    account_locked_until DATETIME,
    
    -- Constraints
    CONSTRAINT CK_users_email_format CHECK (email LIKE '%@%.%'),
    CONSTRAINT CK_users_names_not_empty CHECK (LEN(TRIM(first_name)) > 0 AND LEN(TRIM(last_name)) > 0)
    );
    PRINT 'Users table created successfully.';
END
ELSE
BEGIN
    PRINT 'Users table already exists.';
END
GO

-- ============================================================
-- PROJECTS TABLE  
-- Stores project information and configuration
-- ============================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='projects' AND xtype='U')
BEGIN
    PRINT 'Creating projects table...';
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
    is_active BIT DEFAULT 1,
    artifact_api_key VARCHAR(255),   -- For API-based authentication
    auto_version_increment BIT DEFAULT 1,
    default_environment VARCHAR(20) DEFAULT 'DEV',
    notification_email VARCHAR(500), -- Comma-separated emails
    
    -- Constraints
    CONSTRAINT CK_projects_key_format CHECK (project_key LIKE '[A-Z]%' AND LEN(project_key) >= 3),
    CONSTRAINT CK_projects_colors CHECK (color_primary LIKE '#[0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f]')
    );
    PRINT 'Projects table created successfully.';
END
ELSE
BEGIN
    PRINT 'Projects table already exists.';
END
GO

-- ============================================================
-- COMPONENTS TABLE
-- Stores component information for multi-component projects
-- ============================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='components' AND xtype='U')
BEGIN
    PRINT 'Creating components table...';
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
    
    -- Component Settings
    is_enabled BIT DEFAULT 1 NOT NULL,
    order_index INT DEFAULT 1,
    dependencies VARCHAR(500), -- JSON array of component dependencies
    
    -- Metadata
    created_date DATETIME DEFAULT GETDATE(),
    created_by VARCHAR(50) NOT NULL,
    updated_date DATETIME DEFAULT GETDATE(),
    updated_by VARCHAR(50),
    
    FOREIGN KEY (project_id) REFERENCES projects(project_id) ON DELETE CASCADE,
    
    -- Constraints
    CONSTRAINT CK_components_name_not_empty CHECK (LEN(TRIM(component_name)) > 0),
    CONSTRAINT UK_components_project_name UNIQUE (project_id, component_name)
    );
    PRINT 'Components table created successfully.';
END
ELSE
BEGIN
    PRINT 'Components table already exists.';
END
GO

-- ============================================================
-- PROJECT_ENVIRONMENTS TABLE
-- Stores environment configurations for projects
-- ============================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='project_environments' AND xtype='U')
BEGIN
    PRINT 'Creating project_environments table...';
    CREATE TABLE project_environments (
    env_id INT PRIMARY KEY IDENTITY(1,1),
    project_id INT NOT NULL,
    environment_name VARCHAR(20) NOT NULL,
    environment_description VARCHAR(100),
    servers TEXT,  -- Comma-separated list of servers
    region VARCHAR(50),
    is_active BIT DEFAULT 1,
    environment_type VARCHAR(20) CHECK (environment_type IN ('development', 'testing', 'staging', 'production')),
    order_index INT DEFAULT 1,
    created_date DATETIME DEFAULT GETDATE(),
    
    FOREIGN KEY (project_id) REFERENCES projects(project_id) ON DELETE CASCADE,
    CONSTRAINT UK_project_env_name UNIQUE (project_id, environment_name)
    );
    PRINT 'Project environments table created successfully.';
END
ELSE
BEGIN
    PRINT 'Project environments table already exists.';
END
GO

-- ============================================================
-- GITFLOW & ARTIFACT POLLING TABLES
-- ============================================================

PRINT 'Creating GitFlow and artifact polling tables...';

-- ============================================================
-- BRANCH_MAPPINGS TABLE
-- GitFlow branch to repository path mappings
-- ============================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='branch_mappings' AND xtype='U')
BEGIN
    PRINT 'Creating branch_mappings table...';
    CREATE TABLE branch_mappings (
    mapping_id INT IDENTITY(1,1) PRIMARY KEY,
    project_id INT,
    branch_pattern VARCHAR(100),
    repository_path VARCHAR(200),
    environment_type VARCHAR(50), -- dev, qa, staging, prod
    auto_deploy BIT DEFAULT 0,
    priority INT DEFAULT 5,
    is_active BIT DEFAULT 1 NOT NULL,
    created_date DATETIME DEFAULT GETDATE(),
    
    FOREIGN KEY (project_id) REFERENCES projects(project_id) ON DELETE CASCADE
    );
    PRINT 'Branch mappings table created successfully.';
END
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
BEGIN
    PRINT 'Creating artifact_history table...';
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
    status VARCHAR(20) DEFAULT 'downloaded' CHECK (status IN ('downloading', 'downloaded', 'extracted', 'failed', 'deleted')),
    error_message TEXT,
    
    FOREIGN KEY (component_id) REFERENCES components(component_id) ON DELETE CASCADE
    );
    PRINT 'Artifact history table created successfully.';
END
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
BEGIN
    PRINT 'Creating polling_config table...';
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
    timeout_seconds INT DEFAULT 300,
    notification_on_success BIT DEFAULT 0,
    notification_on_failure BIT DEFAULT 1,
    created_date DATETIME DEFAULT GETDATE(),
    updated_date DATETIME DEFAULT GETDATE(),
    
    FOREIGN KEY (component_id) REFERENCES components(component_id) ON DELETE CASCADE,
    
    CONSTRAINT CK_polling_interval CHECK (polling_interval_seconds >= 30),
    CONSTRAINT CK_max_retries CHECK (max_retries >= 0),
    CONSTRAINT CK_timeout CHECK (timeout_seconds > 0)
    );
    PRINT 'Polling config table created successfully.';
END
GO

-- ============================================================
-- MSI CONFIGURATION TABLES
-- ============================================================

PRINT 'Creating MSI configuration tables...';

-- ============================================================
-- MSI_CONFIGURATIONS TABLE
-- Comprehensive MSI and deployment configuration per component
-- ============================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='msi_configurations' AND xtype='U')
BEGIN
    PRINT 'Creating msi_configurations table...';
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
    is_active BIT DEFAULT 1,
    
    FOREIGN KEY (component_id) REFERENCES components(component_id) ON DELETE CASCADE,
    
    CONSTRAINT CK_msi_port CHECK (iis_port IS NULL OR (iis_port BETWEEN 1 AND 65535)),
    CONSTRAINT CK_msi_pipeline CHECK (app_pool_pipeline_mode IS NULL OR app_pool_pipeline_mode IN ('Integrated', 'Classic')),
    CONSTRAINT CK_msi_start_mode CHECK (app_pool_start_mode IS NULL OR app_pool_start_mode IN ('OnDemand', 'AlwaysRunning')),
    CONSTRAINT CK_service_start CHECK (service_start_type IS NULL OR service_start_type IN ('Automatic', 'Manual', 'Disabled'))
    );
    PRINT 'MSI configurations table created successfully.';
END
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
-- VIEWS FOR COMMON QUERIES
-- ============================================================

PRINT 'Creating views...';

-- Component details with project info
IF EXISTS (SELECT * FROM sys.views WHERE name = 'vw_component_details')
    DROP VIEW vw_component_details
GO

CREATE VIEW vw_component_details
AS
SELECT 
    c.component_id,
    c.component_guid,
    c.unique_guid,
    c.component_name,
    c.component_type,
    c.framework,
    c.is_enabled,
    p.project_id,
    p.project_name,
    p.project_key,
    p.project_type,
    p.owner_team,
    p.status as project_status,
    mc.config_id,
    mc.unique_id as msi_unique_id,
    mc.app_name,
    mc.app_version,
    mc.target_environment,
    c.created_date,
    c.created_by
FROM components c
INNER JOIN projects p ON c.project_id = p.project_id
LEFT JOIN msi_configurations mc ON c.component_id = mc.component_id
WHERE c.is_enabled = 1 AND p.is_active = 1
GO

-- ============================================================
-- HEALTH CHECK PROCEDURE
-- ============================================================

IF EXISTS (SELECT * FROM sys.objects WHERE type = 'P' AND name = 'sp_HealthCheck')
    DROP PROCEDURE sp_HealthCheck
GO

CREATE PROCEDURE sp_HealthCheck
AS
BEGIN
    SET NOCOUNT ON;
    
    DECLARE @results TABLE (
        check_name VARCHAR(100),
        status VARCHAR(20),
        details VARCHAR(500)
    );
    
    -- Check table counts
    INSERT INTO @results SELECT 'Users Count', 'OK', CAST(COUNT(*) AS VARCHAR) + ' users' FROM users;
    INSERT INTO @results SELECT 'Projects Count', 'OK', CAST(COUNT(*) AS VARCHAR) + ' projects' FROM projects;
    INSERT INTO @results SELECT 'Components Count', 'OK', CAST(COUNT(*) AS VARCHAR) + ' components' FROM components;
    
    -- Check for orphaned records
    IF EXISTS (SELECT 1 FROM components c LEFT JOIN projects p ON c.project_id = p.project_id WHERE p.project_id IS NULL)
        INSERT INTO @results VALUES ('Orphaned Components', 'WARNING', 'Found components without valid projects');
    ELSE
        INSERT INTO @results VALUES ('Orphaned Components', 'OK', 'No orphaned components found');
    
    -- Check database size
    DECLARE @db_size VARCHAR(20)
    SELECT @db_size = CAST(SUM(size * 8.0 / 1024) AS VARCHAR(20)) + ' MB'
    FROM sys.master_files 
    WHERE database_id = DB_ID();
    
    INSERT INTO @results VALUES ('Database Size', 'OK', @db_size);
    
    SELECT * FROM @results ORDER BY check_name;
END
GO

-- ============================================================
-- FINAL VALIDATION AND CLEANUP
-- ============================================================

PRINT 'Running final validation...';

-- Validate critical constraints
IF NOT EXISTS (SELECT * FROM users WHERE role = 'admin')
BEGIN
    PRINT 'WARNING: No admin users found. Creating emergency admin...';
    INSERT INTO users (username, email, first_name, last_name, status, role, created_date, approved_date, approved_by, is_active)
    VALUES ('emergency_admin', 'emergency@company.com', 'Emergency', 'Admin', 'approved', 'admin', GETDATE(), GETDATE(), 'system', 1);
END

-- Update statistics for better performance
UPDATE STATISTICS users;
UPDATE STATISTICS projects;
UPDATE STATISTICS components;

-- ============================================================
-- FINAL SUMMARY
-- ============================================================
PRINT '============================================================'
PRINT 'MSI Factory Baseline Database Schema v4.0 - INSTALLATION COMPLETE'
PRINT '============================================================'
PRINT 'Database: MSIFactory'
PRINT 'Schema Version: 4.0'
PRINT 'Installation Date: ' + CONVERT(VARCHAR, GETDATE(), 120)
PRINT ''
PRINT 'Features Successfully Installed:'
PRINT '  ✓ Enhanced user management with security features'
PRINT '  ✓ Multi-component project support with unique GUIDs'
PRINT '  ✓ Dynamic environment configurations'
PRINT '  ✓ GitFlow branch tracking and artifact polling'
PRINT '  ✓ Comprehensive MSI configuration management'
PRINT '  ✓ IIS and Windows Service deployment settings'
PRINT '  ✓ Version history and configuration templates'
PRINT '  ✓ Build queue and deployment management'
PRINT '  ✓ Advanced audit logging and session management'
PRINT '  ✓ Performance optimized indexes'
PRINT '  ✓ Data validation and constraints'
PRINT '  ✓ Stored procedures and views'
PRINT '  ✓ Health monitoring capabilities'
PRINT ''
PRINT 'Next Steps:'
PRINT '  1. Create application database user and assign permissions'
PRINT '  2. Configure connection strings in your application'
PRINT '  3. Test connectivity using the sp_HealthCheck procedure'
PRINT '  4. Review and customize default configuration templates'
PRINT ''
PRINT 'For support and documentation, refer to the MSI Factory documentation.'
PRINT '============================================================'

-- Run health check
EXEC sp_HealthCheck;

GO

SET NOCOUNT OFF;