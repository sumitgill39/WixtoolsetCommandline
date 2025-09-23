-- ============================================================
-- MSI Factory Complete Database Schema for MS SQL Server
-- Version: 6.0 - PRODUCTION READY
-- Created: 2025-09-19
-- Description: Complete production-ready MS SQL Server schema for MSI Factory system
--              with CMDB integration, GitFlow, JFrog integration, and comprehensive MSI configuration
--
-- FEATURES:
-- - User Management with Security
-- - Multi-Component Projects
-- - Dynamic Environments
-- - GitFlow & Artifact Management
-- - MSI Configuration Management
-- - CMDB Server Inventory
-- - Project-Server Assignments
-- - Audit Logging
-- - Performance Optimized
--
-- This script is FULLY IDEMPOTENT - can be run multiple times safely
-- ============================================================

SET NOCOUNT ON;
GO

-- ============================================================
-- ENVIRONMENT VALIDATION
-- ============================================================
PRINT '============================================================';
PRINT 'MSI Factory Complete Schema v6.0 - Starting Installation...';
PRINT '============================================================';
PRINT '';
PRINT 'Checking SQL Server environment...';

-- Check SQL Server version (gracefully handle all versions)
DECLARE @sql_version VARCHAR(500) = @@VERSION;
DECLARE @version_year INT =
    CASE
        WHEN @sql_version LIKE '%2022%' THEN 2022
        WHEN @sql_version LIKE '%2019%' THEN 2019
        WHEN @sql_version LIKE '%2017%' THEN 2017
        WHEN @sql_version LIKE '%2016%' THEN 2016
        WHEN @sql_version LIKE '%2014%' THEN 2014
        WHEN @sql_version LIKE '%2012%' THEN 2012
        ELSE 2012 -- Default to 2012 for compatibility
    END;

PRINT 'SQL Server version detected: ' + CAST(@version_year AS VARCHAR(4));

-- ============================================================
-- DATABASE CREATION
-- ============================================================
IF NOT EXISTS (SELECT * FROM sys.databases WHERE name = 'MSIFactory')
BEGIN
    PRINT 'Creating MSIFactory database...';
    CREATE DATABASE MSIFactory;
    PRINT 'Database MSIFactory created successfully.';
END
ELSE
BEGIN
    PRINT 'Database MSIFactory already exists.';
END
GO

USE MSIFactory;
GO

-- ============================================================
-- DATABASE CONFIGURATION
-- ============================================================
PRINT 'Configuring database settings...';

ALTER DATABASE MSIFactory SET RECOVERY SIMPLE;
ALTER DATABASE MSIFactory SET AUTO_SHRINK OFF;
ALTER DATABASE MSIFactory SET AUTO_CREATE_STATISTICS ON;
ALTER DATABASE MSIFactory SET AUTO_UPDATE_STATISTICS ON;
ALTER DATABASE MSIFactory SET PAGE_VERIFY CHECKSUM;

PRINT 'Database configuration completed.';
GO

-- ============================================================
-- DROP AND RECREATE VIEWS (to avoid dependency issues)
-- ============================================================
IF EXISTS (SELECT * FROM sys.views WHERE name = 'vw_component_details')
    DROP VIEW vw_component_details;
IF EXISTS (SELECT * FROM sys.views WHERE name = 'vw_cmdb_server_inventory')
    DROP VIEW vw_cmdb_server_inventory;
IF EXISTS (SELECT * FROM sys.views WHERE name = 'vw_project_server_assignments')
    DROP VIEW vw_project_server_assignments;
GO

-- ============================================================
-- CORE TABLES
-- ============================================================

PRINT '';
PRINT 'Creating core tables...';

-- Users Table
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='users' AND xtype='U')
BEGIN
    PRINT '  Creating users table...';
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
        password_hash VARCHAR(255),
        password_salt VARCHAR(255),
        last_password_change DATETIME,
        failed_login_attempts INT DEFAULT 0,
        account_locked_until DATETIME,

        CONSTRAINT CK_users_email_format CHECK (email LIKE '%@%.%'),
        CONSTRAINT CK_users_names_not_empty CHECK (LEN(TRIM(first_name)) > 0 AND LEN(TRIM(last_name)) > 0)
    );
    PRINT '  Users table created successfully.';
END
ELSE
    PRINT '  Users table already exists.';
GO

-- Projects Table
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='projects' AND xtype='U')
BEGIN
    PRINT '  Creating projects table...';
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
        artifact_source_type VARCHAR(50),
        artifact_url VARCHAR(500),
        artifact_username VARCHAR(100),
        artifact_password VARCHAR(100),
        artifact_api_key VARCHAR(255),

        -- Metadata
        created_date DATETIME DEFAULT GETDATE(),
        created_by VARCHAR(50) NOT NULL,
        updated_date DATETIME DEFAULT GETDATE(),
        updated_by VARCHAR(50),
        is_active BIT DEFAULT 1,
        auto_version_increment BIT DEFAULT 1,
        default_environment VARCHAR(20) DEFAULT 'DEV',
        notification_email VARCHAR(500),

        -- CMDB Integration Fields (added later if needed)
        default_server_group_id INT,
        preferred_infra_type VARCHAR(50),
        preferred_region VARCHAR(100),

        CONSTRAINT CK_projects_key_format CHECK (project_key LIKE '[A-Z]%' AND LEN(project_key) >= 3),
        CONSTRAINT CK_projects_colors CHECK (color_primary LIKE '#[0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f]')
    );
    PRINT '  Projects table created successfully.';
END
ELSE
    PRINT '  Projects table already exists.';
GO

-- Components Table
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='components' AND xtype='U')
BEGIN
    PRINT '  Creating components table...';
    CREATE TABLE components (
        component_id INT PRIMARY KEY IDENTITY(1,1),
        component_guid UNIQUEIDENTIFIER DEFAULT NEWID(),
        unique_guid UNIQUEIDENTIFIER DEFAULT NEWID(),
        project_id INT NOT NULL,
        component_name VARCHAR(100) NOT NULL,
        component_type VARCHAR(20) NOT NULL CHECK (component_type IN ('webapp', 'website', 'service', 'scheduler', 'api', 'desktop', 'library')),
        framework VARCHAR(20) NOT NULL CHECK (framework IN ('netframework', 'netcore', 'react', 'angular', 'python', 'static', 'vue', 'nodejs')),
        description TEXT,

        -- GitFlow Branch Tracking (kept for backward compatibility)
        branch_name VARCHAR(100),
        polling_enabled BIT DEFAULT 1,
        last_poll_time DATETIME,
        last_artifact_version VARCHAR(100),
        last_download_path VARCHAR(500),
        last_extract_path VARCHAR(500),
        last_artifact_time DATETIME,
        artifact_source VARCHAR(255),

        -- Component Settings
        is_enabled BIT DEFAULT 1 NOT NULL,
        order_index INT DEFAULT 1,
        dependencies VARCHAR(500),

        -- MSI Package Information
        app_name VARCHAR(100),
        app_version VARCHAR(50) DEFAULT '1.0.0.0',
        manufacturer VARCHAR(100) DEFAULT 'Your Company',

        -- Deployment Configuration
        target_server VARCHAR(100),
        install_folder VARCHAR(500),

        -- IIS Configuration (for web components)
        iis_website_name VARCHAR(100),
        iis_app_pool_name VARCHAR(100),
        port INT,

        -- Windows Service Configuration
        service_name VARCHAR(100),
        service_display_name VARCHAR(100),

        -- Artifact Configuration
        artifact_url VARCHAR(500),

        -- CMDB Integration Fields
        preferred_server_id INT,
        deployment_strategy VARCHAR(50) DEFAULT 'single_server' CHECK (deployment_strategy IN ('single_server', 'load_balanced', 'clustered') OR deployment_strategy IS NULL),
        resource_requirements TEXT,

        -- Metadata
        created_date DATETIME DEFAULT GETDATE(),
        created_by VARCHAR(50) NOT NULL,
        updated_date DATETIME DEFAULT GETDATE(),
        updated_by VARCHAR(50),

        FOREIGN KEY (project_id) REFERENCES projects(project_id) ON DELETE CASCADE,

        CONSTRAINT CK_components_name_not_empty CHECK (LEN(TRIM(component_name)) > 0),
        CONSTRAINT UK_components_project_name UNIQUE (project_id, component_name)
    );
    PRINT '  Components table created successfully.';
