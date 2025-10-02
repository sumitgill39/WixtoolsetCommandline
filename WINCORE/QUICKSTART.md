# Quick Start Guide - JFrog Polling System

## Step 1: Install Prerequisites

### Install Python Dependencies
```bash
pip install -r requirements.txt
```

### Verify ODBC Driver
Ensure "ODBC Driver 17 for SQL Server" is installed:
```bash
# Windows: Check in ODBC Data Source Administrator
odbcad32
```

## Step 2: Setup Database

Run the SQL schema script:

### Option A: Using sqlcmd
```bash
sqlcmd -S SUMEETGILL7E47\MSSQLSERVER01 -d MSIFactory -i jfrog_polling_schema.sql
```

### Option B: Using SQL Server Management Studio (SSMS)
1. Open SSMS
2. Connect to `SUMEETGILL7E47\MSSQLSERVER01`
3. Open `jfrog_polling_schema.sql`
4. Execute the script against `MSIFactory` database

## Step 3: Configure JFrog Credentials

### Option A: Using Setup Script (Recommended)
```bash
python setup_config.py
```

Follow the interactive prompts to configure:
- JFrog Base URL (e.g., `https://jfrog.company.com/artifactory`)
- JFrog Username
- JFrog Password
- Base Drive (default: `C:\WINCORE`)
- Max Concurrent Threads (default: 100)
- Max Builds to Keep (default: 5)

### Option B: Manual SQL Configuration
```sql
UPDATE jfrog_system_config SET config_value = 'https://your-jfrog-url.com/artifactory' WHERE config_key = 'JFrogBaseURL';
UPDATE jfrog_system_config SET config_value = 'your-username' WHERE config_key = 'SVCJFROGUSR';
UPDATE jfrog_system_config SET config_value = 'your-password' WHERE config_key = 'SVCJFROGPAS';
```

## Step 4: Test Connection

```bash
python jfrog_polling_main.py test
```

Expected output:
```
✓ JFrog connection test PASSED
```

## Step 5: Check System Status

```bash
python jfrog_polling_main.py status
```

This shows:
- Number of active components
- Database connection status
- JFrog connection status
- List of active component/branch configurations

## Step 6: Run Your First Poll

### Single Poll Cycle
```bash
python jfrog_polling_main.py poll
```

This will:
1. Check all active components for new builds
2. Download any new builds found
3. Extract the .zip files
4. Update the database
5. Display a summary

### Continuous Polling
```bash
python jfrog_polling_main.py start
```

This will:
1. Start continuous polling (default: every 5 minutes)
2. Run until you press `Ctrl+C`
3. Log all activities to file and console

## Common Commands

### View Configuration
```bash
python jfrog_polling_main.py config
```

### Run Cleanup
```bash
python jfrog_polling_main.py cleanup
```

### View Help
```bash
python jfrog_polling_main.py --help
```

## What Happens When a New Build is Found?

1. **Detection**: System finds `Build20251002.5` is newer than `Build20251002.4`

2. **Download**:
   - Creates folder: `C:\WINCORE\{ComponentGUID}\s\`
   - Downloads: `ComponentName.zip`

3. **Extraction**:
   - Creates folder: `C:\WINCORE\{ComponentGUID}\a\ComponentName\`
   - Extracts all files from .zip

4. **Cleanup**:
   - Keeps last 5 builds
   - Deletes older builds from both `s\` and `a\` folders

5. **Logging**:
   - All activities logged to database
   - Daily log file created: `jfrog_polling_YYYYMMDD.log`

## Folder Structure Example

After running, you'll see:
```
C:\WINCORE\
├── {ComponentGUID-1}\
│   ├── s\
│   │   └── MyComponent.zip
│   └── a\
│       └── MyComponent\
│           ├── index.html
│           ├── web.config
│           └── [other files]
├── {ComponentGUID-2}\
│   ├── s\
│   │   └── AnotherComponent.zip
│   └── a\
│       └── AnotherComponent\
│           └── [extracted files]
```

## Monitoring

### View Recent Activity
```sql
SELECT TOP 100 * FROM jfrog_polling_log ORDER BY log_date DESC;
```

### Check Latest Builds
```sql
SELECT c.component_name, cb.branch_name, bt.latest_build_date, bt.latest_build_number
FROM jfrog_build_tracking bt
JOIN components c ON bt.component_id = c.component_id
JOIN component_branches cb ON bt.branch_id = cb.branch_id
ORDER BY bt.last_checked_time DESC;
```

### View Errors
```sql
SELECT * FROM jfrog_polling_log
WHERE log_level = 'ERROR'
ORDER BY log_date DESC;
```

## Troubleshooting

### Issue: "Database connection failed"
**Solution**: Check SQL Server is running and connection details in `db_helper.py`

### Issue: "JFrog connection test FAILED"
**Solution**:
1. Verify JFrog URL is correct
2. Check username and password
3. Ensure network connectivity to JFrog

### Issue: "No new builds found"
**Solution**:
1. Verify builds exist in JFrog
2. Check URL pattern matches your JFrog structure
3. Ensure component is enabled: `polling_enabled = 1` in `components` table

### Issue: "Download timeout"
**Solution**:
1. Increase timeout in system config
2. Check network connectivity
3. Verify artifact size is reasonable

## Next Steps

1. **Configure Components**: Add your projects and components to the database
2. **Set Polling Intervals**: Adjust per-component polling frequency
3. **Monitor Logs**: Set up log rotation and monitoring
4. **Automate**: Set up Windows Task Scheduler or service to run continuously

## Support

For issues or questions:
1. Check logs: `jfrog_polling_YYYYMMDD.log`
2. Review database error logs: `jfrog_polling_log` table
3. Refer to full documentation: `README_JFROG_POLLING.md`
