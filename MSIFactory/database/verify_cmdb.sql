-- ============================================================
-- Verify CMDB Installation
-- ============================================================

USE MSIFactory;
GO

PRINT '============================================================';
PRINT 'CMDB Installation Verification';
PRINT '============================================================';
PRINT '';

-- Check CMDB tables
PRINT 'Checking CMDB Tables...';
IF EXISTS (SELECT * FROM sysobjects WHERE name='cmdb_servers' AND xtype='U')
    PRINT '  ✓ cmdb_servers table exists';
ELSE
    PRINT '  ✗ cmdb_servers table MISSING';

IF EXISTS (SELECT * FROM sysobjects WHERE name='cmdb_server_groups' AND xtype='U')
    PRINT '  ✓ cmdb_server_groups table exists';
ELSE
    PRINT '  ✗ cmdb_server_groups table MISSING';

IF EXISTS (SELECT * FROM sysobjects WHERE name='cmdb_server_group_members' AND xtype='U')
    PRINT '  ✓ cmdb_server_group_members table exists';
ELSE
    PRINT '  ✗ cmdb_server_group_members table MISSING';

IF EXISTS (SELECT * FROM sysobjects WHERE name='project_servers' AND xtype='U')
    PRINT '  ✓ project_servers table exists';
ELSE
    PRINT '  ✗ project_servers table MISSING';

IF EXISTS (SELECT * FROM sysobjects WHERE name='component_servers' AND xtype='U')
    PRINT '  ✓ component_servers table exists';
ELSE
    PRINT '  ✗ component_servers table MISSING';

IF EXISTS (SELECT * FROM sysobjects WHERE name='cmdb_server_changes' AND xtype='U')
    PRINT '  ✓ cmdb_server_changes table exists';
ELSE
    PRINT '  ✗ cmdb_server_changes table MISSING';

PRINT '';

-- Check sample data
PRINT 'Checking Sample Data...';
DECLARE @server_count INT;
SELECT @server_count = COUNT(*) FROM cmdb_servers;
PRINT '  Server count: ' + CAST(@server_count AS VARCHAR(10));

DECLARE @group_count INT;
SELECT @group_count = COUNT(*) FROM cmdb_server_groups;
PRINT '  Server group count: ' + CAST(@group_count AS VARCHAR(10));

PRINT '';

-- Check views
PRINT 'Checking Views...';
IF EXISTS (SELECT * FROM sys.views WHERE name = 'vw_cmdb_server_inventory')
    PRINT '  ✓ vw_cmdb_server_inventory view exists';
ELSE
    PRINT '  ✗ vw_cmdb_server_inventory view MISSING';

IF EXISTS (SELECT * FROM sys.views WHERE name = 'vw_project_server_assignments')
    PRINT '  ✓ vw_project_server_assignments view exists';
ELSE
    PRINT '  ✗ vw_project_server_assignments view MISSING';

PRINT '';

-- Check stored procedures
PRINT 'Checking Stored Procedures...';
IF EXISTS (SELECT * FROM sys.objects WHERE type = 'P' AND name = 'sp_CMDB_DiscoverServer')
    PRINT '  ✓ sp_CMDB_DiscoverServer exists';
ELSE
    PRINT '  ✗ sp_CMDB_DiscoverServer MISSING';

IF EXISTS (SELECT * FROM sys.objects WHERE type = 'P' AND name = 'sp_AssignServerToProject')
    PRINT '  ✓ sp_AssignServerToProject exists';
ELSE
    PRINT '  ✗ sp_AssignServerToProject MISSING';

PRINT '';

-- Test a view
PRINT 'Testing vw_cmdb_server_inventory view...';
BEGIN TRY
    SELECT TOP 1 * FROM vw_cmdb_server_inventory;
    PRINT '  ✓ View is working';
END TRY
BEGIN CATCH
    PRINT '  ✗ View error: ' + ERROR_MESSAGE();
END CATCH

PRINT '';
PRINT '============================================================';
PRINT 'CMDB Verification Complete';
PRINT '============================================================';

-- Show sample servers
PRINT '';
PRINT 'Sample Servers in CMDB:';
SELECT server_name, infra_type, ip_address, region, status
FROM cmdb_servers;