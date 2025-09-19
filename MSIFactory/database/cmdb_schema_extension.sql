-- ============================================================
-- MSI Factory CMDB (Configuration Management Database) Extension
-- Version: 1.0
-- Created: 2025-09-18
-- Description: Server inventory and infrastructure management system
--              Enables shared server resources across projects and components
-- ============================================================

SET NOCOUNT ON;
GO

USE MSIFactory;
GO

PRINT 'Installing MSI Factory CMDB Extension...';

-- ============================================================
-- CMDB CORE TABLES
-- ============================================================

-- ============================================================
-- CMDB_SERVERS TABLE
-- Central server inventory with comprehensive attributes
-- ============================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='cmdb_servers' AND xtype='U')
BEGIN
    PRINT 'Creating cmdb_servers table...';
    CREATE TABLE cmdb_servers (
        server_id INT PRIMARY KEY IDENTITY(1,1),
        server_name VARCHAR(100) UNIQUE NOT NULL,
        fqdn VARCHAR(255) UNIQUE NOT NULL,

        -- Infrastructure Details
        infra_type VARCHAR(20) NOT NULL CHECK (infra_type IN ('AWS', 'AZURE', 'WINTEL', 'VMWARE', 'HYPERV')),
        ip_address VARCHAR(45) NOT NULL,
        ip_address_internal VARCHAR(45), -- For dual-homed servers
        subnet VARCHAR(50),
        vlan VARCHAR(20),

        -- Location & Region
        region VARCHAR(50) NOT NULL,
        datacenter VARCHAR(100),
        availability_zone VARCHAR(50), -- For cloud providers
        rack_location VARCHAR(50), -- For on-premises

        -- Hardware Specifications
        cpu_cores INT,
        memory_gb INT,
        storage_gb INT,
        os_version VARCHAR(100),
        os_edition VARCHAR(50),
        architecture VARCHAR(20) CHECK (architecture IN ('x64', 'x86', 'ARM64')),

        -- Cloud-Specific Attributes (AWS/Azure)
        cloud_instance_id VARCHAR(100), -- i-1234567890abcdef0 or /subscriptions/.../vm-name
        cloud_instance_type VARCHAR(50), -- t3.medium, Standard_D2s_v3
        cloud_account_id VARCHAR(100),
        cloud_subscription VARCHAR(200),
        cloud_resource_group VARCHAR(100),

        -- Virtualization (WINTEL/VMware)
        hypervisor_host VARCHAR(100),
        vm_tools_version VARCHAR(50),
        vm_id VARCHAR(100),

        -- Network Configuration
        dns_servers VARCHAR(200), -- Comma-separated
        gateway VARCHAR(45),
        domain_name VARCHAR(100),

        -- Service Configuration
        iis_installed BIT DEFAULT 0,
        iis_version VARCHAR(20),
        dotnet_versions VARCHAR(200), -- Comma-separated: 4.8,6.0,8.0
        sql_server_installed BIT DEFAULT 0,
        sql_server_version VARCHAR(50),

        -- Security & Compliance
        security_group VARCHAR(100),
        patch_group VARCHAR(50),
        compliance_level VARCHAR(20) CHECK (compliance_level IN ('DEV', 'TEST', 'PROD', 'DMZ')),
        antivirus_status VARCHAR(50),
        last_patched DATE,

        -- Operational Status
        status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'maintenance', 'decommissioned')),
        environment_type VARCHAR(20) CHECK (environment_type IN ('development', 'testing', 'staging', 'production')),
        criticality VARCHAR(20) DEFAULT 'medium' CHECK (criticality IN ('low', 'medium', 'high', 'critical')),

        -- Capacity & Performance
        cpu_utilization_avg DECIMAL(5,2), -- Average CPU utilization %
        memory_utilization_avg DECIMAL(5,2), -- Average memory utilization %
        disk_utilization_avg DECIMAL(5,2), -- Average disk utilization %
        max_concurrent_apps INT DEFAULT 5,
        current_app_count INT DEFAULT 0,

        -- Maintenance & Monitoring
        monitoring_enabled BIT DEFAULT 1,
        backup_enabled BIT DEFAULT 1,
        maintenance_window VARCHAR(100), -- "SAT 02:00-06:00 EST"

        -- Ownership & Contacts
        owner_team VARCHAR(100),
        technical_contact VARCHAR(100),
        business_contact VARCHAR(100),
        cost_center VARCHAR(50),

        -- Metadata
        discovered_date DATETIME DEFAULT GETDATE(),
        last_updated DATETIME DEFAULT GETDATE(),
        updated_by VARCHAR(50),
        created_by VARCHAR(50) NOT NULL,
        is_active BIT DEFAULT 1,

        -- Additional Attributes (JSON for extensibility)
        custom_attributes TEXT, -- JSON format for additional properties
        tags VARCHAR(500), -- Comma-separated tags
        notes TEXT,

        -- Constraints
        CONSTRAINT CK_cmdb_server_name CHECK (LEN(TRIM(server_name)) > 0),
        CONSTRAINT CK_cmdb_ip_format CHECK (ip_address LIKE '%.%.%.%' OR ip_address LIKE '%:%'), -- IPv4 or IPv6
        CONSTRAINT CK_cmdb_utilization CHECK (
            (cpu_utilization_avg IS NULL OR cpu_utilization_avg BETWEEN 0 AND 100) AND
            (memory_utilization_avg IS NULL OR memory_utilization_avg BETWEEN 0 AND 100) AND
            (disk_utilization_avg IS NULL OR disk_utilization_avg BETWEEN 0 AND 100)
        )
    );
    PRINT 'CMDB servers table created successfully.';
