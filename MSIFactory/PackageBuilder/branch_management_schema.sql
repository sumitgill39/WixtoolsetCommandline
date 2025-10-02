-- ============================================================
-- Branch Management Schema Extension for MSI Factory
-- Version: 1.0
-- Description: Creates component_branches table for advanced branch management
-- Author: MSI Factory Team
-- ============================================================

USE MSIFactory;
GO

SET NOCOUNT ON;

PRINT '============================================================';
PRINT 'Creating Component Branches Management Schema...';
PRINT '============================================================';

-- ============================================================
-- CREATE COMPONENT BRANCHES TABLE
-- ============================================================

IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='component_branches' AND xtype='U')
BEGIN
    PRINT 'Creating component_branches table...';

    CREATE TABLE component_branches (
        branch_id INT PRIMARY KEY IDENTITY(1,1),
        component_id INT NOT NULL,
        branch_name VARCHAR(100) NOT NULL,

        -- Path configuration
        path_pattern_override VARCHAR(500) DEFAULT '{ComponentName}/{branch}/Build{date}.{buildNumber}/{componentName}.zip',

        -- Version management
        major_version INT DEFAULT 1,
        minor_version INT DEFAULT 0,
        patch_version INT DEFAULT 0,
        build_number INT DEFAULT 0,
        auto_increment VARCHAR(20) DEFAULT 'build' CHECK (auto_increment IN ('major', 'minor', 'build', 'revision')),

        -- Branch configuration
        branch_status VARCHAR(20) DEFAULT 'active' CHECK (branch_status IN ('active', 'inactive', 'archived')),
        description VARCHAR(500),

        -- Metadata
        created_date DATETIME DEFAULT GETDATE(),
        created_by VARCHAR(50) NOT NULL,
        updated_date DATETIME DEFAULT GETDATE(),
        updated_by VARCHAR(50),
        is_active BIT DEFAULT 1 NOT NULL,

        -- Foreign key and constraints
        FOREIGN KEY (component_id) REFERENCES components(component_id) ON DELETE CASCADE,
        CONSTRAINT UK_component_branches_name UNIQUE (component_id, branch_name),
        CONSTRAINT CK_branch_version_numbers CHECK (
            major_version >= 0 AND minor_version >= 0 AND
            patch_version >= 0 AND build_number >= 0
        ),
        CONSTRAINT CK_branch_name_not_empty CHECK (LEN(TRIM(branch_name)) > 0)
    );

    PRINT 'Component branches table created successfully.';
END
ELSE
BEGIN
    PRINT 'Component branches table already exists.';
END
GO

-- ============================================================
-- CREATE INDEXES FOR PERFORMANCE
-- ============================================================

PRINT 'Creating indexes for component_branches table...';

-- Index on component_id for fast lookups by component
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_component_branches_component')
    CREATE INDEX idx_component_branches_component ON component_branches(component_id);

-- Index on branch_name for fast searches
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_component_branches_name')
    CREATE INDEX idx_component_branches_name ON component_branches(branch_name);

-- Index on branch_status for filtering
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_component_branches_status')
    CREATE INDEX idx_component_branches_status ON component_branches(branch_status);

-- Index on is_active for soft delete filtering
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_component_branches_active')
    CREATE INDEX idx_component_branches_active ON component_branches(is_active);

-- Composite index for common queries
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_component_branches_composite')
    CREATE INDEX idx_component_branches_composite ON component_branches(component_id, is_active, branch_status);

PRINT 'Indexes created successfully.';
GO

-- ============================================================
-- CREATE STORED PROCEDURES
-- ============================================================

PRINT 'Creating stored procedures for branch management...';

-- Procedure to get next version for a branch
IF EXISTS (SELECT * FROM sys.objects WHERE type = 'P' AND name = 'sp_GetNextBranchVersion')
    DROP PROCEDURE sp_GetNextBranchVersion;
GO

CREATE PROCEDURE sp_GetNextBranchVersion
    @branch_id INT,
    @auto_increment_type VARCHAR(20),
    @next_version VARCHAR(50) OUTPUT