END
ELSE
BEGIN
    PRINT '  Components table already exists.';
    -- Add description column if missing
    IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.COLUMNS
                   WHERE TABLE_NAME = 'components' AND COLUMN_NAME = 'description')
    BEGIN
        ALTER TABLE components ADD description TEXT;
        PRINT '  Added description column to components table.';
    END
END
GO

-- Project Environments Table
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='project_environments' AND xtype='U')
BEGIN
    PRINT '  Creating project_environments table...';
    CREATE TABLE project_environments (
        env_id INT PRIMARY KEY IDENTITY(1,1),
        project_id INT NOT NULL,
        environment_name VARCHAR(20) NOT NULL,
        environment_description VARCHAR(100),
        environment_type VARCHAR(20) CHECK (environment_type IN ('development', 'testing', 'staging', 'production')),
        servers TEXT,
        region VARCHAR(50),
        is_active BIT DEFAULT 1,
        order_index INT DEFAULT 1,

        -- CMDB Integration Fields
        assigned_server_count INT DEFAULT 0,
        load_balancer_server_id INT,

        created_date DATETIME DEFAULT GETDATE(),

        FOREIGN KEY (project_id) REFERENCES projects(project_id) ON DELETE CASCADE,
        CONSTRAINT UK_project_env_name UNIQUE (project_id, environment_name)
    );
    PRINT '  Project environments table created successfully.';
END
ELSE
    PRINT '  Project environments table already exists.';
GO

-- ============================================================
-- GITFLOW & ARTIFACT TABLES
-- ============================================================

PRINT '';
PRINT 'Creating GitFlow and artifact tables...';

-- Branch Mappings Table
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='branch_mappings' AND xtype='U')
BEGIN
    PRINT '  Creating branch_mappings table...';
    CREATE TABLE branch_mappings (
        mapping_id INT IDENTITY(1,1) PRIMARY KEY,
        project_id INT,
        branch_pattern VARCHAR(100),
        repository_path VARCHAR(200),
        environment_type VARCHAR(50),
        auto_deploy BIT DEFAULT 0,
        priority INT DEFAULT 5,
        is_active BIT DEFAULT 1 NOT NULL,
        created_date DATETIME DEFAULT GETDATE(),

        FOREIGN KEY (project_id) REFERENCES projects(project_id) ON DELETE CASCADE
    );
    PRINT '  Branch mappings table created successfully.';

    -- Insert default GitFlow patterns
    INSERT INTO branch_mappings (project_id, branch_pattern, repository_path, environment_type, auto_deploy)
    VALUES
        (NULL, 'develop', '/snapshots/develop', 'dev', 1),
        (NULL, 'master', '/releases/stable', 'prod', 0),
        (NULL, 'main', '/releases/stable', 'prod', 0),
        (NULL, 'feature/*', '/feature-builds', 'dev', 1),
        (NULL, 'release/*', '/release-candidates', 'staging', 1),
        (NULL, 'hotfix/*', '/hotfixes', 'prod', 0);
    PRINT '  Default branch mappings inserted.';
END
ELSE
    PRINT '  Branch mappings table already exists.';
GO

-- Artifact History Table
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='artifact_history' AND xtype='U')
BEGIN
    PRINT '  Creating artifact_history table...';
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
    PRINT '  Artifact history table created successfully.';
END
ELSE
    PRINT '  Artifact history table already exists.';
GO

-- Polling Config Table
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='polling_config' AND xtype='U')
BEGIN
    PRINT '  Creating polling_config table...';
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
    PRINT '  Polling config table created successfully.';
END
ELSE
    PRINT '  Polling config table already exists.';
GO

-- ============================================================
-- MSI CONFIGURATION TABLES
-- ============================================================

PRINT '';
PRINT 'Creating MSI configuration tables...';

-- MSI Configurations Table
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='msi_configurations' AND xtype='U')
BEGIN
    PRINT '  Creating msi_configurations table...';
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
        target_environment VARCHAR(50),
        target_server_id INT, -- CMDB Integration
        backup_server_id INT, -- CMDB Integration

        -- Component Type Specific
        component_type VARCHAR(50),

        -- IIS Configuration
        iis_website_name VARCHAR(255),
        iis_app_path VARCHAR(255),
        iis_app_pool_name VARCHAR(255),
        iis_port INT,
        iis_binding_info TEXT,
        parent_website VARCHAR(255),
        parent_webapp VARCHAR(255),

        -- App Pool Configuration
        app_pool_identity VARCHAR(100),
        app_pool_dotnet_version VARCHAR(20),
        app_pool_pipeline_mode VARCHAR(20),
        app_pool_enable_32bit BIT DEFAULT 0,
        app_pool_start_mode VARCHAR(20),
        app_pool_idle_timeout INT DEFAULT 20,
        app_pool_recycling_schedule VARCHAR(500),

        -- Advanced Settings
        enable_preload BIT DEFAULT 0,
        enable_anonymous_auth BIT DEFAULT 1,
        enable_windows_auth BIT DEFAULT 0,
        custom_headers TEXT,
        connection_strings TEXT,
        app_settings TEXT,

        -- Windows Service Configuration
        service_name VARCHAR(255),
        service_display_name VARCHAR(255),
        service_description TEXT,
        service_start_type VARCHAR(50),
        service_account VARCHAR(255),
        service_password VARCHAR(500),
        service_dependencies VARCHAR(500),

        -- MSI Features
        features TEXT,
        registry_entries TEXT,
        environment_variables TEXT,
        shortcuts TEXT,

        -- Scripts
        pre_install_script TEXT,
        post_install_script TEXT,
        pre_uninstall_script TEXT,
        post_uninstall_script TEXT,

        -- Permissions
        folder_permissions TEXT,

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
    PRINT '  MSI configurations table created successfully.';
END
ELSE
    PRINT '  MSI configurations table already exists.';
GO

-- Other MSI Related Tables
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='msi_environment_configs' AND xtype='U')
BEGIN
    PRINT '  Creating msi_environment_configs table...';
    CREATE TABLE msi_environment_configs (
        env_config_id INT IDENTITY(1,1) PRIMARY KEY,
        config_id INT NOT NULL,
        environment VARCHAR(50) NOT NULL,
        target_server VARCHAR(255),
        install_folder VARCHAR(500),
        iis_website_name VARCHAR(255),
        iis_app_pool_name VARCHAR(255),
        iis_port INT,
        connection_strings TEXT,
        app_settings TEXT,
        service_account VARCHAR(255),
        approved_by VARCHAR(100),
        approval_date DATETIME,
        notes TEXT,

        FOREIGN KEY (config_id) REFERENCES msi_configurations(config_id),
        UNIQUE(config_id, environment)
    );
    PRINT '  MSI environment configs table created successfully.';