END
ELSE
BEGIN
    PRINT 'CMDB servers table already exists.';
END
GO

-- ============================================================
-- CMDB_SERVER_GROUPS TABLE
-- Logical grouping of servers (clusters, load balancers, etc.)
-- ============================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='cmdb_server_groups' AND xtype='U')
BEGIN
    PRINT 'Creating cmdb_server_groups table...';
    CREATE TABLE cmdb_server_groups (
        group_id INT PRIMARY KEY IDENTITY(1,1),
        group_name VARCHAR(100) UNIQUE NOT NULL,
        group_type VARCHAR(50) NOT NULL CHECK (group_type IN ('cluster', 'load_balancer', 'farm', 'availability_set', 'auto_scaling_group')),
        description TEXT,

        -- Group Configuration
        load_balancer_ip VARCHAR(45),
        load_balancer_fqdn VARCHAR(255),
        health_check_url VARCHAR(500),

        -- Metadata
        created_date DATETIME DEFAULT GETDATE(),
        created_by VARCHAR(50) NOT NULL,
        is_active BIT DEFAULT 1
    );
    PRINT 'CMDB server groups table created successfully.';
END
GO

-- ============================================================
-- CMDB_SERVER_GROUP_MEMBERS TABLE
-- Many-to-many relationship between servers and groups
-- ============================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='cmdb_server_group_members' AND xtype='U')
BEGIN
    PRINT 'Creating cmdb_server_group_members table...';
    CREATE TABLE cmdb_server_group_members (
        member_id INT PRIMARY KEY IDENTITY(1,1),
        group_id INT NOT NULL,
        server_id INT NOT NULL,
        role_in_group VARCHAR(50), -- primary, secondary, witness, etc.
        priority INT DEFAULT 1,
        is_active BIT DEFAULT 1,
        added_date DATETIME DEFAULT GETDATE(),

        FOREIGN KEY (group_id) REFERENCES cmdb_server_groups(group_id) ON DELETE CASCADE,
        FOREIGN KEY (server_id) REFERENCES cmdb_servers(server_id) ON DELETE CASCADE,

        CONSTRAINT UK_server_group_member UNIQUE (group_id, server_id)
    );
    PRINT 'CMDB server group members table created successfully.';
END
GO

-- ============================================================
-- PROJECT-CMDB INTEGRATION TABLES
-- ============================================================

