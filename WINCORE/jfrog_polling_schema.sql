-- ============================================================
-- JFrog Multi-threaded Polling System Database Schema
-- Version: 1.0
-- Created: 2025-10-02
-- Description: Database schema for multi-threaded JFrog artifact polling,
--              download, and extraction system (10K+ threads support)
-- Note: This schema extends the existing MSIFactory database

--============================================================
--JFrog Polling System Schema Created Successfully!
--============================================================
--Tables Created:
--  - jfrog_polling_threads
--  - jfrog_build_tracking
--  - jfrog_build_history
--  - jfrog_polling_log
--  - jfrog_system_config
 
--Stored Procedures Created:
--  - sp_GetActivePollingConfig
--  - sp_UpdateBuildTracking
--  - sp_CleanupOldBuilds
--  - sp_LogPollingActivity
--============================================================

--Completion time: 2025-10-02T19:56:15.4778411+05:

-- ============================================================

USE MSIFactory;
GO

-- ============================================================
-- Table: jfrog_polling_threads
-- Description: Tracks active polling threads and their status
-- ============================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='jfrog_polling_threads' AND xtype='U')
BEGIN
    CREATE TABLE jfrog_polling_threads (
        thread_id INT IDENTITY(1,1) PRIMARY KEY,
        component_id INT NOT NULL,
        branch_id INT NOT NULL,
        thread_status VARCHAR(20) DEFAULT 'idle',
        current_build_date VARCHAR(8),
        current_build_number INT,
        last_poll_time DATETIME,
        next_poll_time DATETIME,
        polling_frequency_seconds INT DEFAULT 300,
        consecutive_failures INT DEFAULT 0,
        last_error_message TEXT,
        thread_start_time DATETIME DEFAULT GETDATE(),
        is_active BIT DEFAULT 1,
        CONSTRAINT FK_polling_threads_component FOREIGN KEY (component_id) REFERENCES components(component_id) ON DELETE CASCADE,
        CONSTRAINT FK_polling_threads_branch FOREIGN KEY (branch_id) REFERENCES component_branches(branch_id) ON DELETE NO ACTION,
        CONSTRAINT CHK_thread_status CHECK (thread_status IN ('idle', 'polling', 'downloading', 'extracting', 'error', 'stopped'))
    );

    CREATE INDEX IX_polling_threads_component_branch ON jfrog_polling_threads(component_id, branch_id);
    CREATE INDEX IX_polling_threads_status ON jfrog_polling_threads(thread_status);
    CREATE INDEX IX_polling_threads_next_poll ON jfrog_polling_threads(next_poll_time);
END
GO

-- ============================================================
-- Table: jfrog_build_tracking
-- Description: Tracks latest build numbers for each component/branch
-- ============================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='jfrog_build_tracking' AND xtype='U')
BEGIN
    CREATE TABLE jfrog_build_tracking (
        tracking_id INT IDENTITY(1,1) PRIMARY KEY,
        component_id INT NOT NULL,
        branch_id INT NOT NULL,
        latest_build_date VARCHAR(8) NOT NULL,
        latest_build_number INT NOT NULL,
        build_url VARCHAR(1000),
        last_checked_time DATETIME DEFAULT GETDATE(),
        last_downloaded_time DATETIME,
        download_status VARCHAR(20) DEFAULT 'pending',
        extraction_status VARCHAR(20) DEFAULT 'pending',
        download_path VARCHAR(500),
        extraction_path VARCHAR(500),
        file_size BIGINT,
        checksum VARCHAR(100),
        error_message TEXT,
        created_date DATETIME DEFAULT GETDATE(),
        updated_date DATETIME DEFAULT GETDATE(),
        CONSTRAINT FK_build_tracking_component FOREIGN KEY (component_id) REFERENCES components(component_id) ON DELETE CASCADE,
        CONSTRAINT FK_build_tracking_branch FOREIGN KEY (branch_id) REFERENCES component_branches(branch_id) ON DELETE NO ACTION,
        CONSTRAINT UQ_component_branch_tracking UNIQUE (component_id, branch_id),
        CONSTRAINT CHK_download_status CHECK (download_status IN ('pending', 'downloading', 'completed', 'failed')),
        CONSTRAINT CHK_extraction_status CHECK (extraction_status IN ('pending', 'extracting', 'completed', 'failed'))
    );

    CREATE INDEX IX_build_tracking_component_branch ON jfrog_build_tracking(component_id, branch_id);
    CREATE INDEX IX_build_tracking_status ON jfrog_build_tracking(download_status, extraction_status);