AS
BEGIN
    SET NOCOUNT ON;

    DECLARE @major INT, @minor INT, @patch INT, @build INT;

    -- Get current version
    SELECT
        @major = major_version,
        @minor = minor_version,
        @patch = patch_version,
        @build = build_number
    FROM component_branches
    WHERE branch_id = @branch_id;

    -- Increment based on type
    IF @auto_increment_type = 'major'
    BEGIN
        SET @major = @major + 1;
        SET @minor = 0;
        SET @patch = 0;
        SET @build = 0;
    END
    ELSE IF @auto_increment_type = 'minor'
    BEGIN
        SET @minor = @minor + 1;
        SET @patch = 0;
        SET @build = 0;
    END
    ELSE IF @auto_increment_type = 'build'
    BEGIN
        SET @patch = @patch + 1;
        SET @build = 0;
    END
    ELSE IF @auto_increment_type = 'revision'
    BEGIN
        SET @build = @build + 1;
    END

    -- Update the branch with new version
    UPDATE component_branches
    SET major_version = @major,
        minor_version = @minor,
        patch_version = @patch,
        build_number = @build,
        updated_date = GETDATE()
    WHERE branch_id = @branch_id;

    -- Return formatted version
    SET @next_version = CAST(@major AS VARCHAR) + '.' +
                       CAST(@minor AS VARCHAR) + '.' +
                       CAST(@patch AS VARCHAR) + '.' +
                       CAST(@build AS VARCHAR);
END
GO

-- Procedure to archive old branches
IF EXISTS (SELECT * FROM sys.objects WHERE type = 'P' AND name = 'sp_ArchiveOldBranches')
    DROP PROCEDURE sp_ArchiveOldBranches;
GO

CREATE PROCEDURE sp_ArchiveOldBranches
    @days_old INT = 90,
    @archived_by VARCHAR(50) = 'system'
AS
BEGIN
    SET NOCOUNT ON;

    DECLARE @archived_count INT = 0;

    -- Archive branches that haven't been updated in specified days
    UPDATE component_branches
    SET branch_status = 'archived',
        updated_by = @archived_by,
        updated_date = GETDATE()
    WHERE updated_date < DATEADD(DAY, -@days_old, GETDATE())
    AND branch_status = 'inactive'
    AND is_active = 1;

    SET @archived_count = @@ROWCOUNT;

    SELECT @archived_count as archived_branches_count;
END
GO

-- Procedure to get branch statistics
IF EXISTS (SELECT * FROM sys.objects WHERE type = 'P' AND name = 'sp_GetBranchStatistics')
    DROP PROCEDURE sp_GetBranchStatistics;
GO

CREATE PROCEDURE sp_GetBranchStatistics
AS
BEGIN
    SET NOCOUNT ON;

    SELECT
        'Total Branches' as statistic,
        COUNT(*) as count
    FROM component_branches
    WHERE is_active = 1

    UNION ALL

    SELECT
        'Active Branches',
        COUNT(*)
    FROM component_branches
    WHERE is_active = 1 AND branch_status = 'active'

    UNION ALL

    SELECT
        'Inactive Branches',
        COUNT(*)
    FROM component_branches
    WHERE is_active = 1 AND branch_status = 'inactive'

    UNION ALL

    SELECT
        'Archived Branches',
        COUNT(*)
    FROM component_branches
    WHERE is_active = 1 AND branch_status = 'archived'

    UNION ALL

    SELECT
        'Components with Branches',
        COUNT(DISTINCT component_id)
    FROM component_branches
    WHERE is_active = 1;
END
GO

PRINT 'Stored procedures created successfully.';
GO

-- ============================================================
-- CREATE VIEWS
-- ============================================================

PRINT 'Creating views for branch management...';

-- View for detailed branch information
IF EXISTS (SELECT * FROM sys.views WHERE name = 'vw_branch_details')
    DROP VIEW vw_branch_details;
GO

