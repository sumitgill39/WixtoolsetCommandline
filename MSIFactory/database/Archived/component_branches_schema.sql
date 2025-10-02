-- ============================================================
-- COMPONENT BRANCHES AND BUILDS SCHEMA
-- Branch-based component versioning with JFrog integration
-- Author: Claude Code Assistant
-- Date: 2025-09-30
-- ============================================================

USE MSIFactory;
GO

SET NOCOUNT ON;

PRINT '============================================================';
PRINT 'MSI Factory - Component Branches & Builds Schema';
PRINT '============================================================';

-- Component Branches Table
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='component_branches' AND xtype='U')
BEGIN
    PRINT '  Creating component_branches table...';
    CREATE TABLE component_branches (
        branch_id INT PRIMARY KEY IDENTITY(1,1),
        component_id INT NOT NULL,
        branch_name VARCHAR(100) NOT NULL,
        current_version INT DEFAULT 1,
        last_build_date DATETIME,
        last_build_number VARCHAR(50),
        branch_status VARCHAR(20) DEFAULT 'active' CHECK (branch_status IN ('active', 'inactive', 'archived')),
        auto_build BIT DEFAULT 0,
        description TEXT,
        is_active BIT DEFAULT 1,
        created_date DATETIME DEFAULT GETDATE(),
        created_by VARCHAR(100),
        updated_date DATETIME,
        updated_by VARCHAR(100),

        FOREIGN KEY (component_id) REFERENCES components(component_id) ON DELETE CASCADE,
        UNIQUE(component_id, branch_name)
    );
    PRINT '  ✓ Component branches table created successfully.';
END
ELSE
    PRINT '  ✓ Component branches table already exists.';
GO

-- Component Builds Table
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='component_builds' AND xtype='U')
BEGIN
    PRINT '  Creating component_builds table...';
    CREATE TABLE component_builds (
        build_id INT PRIMARY KEY IDENTITY(1,1),
        branch_id INT NOT NULL,
        build_number VARCHAR(50) NOT NULL,
        version_number INT NOT NULL,
        build_date DATETIME DEFAULT GETDATE(),
        build_status VARCHAR(20) DEFAULT 'pending' CHECK (build_status IN ('pending', 'building', 'success', 'failed', 'cancelled')),

        -- JFrog Integration
        jfrog_path VARCHAR(500),
        jfrog_download_url VARCHAR(1000),
        artifact_size BIGINT,
        artifact_checksum VARCHAR(100),

        -- Build Information
        git_commit_hash VARCHAR(40),
        git_commit_message TEXT,
        build_duration_seconds INT,
        build_log_path VARCHAR(500),

        -- CI/CD Information
        ci_job_id VARCHAR(100),
        ci_pipeline_id VARCHAR(100),
        ci_system VARCHAR(50), -- Jenkins, Azure DevOps, GitHub Actions, etc.

        -- Quality Gates
        tests_passed INT DEFAULT 0,
        tests_failed INT DEFAULT 0,
        code_coverage_percent DECIMAL(5,2),
        quality_gate_status VARCHAR(20) CHECK (quality_gate_status IN ('passed', 'failed', 'warning', 'not_run')),

        -- Deployment Tracking
        is_deployed BIT DEFAULT 0,
        deployed_environments TEXT, -- JSON array of environments where this build is deployed

        -- Metadata
        created_by VARCHAR(100),
        is_active BIT DEFAULT 1,

        FOREIGN KEY (branch_id) REFERENCES component_branches(branch_id) ON DELETE CASCADE,
        UNIQUE(branch_id, build_number)
    );
    PRINT '  ✓ Component builds table created successfully.';
END
ELSE
    PRINT '  ✓ Component builds table already exists.';
GO

-- Component Build Artifacts Table (for tracking multiple artifacts per build)
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='component_build_artifacts' AND xtype='U')
BEGIN
    PRINT '  Creating component_build_artifacts table...';
    CREATE TABLE component_build_artifacts (
        artifact_id INT PRIMARY KEY IDENTITY(1,1),
        build_id INT NOT NULL,
        artifact_name VARCHAR(255) NOT NULL,
        artifact_type VARCHAR(50) DEFAULT 'zip' CHECK (artifact_type IN ('zip', 'msi', 'exe', 'dll', 'jar', 'war', 'tar', 'other')),
        artifact_path VARCHAR(500),
        download_url VARCHAR(1000),
        file_size BIGINT,
        checksum VARCHAR(100),
        checksum_type VARCHAR(20) DEFAULT 'SHA256',
        is_primary BIT DEFAULT 0, -- Main artifact for the build
        created_date DATETIME DEFAULT GETDATE(),

        FOREIGN KEY (build_id) REFERENCES component_builds(build_id) ON DELETE CASCADE
    );
    PRINT '  ✓ Component build artifacts table created successfully.';
END
ELSE
    PRINT '  ✓ Component build artifacts table already exists.';
GO