END
GO

-- ============================================================
-- Table: jfrog_build_history
-- Description: Historical record of all builds (for cleanup - last 5 builds)
-- ============================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='jfrog_build_history' AND xtype='U')
BEGIN
    CREATE TABLE jfrog_build_history (
        history_id INT IDENTITY(1,1) PRIMARY KEY,
        component_id INT NOT NULL,
        branch_id INT NOT NULL,
        build_date VARCHAR(8) NOT NULL,
        build_number INT NOT NULL,
        build_url VARCHAR(1000),
        download_path VARCHAR(500),
        extraction_path VARCHAR(500),
        file_size BIGINT,
        checksum VARCHAR(100),
        downloaded_time DATETIME,
        extracted_time DATETIME,
        is_deleted BIT DEFAULT 0,
        deleted_time DATETIME,
        created_date DATETIME DEFAULT GETDATE(),
        CONSTRAINT FK_build_history_component FOREIGN KEY (component_id) REFERENCES components(component_id) ON DELETE CASCADE,
        CONSTRAINT FK_build_history_branch FOREIGN KEY (branch_id) REFERENCES component_branches(branch_id) ON DELETE NO ACTION
    );

    CREATE INDEX IX_build_history_component_branch ON jfrog_build_history(component_id, branch_id);
    CREATE INDEX IX_build_history_build_date ON jfrog_build_history(build_date DESC, build_number DESC);
    CREATE INDEX IX_build_history_is_deleted ON jfrog_build_history(is_deleted);
END
GO

-- ============================================================
-- Table: jfrog_polling_log
-- Description: Detailed polling activity logs for audit and debugging
-- ============================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='jfrog_polling_log' AND xtype='U')
BEGIN
    CREATE TABLE jfrog_polling_log (
        log_id INT IDENTITY(1,1) PRIMARY KEY,
        thread_id INT,
        component_id INT,
        branch_id INT,
        log_level VARCHAR(20) NOT NULL,
        log_message TEXT,
        build_date VARCHAR(8),
        build_number INT,
        operation_type VARCHAR(50),
        duration_ms INT,
        log_date DATETIME DEFAULT GETDATE(),
        CONSTRAINT FK_polling_log_thread FOREIGN KEY (thread_id) REFERENCES jfrog_polling_threads(thread_id) ON DELETE NO ACTION,
        CONSTRAINT FK_polling_log_component FOREIGN KEY (component_id) REFERENCES components(component_id) ON DELETE NO ACTION,
        CONSTRAINT FK_polling_log_branch FOREIGN KEY (branch_id) REFERENCES component_branches(branch_id) ON DELETE NO ACTION,
        CONSTRAINT CHK_log_level CHECK (log_level IN ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'))
    );

    CREATE INDEX IX_polling_log_date ON jfrog_polling_log(log_date DESC);
    CREATE INDEX IX_polling_log_level ON jfrog_polling_log(log_level);
    CREATE INDEX IX_polling_log_component_branch ON jfrog_polling_log(component_id, branch_id);
    CREATE INDEX IX_polling_log_thread ON jfrog_polling_log(thread_id);
END
GO

-- ============================================================
-- Table: jfrog_system_config
-- Description: System-wide configuration for JFrog polling
-- ============================================================
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='jfrog_system_config' AND xtype='U')
BEGIN
    CREATE TABLE jfrog_system_config (
        config_id INT IDENTITY(1,1) PRIMARY KEY,
        config_key VARCHAR(100) NOT NULL UNIQUE,
        config_value VARCHAR(MAX),
        config_description VARCHAR(500),
        is_encrypted BIT DEFAULT 0,
        is_enabled BIT DEFAULT 1,
        created_date DATETIME DEFAULT GETDATE(),
        updated_date DATETIME DEFAULT GETDATE(),
        created_by VARCHAR(100),
        updated_by VARCHAR(100)
    );

    CREATE INDEX IX_jfrog_config_key ON jfrog_system_config(config_key);
    CREATE INDEX IX_jfrog_config_enabled ON jfrog_system_config(is_enabled);