CREATE VIEW vw_branch_details
AS
SELECT
    cb.branch_id,
    cb.component_id,
    cb.branch_name,
    cb.path_pattern_override,
    cb.major_version,
    cb.minor_version,
    cb.patch_version,
    cb.build_number,
    CAST(cb.major_version AS VARCHAR) + '.' +
    CAST(cb.minor_version AS VARCHAR) + '.' +
    CAST(cb.patch_version AS VARCHAR) + '.' +
    CAST(cb.build_number AS VARCHAR) as version_string,
    cb.auto_increment,
    cb.branch_status,
    cb.description,
    cb.created_date,
    cb.created_by,
    cb.updated_date,
    cb.updated_by,
    cb.is_active,

    -- Component information
    c.component_name,
    c.component_type,
    c.framework,
    c.is_enabled as component_enabled,

    -- Project information
    p.project_id,
    p.project_name,
    p.project_key,
    p.project_type,
    p.owner_team,
    p.status as project_status,

    -- Derived fields for display
    '[' + cb.branch_name + '] - {baseURL}/' + c.component_name + '/' + cb.branch_name + '/Build{date}.{buildNumber}/' + c.component_name + '.zip - Version[' +
    CAST(cb.major_version AS VARCHAR) + ',' +
    CAST(cb.minor_version AS VARCHAR) + ',' +
    CAST(cb.patch_version AS VARCHAR) + ',' +
    CAST(cb.build_number AS VARCHAR) + '] - Auto Increment[' + cb.auto_increment + ']' as display_format

FROM component_branches cb
INNER JOIN components c ON cb.component_id = c.component_id
INNER JOIN projects p ON c.project_id = p.project_id
WHERE cb.is_active = 1 AND c.is_enabled = 1 AND p.is_active = 1;
GO

PRINT 'Views created successfully.';
GO

-- ============================================================
-- INSERT SAMPLE DATA
-- ============================================================

PRINT 'Inserting sample branch data...';

-- Insert sample branches for existing components
IF EXISTS (SELECT * FROM components WHERE component_name = 'Web Frontend')
BEGIN
    DECLARE @frontend_component_id INT = (SELECT component_id FROM components WHERE component_name = 'Web Frontend');

    IF NOT EXISTS (SELECT * FROM component_branches WHERE component_id = @frontend_component_id AND branch_name = 'main')
    BEGIN
        INSERT INTO component_branches (component_id, branch_name, description, created_by, updated_by)
        VALUES (@frontend_component_id, 'main', 'Main production branch', 'system', 'system');

        INSERT INTO component_branches (component_id, branch_name, major_version, minor_version, patch_version, build_number,
                                      auto_increment, branch_status, description, created_by, updated_by)
        VALUES (@frontend_component_id, 'develop', 1, 1, 0, 0, 'build', 'active', 'Development branch', 'system', 'system');

        PRINT 'Sample branches created for Web Frontend component.';
    END
END

IF EXISTS (SELECT * FROM components WHERE component_name = 'API Backend')
BEGIN
    DECLARE @api_component_id INT = (SELECT component_id FROM components WHERE component_name = 'API Backend');

    IF NOT EXISTS (SELECT * FROM component_branches WHERE component_id = @api_component_id AND branch_name = 'main')
    BEGIN
        INSERT INTO component_branches (component_id, branch_name, description, created_by, updated_by)
        VALUES (@api_component_id, 'main', 'Main production branch', 'system', 'system');

        INSERT INTO component_branches (component_id, branch_name, major_version, minor_version, patch_version, build_number,
                                      auto_increment, branch_status, description, created_by, updated_by)
        VALUES (@api_component_id, 'develop', 1, 0, 5, 12, 'revision', 'active', 'Development branch', 'system', 'system');

        PRINT 'Sample branches created for API Backend component.';
    END
END

-- ============================================================
-- UPDATE STATISTICS
-- ============================================================

PRINT 'Updating statistics...';

UPDATE STATISTICS component_branches;

-- ============================================================
-- FINAL VALIDATION
-- ============================================================

PRINT 'Running final validation...';

-- Check branch statistics
EXEC sp_GetBranchStatistics;

PRINT '';
PRINT '============================================================';
PRINT 'Branch Management Schema Installation Complete!';
PRINT '============================================================';
PRINT '';
PRINT 'Features Added:';
PRINT '  ✓ Component Branches table with version management';
PRINT '  ✓ Branch status tracking (active, inactive, archived)';
PRINT '  ✓ Path pattern override for flexible artifact paths';
PRINT '  ✓ Auto-increment version management';
PRINT '  ✓ Soft delete support';
PRINT '  ✓ Performance optimized indexes';
PRINT '  ✓ Stored procedures for version management';
PRINT '  ✓ Views for easy data access';
PRINT '  ✓ Sample data for testing';
PRINT '';
PRINT 'Database ready for Branch Management functionality!';
PRINT '============================================================';

SET NOCOUNT OFF;