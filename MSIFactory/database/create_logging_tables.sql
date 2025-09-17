-- MSI Factory System Logging Tables
-- Complete audit trail for all system actions

-- Drop existing tables if they exist (for clean installation)
IF OBJECT_ID('dbo.ActionLogs', 'U') IS NOT NULL DROP TABLE dbo.ActionLogs;
IF OBJECT_ID('dbo.RequestLogs', 'U') IS NOT NULL DROP TABLE dbo.RequestLogs;
IF OBJECT_ID('dbo.ErrorLogs', 'U') IS NOT NULL DROP TABLE dbo.ErrorLogs;
IF OBJECT_ID('dbo.AuditLogs', 'U') IS NOT NULL DROP TABLE dbo.AuditLogs;
IF OBJECT_ID('dbo.SystemEvents', 'U') IS NOT NULL DROP TABLE dbo.SystemEvents;

-- 1. Action Logs Table (Main action tracking)
CREATE TABLE dbo.ActionLogs (
    log_id BIGINT IDENTITY(1,1) PRIMARY KEY,
    timestamp DATETIME2 NOT NULL DEFAULT GETUTCDATE(),
    action_type VARCHAR(50) NOT NULL, -- CREATE, READ, UPDATE, DELETE, EXECUTE
    entity_type VARCHAR(50) NOT NULL, -- project, component, environment, user, system
    entity_id VARCHAR(100),
    entity_name NVARCHAR(255),
    user_id VARCHAR(100),
    user_name NVARCHAR(255),
    ip_address VARCHAR(45),
    session_id VARCHAR(100),
    success BIT NOT NULL DEFAULT 1,
    error_message NVARCHAR(MAX),
    details NVARCHAR(MAX), -- JSON format for additional details
    duration_ms INT,
    affected_rows INT,
    old_values NVARCHAR(MAX), -- JSON of old values (for UPDATE/DELETE)
    new_values NVARCHAR(MAX), -- JSON of new values (for CREATE/UPDATE)
    
    -- Indexes for performance
    INDEX IX_ActionLogs_Timestamp (timestamp DESC),
    INDEX IX_ActionLogs_EntityType (entity_type, entity_id),
    INDEX IX_ActionLogs_User (user_id, timestamp DESC),
    INDEX IX_ActionLogs_Action (action_type, timestamp DESC)
);

-- 2. Request Logs Table (API request tracking)
CREATE TABLE dbo.RequestLogs (
    request_id BIGINT IDENTITY(1,1) PRIMARY KEY,
    timestamp DATETIME2 NOT NULL DEFAULT GETUTCDATE(),
    method VARCHAR(10) NOT NULL, -- GET, POST, PUT, DELETE, PATCH
    endpoint VARCHAR(500) NOT NULL,
    full_url VARCHAR(2000),
    status_code INT NOT NULL,
    user_id VARCHAR(100),
    user_agent VARCHAR(500),
    ip_address VARCHAR(45),
    referrer VARCHAR(500),
    session_id VARCHAR(100),
    request_headers NVARCHAR(MAX), -- JSON format
    request_body NVARCHAR(MAX), -- JSON format (sanitized)
    response_body NVARCHAR(MAX), -- JSON format (truncated if needed)
    response_time_ms INT,
    bytes_sent INT,
    bytes_received INT,
    
    -- Indexes for performance
    INDEX IX_RequestLogs_Timestamp (timestamp DESC),
    INDEX IX_RequestLogs_Endpoint (endpoint, timestamp DESC),
    INDEX IX_RequestLogs_StatusCode (status_code, timestamp DESC),
    INDEX IX_RequestLogs_User (user_id, timestamp DESC)
);

-- 3. Error Logs Table (System errors and exceptions)
CREATE TABLE dbo.ErrorLogs (
    error_id BIGINT IDENTITY(1,1) PRIMARY KEY,
    timestamp DATETIME2 NOT NULL DEFAULT GETUTCDATE(),
    error_level VARCHAR(20) NOT NULL, -- DEBUG, INFO, WARNING, ERROR, CRITICAL
    error_type VARCHAR(100) NOT NULL,
    error_message NVARCHAR(MAX) NOT NULL,
    error_code VARCHAR(50),
    stack_trace NVARCHAR(MAX),
    user_id VARCHAR(100),
    session_id VARCHAR(100),
    request_id BIGINT, -- Link to RequestLogs
    action_id BIGINT, -- Link to ActionLogs
    module_name VARCHAR(255),
    function_name VARCHAR(255),
    line_number INT,
    context_data NVARCHAR(MAX), -- JSON format
    resolution_status VARCHAR(20) DEFAULT 'UNRESOLVED', -- UNRESOLVED, INVESTIGATING, RESOLVED, IGNORED
    resolved_by VARCHAR(100),
    resolved_at DATETIME2,
    resolution_notes NVARCHAR(MAX),
    
    -- Foreign keys
    CONSTRAINT FK_ErrorLogs_Request FOREIGN KEY (request_id) REFERENCES RequestLogs(request_id),
    CONSTRAINT FK_ErrorLogs_Action FOREIGN KEY (action_id) REFERENCES ActionLogs(log_id),
    
    -- Indexes
    INDEX IX_ErrorLogs_Timestamp (timestamp DESC),
    INDEX IX_ErrorLogs_Level (error_level, timestamp DESC),
    INDEX IX_ErrorLogs_Status (resolution_status, timestamp DESC)
);