END
GO

-- ============================================================
-- Insert Default JFrog System Configuration
-- ============================================================
IF NOT EXISTS (SELECT * FROM jfrog_system_config WHERE config_key = 'JFrogBaseURL')
BEGIN
    INSERT INTO jfrog_system_config (config_key, config_value, config_description, is_encrypted, is_enabled)
    VALUES
        ('JFrogBaseURL', '', 'Base URL for JFrog Artifactory (e.g., https://jfrog.company.com/artifactory)', 0, 1),
        ('SVCJFROGUSR', '', 'JFrog service account username', 0, 1),
        ('SVCJFROGPAS', '', 'JFrog service account password (encrypted)', 1, 1),
        ('BaseDrive', 'C:\WINCORE', 'Base drive path for storing artifacts (e.g., C:\WINCORE)', 0, 1),
        ('MaxConcurrentThreads', '100', 'Maximum number of concurrent polling threads (max 10000)', 0, 1),
        ('DefaultPollingFrequency', '300', 'Default polling frequency in seconds (5 minutes)', 0, 1),
        ('MaxBuildsToKeep', '5', 'Maximum number of builds to keep per component/branch', 0, 1),
        ('DownloadTimeout', '600', 'Download timeout in seconds (10 minutes)', 0, 1),
        ('ExtractionTimeout', '300', 'Extraction timeout in seconds (5 minutes)', 0, 1),
        ('RetryAttempts', '3', 'Number of retry attempts for failed operations', 0, 1),
        ('LogRetentionDays', '30', 'Number of days to retain polling logs', 0, 1);
    PRINT 'Default JFrog system configuration inserted successfully.';
END
GO

-- ============================================================
-- Stored Procedure: Get Active Polling Configuration
-- ============================================================
IF EXISTS (SELECT * FROM sys.objects WHERE type = 'P' AND name = 'sp_GetActivePollingConfig')
    DROP PROCEDURE sp_GetActivePollingConfig;
GO

CREATE PROCEDURE sp_GetActivePollingConfig
AS
BEGIN
    SET NOCOUNT ON;

    SELECT
        c.component_id,
        c.component_guid,
        c.component_name,
        p.project_id,
        p.project_key,
        cb.branch_id,
        cb.branch_name,
        pc.polling_interval_seconds,
        pc.enabled AS polling_enabled,
        c.jfrog_path_pattern,
        bt.latest_build_date,
        bt.latest_build_number
    FROM components c
    INNER JOIN projects p ON c.project_id = p.project_id
    INNER JOIN component_branches cb ON c.component_id = cb.component_id
    LEFT JOIN polling_config pc ON c.component_id = pc.component_id
    LEFT JOIN jfrog_build_tracking bt ON c.component_id = bt.component_id AND cb.branch_id = bt.branch_id
    WHERE c.is_enabled = 1
        AND c.polling_enabled = 1
        AND cb.is_active = 1
        AND (pc.enabled = 1 OR pc.enabled IS NULL);
END
GO

-- ============================================================
-- Stored Procedure: Update Build Tracking
-- ============================================================
IF EXISTS (SELECT * FROM sys.objects WHERE type = 'P' AND name = 'sp_UpdateBuildTracking')
    DROP PROCEDURE sp_UpdateBuildTracking;
GO

CREATE PROCEDURE sp_UpdateBuildTracking
    @component_id INT,
    @branch_id INT,
    @build_date VARCHAR(8),
    @build_number INT,
    @build_url VARCHAR(1000),
    @download_status VARCHAR(20) = 'pending',
    @extraction_status VARCHAR(20) = 'pending'
