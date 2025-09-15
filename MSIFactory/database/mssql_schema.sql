-- ============================================================
-- MSI Factory Database Schema for MS SQL Server
-- Version: 2.0
-- Created: 2024-09-15
-- Description: Complete MS SQL Server schema for MSI Factory system
-- ============================================================

USE MSIFactory;
GO

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
    created_date DATETIME DEFAULT GETDATE(),
    created_by VARCHAR(50) NOT NULL,
    updated_date DATETIME DEFAULT GETDATE(),
    updated_by VARCHAR(50)
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
    project_id INT NOT NULL,
    component_name VARCHAR(100) NOT NULL,
    component_type VARCHAR(20) NOT NULL CHECK (component_type IN ('webapp', 'website', 'service', 'scheduler', 'api', 'desktop')),
    framework VARCHAR(20) NOT NULL CHECK (framework IN ('netframework', 'netcore', 'react', 'angular', 'python', 'static', 'vue')),
    artifact_source VARCHAR(255),
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
    environment_id INT PRIMARY KEY IDENTITY(1,1),
    project_id INT NOT NULL,
    environment_name VARCHAR(50) NOT NULL,
    environment_description VARCHAR(255),
    servers TEXT,
    region VARCHAR(20),
    is_active BIT DEFAULT 1,
    created_date DATETIME DEFAULT GETDATE(),
    FOREIGN KEY (project_id) REFERENCES projects(project_id) ON DELETE CASCADE
);
GO

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
    FOREIGN KEY (component_id) REFERENCES components(component_id) ON DELETE CASCADE,
    FOREIGN KEY (environment_id) REFERENCES project_environments(environment_id) ON DELETE CASCADE
);
GO

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
    INSERT INTO projects (project_guid, project_name, project_key, description, project_type, owner_team, status, created_by)
    VALUES (NEWID(), 'Demo E-commerce Platform', 'DEMO01', 'Complete e-commerce solution with multiple components', 'WebApp', 'Development Team', 'active', 'admin');
    
    DECLARE @project_id INT = SCOPE_IDENTITY();
    
    -- Insert components for the demo project
    INSERT INTO components (component_guid, project_id, component_name, component_type, framework, artifact_source, created_by)
    VALUES 
        (NEWID(), @project_id, 'Web Frontend', 'webapp', 'react', 'artifactory://frontend-builds', 'admin'),
        (NEWID(), @project_id, 'API Backend', 'api', 'netcore', 'artifactory://api-builds', 'admin'),
        (NEWID(), @project_id, 'Background Service', 'service', 'netframework', 'artifactory://service-builds', 'admin');
    
    -- Insert environments
    INSERT INTO project_environments (project_id, environment_name, environment_description, region)
    VALUES 
        (@project_id, 'DEV1', 'Development Environment 1', 'US-EAST'),
        (@project_id, 'QA1', 'Quality Assurance Environment 1', 'US-EAST'),
        (@project_id, 'PROD_USA', 'Production USA Environment', 'US-EAST');
END

PRINT 'MSI Factory database schema created successfully for MS SQL Server'
GO