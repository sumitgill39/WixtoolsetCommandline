# JFrog Multi-threaded Polling System

A high-performance, multi-threaded polling system for JFrog Artifactory that automatically detects, downloads, and extracts new builds across multiple projects, components, and branches.

## Features

- **Multi-threaded Architecture**: Supports 10,000+ concurrent threads for polling multiple components
- **Intelligent Build Detection**: Automatically finds the latest builds by incrementing build numbers
- **Automatic Download & Extraction**: Downloads .zip artifacts and extracts them to structured folders
- **Build History Management**: Keeps the last 5 builds per component/branch, automatically cleaning up old builds
- **Comprehensive Logging**: Detailed logging of all polling, download, extraction, and cleanup activities
- **Database Integration**: Full SQL Server integration for tracking and configuration
- **Configurable Polling**: Control which projects/components/branches to poll and polling frequency

## System Architecture

### URL Structure
```
https://{JFROGBaseURL}/{ProjectShortKey}/{ComponentGUID}/{branch}/Build{date(YYYYMMDD)}.{buildNumber}/{componentName}.zip
```

Example:
```
https://jfrog.company.com/myproject/12345678-1234-1234-1234-123456789012/main/Build20251002.5/MyComponent.zip
```

### Folder Structure
```
BaseDrive:\WINCORE\
├── {ComponentGUID}\
│   ├── s\                          # Source folder (downloaded .zip files)
│   │   └── {componentName}.zip
│   └── a\                          # Artifact folder (extracted files)
│       └── {componentName}\
│           └── [extracted files]
```

## Installation

### Prerequisites
- Python 3.8 or higher
- MS SQL Server 2016 or higher
- ODBC Driver 17 for SQL Server
- JFrog Artifactory access credentials

### Step 1: Install Python Dependencies
```bash
pip install -r requirements.txt
```

### Step 2: Setup Database Schema
Run the SQL schema script to create required tables:
```bash
sqlcmd -S SUMEETGILL7E47\MSSQLSERVER01 -d MSIFactory -i jfrog_polling_schema.sql
```

Or using SQL Server Management Studio (SSMS):
1. Open `jfrog_polling_schema.sql`
2. Execute the script against the `MSIFactory` database

### Step 3: Configure JFrog Credentials
Update the system configuration in the database:

```sql
-- Set JFrog Base URL
UPDATE jfrog_system_config
SET config_value = 'https://your-jfrog-url.com/artifactory'
WHERE config_key = 'JFrogBaseURL';

-- Set JFrog Username
UPDATE jfrog_system_config
SET config_value = 'your-username'
WHERE config_key = 'SVCJFROGUSR';

-- Set JFrog Password
UPDATE jfrog_system_config
SET config_value = 'your-password'
WHERE config_key = 'SVCJFROGPAS';

-- Set Base Drive (optional, default is C:\WINCORE)
UPDATE jfrog_system_config
SET config_value = 'D:\WINCORE'
WHERE config_key = 'BaseDrive';

-- Set Max Concurrent Threads (optional, default is 100)
UPDATE jfrog_system_config
SET config_value = '500'
WHERE config_key = 'MaxConcurrentThreads';
```

## Usage

### Command-Line Interface

The system provides several commands:

#### 1. Test JFrog Connection
```bash
python jfrog_polling_main.py test
```
Tests connectivity to JFrog Artifactory and validates credentials.

#### 2. Show Configuration
```bash
python jfrog_polling_main.py config
```
Displays current system configuration.

#### 3. Show System Status
```bash
python jfrog_polling_main.py status
```
Shows active components and their polling status.

#### 4. Run Single Poll Cycle
```bash
python jfrog_polling_main.py poll
```
Executes one polling cycle across all active components.

#### 5. Start Continuous Polling
```bash
python jfrog_polling_main.py start
```
Starts continuous polling (runs every 5 minutes by default).
Press `Ctrl+C` to stop.

#### 6. Run Cleanup
```bash
python jfrog_polling_main.py cleanup
```
Manually trigger cleanup of old builds (keeps last 5).

## Database Schema

### Key Tables

#### jfrog_system_config
Stores system-wide configuration:
- JFrogBaseURL
- SVCJFROGUSR (username)
- SVCJFROGPAS (password)
- BaseDrive
- MaxConcurrentThreads
- MaxBuildsToKeep

#### jfrog_build_tracking
Tracks the latest build for each component/branch:
- component_id
- branch_id
- latest_build_date
- latest_build_number
- download_status
- extraction_status

#### jfrog_build_history
Historical record of all builds:
- build_date
- build_number
- download_path
- extraction_path
- is_deleted (for cleanup tracking)

#### jfrog_polling_log
Detailed activity logs:
- log_level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- log_message
- operation_type (poll, download, extraction, cleanup)
- duration_ms

## Configuration

### Polling Configuration
Enable/disable polling for specific components in the `polling_config` table:

```sql
-- Enable polling for a component
UPDATE polling_config
SET enabled = 1, polling_interval_seconds = 300
WHERE component_id = 1;

-- Disable polling for a component
UPDATE polling_config
SET enabled = 0
WHERE component_id = 2;
```

### Component Configuration
Configure components in the `components` table:

```sql
-- Enable component for polling
UPDATE components
SET polling_enabled = 1, is_enabled = 1
WHERE component_id = 1;
```