-- ============================================================
-- PROJECT_SERVERS TABLE
-- Links projects to their assigned servers
-- ============================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='project_servers' AND xtype='U')
BEGIN
    PRINT 'Creating project_servers table...';
    CREATE TABLE project_servers (
        project_server_id INT PRIMARY KEY IDENTITY(1,1),
        project_id INT NOT NULL,
        server_id INT NOT NULL,
        environment_name VARCHAR(50) NOT NULL,

        -- Assignment Details
        assignment_type VARCHAR(20) NOT NULL CHECK (assignment_type IN ('dedicated', 'shared', 'primary', 'secondary')),
        purpose VARCHAR(100), -- "Web Server", "Database Server", "Load Balancer"
        priority INT DEFAULT 1,

        -- Resource Allocation
        allocated_cpu_percent DECIMAL(5,2),
        allocated_memory_gb INT,
        allocated_storage_gb INT,

        -- Status
        status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'pending', 'maintenance')),

        -- Metadata
        assigned_date DATETIME DEFAULT GETDATE(),
        assigned_by VARCHAR(50) NOT NULL,
        is_active BIT DEFAULT 1,

        FOREIGN KEY (project_id) REFERENCES projects(project_id) ON DELETE CASCADE,
        FOREIGN KEY (server_id) REFERENCES cmdb_servers(server_id) ON DELETE CASCADE,

        CONSTRAINT UK_project_server_env UNIQUE (project_id, server_id, environment_name)
    );
    PRINT 'Project servers table created successfully.';
END
GO

-- ============================================================
-- COMPONENT_SERVERS TABLE
-- Links components to their specific deployment servers
-- ============================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='component_servers' AND xtype='U')
BEGIN
    PRINT 'Creating component_servers table...';
    CREATE TABLE component_servers (
        component_server_id INT PRIMARY KEY IDENTITY(1,1),
        component_id INT NOT NULL,
        server_id INT NOT NULL,
        environment_name VARCHAR(50) NOT NULL,

        -- Deployment Configuration
        deployment_path VARCHAR(500), -- Physical path on server
        service_name VARCHAR(255), -- For Windows services
        iis_site_name VARCHAR(255), -- For web applications
        port_number INT,

        -- Resource Requirements
        min_cpu_cores INT,
        min_memory_gb INT,
        min_storage_gb INT,

        -- Status
        status VARCHAR(20) DEFAULT 'planned' CHECK (status IN ('planned', 'deployed', 'active', 'inactive', 'failed')),
        deployment_date DATETIME,
        last_deployment_date DATETIME,

        -- Metadata
        assigned_date DATETIME DEFAULT GETDATE(),
        assigned_by VARCHAR(50) NOT NULL,
        is_active BIT DEFAULT 1,

        FOREIGN KEY (component_id) REFERENCES components(component_id) ON DELETE CASCADE,
        FOREIGN KEY (server_id) REFERENCES cmdb_servers(server_id) ON DELETE CASCADE,

        CONSTRAINT UK_component_server_env UNIQUE (component_id, server_id, environment_name),
        CONSTRAINT CK_component_port CHECK (port_number IS NULL OR port_number BETWEEN 1 AND 65535)
    );
    PRINT 'Component servers table created successfully.';
END
GO

-- ============================================================
-- CMDB AUDIT AND MONITORING TABLES
-- ============================================================

-- ============================================================
-- CMDB_SERVER_CHANGES TABLE
-- Audit trail for server configuration changes
-- ============================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='cmdb_server_changes' AND xtype='U')
BEGIN
    PRINT 'Creating cmdb_server_changes table...';
    CREATE TABLE cmdb_server_changes (
        change_id INT PRIMARY KEY IDENTITY(1,1),
        server_id INT NOT NULL,
        change_type VARCHAR(50) NOT NULL, -- 'created', 'updated', 'deleted', 'status_change'
        field_name VARCHAR(100),
        old_value VARCHAR(500),
        new_value VARCHAR(500),
        change_reason TEXT,

        -- Metadata
        changed_date DATETIME DEFAULT GETDATE(),
        changed_by VARCHAR(50) NOT NULL,
        change_source VARCHAR(50) DEFAULT 'manual', -- manual, automated, discovery

        FOREIGN KEY (server_id) REFERENCES cmdb_servers(server_id) ON DELETE CASCADE
    );
    PRINT 'CMDB server changes table created successfully.';
