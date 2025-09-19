-- ============================================================
-- MSI Factory CMDB Integration Updates
-- Version: 1.0
-- Created: 2025-09-18
-- Description: Updates existing Projects and Components tables to integrate with CMDB
--              Maintains backward compatibility while adding CMDB references
-- ============================================================

SET NOCOUNT ON;
GO

USE MSIFactory;
GO

PRINT 'Updating Projects and Components tables for CMDB integration...';

-- ============================================================
-- UPDATE PROJECTS TABLE
-- Add CMDB-related columns to projects table
-- ============================================================

-- Add default_server_group column to projects
IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('projects') AND name = 'default_server_group_id')
BEGIN
    PRINT 'Adding CMDB columns to projects table...';

    ALTER TABLE projects ADD
        default_server_group_id INT,
        preferred_infra_type VARCHAR(20) CHECK (preferred_infra_type IN ('AWS', 'AZURE', 'WINTEL', 'VMWARE', 'HYPERV')),
        preferred_region VARCHAR(50),
        resource_requirements TEXT, -- JSON: {"min_cpu": 2, "min_memory_gb": 4, "min_storage_gb": 50}
        deployment_strategy VARCHAR(20) DEFAULT 'dedicated' CHECK (deployment_strategy IN ('dedicated', 'shared', 'mixed')),
        server_assignment_mode VARCHAR(20) DEFAULT 'manual' CHECK (server_assignment_mode IN ('manual', 'automatic', 'policy'));

    -- Add foreign key constraint
    ALTER TABLE projects ADD CONSTRAINT FK_projects_server_group
        FOREIGN KEY (default_server_group_id) REFERENCES cmdb_server_groups(group_id);

    PRINT 'Projects table updated with CMDB integration.';
END
ELSE
BEGIN
    PRINT 'Projects table already has CMDB integration columns.';
END
GO

-- ============================================================
-- UPDATE COMPONENTS TABLE
-- Add CMDB-related columns to components table
-- ============================================================

-- Add server deployment preferences to components
IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('components') AND name = 'preferred_server_id')
BEGIN
    PRINT 'Adding CMDB columns to components table...';

    ALTER TABLE components ADD
        preferred_server_id INT,
        deployment_strategy VARCHAR(20) DEFAULT 'automatic' CHECK (deployment_strategy IN ('manual', 'automatic', 'load_balanced')),
        resource_requirements TEXT, -- JSON: component-specific requirements
        network_requirements TEXT, -- JSON: ports, protocols, connectivity
        storage_requirements TEXT, -- JSON: storage paths, sizes, permissions
        service_dependencies VARCHAR(500), -- Comma-separated list of required services
        min_server_specs TEXT, -- JSON: minimum server specifications required
        scaling_policy VARCHAR(20) DEFAULT 'none' CHECK (scaling_policy IN ('none', 'manual', 'auto_scale')),
        max_instances INT DEFAULT 1;

    -- Add foreign key constraint
    ALTER TABLE components ADD CONSTRAINT FK_components_preferred_server
        FOREIGN KEY (preferred_server_id) REFERENCES cmdb_servers(server_id);

    PRINT 'Components table updated with CMDB integration.';
END
ELSE
BEGIN
    PRINT 'Components table already has CMDB integration columns.';
END
GO

-- ============================================================
-- UPDATE PROJECT_ENVIRONMENTS TABLE
-- Add server assignment tracking to environments
-- ============================================================

-- Add server count and assignment tracking to environments
IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('project_environments') AND name = 'assigned_server_count')
BEGIN
    PRINT 'Adding CMDB tracking to project_environments table...';

    ALTER TABLE project_environments ADD
        assigned_server_count INT DEFAULT 0,
        required_server_count INT DEFAULT 1,
        load_balancer_server_id INT,
        server_assignment_strategy VARCHAR(20) DEFAULT 'round_robin' CHECK (server_assignment_strategy IN ('round_robin', 'least_loaded', 'manual', 'affinity'));

    -- Add foreign key for load balancer
    ALTER TABLE project_environments ADD CONSTRAINT FK_project_env_load_balancer
        FOREIGN KEY (load_balancer_server_id) REFERENCES cmdb_servers(server_id);

    PRINT 'Project environments table updated with CMDB integration.';
END
ELSE
BEGIN
    PRINT 'Project environments table already has CMDB integration columns.';
END
GO

-- ============================================================
-- UPDATE MSI_CONFIGURATIONS TABLE
-- Add server-specific deployment configurations
-- ============================================================

