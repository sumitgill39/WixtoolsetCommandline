-- ============================================================
-- Add Versioning and Path Pattern Fields to Components
-- For managing component-specific JFrog patterns and version strategies
-- Author: Claude Code Assistant
-- Date: 2025-09-30
-- ============================================================

USE MSIFactory;
GO

SET NOCOUNT ON;

PRINT '============================================================';
PRINT 'Adding Component Versioning and Path Pattern Fields';
PRINT '============================================================';
PRINT '';

-- Add JFrog path pattern to components table
IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('components') AND name = 'jfrog_path_pattern')
BEGIN
    PRINT '  Adding jfrog_path_pattern column...';
    ALTER TABLE components ADD jfrog_path_pattern VARCHAR(500)
        DEFAULT '{branch}/Build{date}.{buildNumber}/{componentName}.zip';
    PRINT '  ✓ jfrog_path_pattern column added.';
END
ELSE
    PRINT '  ✓ jfrog_path_pattern column already exists.';

-- Add version strategy to components table
IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('components') AND name = 'version_strategy')
BEGIN
    PRINT '  Adding version_strategy column...';
    ALTER TABLE components ADD version_strategy VARCHAR(50)
        DEFAULT 'auto_increment'
        CHECK (version_strategy IN ('auto_increment', 'semantic', 'manual', 'date_based'));
    PRINT '  ✓ version_strategy column added.';
END
ELSE
    PRINT '  ✓ version_strategy column already exists.';

-- Add version format to components table (for semantic versioning)
IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('components') AND name = 'version_format')
BEGIN
    PRINT '  Adding version_format column...';
    ALTER TABLE components ADD version_format VARCHAR(50)
        DEFAULT '{major}.{minor}.{patch}.{build}';
    PRINT '  ✓ version_format column added.';
END
ELSE
    PRINT '  ✓ version_format column already exists.';

-- Add current version fields to components table
IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('components') AND name = 'current_major_version')
BEGIN
    PRINT '  Adding version number columns...';
    ALTER TABLE components ADD current_major_version INT DEFAULT 1;
    ALTER TABLE components ADD current_minor_version INT DEFAULT 0;
    ALTER TABLE components ADD current_patch_version INT DEFAULT 0;
    ALTER TABLE components ADD current_build_number INT DEFAULT 0;
    PRINT '  ✓ Version number columns added.';
END
ELSE
    PRINT '  ✓ Version number columns already exist.';

-- Add date format preference for the path pattern
IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('components') AND name = 'date_format')
BEGIN
    PRINT '  Adding date_format column...';
    ALTER TABLE components ADD date_format VARCHAR(20)
        DEFAULT 'yyyyMMdd'
        CHECK (date_format IN ('yyyyMMdd', 'yyyy-MM-dd', 'yyyy.MM.dd', 'yyMMdd'));
    PRINT '  ✓ date_format column added.';
END
ELSE
    PRINT '  ✓ date_format column already exists.';

-- Add build number format to components table
IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('components') AND name = 'build_number_format')
BEGIN
    PRINT '  Adding build_number_format column...';
    ALTER TABLE components ADD build_number_format VARCHAR(50)
        DEFAULT '{date}.{sequence}';
    PRINT '  ✓ build_number_format column added.';
END
ELSE
    PRINT '  ✓ build_number_format column already exists.';

-- Add auto version increment flag
IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('components') AND name = 'auto_version_increment')
BEGIN
    PRINT '  Adding auto_version_increment column...';
    ALTER TABLE components ADD auto_version_increment BIT DEFAULT 1;
    PRINT '  ✓ auto_version_increment column added.';
END
ELSE
    PRINT '  ✓ auto_version_increment column already exists.';

-- Update existing component_branches table to add version fields per branch
IF EXISTS (SELECT * FROM sysobjects WHERE name='component_branches' AND xtype='U')
BEGIN
    -- Add major version to component_branches
    IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('component_branches') AND name = 'major_version')
    BEGIN
        PRINT '  Adding version fields to component_branches...';
        ALTER TABLE component_branches ADD major_version INT DEFAULT 1;
        ALTER TABLE component_branches ADD minor_version INT DEFAULT 0;
        ALTER TABLE component_branches ADD patch_version INT DEFAULT 0;
        ALTER TABLE component_branches ADD build_number INT DEFAULT 0;
        PRINT '  ✓ Version fields added to component_branches.';
    END
    ELSE
        PRINT '  ✓ Version fields already exist in component_branches.';

    -- Add path pattern override for specific branches
    IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('component_branches') AND name = 'path_pattern_override')
    BEGIN
        PRINT '  Adding path_pattern_override to component_branches...';
        ALTER TABLE component_branches ADD path_pattern_override VARCHAR(500);
        PRINT '  ✓ path_pattern_override added to component_branches.';
    END
    ELSE
        PRINT '  ✓ path_pattern_override already exists in component_branches.';
END

PRINT '';
PRINT '============================================================';
PRINT '  COMPONENT VERSIONING FIELDS ADDED SUCCESSFULLY';
PRINT '============================================================';
PRINT '';
PRINT 'New Fields Added to Components Table:';
PRINT '  ✓ jfrog_path_pattern - Component-specific artifact path pattern';
PRINT '  ✓ version_strategy - How versions are managed (auto/semantic/manual/date)';
PRINT '  ✓ version_format - Version display format';
PRINT '  ✓ current_[major/minor/patch/build] - Current version numbers';
PRINT '  ✓ date_format - Date format for build paths';
PRINT '  ✓ build_number_format - Build number pattern';
PRINT '  ✓ auto_version_increment - Auto-increment flag';
PRINT '';
PRINT 'Version Strategies Available:';
PRINT '  • auto_increment - Automatically increment build number';
PRINT '  • semantic - Use semantic versioning (major.minor.patch)';
PRINT '  • manual - Manual version management';
PRINT '  • date_based - Version based on date';
PRINT '';
PRINT 'Path Pattern Variables:';
PRINT '  • {branch} - Git branch name';
PRINT '  • {date} - Build date';
PRINT '  • {buildNumber} - Build number/sequence';
PRINT '  • {componentName} - Component name';
PRINT '  • {version} - Full version string';
PRINT '';
PRINT '============================================================';
GO

SET NOCOUNT OFF;