-- 4. Audit Logs Table (Compliance and security audit trail)
CREATE TABLE dbo.AuditLogs (
    audit_id BIGINT IDENTITY(1,1) PRIMARY KEY,
    timestamp DATETIME2 NOT NULL DEFAULT GETUTCDATE(),
    event_type VARCHAR(100) NOT NULL, -- LOGIN, LOGOUT, PERMISSION_CHANGE, DATA_ACCESS, DATA_EXPORT, etc.
    event_category VARCHAR(50) NOT NULL, -- SECURITY, DATA, SYSTEM, COMPLIANCE
    severity VARCHAR(20) NOT NULL, -- INFO, LOW, MEDIUM, HIGH, CRITICAL
    user_id VARCHAR(100),
    user_name NVARCHAR(255),
    user_role VARCHAR(100),
    ip_address VARCHAR(45),
    machine_name VARCHAR(255),
    resource_type VARCHAR(100),
    resource_id VARCHAR(100),
    resource_name NVARCHAR(500),
    action_performed NVARCHAR(500),
    action_result VARCHAR(50),
    reason NVARCHAR(MAX),
    compliance_flags VARCHAR(500), -- Comma-separated compliance requirements (GDPR, HIPAA, etc.)
    data_classification VARCHAR(50), -- PUBLIC, INTERNAL, CONFIDENTIAL, RESTRICTED
    additional_metadata NVARCHAR(MAX), -- JSON format
    
    -- Indexes
    INDEX IX_AuditLogs_Timestamp (timestamp DESC),
    INDEX IX_AuditLogs_EventType (event_type, timestamp DESC),
    INDEX IX_AuditLogs_User (user_id, timestamp DESC),
    INDEX IX_AuditLogs_Severity (severity, timestamp DESC),
    INDEX IX_AuditLogs_Category (event_category, timestamp DESC)
);

-- 5. System Events Table (System-level events and monitoring)
CREATE TABLE dbo.SystemEvents (
    event_id BIGINT IDENTITY(1,1) PRIMARY KEY,
    timestamp DATETIME2 NOT NULL DEFAULT GETUTCDATE(),
    event_name VARCHAR(100) NOT NULL,
    event_source VARCHAR(100) NOT NULL, -- API_SERVER, DATABASE, SCHEDULER, WORKER, etc.
    event_level VARCHAR(20) NOT NULL, -- DEBUG, INFO, WARNING, ERROR, CRITICAL
    host_name VARCHAR(255),
    process_id INT,
    thread_id INT,
    memory_usage_mb INT,
    cpu_usage_percent DECIMAL(5,2),
    disk_usage_mb INT,
    network_bytes_sent BIGINT,
    network_bytes_received BIGINT,
    message NVARCHAR(MAX),
    details NVARCHAR(MAX), -- JSON format
    
    -- Indexes
    INDEX IX_SystemEvents_Timestamp (timestamp DESC),
    INDEX IX_SystemEvents_Source (event_source, timestamp DESC),
    INDEX IX_SystemEvents_Level (event_level, timestamp DESC)
);

-- Create views for common queries

-- Recent actions view
CREATE VIEW vw_RecentActions AS
SELECT TOP 1000
    a.timestamp,
    a.action_type,
    a.entity_type,
    a.entity_id,
    a.entity_name,
    a.user_name,
    a.success,
    a.error_message,
    a.duration_ms
FROM ActionLogs a
ORDER BY a.timestamp DESC;

-- Error summary view
CREATE VIEW vw_ErrorSummary AS
SELECT 
    CAST(timestamp AS DATE) as error_date,
    error_level,
    error_type,
    COUNT(*) as error_count,
    MAX(timestamp) as last_occurrence
FROM ErrorLogs
WHERE timestamp >= DATEADD(day, -30, GETUTCDATE())
GROUP BY CAST(timestamp AS DATE), error_level, error_type;

-- User activity view
CREATE VIEW vw_UserActivity AS
SELECT 
    user_id,
    user_name,
    COUNT(*) as action_count,
    SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful_actions,
    SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) as failed_actions,
    MIN(timestamp) as first_action,
    MAX(timestamp) as last_action
FROM ActionLogs
WHERE timestamp >= DATEADD(day, -7, GETUTCDATE())
GROUP BY user_id, user_name;

-- Stored procedures for log management

-- Procedure to clean old logs
CREATE PROCEDURE sp_CleanOldLogs
    @DaysToKeep INT = 90
AS
BEGIN
    DECLARE @CutoffDate DATETIME2 = DATEADD(day, -@DaysToKeep, GETUTCDATE());
    
    DELETE FROM RequestLogs WHERE timestamp < @CutoffDate;
    DELETE FROM ErrorLogs WHERE timestamp < @CutoffDate AND resolution_status = 'RESOLVED';
    DELETE FROM SystemEvents WHERE timestamp < @CutoffDate AND event_level IN ('DEBUG', 'INFO');
    
    -- Keep audit logs longer (1 year minimum)
    DELETE FROM AuditLogs WHERE timestamp < DATEADD(day, -365, GETUTCDATE());
END;

-- Procedure to get action statistics
CREATE PROCEDURE sp_GetActionStatistics
    @StartDate DATETIME2 = NULL,
    @EndDate DATETIME2 = NULL
AS
BEGIN
    IF @StartDate IS NULL SET @StartDate = DATEADD(day, -7, GETUTCDATE());
    IF @EndDate IS NULL SET @EndDate = GETUTCDATE();
    
    SELECT 
        action_type,
        entity_type,
        COUNT(*) as total_count,
        SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as success_count,
        SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) as failure_count,
        AVG(duration_ms) as avg_duration_ms,
        MAX(duration_ms) as max_duration_ms,
        MIN(duration_ms) as min_duration_ms
    FROM ActionLogs
    WHERE timestamp BETWEEN @StartDate AND @EndDate
    GROUP BY action_type, entity_type
    ORDER BY total_count DESC;
END;