END
GO

IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='msi_version_history' AND xtype='U')
BEGIN
    PRINT '  Creating msi_version_history table...';
    CREATE TABLE msi_version_history (
        version_id INT IDENTITY(1,1) PRIMARY KEY,
        component_id INT NOT NULL,
        version_number VARCHAR(50) NOT NULL,
        build_number INT,
        product_code UNIQUEIDENTIFIER,
        msi_file_path VARCHAR(500),
        msi_file_size BIGINT,
        msi_file_hash VARCHAR(100),
        build_date DATETIME,
        build_by VARCHAR(100),
        build_machine VARCHAR(100),
        source_branch VARCHAR(100),
        source_commit VARCHAR(100),
        deployed_environments TEXT,
        deployment_notes TEXT,
        status VARCHAR(50),
        release_date DATETIME,
        deprecated_date DATETIME,

        FOREIGN KEY (component_id) REFERENCES components(component_id)
    );
    PRINT '  MSI version history table created successfully.';
END
GO

IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='msi_build_queue' AND xtype='U')
BEGIN
    PRINT '  Creating msi_build_queue table...';
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
    PRINT '  MSI build queue table created successfully.';
END
GO

IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='msi_builds' AND xtype='U')
BEGIN
    PRINT '  Creating msi_builds table...';
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
    PRINT '  MSI builds table created successfully.';
END
GO

-- ============================================================
-- ACCESS CONTROL TABLES
-- ============================================================

PRINT '';
PRINT 'Creating access control tables...';

-- User Projects Table
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='user_projects' AND xtype='U')
BEGIN
    PRINT '  Creating user_projects table...';
    CREATE TABLE user_projects (
        user_project_id INT PRIMARY KEY IDENTITY(1,1),
        user_id INT NOT NULL,
        project_id INT NOT NULL,
        access_level VARCHAR(20) DEFAULT 'read' CHECK (access_level IN ('read', 'write', 'admin')),
        granted_date DATETIME DEFAULT GETDATE(),
        granted_by VARCHAR(50),
        is_active BIT DEFAULT 1,

        FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
        FOREIGN KEY (project_id) REFERENCES projects(project_id) ON DELETE CASCADE,
        UNIQUE(user_id, project_id)
    );
    PRINT '  User projects table created successfully.';
END
ELSE
    PRINT '  User projects table already exists.';
GO

-- System Logs Table (Fix the created_date issue)
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='system_logs' AND xtype='U')
BEGIN
    PRINT '  Creating system_logs table...';
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
    PRINT '  System logs table created successfully.';
END
ELSE
BEGIN
    PRINT '  System logs table already exists.';
    -- Add created_date column if missing
    IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.COLUMNS
                   WHERE TABLE_NAME = 'system_logs' AND COLUMN_NAME = 'created_date')
    BEGIN
        ALTER TABLE system_logs ADD created_date DATETIME DEFAULT GETDATE();
        PRINT '  Added created_date column to system_logs table.';
    END
END
GO

-- User Sessions Table
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='user_sessions' AND xtype='U')
BEGIN
    PRINT '  Creating user_sessions table...';
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
    PRINT '  User sessions table created successfully.';
END
ELSE
    PRINT '  User sessions table already exists.';
GO

-- Component Environments Table
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='component_environments' AND xtype='U')
BEGIN
    PRINT '  Creating component_environments table...';
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
    PRINT '  Component environments table created successfully.';
END
ELSE
    PRINT '  Component environments table already exists.';
GO

-- ============================================================
-- CMDB TABLES
-- ============================================================

PRINT '';
PRINT 'Creating CMDB tables...';

-- CMDB Servers Table
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='cmdb_servers' AND xtype='U')
BEGIN
    PRINT '  Creating cmdb_servers table...';
    CREATE TABLE cmdb_servers (
        server_id INT PRIMARY KEY IDENTITY(1,1),
        server_name VARCHAR(255) UNIQUE NOT NULL,
        fqdn VARCHAR(500),

        -- Infrastructure Details
        infra_type VARCHAR(50) NOT NULL CHECK (infra_type IN ('AWS', 'AZURE', 'WINTEL', 'VMWARE', 'HYPERV')),
        ip_address VARCHAR(45) NOT NULL,
        ip_address_internal VARCHAR(45),
        region VARCHAR(100),
        datacenter VARCHAR(100),
        availability_zone VARCHAR(50),

        -- Environment and Status
        environment_type VARCHAR(50) CHECK (environment_type IN ('development', 'testing', 'staging', 'production', 'shared')),
        status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'maintenance', 'decommissioned')),

        -- Hardware Specifications
        cpu_cores INT,
        memory_gb INT,
        storage_gb BIGINT,
        network_speed VARCHAR(20),

        -- Capacity Management
        current_app_count INT DEFAULT 0,
        max_concurrent_apps INT DEFAULT 1,

        -- Cloud/Virtual Details
        instance_type VARCHAR(100),
        instance_id VARCHAR(200),
        cloud_account_id VARCHAR(200),
        resource_group VARCHAR(200),
        subnet_id VARCHAR(200),
        security_groups TEXT,

        -- Operating System
        os_name VARCHAR(100),
        os_version VARCHAR(50),
        os_architecture VARCHAR(20),
        patch_level VARCHAR(100),

        -- Network Configuration
        public_dns VARCHAR(500),
        private_dns VARCHAR(500),
        vpc_id VARCHAR(200),
        network_acl TEXT,

        -- Management
        owner_team VARCHAR(100),
        technical_contact VARCHAR(100),
        business_contact VARCHAR(100),
        cost_center VARCHAR(50),

        -- Monitoring
        monitoring_enabled BIT DEFAULT 1,
        backup_enabled BIT DEFAULT 1,
        patching_group VARCHAR(50),
        maintenance_window VARCHAR(100),

        -- Compliance
        compliance_tags TEXT,
        security_classification VARCHAR(50),
        data_classification VARCHAR(50),

        -- Metadata
        created_date DATETIME DEFAULT GETDATE(),
        created_by VARCHAR(100),
        last_updated DATETIME DEFAULT GETDATE(),
        updated_by VARCHAR(100),
        is_active BIT DEFAULT 1,

        CONSTRAINT CK_cmdb_cpu_cores CHECK (cpu_cores IS NULL OR cpu_cores > 0),
        CONSTRAINT CK_cmdb_memory CHECK (memory_gb IS NULL OR memory_gb > 0),
        CONSTRAINT CK_cmdb_storage CHECK (storage_gb IS NULL OR storage_gb > 0),
        CONSTRAINT CK_cmdb_max_apps CHECK (max_concurrent_apps > 0),
        CONSTRAINT CK_cmdb_current_apps CHECK (current_app_count >= 0)
    );
    PRINT '  CMDB servers table created successfully.';
END
ELSE
    PRINT '  CMDB servers table already exists.';
GO