### Branch Configuration
Manage branches in the `component_branches` table:

```sql
-- Activate a branch for polling
UPDATE component_branches
SET is_active = 1
WHERE branch_id = 1;
```

## Module Overview

### 1. db_helper.py
- Database connection management
- Query execution
- Configuration retrieval
- Stored procedure calls

### 2. jfrog_config.py
- JFrog credential management
- URL construction
- Artifact existence checking
- Latest build detection

### 3. download_manager.py
- Folder structure creation
- Artifact downloading
- Checksum calculation
- Download tracking

### 4. extraction_manager.py
- ZIP file extraction
- Extraction verification
- Extraction tracking

### 5. cleanup_manager.py
- Old build cleanup (keeps last 5)
- Space management
- Storage statistics

### 6. polling_engine.py
- Multi-threaded polling orchestration
- Thread pool management
- Concurrent component polling
- Result aggregation

### 7. jfrog_polling_main.py
- CLI interface
- System orchestration
- Command execution

## Workflow

1. **Polling Phase**
   - Retrieve active component/branch configurations
   - For each configuration, spawn a thread
   - Check JFrog for latest build using incremental detection
   - Compare with last known build in database

2. **Download Phase** (if new build found)
   - Create folder structure: `{BaseDrive}\WINCORE\{ComponentGUID}\s\`
   - Download .zip file from JFrog
   - Calculate checksum
   - Update download tracking

3. **Extraction Phase**
   - Create extraction folder: `{BaseDrive}\WINCORE\{ComponentGUID}\a\{componentName}\`
   - Extract .zip contents
   - Verify extraction
   - Update extraction tracking

4. **History & Cleanup Phase**
   - Insert build into history
   - Query builds older than last 5
   - Delete old .zip files and extracted folders
   - Log cleanup activity

## Monitoring & Troubleshooting

### View Recent Logs
```sql
SELECT TOP 100 *
FROM jfrog_polling_log
ORDER BY log_date DESC;
```

### Check Failed Operations
```sql
SELECT *
FROM jfrog_polling_log
WHERE log_level = 'ERROR'
ORDER BY log_date DESC;
```

### View Build Tracking Status
```sql
SELECT
    c.component_name,
    cb.branch_name,
    bt.latest_build_date,
    bt.latest_build_number,
    bt.download_status,
    bt.extraction_status,
    bt.last_checked_time
FROM jfrog_build_tracking bt
INNER JOIN components c ON bt.component_id = c.component_id
INNER JOIN component_branches cb ON bt.branch_id = cb.branch_id
ORDER BY bt.last_checked_time DESC;
```

### Storage Statistics
```sql
SELECT
    c.component_name,
    COUNT(bh.history_id) as total_builds,
    SUM(bh.file_size) / 1024 / 1024 as total_size_mb
FROM components c
LEFT JOIN jfrog_build_history bh ON c.component_id = bh.component_id
WHERE bh.is_deleted = 0
GROUP BY c.component_name
ORDER BY total_size_mb DESC;
```

## Performance Tuning

### Thread Pool Size
Adjust based on your system resources:
```sql
UPDATE jfrog_system_config
SET config_value = '1000'  -- Increase for more concurrent threads
WHERE config_key = 'MaxConcurrentThreads';
```

### Polling Frequency
Adjust per component:
```sql
UPDATE polling_config
SET polling_interval_seconds = 600  -- Poll every 10 minutes
WHERE component_id = 1;
```

### Build Retention
Change how many builds to keep:
```sql
UPDATE jfrog_system_config
SET config_value = '10'  -- Keep last 10 builds instead of 5
WHERE config_key = 'MaxBuildsToKeep';
```

## Error Handling

The system includes comprehensive error handling:
- Connection failures: Automatic retry with configurable attempts
- Download failures: Logged and status updated to 'failed'
- Extraction failures: Logged with detailed error messages
- Database errors: Transaction rollback and error logging

## Security Considerations

1. **Credential Storage**: JFrog passwords are stored in the database
   - Consider implementing encryption for `SVCJFROGPAS`
   - Use SQL Server encryption features or application-level encryption

2. **Access Control**: Restrict database access to polling system
   - Use dedicated SQL Server login for the application
   - Grant minimum required permissions

3. **Network Security**: Ensure secure communication with JFrog
   - Use HTTPS for JFrog URLs
   - Validate SSL certificates

## Maintenance

### Regular Tasks
1. Monitor log file size and implement rotation
2. Review and archive old polling logs (> 30 days)
3. Monitor disk space on artifact storage drive
4. Review failed operations and investigate root causes

### Backup Strategy
Include these tables in your backup plan:
- jfrog_build_tracking
- jfrog_build_history
- jfrog_system_config
- jfrog_polling_log

## Support & Troubleshooting

### Common Issues

**Issue**: "Database connection failed"
- **Solution**: Verify SQL Server is running and connection string is correct

**Issue**: "JFrog connection test FAILED"
- **Solution**: Check JFrog URL, username, and password in configuration

**Issue**: "No new builds found"
- **Solution**: Verify build exists in JFrog and URL pattern is correct

**Issue**: "Download timeout"
- **Solution**: Increase timeout in system config or check network connectivity

## License

Internal use only - MSI Factory Project

## Authors

MSI Factory Development Team