-- Add target server references to MSI configurations
IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('msi_configurations') AND name = 'target_server_id')
BEGIN
    PRINT 'Adding CMDB references to msi_configurations table...';

    ALTER TABLE msi_configurations ADD
        target_server_id INT,
        backup_server_id INT,
        deployment_method VARCHAR(20) DEFAULT 'msi' CHECK (deployment_method IN ('msi', 'xcopy', 'robocopy', 'powershell')),
        server_validation_required BIT DEFAULT 1,
        pre_deployment_checks TEXT, -- JSON array of validation checks
        post_deployment_validation TEXT; -- JSON array of post-deployment tests

    -- Add foreign key constraints
    ALTER TABLE msi_configurations ADD CONSTRAINT FK_msi_config_target_server
        FOREIGN KEY (target_server_id) REFERENCES cmdb_servers(server_id);

    ALTER TABLE msi_configurations ADD CONSTRAINT FK_msi_config_backup_server
        FOREIGN KEY (backup_server_id) REFERENCES cmdb_servers(server_id);

    PRINT 'MSI configurations table updated with CMDB integration.';
END
ELSE
BEGIN
    PRINT 'MSI configurations table already has CMDB integration columns.';
END
GO

-- ============================================================
-- CREATE CMDB INTEGRATION VIEWS
-- ============================================================

PRINT 'Creating CMDB integration views...';

-- View: Project Server Allocation Summary
IF EXISTS (SELECT * FROM sys.views WHERE name = 'vw_project_server_allocation')
    DROP VIEW vw_project_server_allocation
GO

CREATE VIEW vw_project_server_allocation
AS
SELECT
    p.project_id,
    p.project_name,
    p.project_key,
    p.deployment_strategy,
    p.preferred_infra_type,
    p.preferred_region,

    -- Server assignment counts by environment
    (SELECT COUNT(*) FROM project_servers ps WHERE ps.project_id = p.project_id AND ps.is_active = 1) AS total_assigned_servers,

    -- Server assignments by environment
    (SELECT COUNT(*) FROM project_servers ps WHERE ps.project_id = p.project_id AND ps.environment_name LIKE '%DEV%' AND ps.is_active = 1) AS dev_servers,
    (SELECT COUNT(*) FROM project_servers ps WHERE ps.project_id = p.project_id AND ps.environment_name LIKE '%QA%' AND ps.is_active = 1) AS qa_servers,
    (SELECT COUNT(*) FROM project_servers ps WHERE ps.project_id = p.project_id AND ps.environment_name LIKE '%PROD%' AND ps.is_active = 1) AS prod_servers,

    -- Infrastructure distribution
    (SELECT COUNT(*) FROM project_servers ps INNER JOIN cmdb_servers s ON ps.server_id = s.server_id WHERE ps.project_id = p.project_id AND s.infra_type = 'AWS' AND ps.is_active = 1) AS aws_servers,
    (SELECT COUNT(*) FROM project_servers ps INNER JOIN cmdb_servers s ON ps.server_id = s.server_id WHERE ps.project_id = p.project_id AND s.infra_type = 'AZURE' AND ps.is_active = 1) AS azure_servers,
    (SELECT COUNT(*) FROM project_servers ps INNER JOIN cmdb_servers s ON ps.server_id = s.server_id WHERE ps.project_id = p.project_id AND s.infra_type = 'WINTEL' AND ps.is_active = 1) AS wintel_servers,

    p.created_date,
    p.created_by
FROM projects p
WHERE p.is_active = 1
GO

-- View: Component Deployment Status
IF EXISTS (SELECT * FROM sys.views WHERE name = 'vw_component_deployment_status')
    DROP VIEW vw_component_deployment_status
GO

CREATE VIEW vw_component_deployment_status
AS
SELECT
    c.component_id,
    c.component_name,
    c.component_type,
    c.framework,
    p.project_name,
    p.project_key,

    -- Deployment status by environment
    (SELECT COUNT(*) FROM component_servers cs WHERE cs.component_id = c.component_id AND cs.status = 'deployed' AND cs.is_active = 1) AS deployed_instances,
    (SELECT COUNT(*) FROM component_servers cs WHERE cs.component_id = c.component_id AND cs.status = 'active' AND cs.is_active = 1) AS active_instances,
    (SELECT COUNT(*) FROM component_servers cs WHERE cs.component_id = c.component_id AND cs.status = 'failed' AND cs.is_active = 1) AS failed_instances,

    -- Server assignments
    (SELECT COUNT(DISTINCT cs.server_id) FROM component_servers cs WHERE cs.component_id = c.component_id AND cs.is_active = 1) AS unique_servers,

    -- Preferred server info
    s.server_name AS preferred_server,
    s.infra_type AS preferred_infra_type,
    s.region AS preferred_region,

    c.deployment_strategy,
    c.scaling_policy,
    c.max_instances,
    c.created_date
