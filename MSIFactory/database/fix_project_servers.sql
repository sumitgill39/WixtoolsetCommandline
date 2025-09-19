-- ============================================================
-- Fix for project_servers table creation
-- This script creates the missing project_servers table
-- ============================================================

USE MSIFactory;
GO

-- Drop the table if it exists (in case of partial creation)
IF EXISTS (SELECT * FROM sysobjects WHERE name='project_servers' AND xtype='U')
BEGIN
    DROP TABLE project_servers;
    PRINT 'Dropped existing project_servers table.';
END
GO

-- Create project_servers table with corrected foreign key constraints
PRINT 'Creating project_servers table...';
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

    FOREIGN KEY (project_id) REFERENCES projects(project_id) ON DELETE NO ACTION,
    FOREIGN KEY (environment_id) REFERENCES project_environments(env_id) ON DELETE NO ACTION,
    FOREIGN KEY (server_id) REFERENCES cmdb_servers(server_id) ON DELETE CASCADE,

    UNIQUE(project_id, environment_id, server_id, assignment_type)
);
PRINT 'Project servers table created successfully.';
GO

-- Create indexes for performance
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_project_servers_project' AND object_id = OBJECT_ID('project_servers'))
    CREATE INDEX idx_project_servers_project ON project_servers(project_id);

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_project_servers_server' AND object_id = OBJECT_ID('project_servers'))
    CREATE INDEX idx_project_servers_server ON project_servers(server_id);

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_project_servers_env' AND object_id = OBJECT_ID('project_servers'))
    CREATE INDEX idx_project_servers_env ON project_servers(environment_id);
GO

-- Recreate the views that depend on project_servers
IF EXISTS (SELECT * FROM sys.views WHERE name = 'vw_project_server_assignments')
    DROP VIEW vw_project_server_assignments
GO

CREATE VIEW vw_project_server_assignments
AS
SELECT
    ps.assignment_id,
    p.project_name,
    p.project_key,
    pe.environment_name,
    pe.environment_type,
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
GO

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
    -- Group membership
    STRING_AGG(sg.group_name, ', ') as server_groups,
    -- Project assignments count
    (SELECT COUNT(*) FROM project_servers ps WHERE ps.server_id = s.server_id AND ps.status = 'active') as active_assignments
FROM cmdb_servers s
LEFT JOIN cmdb_server_group_members sgm ON s.server_id = sgm.server_id AND sgm.is_active = 1
LEFT JOIN cmdb_server_groups sg ON sgm.group_id = sg.group_id AND sg.is_active = 1
WHERE s.is_active = 1
GROUP BY
    s.server_id, s.server_name, s.fqdn, s.infra_type, s.ip_address, s.ip_address_internal,
    s.region, s.datacenter, s.environment_type, s.status, s.cpu_cores, s.memory_gb,
    s.storage_gb, s.current_app_count, s.max_concurrent_apps, s.owner_team,
    s.technical_contact, s.created_date, s.last_updated
GO

-- Update statistics
UPDATE STATISTICS project_servers;
GO

PRINT '============================================================';
PRINT 'Project Servers Table Fix Complete';
PRINT '============================================================';
PRINT 'Successfully created:';
PRINT '  ✓ project_servers table';
PRINT '  ✓ Performance indexes';
PRINT '  ✓ vw_project_server_assignments view';
PRINT '  ✓ vw_cmdb_server_inventory view';
PRINT '============================================================';