END
GO

-- ============================================================
-- CMDB_DISCOVERY_RUNS TABLE
-- Track automated discovery processes
-- ============================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='cmdb_discovery_runs' AND xtype='U')
BEGIN
    PRINT 'Creating cmdb_discovery_runs table...';
    CREATE TABLE cmdb_discovery_runs (
        run_id INT PRIMARY KEY IDENTITY(1,1),
        discovery_type VARCHAR(50) NOT NULL, -- 'network_scan', 'cloud_api', 'manual_import'
        discovery_scope VARCHAR(200), -- IP range, cloud subscription, etc.

        -- Results
        servers_discovered INT DEFAULT 0,
        servers_updated INT DEFAULT 0,
        servers_new INT DEFAULT 0,

        -- Status
        status VARCHAR(20) DEFAULT 'running' CHECK (status IN ('running', 'completed', 'failed', 'cancelled')),
        start_time DATETIME DEFAULT GETDATE(),
        end_time DATETIME,
        error_message TEXT,

        -- Metadata
        initiated_by VARCHAR(50) NOT NULL,
        discovery_log TEXT -- Detailed log of discovery process
    );
    PRINT 'CMDB discovery runs table created successfully.';
END
GO

-- ============================================================
-- INDEXES FOR PERFORMANCE
-- ============================================================
PRINT 'Creating CMDB indexes...';

-- CMDB Servers indexes
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_cmdb_servers_name' AND object_id = OBJECT_ID('cmdb_servers'))
    CREATE INDEX idx_cmdb_servers_name ON cmdb_servers(server_name);

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_cmdb_servers_fqdn' AND object_id = OBJECT_ID('cmdb_servers'))
    CREATE INDEX idx_cmdb_servers_fqdn ON cmdb_servers(fqdn);

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_cmdb_servers_ip' AND object_id = OBJECT_ID('cmdb_servers'))
    CREATE INDEX idx_cmdb_servers_ip ON cmdb_servers(ip_address);

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_cmdb_servers_infra_region' AND object_id = OBJECT_ID('cmdb_servers'))
    CREATE INDEX idx_cmdb_servers_infra_region ON cmdb_servers(infra_type, region);

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_cmdb_servers_status' AND object_id = OBJECT_ID('cmdb_servers'))
    CREATE INDEX idx_cmdb_servers_status ON cmdb_servers(status, environment_type);

-- Project-Server relationship indexes
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_project_servers_project' AND object_id = OBJECT_ID('project_servers'))
    CREATE INDEX idx_project_servers_project ON project_servers(project_id, environment_name);

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_project_servers_server' AND object_id = OBJECT_ID('project_servers'))
    CREATE INDEX idx_project_servers_server ON project_servers(server_id);

-- Component-Server relationship indexes
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_component_servers_component' AND object_id = OBJECT_ID('component_servers'))
    CREATE INDEX idx_component_servers_component ON component_servers(component_id, environment_name);

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_component_servers_server' AND object_id = OBJECT_ID('component_servers'))
    CREATE INDEX idx_component_servers_server ON component_servers(server_id);

-- Audit indexes
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_cmdb_changes_server_date' AND object_id = OBJECT_ID('cmdb_server_changes'))
    CREATE INDEX idx_cmdb_changes_server_date ON cmdb_server_changes(server_id, changed_date);

GO

-- ============================================================
-- SAMPLE CMDB DATA
-- ============================================================
PRINT 'Inserting sample CMDB data...';