FROM components c
INNER JOIN projects p ON c.project_id = p.project_id
LEFT JOIN cmdb_servers s ON c.preferred_server_id = s.server_id
WHERE c.is_enabled = 1 AND p.is_active = 1
GO

-- View: Server Utilization and Assignments
IF EXISTS (SELECT * FROM sys.views WHERE name = 'vw_server_utilization_dashboard')
    DROP VIEW vw_server_utilization_dashboard
GO

CREATE VIEW vw_server_utilization_dashboard
AS
SELECT
    s.server_id,
    s.server_name,
    s.fqdn,
    s.infra_type,
    s.region,
    s.environment_type,
    s.status,

    -- Resource specifications
    s.cpu_cores,
    s.memory_gb,
    s.storage_gb,

    -- Current utilization
    s.current_app_count,
    s.max_concurrent_apps,
    CASE
        WHEN s.max_concurrent_apps > 0
        THEN CAST(s.current_app_count AS DECIMAL(5,2)) / s.max_concurrent_apps * 100
        ELSE 0
    END AS capacity_utilization_percent,

    -- Project assignments
    (SELECT COUNT(*) FROM project_servers ps WHERE ps.server_id = s.server_id AND ps.is_active = 1) AS project_assignments,
    (SELECT COUNT(*) FROM component_servers cs WHERE cs.server_id = s.server_id AND cs.is_active = 1) AS component_deployments,

    -- Team assignments
    (SELECT COUNT(DISTINCT p.owner_team) FROM project_servers ps INNER JOIN projects p ON ps.project_id = p.project_id WHERE ps.server_id = s.server_id AND ps.is_active = 1) AS assigned_teams,

    s.owner_team,
    s.technical_contact,
    s.last_updated
FROM cmdb_servers s
WHERE s.is_active = 1
GO

-- ============================================================
-- CREATE CMDB HELPER STORED PROCEDURES
-- ============================================================

PRINT 'Creating CMDB helper procedures...';

-- Procedure: Assign Server to Project Environment
IF EXISTS (SELECT * FROM sys.objects WHERE type = 'P' AND name = 'sp_AssignServerToProject')
    DROP PROCEDURE sp_AssignServerToProject
GO

CREATE PROCEDURE sp_AssignServerToProject
    @project_id INT,
    @server_id INT,
    @environment_name VARCHAR(50),
    @assignment_type VARCHAR(20) = 'shared',
    @purpose VARCHAR(100) = NULL,
    @assigned_by VARCHAR(50)
AS
BEGIN
    SET NOCOUNT ON;

    DECLARE @result VARCHAR(100);

    -- Validate inputs
    IF NOT EXISTS (SELECT 1 FROM projects WHERE project_id = @project_id AND is_active = 1)
    BEGIN
        SELECT 'ERROR: Project not found or inactive' AS result;
        RETURN;
    END

    IF NOT EXISTS (SELECT 1 FROM cmdb_servers WHERE server_id = @server_id AND is_active = 1)
    BEGIN
        SELECT 'ERROR: Server not found or inactive' AS result;
        RETURN;
    END

    -- Check if assignment already exists
    IF EXISTS (SELECT 1 FROM project_servers WHERE project_id = @project_id AND server_id = @server_id AND environment_name = @environment_name AND is_active = 1)
    BEGIN
        SELECT 'WARNING: Server already assigned to this project environment' AS result;
        RETURN;
    END

    -- Insert assignment
    INSERT INTO project_servers (
        project_id, server_id, environment_name, assignment_type, purpose, assigned_by
    )
    VALUES (
        @project_id, @server_id, @environment_name, @assignment_type, @purpose, @assigned_by
    );

    -- Update server current app count
    UPDATE cmdb_servers
    SET current_app_count = current_app_count + 1, last_updated = GETDATE()
    WHERE server_id = @server_id;

    -- Update environment server count
    UPDATE project_environments
    SET assigned_server_count = assigned_server_count + 1
    WHERE project_id = @project_id AND environment_name = @environment_name;

    SELECT 'SUCCESS: Server assigned to project environment' AS result;
END
GO

-- Procedure: Auto-assign servers based on requirements
IF EXISTS (SELECT * FROM sys.objects WHERE type = 'P' AND name = 'sp_AutoAssignServers')
    DROP PROCEDURE sp_AutoAssignServers
GO

CREATE PROCEDURE sp_AutoAssignServers
    @project_id INT,
    @environment_name VARCHAR(50),
    @required_servers INT = 1,
    @preferred_infra_type VARCHAR(20) = NULL,
    @preferred_region VARCHAR(50) = NULL,
    @assigned_by VARCHAR(50)