-- MSI Generation Jobs Table (Enhanced for multi-branch support)
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='msi_generation_jobs' AND xtype='U')
BEGIN
    PRINT '  Creating msi_generation_jobs table...';
    CREATE TABLE msi_generation_jobs (
        job_id INT PRIMARY KEY IDENTITY(1,1),
        project_id INT NOT NULL,
        build_id INT, -- Reference to specific build
        branch_id INT, -- Reference to branch (for latest build)
        job_name VARCHAR(255) NOT NULL,
        job_status VARCHAR(20) DEFAULT 'pending' CHECK (job_status IN ('pending', 'running', 'completed', 'failed', 'cancelled')),

        -- Build Selection
        use_specific_build BIT DEFAULT 0, -- If false, use latest build from branch
        selected_builds TEXT, -- JSON array of selected build IDs for components

        -- MSI Configuration
        msi_version VARCHAR(50),
        output_filename VARCHAR(255),
        output_path VARCHAR(500),

        -- Progress Tracking
        total_components INT DEFAULT 0,
        completed_components INT DEFAULT 0,
        progress_percent DECIMAL(5,2) DEFAULT 0,

        -- Timing
        started_at DATETIME,
        completed_at DATETIME,
        duration_seconds INT,

        -- Results
        success_message TEXT,
        error_message TEXT,
        warnings TEXT,

        -- Metadata
        created_by VARCHAR(100),
        created_date DATETIME DEFAULT GETDATE(),

        FOREIGN KEY (project_id) REFERENCES projects(project_id) ON DELETE NO ACTION,
        FOREIGN KEY (build_id) REFERENCES component_builds(build_id) ON DELETE SET NULL,
        FOREIGN KEY (branch_id) REFERENCES component_branches(branch_id) ON DELETE SET NULL
    );
    PRINT '  ✓ MSI generation jobs table created successfully.';
END
ELSE
    PRINT '  ✓ MSI generation jobs table already exists.';
GO

-- Create indexes for performance
PRINT '  Creating indexes for optimal performance...';

-- Component branches indexes
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_component_branches_component_id')
    CREATE INDEX IX_component_branches_component_id ON component_branches(component_id);

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_component_branches_branch_name')
    CREATE INDEX IX_component_branches_branch_name ON component_branches(branch_name);

-- Component builds indexes
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_component_builds_branch_id')
    CREATE INDEX IX_component_builds_branch_id ON component_builds(branch_id);

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_component_builds_build_date')
    CREATE INDEX IX_component_builds_build_date ON component_builds(build_date DESC);

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_component_builds_status')
    CREATE INDEX IX_component_builds_status ON component_builds(build_status);

-- Artifacts indexes
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_component_build_artifacts_build_id')
    CREATE INDEX IX_component_build_artifacts_build_id ON component_build_artifacts(build_id);

PRINT '  ✓ Indexes created successfully.';

-- Insert sample data for testing (if component exists)
IF EXISTS (SELECT 1 FROM components WHERE component_name = 'WebPortal')
BEGIN
    DECLARE @component_id INT;
    SELECT @component_id = component_id FROM components WHERE component_name = 'WebPortal';

    IF NOT EXISTS (SELECT 1 FROM component_branches WHERE component_id = @component_id AND branch_name = 'main')
    BEGIN
        PRINT '  Adding sample branch data...';

        INSERT INTO component_branches (component_id, branch_name, current_version, description, created_by)
        VALUES
            (@component_id, 'main', 5, 'Main production branch', 'system'),
            (@component_id, 'develop', 12, 'Development branch', 'system'),
            (@component_id, 'feature/auth', 3, 'Authentication feature branch', 'system');

        DECLARE @main_branch_id INT, @dev_branch_id INT, @feature_branch_id INT;
        SELECT @main_branch_id = branch_id FROM component_branches WHERE component_id = @component_id AND branch_name = 'main';
        SELECT @dev_branch_id = branch_id FROM component_branches WHERE component_id = @component_id AND branch_name = 'develop';
        SELECT @feature_branch_id = branch_id FROM component_branches WHERE component_id = @component_id AND branch_name = 'feature/auth';

        INSERT INTO component_builds (branch_id, build_number, version_number, build_status, jfrog_path, artifact_size, created_by)
        VALUES
            (@main_branch_id, 'Build20250930.001', 5, 'success', 'main/Build20250930.001/WebPortal.zip', 15728640, 'system'),
            (@main_branch_id, 'Build20250929.003', 4, 'success', 'main/Build20250929.003/WebPortal.zip', 15234560, 'system'),
            (@dev_branch_id, 'Build20250930.005', 12, 'success', 'develop/Build20250930.005/WebPortal.zip', 16234560, 'system'),
            (@dev_branch_id, 'Build20250930.004', 11, 'success', 'develop/Build20250930.004/WebPortal.zip', 16123456, 'system'),
            (@feature_branch_id, 'Build20250929.001', 3, 'success', 'feature-auth/Build20250929.001/WebPortal.zip', 15987654, 'system');

        PRINT '  ✓ Sample data inserted successfully.';
    END
    ELSE
        PRINT '  ✓ Sample data already exists.';
END

PRINT '';
PRINT '============================================================';
PRINT '  COMPONENT BRANCHES & BUILDS SCHEMA COMPLETE';
PRINT '============================================================';
PRINT '';
PRINT 'Tables Created:';
PRINT '  ✓ component_branches - Branch management per component';
PRINT '  ✓ component_builds - Build tracking with JFrog integration';
PRINT '  ✓ component_build_artifacts - Multiple artifacts per build';
PRINT '  ✓ msi_generation_jobs - Enhanced MSI generation tracking';
PRINT '';
PRINT 'Features:';
PRINT '  ✓ Multi-branch component versioning';
PRINT '  ✓ JFrog Artifactory integration';
PRINT '  ✓ Build status and quality gate tracking';
PRINT '  ✓ CI/CD pipeline integration';
PRINT '  ✓ Deployment environment tracking';
PRINT '  ✓ Performance optimized indexes';
PRINT '';
PRINT 'Path Pattern Support:';
PRINT '  ✓ {branch}/Build{date}.{buildNumber}/{componentName}.zip';
PRINT '  ✓ Configurable date formats';
PRINT '  ✓ Version sequencing per branch';
PRINT '';
PRINT '============================================================';
GO

SET NOCOUNT OFF;