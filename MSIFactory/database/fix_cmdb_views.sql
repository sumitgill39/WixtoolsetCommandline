-- ============================================================
-- Fix for CMDB Views
-- This script fixes the view errors
-- ============================================================

USE MSIFactory;
GO

-- First, let's check what columns exist in project_environments table
-- SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'project_environments';

-- Drop and recreate the view with correct column names
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
    pe.environment_description,  -- Changed from environment_type
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

PRINT 'View vw_project_server_assignments recreated successfully.';

-- Also fix the component details view
IF EXISTS (SELECT * FROM sys.views WHERE name = 'vw_component_details')
    DROP VIEW vw_component_details
GO

CREATE VIEW vw_component_details
AS
SELECT
    c.component_id,
    c.component_guid,
    c.component_name,
    c.component_type,
    c.framework,
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
WHERE p.is_active = 1
GO

PRINT 'View vw_component_details recreated successfully.';

PRINT '============================================================';
PRINT 'CMDB Views Fix Complete';
PRINT '============================================================';
PRINT 'Successfully fixed:';
PRINT '  ✓ vw_project_server_assignments view';
PRINT '  ✓ vw_component_details view';
PRINT '============================================================';