-- Sample servers for different infrastructure types
IF NOT EXISTS (SELECT * FROM cmdb_servers WHERE server_name = 'DEVWEB01')
BEGIN
    INSERT INTO cmdb_servers (
        server_name, fqdn, infra_type, ip_address, region, datacenter,
        cpu_cores, memory_gb, storage_gb, os_version, architecture,
        iis_installed, iis_version, dotnet_versions,
        status, environment_type, criticality,
        owner_team, technical_contact, created_by
    ) VALUES
    -- On-premises WINTEL servers
    ('DEVWEB01', 'devweb01.company.local', 'WINTEL', '10.1.1.10', 'US-EAST-1', 'DC-CORP-01',
     4, 8, 100, 'Windows Server 2019', 'x64',
     1, '10.0', '4.8,6.0,8.0',
     'active', 'development', 'medium',
     'DevOps Team', 'admin@company.com', 'admin'),

    ('DEVWEB02', 'devweb02.company.local', 'WINTEL', '10.1.1.11', 'US-EAST-1', 'DC-CORP-01',
     4, 8, 100, 'Windows Server 2019', 'x64',
     1, '10.0', '4.8,6.0,8.0',
     'active', 'development', 'medium',
     'DevOps Team', 'admin@company.com', 'admin'),

    -- AWS servers
    ('AWS-PROD-WEB01', 'aws-prod-web01.company.com', 'AWS', '10.0.1.10', 'US-EAST-1', 'AWS-Virginia',
     2, 4, 50, 'Windows Server 2022', 'x64',
     1, '10.0', '4.8,6.0,8.0',
     'active', 'production', 'high',
     'Production Team', 'ops@company.com', 'admin'),

    -- Azure servers
    ('AZ-QA-WEB01', 'az-qa-web01.company.com', 'AZURE', '10.2.1.10', 'US-WEST-2', 'Azure-West',
     2, 4, 50, 'Windows Server 2022', 'x64',
     1, '10.0', '4.8,6.0,8.0',
     'active', 'testing', 'medium',
     'QA Team', 'qa@company.com', 'admin');

    PRINT 'Sample CMDB servers inserted.';
END

-- Sample server groups
IF NOT EXISTS (SELECT * FROM cmdb_server_groups WHERE group_name = 'DEV-WEB-FARM')
BEGIN
    INSERT INTO cmdb_server_groups (group_name, group_type, description, created_by)
    VALUES
    ('DEV-WEB-FARM', 'farm', 'Development web server farm', 'admin'),
    ('PROD-WEB-CLUSTER', 'cluster', 'Production web server cluster with load balancer', 'admin');

    -- Add servers to groups
    DECLARE @dev_group_id INT = (SELECT group_id FROM cmdb_server_groups WHERE group_name = 'DEV-WEB-FARM');
    DECLARE @devweb01_id INT = (SELECT server_id FROM cmdb_servers WHERE server_name = 'DEVWEB01');
    DECLARE @devweb02_id INT = (SELECT server_id FROM cmdb_servers WHERE server_name = 'DEVWEB02');

    INSERT INTO cmdb_server_group_members (group_id, server_id, role_in_group, priority)
    VALUES
    (@dev_group_id, @devweb01_id, 'primary', 1),
    (@dev_group_id, @devweb02_id, 'secondary', 2);

    PRINT 'Sample server groups and memberships created.';
END

GO

-- ============================================================
-- VIEWS FOR CMDB QUERIES
-- ============================================================
PRINT 'Creating CMDB views...';

-- Server inventory view with utilization
IF EXISTS (SELECT * FROM sys.views WHERE name = 'vw_cmdb_server_inventory')
    DROP VIEW vw_cmdb_server_inventory
GO

CREATE VIEW vw_cmdb_server_inventory
AS
SELECT
    s.server_id,
    s.server_name,
    s.fqdn,
    s.infra_type,
    s.ip_address,
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
        WHEN s.max_concurrent_apps > 0
        THEN CAST(s.current_app_count AS DECIMAL(5,2)) / s.max_concurrent_apps * 100
        ELSE 0
    END AS capacity_utilization_percent,
    s.owner_team,
    s.technical_contact,
    s.last_updated
FROM cmdb_servers s
WHERE s.is_active = 1
GO