AS
BEGIN
    SET NOCOUNT ON;

    IF EXISTS (SELECT 1 FROM jfrog_build_tracking WHERE component_id = @component_id AND branch_id = @branch_id)
    BEGIN
        UPDATE jfrog_build_tracking
        SET latest_build_date = @build_date,
            latest_build_number = @build_number,
            build_url = @build_url,
            download_status = @download_status,
            extraction_status = @extraction_status,
            last_checked_time = GETDATE(),
            updated_date = GETDATE()
        WHERE component_id = @component_id AND branch_id = @branch_id;
    END
    ELSE
    BEGIN
        INSERT INTO jfrog_build_tracking (component_id, branch_id, latest_build_date, latest_build_number, build_url, download_status, extraction_status)
        VALUES (@component_id, @branch_id, @build_date, @build_number, @build_url, @download_status, @extraction_status);
    END
END
GO

-- ============================================================
-- Stored Procedure: Cleanup Old Builds (Keep Last 5)
-- ============================================================
IF EXISTS (SELECT * FROM sys.objects WHERE type = 'P' AND name = 'sp_CleanupOldBuilds')
    DROP PROCEDURE sp_CleanupOldBuilds;
GO

CREATE PROCEDURE sp_CleanupOldBuilds
    @component_id INT,
    @branch_id INT,
    @max_builds_to_keep INT = 5
AS
BEGIN
    SET NOCOUNT ON;

    -- Mark old builds as deleted
    WITH RankedBuilds AS (
        SELECT
            history_id,
            ROW_NUMBER() OVER (ORDER BY build_date DESC, build_number DESC) as rn
        FROM jfrog_build_history
        WHERE component_id = @component_id
            AND branch_id = @branch_id
            AND is_deleted = 0
    )
    UPDATE jfrog_build_history
    SET is_deleted = 1,
        deleted_time = GETDATE()
    WHERE history_id IN (
        SELECT history_id
        FROM RankedBuilds
        WHERE rn > @max_builds_to_keep
    );

    -- Return list of builds to delete from disk
    SELECT
        download_path,
        extraction_path
    FROM jfrog_build_history
    WHERE component_id = @component_id
        AND branch_id = @branch_id
        AND is_deleted = 1
        AND deleted_time >= DATEADD(MINUTE, -5, GETDATE());
END
GO

-- ============================================================
-- Stored Procedure: Log Polling Activity
-- ============================================================
IF EXISTS (SELECT * FROM sys.objects WHERE type = 'P' AND name = 'sp_LogPollingActivity')
    DROP PROCEDURE sp_LogPollingActivity;
GO

CREATE PROCEDURE sp_LogPollingActivity
    @thread_id INT = NULL,
    @component_id INT = NULL,
    @branch_id INT = NULL,
    @log_level VARCHAR(20),
    @log_message TEXT,
    @build_date VARCHAR(8) = NULL,
    @build_number INT = NULL,
    @operation_type VARCHAR(50) = NULL,
    @duration_ms INT = NULL
AS
BEGIN
    SET NOCOUNT ON;

    INSERT INTO jfrog_polling_log (thread_id, component_id, branch_id, log_level, log_message, build_date, build_number, operation_type, duration_ms)
    VALUES (@thread_id, @component_id, @branch_id, @log_level, @log_message, @build_date, @build_number, @operation_type, @duration_ms);
END
GO

PRINT '============================================================';
PRINT 'JFrog Polling System Schema Created Successfully!';
PRINT '============================================================';
PRINT 'Tables Created:';
PRINT '  - jfrog_polling_threads';
PRINT '  - jfrog_build_tracking';
PRINT '  - jfrog_build_history';
PRINT '  - jfrog_polling_log';
PRINT '  - jfrog_system_config';
PRINT '';
PRINT 'Stored Procedures Created:';
PRINT '  - sp_GetActivePollingConfig';
PRINT '  - sp_UpdateBuildTracking';
PRINT '  - sp_CleanupOldBuilds';
PRINT '  - sp_LogPollingActivity';
PRINT '============================================================';