AS
BEGIN
    SET NOCOUNT ON;

    DECLARE @assigned_count INT = 0;
    DECLARE @server_id INT;

    -- Cursor to find available servers
    DECLARE server_cursor CURSOR FOR
    SELECT TOP (@required_servers) server_id
    FROM cmdb_servers
    WHERE status = 'active'
      AND is_active = 1
      AND (current_app_count < max_concurrent_apps OR max_concurrent_apps = 0)
      AND (@preferred_infra_type IS NULL OR infra_type = @preferred_infra_type)
      AND (@preferred_region IS NULL OR region = @preferred_region)
      AND server_id NOT IN (
          SELECT server_id FROM project_servers
          WHERE project_id = @project_id AND environment_name = @environment_name AND is_active = 1
      )
    ORDER BY
        CASE WHEN current_app_count = 0 THEN 0 ELSE 1 END, -- Prefer unused servers
        current_app_count ASC; -- Then least utilized

    OPEN server_cursor;
    FETCH NEXT FROM server_cursor INTO @server_id;

    WHILE @@FETCH_STATUS = 0 AND @assigned_count < @required_servers
    BEGIN
        -- Assign server to project
        EXEC sp_AssignServerToProject
            @project_id = @project_id,
            @server_id = @server_id,
            @environment_name = @environment_name,
            @assignment_type = 'shared',
            @purpose = 'Auto-assigned',
            @assigned_by = @assigned_by;

        SET @assigned_count = @assigned_count + 1;

        FETCH NEXT FROM server_cursor INTO @server_id;
    END

    CLOSE server_cursor;
    DEALLOCATE server_cursor;

    SELECT @assigned_count AS servers_assigned, @required_servers AS servers_requested;
END
GO

-- ============================================================
-- UPDATE SAMPLE DATA
-- ============================================================

PRINT 'Updating sample data with CMDB assignments...';

-- Update sample project with CMDB preferences
IF EXISTS (SELECT * FROM projects WHERE project_key = 'DEMO01')
BEGIN
    UPDATE projects
    SET preferred_infra_type = 'WINTEL',
        preferred_region = 'US-EAST-1',
        deployment_strategy = 'mixed',
        resource_requirements = '{"min_cpu": 2, "min_memory_gb": 4, "min_storage_gb": 50, "iis_required": true}'
    WHERE project_key = 'DEMO01';

    -- Assign servers to the demo project
    DECLARE @demo_project_id INT = (SELECT project_id FROM projects WHERE project_key = 'DEMO01');
    DECLARE @devweb01_id INT = (SELECT server_id FROM cmdb_servers WHERE server_name = 'DEVWEB01');
    DECLARE @devweb02_id INT = (SELECT server_id FROM cmdb_servers WHERE server_name = 'DEVWEB02');

    IF @demo_project_id IS NOT NULL AND @devweb01_id IS NOT NULL
    BEGIN
        -- Assign development servers
        IF NOT EXISTS (SELECT 1 FROM project_servers WHERE project_id = @demo_project_id AND server_id = @devweb01_id)
        BEGIN
            EXEC sp_AssignServerToProject
                @project_id = @demo_project_id,
                @server_id = @devweb01_id,
                @environment_name = 'DEV1',
                @assignment_type = 'shared',
                @purpose = 'Web Server',
                @assigned_by = 'admin';
        END

        IF @devweb02_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM project_servers WHERE project_id = @demo_project_id AND server_id = @devweb02_id)
        BEGIN
            EXEC sp_AssignServerToProject
                @project_id = @demo_project_id,
                @server_id = @devweb02_id,
                @environment_name = 'DEV2',
                @assignment_type = 'dedicated',
                @purpose = 'API Server',
                @assigned_by = 'admin';
        END
    END

    PRINT 'Sample project updated with CMDB assignments.';
END

GO

-- ============================================================
-- CMDB INTEGRATION UPDATES COMPLETE
-- ============================================================
PRINT '============================================================'
PRINT 'MSI Factory CMDB Integration Updates COMPLETE'
PRINT '============================================================'
PRINT 'Integration Features Added:'
PRINT '  ✓ Projects table updated with server preferences'
PRINT '  ✓ Components table updated with deployment requirements'
PRINT '  ✓ MSI configurations linked to target servers'
PRINT '  ✓ Project environments track server assignments'
PRINT '  ✓ Server allocation and utilization views'
PRINT '  ✓ Automated server assignment procedures'
PRINT '  ✓ Sample data updated with CMDB relationships'
PRINT ''
PRINT 'Benefits:'
PRINT '  ✓ Shared server resources across projects'
PRINT '  ✓ Multi-team server utilization'
PRINT '  ✓ Infrastructure-aware deployment'
PRINT '  ✓ Automated server selection'
PRINT '  ✓ Resource utilization tracking'
PRINT '============================================================'

GO
SET NOCOUNT OFF;