-- CMDB Server Groups Table
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='cmdb_server_groups' AND xtype='U')
BEGIN
    PRINT '  Creating cmdb_server_groups table...';
    CREATE TABLE cmdb_server_groups (
        group_id INT PRIMARY KEY IDENTITY(1,1),
        group_name VARCHAR(255) UNIQUE NOT NULL,
        group_type VARCHAR(50) NOT NULL CHECK (group_type IN ('cluster', 'load_balancer', 'failover', 'development')),
        description TEXT,

        -- Load Balancing Configuration
        load_balancer_server_id INT,
        load_balancing_algorithm VARCHAR(50),
        health_check_url VARCHAR(500),
        health_check_interval INT DEFAULT 30,

        -- Group Settings
        min_servers INT DEFAULT 1,
        max_servers INT DEFAULT 10,
        auto_scaling_enabled BIT DEFAULT 0,

        -- Metadata
        created_date DATETIME DEFAULT GETDATE(),
        created_by VARCHAR(100),
        is_active BIT DEFAULT 1,

        FOREIGN KEY (load_balancer_server_id) REFERENCES cmdb_servers(server_id),

        CONSTRAINT CK_group_min_max_servers CHECK (min_servers <= max_servers),
        CONSTRAINT CK_group_health_interval CHECK (health_check_interval > 0)
    );
    PRINT '  CMDB server groups table created successfully.';
END
ELSE
    PRINT '  CMDB server groups table already exists.';
GO

-- CMDB Server Group Members Table
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='cmdb_server_group_members' AND xtype='U')
BEGIN
    PRINT '  Creating cmdb_server_group_members table...';
    CREATE TABLE cmdb_server_group_members (
        membership_id INT PRIMARY KEY IDENTITY(1,1),
        group_id INT NOT NULL,
        server_id INT NOT NULL,
        role VARCHAR(50) DEFAULT 'member' CHECK (role IN ('member', 'primary', 'backup', 'load_balancer')),
        priority INT DEFAULT 1,
        is_active BIT DEFAULT 1,
        joined_date DATETIME DEFAULT GETDATE(),

        FOREIGN KEY (group_id) REFERENCES cmdb_server_groups(group_id) ON DELETE CASCADE,
        FOREIGN KEY (server_id) REFERENCES cmdb_servers(server_id) ON DELETE CASCADE,

        UNIQUE(group_id, server_id)
    );
    PRINT '  CMDB server group members table created successfully.';
END
ELSE
    PRINT '  CMDB server group members table already exists.';
GO

-- Project Servers Table (Fixed Foreign Keys)
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='project_servers' AND xtype='U')
BEGIN
    PRINT '  Creating project_servers table...';
    CREATE TABLE project_servers (
        assignment_id INT PRIMARY KEY IDENTITY(1,1),
        project_id INT NOT NULL,
        environment_id INT NOT NULL,
        server_id INT NOT NULL,
        assignment_type VARCHAR(50) NOT NULL CHECK (assignment_type IN ('primary', 'backup', 'load_balancer', 'development', 'testing')),
        purpose TEXT,
        status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'pending')),
        assigned_date DATETIME DEFAULT GETDATE(),
        assigned_by VARCHAR(100),
        is_active BIT DEFAULT 1, -- Added for consistency

        FOREIGN KEY (project_id) REFERENCES projects(project_id) ON DELETE NO ACTION,
        FOREIGN KEY (environment_id) REFERENCES project_environments(env_id) ON DELETE NO ACTION,
        FOREIGN KEY (server_id) REFERENCES cmdb_servers(server_id) ON DELETE CASCADE,

        UNIQUE(project_id, environment_id, server_id, assignment_type)
    );
    PRINT '  Project servers table created successfully.';
END
ELSE
    PRINT '  Project servers table already exists.';
GO

-- Component Servers Table
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='component_servers' AND xtype='U')
BEGIN
    PRINT '  Creating component_servers table...';
    CREATE TABLE component_servers (
        component_server_id INT PRIMARY KEY IDENTITY(1,1),
        component_id INT NOT NULL,
        server_id INT NOT NULL,
        assignment_type VARCHAR(50) NOT NULL CHECK (assignment_type IN ('primary', 'backup', 'development')),
        deployment_path VARCHAR(500),
        status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'pending')),
        assigned_date DATETIME DEFAULT GETDATE(),
        assigned_by VARCHAR(100),

        FOREIGN KEY (component_id) REFERENCES components(component_id) ON DELETE NO ACTION,
        FOREIGN KEY (server_id) REFERENCES cmdb_servers(server_id) ON DELETE CASCADE,

        UNIQUE(component_id, server_id, assignment_type)
    );
    PRINT '  Component servers table created successfully.';
END
ELSE
    PRINT '  Component servers table already exists.';
GO

-- CMDB Server Changes Table
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='cmdb_server_changes' AND xtype='U')
BEGIN
    PRINT '  Creating cmdb_server_changes table...';
    CREATE TABLE cmdb_server_changes (
        change_id INT PRIMARY KEY IDENTITY(1,1),
        server_id INT NOT NULL,
        change_type VARCHAR(50) NOT NULL CHECK (change_type IN ('created', 'updated', 'deleted', 'status_change', 'assignment_change')),
        field_name VARCHAR(100),
        old_value TEXT,
        new_value TEXT,
        change_reason TEXT,
        changed_date DATETIME DEFAULT GETDATE(),
        changed_by VARCHAR(100) NOT NULL,

        FOREIGN KEY (server_id) REFERENCES cmdb_servers(server_id) ON DELETE CASCADE
    );
    PRINT '  CMDB server changes table created successfully.';
END
ELSE
    PRINT '  CMDB server changes table already exists.';
GO

-- ============================================================
-- UPDATE EXISTING TABLES FOR CMDB INTEGRATION
-- ============================================================

PRINT '';
PRINT 'Updating existing tables for CMDB integration...';

-- Update Projects table
IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'projects' AND COLUMN_NAME = 'project_guid')
BEGIN
    ALTER TABLE projects ADD project_guid UNIQUEIDENTIFIER DEFAULT NEWID();
    PRINT '  Added project_guid to projects table.';

    -- Generate GUIDs for existing projects
    UPDATE projects SET project_guid = NEWID() WHERE project_guid IS NULL;
    PRINT '  Generated GUIDs for existing projects.';
END

IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'projects' AND COLUMN_NAME = 'default_server_group_id')
BEGIN
    ALTER TABLE projects ADD default_server_group_id INT;
    PRINT '  Added default_server_group_id to projects table.';
END

IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.CONSTRAINT_TABLE_USAGE WHERE CONSTRAINT_NAME = 'FK_projects_server_group')
BEGIN
    ALTER TABLE projects ADD CONSTRAINT FK_projects_server_group
        FOREIGN KEY (default_server_group_id) REFERENCES cmdb_server_groups(group_id);
    PRINT '  Added FK_projects_server_group constraint.';
END

IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'projects' AND COLUMN_NAME = 'preferred_infra_type')
BEGIN
    ALTER TABLE projects ADD preferred_infra_type VARCHAR(50);
    PRINT '  Added preferred_infra_type to projects table.';
END

IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'projects' AND COLUMN_NAME = 'preferred_region')
BEGIN
    ALTER TABLE projects ADD preferred_region VARCHAR(100);
    PRINT '  Added preferred_region to projects table.';
END

-- Update Components table
IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'components' AND COLUMN_NAME = 'description')
BEGIN
    ALTER TABLE components ADD description TEXT;
    PRINT '  Added description to components table.';
END

IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'components' AND COLUMN_NAME = 'preferred_server_id')
BEGIN
    ALTER TABLE components ADD preferred_server_id INT;
    PRINT '  Added preferred_server_id to components table.';
END

IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.CONSTRAINT_TABLE_USAGE WHERE CONSTRAINT_NAME = 'FK_components_preferred_server')
BEGIN
    ALTER TABLE components ADD CONSTRAINT FK_components_preferred_server
        FOREIGN KEY (preferred_server_id) REFERENCES cmdb_servers(server_id);
    PRINT '  Added FK_components_preferred_server constraint.';
END

IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'components' AND COLUMN_NAME = 'deployment_strategy')
BEGIN
    ALTER TABLE components ADD deployment_strategy VARCHAR(50) DEFAULT 'single_server'
        CHECK (deployment_strategy IN ('single_server', 'load_balanced', 'clustered') OR deployment_strategy IS NULL);
    PRINT '  Added deployment_strategy to components table.';
END

IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'components' AND COLUMN_NAME = 'resource_requirements')
BEGIN
    ALTER TABLE components ADD resource_requirements TEXT;
    PRINT '  Added resource_requirements to components table.';
END

-- Add MSI Package Information fields
IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'components' AND COLUMN_NAME = 'app_name')
BEGIN
    ALTER TABLE components ADD app_name VARCHAR(100);
    PRINT '  Added app_name to components table.';
END

IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'components' AND COLUMN_NAME = 'app_version')
BEGIN
    ALTER TABLE components ADD app_version VARCHAR(50) DEFAULT '1.0.0.0';
    PRINT '  Added app_version to components table.';
END

IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'components' AND COLUMN_NAME = 'manufacturer')
BEGIN
    ALTER TABLE components ADD manufacturer VARCHAR(100) DEFAULT 'Your Company';
    PRINT '  Added manufacturer to components table.';
END

-- Add Deployment Configuration fields
IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'components' AND COLUMN_NAME = 'target_server')
BEGIN
    ALTER TABLE components ADD target_server VARCHAR(100);
    PRINT '  Added target_server to components table.';
END

IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'components' AND COLUMN_NAME = 'install_folder')
BEGIN
    ALTER TABLE components ADD install_folder VARCHAR(500);
    PRINT '  Added install_folder to components table.';
END

-- Add IIS Configuration fields
IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'components' AND COLUMN_NAME = 'iis_website_name')
BEGIN
    ALTER TABLE components ADD iis_website_name VARCHAR(100);
    PRINT '  Added iis_website_name to components table.';
END

IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'components' AND COLUMN_NAME = 'iis_app_pool_name')
BEGIN
    ALTER TABLE components ADD iis_app_pool_name VARCHAR(100);
    PRINT '  Added iis_app_pool_name to components table.';
END

IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'components' AND COLUMN_NAME = 'port')
BEGIN
    ALTER TABLE components ADD port INT;
    PRINT '  Added port to components table.';
END

-- Add Windows Service Configuration fields
IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'components' AND COLUMN_NAME = 'service_name')
BEGIN
    ALTER TABLE components ADD service_name VARCHAR(100);
    PRINT '  Added service_name to components table.';
END

IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'components' AND COLUMN_NAME = 'service_display_name')
BEGIN
    ALTER TABLE components ADD service_display_name VARCHAR(100);
    PRINT '  Added service_display_name to components table.';
END

-- Add Artifact Configuration field
IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'components' AND COLUMN_NAME = 'artifact_url')
BEGIN
    ALTER TABLE components ADD artifact_url VARCHAR(500);
    PRINT '  Added artifact_url to components table.';
END

-- Update Project Environments table
IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'project_environments' AND COLUMN_NAME = 'assigned_server_count')
BEGIN
    ALTER TABLE project_environments ADD assigned_server_count INT DEFAULT 0;
    PRINT '  Added assigned_server_count to project_environments table.';
END

IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'project_environments' AND COLUMN_NAME = 'load_balancer_server_id')
BEGIN
    ALTER TABLE project_environments ADD load_balancer_server_id INT;
    PRINT '  Added load_balancer_server_id to project_environments table.';
END

IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.CONSTRAINT_TABLE_USAGE WHERE CONSTRAINT_NAME = 'FK_env_load_balancer')
BEGIN
    ALTER TABLE project_environments ADD CONSTRAINT FK_env_load_balancer
        FOREIGN KEY (load_balancer_server_id) REFERENCES cmdb_servers(server_id);
    PRINT '  Added FK_env_load_balancer constraint.';
END

-- Update MSI Configurations table
IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'msi_configurations' AND COLUMN_NAME = 'target_server_id')
BEGIN
    ALTER TABLE msi_configurations ADD target_server_id INT;
    PRINT '  Added target_server_id to msi_configurations table.';
END

IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'msi_configurations' AND COLUMN_NAME = 'backup_server_id')
BEGIN
    ALTER TABLE msi_configurations ADD backup_server_id INT;
    PRINT '  Added backup_server_id to msi_configurations table.';
END

IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.CONSTRAINT_TABLE_USAGE WHERE CONSTRAINT_NAME = 'FK_msi_target_server')
BEGIN
    ALTER TABLE msi_configurations ADD CONSTRAINT FK_msi_target_server
        FOREIGN KEY (target_server_id) REFERENCES cmdb_servers(server_id);
    PRINT '  Added FK_msi_target_server constraint.';
END

IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.CONSTRAINT_TABLE_USAGE WHERE CONSTRAINT_NAME = 'FK_msi_backup_server')
BEGIN
    ALTER TABLE msi_configurations ADD CONSTRAINT FK_msi_backup_server
        FOREIGN KEY (backup_server_id) REFERENCES cmdb_servers(server_id);
    PRINT '  Added FK_msi_backup_server constraint.';
END

GO

-- ============================================================
-- CREATE INDEXES FOR PERFORMANCE
-- ============================================================

PRINT '';
PRINT 'Creating performance indexes...';

-- Core table indexes
IF EXISTS (SELECT * FROM sysobjects WHERE name='users' AND xtype='U')
    AND NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_users_username')
    CREATE INDEX idx_users_username ON users(username);

IF EXISTS (SELECT * FROM sysobjects WHERE name='users' AND xtype='U')
    AND NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_users_email')
    CREATE INDEX idx_users_email ON users(email);

IF EXISTS (SELECT * FROM sysobjects WHERE name='projects' AND xtype='U')
    AND NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_projects_key')
    CREATE INDEX idx_projects_key ON projects(project_key);

IF EXISTS (SELECT * FROM sysobjects WHERE name='components' AND xtype='U')
    AND NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_components_project')
    CREATE INDEX idx_components_project ON components(project_id);

IF EXISTS (SELECT * FROM sysobjects WHERE name='components' AND xtype='U')
    AND NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_components_branch')
    CREATE INDEX idx_components_branch ON components(branch_name);

-- System logs index (with proper check)
IF EXISTS (SELECT * FROM sysobjects WHERE name='system_logs' AND xtype='U')
    AND EXISTS (SELECT * FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'system_logs' AND COLUMN_NAME = 'created_date')
    AND NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_system_logs_date')
    CREATE INDEX idx_system_logs_date ON system_logs(created_date);

IF EXISTS (SELECT * FROM sysobjects WHERE name='user_sessions' AND xtype='U')
    AND NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_user_sessions_user')
    CREATE INDEX idx_user_sessions_user ON user_sessions(user_id);

-- Artifact history indexes
IF EXISTS (SELECT * FROM sysobjects WHERE name='artifact_history' AND xtype='U')
    AND NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_artifact_history_component')
    CREATE INDEX idx_artifact_history_component ON artifact_history(component_id);

IF EXISTS (SELECT * FROM sysobjects WHERE name='artifact_history' AND xtype='U')
    AND NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_artifact_history_time')
    CREATE INDEX idx_artifact_history_time ON artifact_history(download_time);

-- MSI configuration indexes
IF EXISTS (SELECT * FROM sysobjects WHERE name='msi_configurations' AND xtype='U')
    AND NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_msi_config_component')
    CREATE INDEX idx_msi_config_component ON msi_configurations(component_id);

