-- ============================================================
-- Remove All Integration Stored Procedures
-- Description: Clean removal of all stored procedures for simple implementation
-- ============================================================

USE MSIFactory;
GO

PRINT '============================================================';
PRINT 'Removing Integration Stored Procedures...';
PRINT '============================================================';

-- Remove sp_GetIntegrationConfig
IF EXISTS (SELECT * FROM sys.objects WHERE type = 'P' AND name = 'sp_GetIntegrationConfig')
BEGIN
    DROP PROCEDURE sp_GetIntegrationConfig;
    PRINT '  ✓ sp_GetIntegrationConfig removed';
END
ELSE
BEGIN
    PRINT '  - sp_GetIntegrationConfig not found';
END

-- Remove sp_UpdateIntegrationUsage
IF EXISTS (SELECT * FROM sys.objects WHERE type = 'P' AND name = 'sp_UpdateIntegrationUsage')
BEGIN
    DROP PROCEDURE sp_UpdateIntegrationUsage;
    PRINT '  ✓ sp_UpdateIntegrationUsage removed';
END
ELSE
BEGIN
    PRINT '  - sp_UpdateIntegrationUsage not found';
END

-- Remove sp_LogIntegrationAudit
IF EXISTS (SELECT * FROM sys.objects WHERE type = 'P' AND name = 'sp_LogIntegrationAudit')
BEGIN
    DROP PROCEDURE sp_LogIntegrationAudit;
    PRINT '  ✓ sp_LogIntegrationAudit removed';
END
ELSE
BEGIN
    PRINT '  - sp_LogIntegrationAudit not found';
END

PRINT '';
PRINT '============================================================';
PRINT 'Stored Procedures Cleanup Complete!';
PRINT '============================================================';
PRINT '';
PRINT 'Result: Simple direct SQL queries only';
PRINT '  ✓ No stored procedure dependencies';
PRINT '  ✓ Easier maintenance and debugging';
PRINT '  ✓ Faster development iterations';
PRINT '';
PRINT '============================================================';