-- Project server assignments view
IF EXISTS (SELECT * FROM sys.views WHERE name = 'vw_project_server_assignments')
    DROP VIEW vw_project_server_assignments
GO

CREATE VIEW vw_project_server_assignments
AS
SELECT
    p.project_name,
    p.project_key,
    s.server_name,
    s.fqdn,
    s.infra_type,
    s.region,
    ps.environment_name,
    ps.assignment_type,
    ps.purpose,
    ps.status,
    ps.assigned_date,
    ps.assigned_by
FROM project_servers ps
INNER JOIN projects p ON ps.project_id = p.project_id
INNER JOIN cmdb_servers s ON ps.server_id = s.server_id
WHERE ps.is_active = 1 AND p.is_active = 1 AND s.is_active = 1
GO

-- ============================================================
-- STORED PROCEDURES FOR CMDB OPERATIONS
-- ============================================================

-- Server discovery procedure
IF EXISTS (SELECT * FROM sys.objects WHERE type = 'P' AND name = 'sp_CMDB_DiscoverServer')
    DROP PROCEDURE sp_CMDB_DiscoverServer
GO

CREATE PROCEDURE sp_CMDB_DiscoverServer
    @server_name VARCHAR(100),
    @ip_address VARCHAR(45),
    @infra_type VARCHAR(20),
    @region VARCHAR(50),
    @discovered_by VARCHAR(50)
AS
BEGIN
    SET NOCOUNT ON;

    DECLARE @server_id INT;

    -- Check if server already exists
    SELECT @server_id = server_id
    FROM cmdb_servers
    WHERE server_name = @server_name OR ip_address = @ip_address;

    IF @server_id IS NULL
    BEGIN
        -- Insert new server
        INSERT INTO cmdb_servers (
            server_name, fqdn, infra_type, ip_address, region,
            status, discovered_date, created_by
        )
        VALUES (
            @server_name,
            @server_name + CASE @infra_type
                WHEN 'WINTEL' THEN '.company.local'
                WHEN 'AWS' THEN '.company.com'
                WHEN 'AZURE' THEN '.company.com'
                ELSE '.company.local'
            END,
            @infra_type,
            @ip_address,
            @region,
            'active',
            GETDATE(),
            @discovered_by
        );

        SET @server_id = SCOPE_IDENTITY();

        -- Log the discovery
        INSERT INTO cmdb_server_changes (
            server_id, change_type, change_reason, changed_by, change_source
        )
        VALUES (
            @server_id, 'created', 'Automated discovery', @discovered_by, 'automated'
        );

        SELECT @server_id AS server_id, 'CREATED' AS action;
    END
    ELSE
    BEGIN
        -- Update last discovered date
        UPDATE cmdb_servers
        SET last_updated = GETDATE(), updated_by = @discovered_by
        WHERE server_id = @server_id;

        SELECT @server_id AS server_id, 'UPDATED' AS action;
    END
END
GO

-- ============================================================
-- CMDB INSTALLATION COMPLETE
-- ============================================================
PRINT '============================================================'
PRINT 'MSI Factory CMDB Extension Installation COMPLETE'
PRINT '============================================================'
PRINT 'CMDB Features Installed:'
PRINT '  ✓ Server inventory with comprehensive attributes'
PRINT '  ✓ Infrastructure type support (AWS, Azure, WINTEL)'
PRINT '  ✓ Server grouping and clustering'
PRINT '  ✓ Project-server assignments'
PRINT '  ✓ Component-server deployments'
PRINT '  ✓ Change tracking and audit trail'
PRINT '  ✓ Automated discovery framework'
PRINT '  ✓ Performance indexes'
PRINT '  ✓ Sample data and views'
PRINT ''
PRINT 'Next Steps:'
PRINT '  1. Use the CMDB web interface to manage servers'
PRINT '  2. Assign servers to projects and environments'
PRINT '  3. Configure component deployment targets'
PRINT '  4. Set up automated discovery processes'
PRINT '============================================================'

GO
SET NOCOUNT OFF;