IF EXISTS (SELECT * FROM sysobjects WHERE name='msi_configurations' AND xtype='U')
    AND NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_msi_config_env')
    CREATE INDEX idx_msi_config_env ON msi_configurations(target_environment);

IF EXISTS (SELECT * FROM sysobjects WHERE name='msi_version_history' AND xtype='U')
    AND NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_version_history')
    CREATE INDEX idx_version_history ON msi_version_history(component_id, version_number);

IF EXISTS (SELECT * FROM sysobjects WHERE name='msi_build_queue' AND xtype='U')
    AND NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_build_queue_status')
    CREATE INDEX idx_build_queue_status ON msi_build_queue(status);

IF EXISTS (SELECT * FROM sysobjects WHERE name='msi_build_queue' AND xtype='U')
    AND NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_build_queue_time')
    CREATE INDEX idx_build_queue_time ON msi_build_queue(queued_time);

-- CMDB indexes
IF EXISTS (SELECT * FROM sysobjects WHERE name='cmdb_servers' AND xtype='U')
    AND NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_cmdb_servers_infra_type')
    CREATE INDEX idx_cmdb_servers_infra_type ON cmdb_servers(infra_type);

IF EXISTS (SELECT * FROM sysobjects WHERE name='cmdb_servers' AND xtype='U')
    AND NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_cmdb_servers_region')
    CREATE INDEX idx_cmdb_servers_region ON cmdb_servers(region);

IF EXISTS (SELECT * FROM sysobjects WHERE name='cmdb_servers' AND xtype='U')
    AND NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_cmdb_servers_status')
    CREATE INDEX idx_cmdb_servers_status ON cmdb_servers(status);

IF EXISTS (SELECT * FROM sysobjects WHERE name='project_servers' AND xtype='U')
    AND NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_project_servers_project')
    CREATE INDEX idx_project_servers_project ON project_servers(project_id);

IF EXISTS (SELECT * FROM sysobjects WHERE name='project_servers' AND xtype='U')
    AND NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_project_servers_server')
    CREATE INDEX idx_project_servers_server ON project_servers(server_id);

IF EXISTS (SELECT * FROM sysobjects WHERE name='cmdb_server_changes' AND xtype='U')
    AND NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_cmdb_changes_server')
    CREATE INDEX idx_cmdb_changes_server ON cmdb_server_changes(server_id);

IF EXISTS (SELECT * FROM sysobjects WHERE name='cmdb_server_changes' AND xtype='U')
    AND NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_cmdb_changes_date')
    CREATE INDEX idx_cmdb_changes_date ON cmdb_server_changes(changed_date);

PRINT '  Indexes created successfully.';
GO

-- ============================================================
-- CREATE STORED PROCEDURES
-- ============================================================

PRINT '';
PRINT 'Creating stored procedures...';

-- Get Next Version procedure
IF EXISTS (SELECT * FROM sys.objects WHERE type = 'P' AND name = 'sp_GetNextVersion')
    DROP PROCEDURE sp_GetNextVersion;
GO

CREATE PROCEDURE sp_GetNextVersion
    @component_id INT,
    @next_version VARCHAR(50) OUTPUT
AS
BEGIN
    DECLARE @current_version VARCHAR(50);

    SELECT TOP 1 @current_version = version_number
    FROM msi_version_history
    WHERE component_id = @component_id
    ORDER BY version_id DESC;

    IF @current_version IS NULL
        SET @next_version = '1.0.0.0';
    ELSE
    BEGIN
        DECLARE @major INT, @minor INT, @build INT, @revision INT;

        SET @major = PARSENAME(@current_version, 4);
        SET @minor = PARSENAME(@current_version, 3);
        SET @build = PARSENAME(@current_version, 2);
        SET @revision = PARSENAME(@current_version, 1) + 1;

        IF @revision > 9999
        BEGIN
            SET @revision = 0;
            SET @build = @build + 1;
        END

        SET @next_version = CAST(@major AS VARCHAR) + '.' +
                           CAST(@minor AS VARCHAR) + '.' +
                           CAST(@build AS VARCHAR) + '.' +
                           CAST(@revision AS VARCHAR);
    END
END
GO

-- CMDB Discover Server procedure
IF EXISTS (SELECT * FROM sys.objects WHERE type = 'P' AND name = 'sp_CMDB_DiscoverServer')
    DROP PROCEDURE sp_CMDB_DiscoverServer;
GO

CREATE PROCEDURE sp_CMDB_DiscoverServer
    @server_name VARCHAR(255),
    @ip_address VARCHAR(45),
    @infra_type VARCHAR(50),
    @discovered_by VARCHAR(100)
AS
BEGIN
    SET NOCOUNT ON;

    IF NOT EXISTS (SELECT 1 FROM cmdb_servers WHERE server_name = @server_name OR ip_address = @ip_address)
    BEGIN
        INSERT INTO cmdb_servers (server_name, ip_address, infra_type, status, created_by)
        VALUES (@server_name, @ip_address, @infra_type, 'active', @discovered_by);

        DECLARE @server_id INT = SCOPE_IDENTITY();

        INSERT INTO cmdb_server_changes (server_id, change_type, change_reason, changed_by)
        VALUES (@server_id, 'created', 'Server discovered automatically', @discovered_by);

        SELECT @server_id as server_id, 'Server discovered and added' as message;
    END
    ELSE
    BEGIN
        SELECT 0 as server_id, 'Server already exists' as message;
    END
END
GO

-- Assign Server to Project procedure
IF EXISTS (SELECT * FROM sys.objects WHERE type = 'P' AND name = 'sp_AssignServerToProject')
    DROP PROCEDURE sp_AssignServerToProject;
GO

CREATE PROCEDURE sp_AssignServerToProject
    @project_id INT,
    @environment_id INT,
    @server_id INT,
    @assignment_type VARCHAR(50),
    @assigned_by VARCHAR(100)
AS
BEGIN
    SET NOCOUNT ON;

    BEGIN TRY
        IF NOT EXISTS (SELECT 1 FROM project_servers
                      WHERE project_id = @project_id
                        AND environment_id = @environment_id
                        AND server_id = @server_id
                        AND assignment_type = @assignment_type)
        BEGIN
            INSERT INTO project_servers (project_id, environment_id, server_id, assignment_type, assigned_by)
            VALUES (@project_id, @environment_id, @server_id, @assignment_type, @assigned_by);

            INSERT INTO cmdb_server_changes (server_id, change_type, change_reason, changed_by)
            VALUES (@server_id, 'assignment_change',
                   'Assigned to project ' + CAST(@project_id AS VARCHAR), @assigned_by);

            SELECT 1 as success, 'Server assigned successfully' as message;
        END
        ELSE
        BEGIN
            SELECT 0 as success, 'Assignment already exists' as message;
        END
    END TRY
    BEGIN CATCH
        SELECT 0 as success, ERROR_MESSAGE() as message;
    END CATCH
END
GO

-- Health Check procedure
IF EXISTS (SELECT * FROM sys.objects WHERE type = 'P' AND name = 'sp_HealthCheck')
    DROP PROCEDURE sp_HealthCheck;
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
    INSERT INTO @results SELECT 'CMDB Servers Count', 'OK', CAST(COUNT(*) AS VARCHAR) + ' servers' FROM cmdb_servers;

    -- Check for orphaned records
    IF EXISTS (SELECT 1 FROM components c LEFT JOIN projects p ON c.project_id = p.project_id WHERE p.project_id IS NULL)
        INSERT INTO @results VALUES ('Orphaned Components', 'WARNING', 'Found components without valid projects');
    ELSE
        INSERT INTO @results VALUES ('Orphaned Components', 'OK', 'No orphaned components found');

    -- Check database size
    DECLARE @db_size VARCHAR(20);
    SELECT @db_size = CAST(SUM(size * 8.0 / 1024) AS VARCHAR(20)) + ' MB'
    FROM sys.master_files
    WHERE database_id = DB_ID();

    INSERT INTO @results VALUES ('Database Size', 'OK', @db_size);

    SELECT * FROM @results ORDER BY check_name;
END
GO

PRINT '  Stored procedures created successfully.';
GO

-- ============================================================
-- CREATE VIEWS
-- ============================================================

PRINT '';
PRINT 'Creating views...';

-- Component Details View
IF NOT EXISTS (SELECT * FROM sys.views WHERE name = 'vw_component_details')
BEGIN
    EXEC('
    CREATE VIEW vw_component_details
    AS
    SELECT
        c.component_id,
        c.component_guid,
        c.component_name,
        c.component_type,
        c.framework,
        c.description,

        -- MSI Package Information
        c.app_name,
        c.app_version,
        c.manufacturer,

        -- Deployment Configuration
        c.target_server,
        c.install_folder,

        -- IIS Configuration
        c.iis_website_name,
        c.iis_app_pool_name,
        c.port,

        -- Windows Service Configuration
        c.service_name,
        c.service_display_name,

        -- Artifact Configuration
        c.artifact_url,

        -- Project Information
        p.project_id,
        p.project_name,
        p.project_key,
        p.project_type,
        p.owner_team,
        p.status as project_status,

        -- Legacy MSI Configuration (for backward compatibility)
        mc.config_id,
        mc.unique_id as msi_unique_id,
        mc.target_environment,

        -- Metadata
        c.created_date,
        c.created_by,
        c.updated_date,
        c.updated_by
    FROM components c
    INNER JOIN projects p ON c.project_id = p.project_id
    LEFT JOIN msi_configurations mc ON c.component_id = mc.component_id
    WHERE p.is_active = 1
    ');
    PRINT '  View vw_component_details created successfully.';
END
GO

-- CMDB Server Inventory View
IF NOT EXISTS (SELECT * FROM sys.views WHERE name = 'vw_cmdb_server_inventory')
BEGIN
    EXEC('
    CREATE VIEW vw_cmdb_server_inventory
    AS
    SELECT
        s.server_id,
        s.server_name,
        s.fqdn,
        s.infra_type,
        s.ip_address,
        s.ip_address_internal,
        s.region,
        s.datacenter,
        s.environment_type,
        s.status,
        s.cpu_cores,
        s.memory_gb,
        s.storage_gb,
        s.current_app_count,
        s.max_concurrent_apps,
        CASE
            WHEN s.max_concurrent_apps > 0 THEN (s.current_app_count * 100.0 / s.max_concurrent_apps)
            ELSE 0
        END as utilization_percentage,
        s.owner_team,
        s.technical_contact,
        s.created_date,
        s.last_updated,
        STRING_AGG(sg.group_name, '', '') as server_groups,
        (SELECT COUNT(*) FROM project_servers ps WHERE ps.server_id = s.server_id AND ps.status = ''active'') as active_assignments
    FROM cmdb_servers s
    LEFT JOIN cmdb_server_group_members sgm ON s.server_id = sgm.server_id AND sgm.is_active = 1
    LEFT JOIN cmdb_server_groups sg ON sgm.group_id = sg.group_id AND sg.is_active = 1
    WHERE s.is_active = 1
    GROUP BY
        s.server_id, s.server_name, s.fqdn, s.infra_type, s.ip_address, s.ip_address_internal,
        s.region, s.datacenter, s.environment_type, s.status, s.cpu_cores, s.memory_gb,
        s.storage_gb, s.current_app_count, s.max_concurrent_apps, s.owner_team,
        s.technical_contact, s.created_date, s.last_updated
    ');
    PRINT '  View vw_cmdb_server_inventory created successfully.';
END
GO

-- Project Server Assignments View
IF NOT EXISTS (SELECT * FROM sys.views WHERE name = 'vw_project_server_assignments')
BEGIN
    EXEC('
    CREATE VIEW vw_project_server_assignments
    AS
    SELECT
        ps.assignment_id,
        p.project_name,
        p.project_key,
        pe.environment_name,
        pe.environment_description,
        s.server_name,
        s.ip_address,
        s.infra_type,
        s.region,
        ps.assignment_type,
        ps.purpose,
        ps.status,
        ps.assigned_date,
        ps.assigned_by
    FROM project_servers ps
    INNER JOIN projects p ON ps.project_id = p.project_id
    INNER JOIN project_environments pe ON ps.environment_id = pe.env_id
    INNER JOIN cmdb_servers s ON ps.server_id = s.server_id
    WHERE p.is_active = 1 AND s.is_active = 1
    ');
    PRINT '  View vw_project_server_assignments created successfully.';
END
GO

-- ============================================================
-- INSERT SAMPLE DATA
-- ============================================================

PRINT '';
PRINT 'Inserting sample data...';

-- Insert default admin user
IF NOT EXISTS (SELECT * FROM users WHERE username = 'admin')
BEGIN
    INSERT INTO users (username, email, first_name, last_name, status, role, created_date, approved_date, approved_by, is_active)
    VALUES ('admin', 'admin@company.com', 'System', 'Administrator', 'approved', 'admin', GETDATE(), GETDATE(), 'system', 1);
    PRINT '  Admin user created.';
END

-- Insert sample regular user
IF NOT EXISTS (SELECT * FROM users WHERE username = 'john.doe')
BEGIN
    INSERT INTO users (username, email, first_name, last_name, status, role, created_date, approved_date, approved_by, is_active)
    VALUES ('john.doe', 'john.doe@company.com', 'John', 'Doe', 'approved', 'user', GETDATE(), GETDATE(), 'admin', 1);
    PRINT '  Sample user created.';
END

-- Insert sample project
IF NOT EXISTS (SELECT * FROM projects WHERE project_key = 'DEMO01')
BEGIN
    INSERT INTO projects (project_name, project_key, description, project_type, owner_team, status,
                         artifact_source_type, artifact_url, created_by)
    VALUES ('Demo E-commerce Platform', 'DEMO01',
            'Complete e-commerce solution with multiple components', 'WebApp', 'Development Team', 'active',
            'jfrog', 'https://artifactory.example.com/artifactory', 'admin');

    DECLARE @project_id INT = SCOPE_IDENTITY();

    -- Insert components
    INSERT INTO components (project_id, component_name, component_type, framework,
                           description, artifact_source, branch_name, created_by,
                           app_name, app_version, manufacturer, target_server, install_folder,
                           iis_website_name, iis_app_pool_name, port,
                           service_name, service_display_name, artifact_url)
    VALUES
        (@project_id, 'Web Frontend', 'webapp', 'react',
         'React-based user interface for the e-commerce platform', 'artifactory://frontend-builds', 'develop', 'admin',
         'E-Commerce Web Portal', '1.0.0.0', 'Your Company', 'PRODWEB01', 'C:\inetpub\wwwroot\ECommerce',
         'Default Web Site', 'ECommerceAppPool', 80,
         NULL, NULL, 'https://artifactory.example.com/artifactory/frontend-builds'),
        (@project_id, 'API Backend', 'api', 'netcore',
         '.NET Core REST API providing backend services', 'artifactory://api-builds', 'develop', 'admin',
         'E-Commerce API', '1.0.0.0', 'Your Company', 'PRODAPI01', 'C:\inetpub\wwwroot\ECommerceAPI',
         'Default Web Site', 'ECommerceAPIPool', 8080,
         NULL, NULL, 'https://artifactory.example.com/artifactory/api-builds'),
        (@project_id, 'Background Service', 'service', 'netframework',
         'Windows service for background processing tasks', 'artifactory://service-builds', 'master', 'admin',
         'E-Commerce Background Service', '1.0.0.0', 'Your Company', 'PRODSVC01', 'C:\Program Files\ECommerce\BackgroundService',
         NULL, NULL, NULL,
         'ECommerceBackgroundService', 'E-Commerce Background Processing Service', 'https://artifactory.example.com/artifactory/service-builds');

    -- Insert environments
    INSERT INTO project_environments (project_id, environment_name, environment_description, servers, region)
    VALUES
        (@project_id, 'DEV1', 'Development Environment 1', 'DEVSERVER01,DEVSERVER02', 'US-EAST'),
        (@project_id, 'QA1', 'Quality Assurance Environment 1', 'QASERVER01', 'US-EAST'),
        (@project_id, 'PROD_USA', 'Production USA Environment', 'PRODSERVER01,PRODSERVER02', 'US-EAST');

    PRINT '  Sample project with components created.';
END

-- Insert sample CMDB servers
IF NOT EXISTS (SELECT * FROM cmdb_servers WHERE server_name = 'DEV-WEB-01')
BEGIN
    INSERT INTO cmdb_servers (server_name, fqdn, infra_type, ip_address, region, datacenter, environment_type,
                             cpu_cores, memory_gb, storage_gb, max_concurrent_apps, owner_team, technical_contact, created_by)
    VALUES
        ('DEV-WEB-01', 'dev-web-01.company.local', 'WINTEL', '192.168.1.100', 'US-EAST', 'DC01', 'development',
         4, 16, 500, 5, 'Development Team', 'dev-ops@company.com', 'admin'),
        ('PROD-WEB-01', 'prod-web-01.company.com', 'AWS', '10.0.1.100', 'US-EAST-1', 'AWS-USE1-AZ1', 'production',
         8, 32, 1000, 10, 'Production Team', 'prod-ops@company.com', 'admin'),
        ('AZURE-API-01', 'azure-api-01.eastus.cloudapp.azure.com', 'AZURE', '10.1.1.100', 'EAST-US', 'Azure-EastUS', 'production',
         4, 16, 500, 8, 'API Team', 'api-ops@company.com', 'admin'),
        ('QA-SRV-01', 'qa-srv-01.company.local', 'VMWARE', '192.168.10.50', 'US-WEST', 'DC02', 'testing',
         2, 8, 250, 3, 'QA Team', 'qa-ops@company.com', 'admin');
    PRINT '  Sample CMDB servers created.';
END

-- Insert sample server group
IF NOT EXISTS (SELECT * FROM cmdb_server_groups WHERE group_name = 'Production Web Cluster')
BEGIN
    INSERT INTO cmdb_server_groups (group_name, group_type, description, min_servers, max_servers, created_by)
    VALUES ('Production Web Cluster', 'cluster', 'Production web server cluster for load balancing', 2, 5, 'admin');

    DECLARE @group_id INT = SCOPE_IDENTITY();
    DECLARE @prod_server_id INT = (SELECT server_id FROM cmdb_servers WHERE server_name = 'PROD-WEB-01');

    IF @prod_server_id IS NOT NULL
    BEGIN
        INSERT INTO cmdb_server_group_members (group_id, server_id, role, priority)
        VALUES (@group_id, @prod_server_id, 'primary', 1);
        PRINT '  Sample server group created.';
    END
END

PRINT '';
PRINT 'Sample data insertion complete.';
GO

-- ============================================================
-- UPDATE STATISTICS
-- ============================================================

PRINT '';
PRINT 'Updating statistics for optimal performance...';

IF EXISTS (SELECT * FROM sysobjects WHERE name='users' AND xtype='U')
    UPDATE STATISTICS users;
IF EXISTS (SELECT * FROM sysobjects WHERE name='projects' AND xtype='U')
    UPDATE STATISTICS projects;
IF EXISTS (SELECT * FROM sysobjects WHERE name='components' AND xtype='U')
    UPDATE STATISTICS components;
IF EXISTS (SELECT * FROM sysobjects WHERE name='cmdb_servers' AND xtype='U')
    UPDATE STATISTICS cmdb_servers;
IF EXISTS (SELECT * FROM sysobjects WHERE name='project_servers' AND xtype='U')
    UPDATE STATISTICS project_servers;

PRINT 'Statistics updated successfully.';
GO

-- ============================================================
-- FINAL VALIDATION
-- ============================================================

PRINT '';
PRINT 'Running final validation...';

-- Validate critical constraints
IF NOT EXISTS (SELECT * FROM users WHERE role = 'admin')
BEGIN
    PRINT 'WARNING: No admin users found. Creating emergency admin...';
    INSERT INTO users (username, email, first_name, last_name, status, role, created_date, approved_date, approved_by, is_active)
    VALUES ('emergency_admin', 'emergency@company.com', 'Emergency', 'Admin', 'approved', 'admin', GETDATE(), GETDATE(), 'system', 1);
END

-- Run health check
EXEC sp_HealthCheck;
GO

-- ============================================================
-- COMPLETION SUMMARY
-- ============================================================

PRINT '';
PRINT '============================================================';
PRINT 'MSI Factory Complete Schema v6.0 - INSTALLATION COMPLETE';
PRINT '============================================================';
PRINT '';
PRINT 'Database: MSIFactory';
PRINT 'Schema Version: 6.0 (Complete with CMDB Integration)';
PRINT 'Installation Date: ' + CONVERT(VARCHAR, GETDATE(), 120);
PRINT '';
PRINT 'Features Successfully Installed:';
PRINT '  ✓ Enhanced user management with security features';
PRINT '  ✓ Multi-component project support with unique GUIDs';
PRINT '  ✓ Dynamic environment configurations';
PRINT '  ✓ GitFlow branch tracking and artifact polling';
PRINT '  ✓ Comprehensive MSI configuration management';
PRINT '  ✓ IIS and Windows Service deployment settings';
PRINT '  ✓ Version history and configuration templates';
PRINT '  ✓ Build queue and deployment management';
PRINT '  ✓ Advanced audit logging and session management';
PRINT '  ✓ Performance optimized indexes';
PRINT '  ✓ Data validation and constraints';
PRINT '  ✓ Stored procedures and views';
PRINT '  ✓ Health monitoring capabilities';
PRINT '  ✓ CMDB server inventory management';
PRINT '  ✓ Multi-infrastructure support (AWS, AZURE, WINTEL, VMWARE)';
PRINT '  ✓ Server groups and clustering capabilities';
PRINT '  ✓ Project-server assignment management';
PRINT '  ✓ Component-server deployment mapping';
PRINT '  ✓ Server change audit trail';
PRINT '  ✓ CMDB views and reporting';
PRINT '';
PRINT 'This script is IDEMPOTENT - can be run multiple times safely!';
PRINT '';
PRINT 'Next Steps:';
PRINT '  1. Access the application at http://localhost:5000';
PRINT '  2. Login with admin credentials';
PRINT '  3. Access CMDB features from the admin sidebar';
PRINT '  4. Configure your projects and server assignments';
PRINT '';
PRINT '============================================================';
GO

SET NOCOUNT OFF;