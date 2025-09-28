# MSI Factory Logging System

## Overview

The MSI Factory includes a comprehensive logging system that tracks all system activities, security events, and MSI generation processes.

## Log Files

All logs are stored in the `logs/` directory:

### 1. **system.log**
- General system operations
- System startup/shutdown
- Configuration changes
- Component initialization

### 2. **access.log**
- User login/logout events
- Authentication attempts
- Session management
- Access control decisions

### 3. **security.log**
- Failed login attempts
- Unauthorized access attempts
- Security violations
- Admin actions

### 4. **msi_generation.log**
- MSI build start/completion
- Artifact downloads
- Configuration transformations
- Build errors and warnings

### 5. **error.log**
- System errors
- Exceptions
- Critical failures
- Stack traces

### 6. **audit.json**
- Structured audit trail
- JSON format for analysis
- Complete activity history
- Compliance reporting

## Log Levels

- **DEBUG**: Detailed diagnostic information
- **INFO**: General informational messages
- **WARNING**: Warning messages
- **ERROR**: Error messages
- **CRITICAL**: Critical system failures

## Key Features

### Automatic Log Rotation
- Size-based rotation (10MB per file)
- Time-based rotation (daily for MSI logs)
- Keeps last 5-30 backups based on log type

### Structured Logging
- Consistent format across all logs
- Timestamp | Level | Module | Function | Message
- JSON audit trail for compliance

### Real-time Monitoring
- Console output for critical errors
- Live log streaming capability
- Dashboard integration ready

## What Gets Logged

### User Activities
- Login attempts (success/failure)
- Logout events
- Access requests
- Dashboard navigation
- MSI generation requests

### System Events
- Service startup/shutdown
- Configuration changes
- Directory creation
- Module initialization
- Background job status

### Security Events
- Failed authentication
- Unauthorized access attempts
- Permission violations
- Admin privilege usage
- Suspicious activities

### MSI Generation
- Job creation with unique ID
- Environment processing
- Artifact downloads
- Configuration transformations
- Build success/failure
- Output file locations

### Errors
- Application exceptions
- API failures
- File system errors
- Network issues
- Database errors

## Usage Examples

### Viewing Logs

```bash
# View recent system activity
tail -f logs/system.log

# Check authentication events
tail -f logs/access.log

# Monitor security issues
tail -f logs/security.log

# Track MSI generation
tail -f logs/msi_generation.log

# Check errors
tail -f logs/error.log
```

### Log Analysis

```bash
# Count successful logins today
grep "Login SUCCESS" logs/access.log | grep "$(date +%Y-%m-%d)" | wc -l

# Find failed login attempts
grep "Login FAILED" logs/access.log

# Check MSI generation success rate
grep "Generation SUCCESS" logs/msi_generation.log | wc -l
grep "Generation FAILED" logs/msi_generation.log | wc -l

# View audit trail
python -m json.tool logs/audit.json | less
```

## Integration

The logging system is automatically integrated with:

1. **Authentication Module** - Tracks all auth events
2. **MSI Generation Engine** - Logs build process
3. **Admin Panel** - Records admin actions
4. **API Endpoints** - Logs API usage
5. **Error Handlers** - Captures all exceptions

## Compliance & Auditing

The logging system supports:
- **Security Auditing** - Track all security events
- **Access Control** - Monitor who accessed what
- **Change Management** - Log all system changes
- **Compliance Reporting** - Generate audit reports
- **Incident Investigation** - Detailed event history

## Log Retention

Default retention policies:
- System logs: 30 days
- Access logs: 90 days
- Security logs: 365 days
- MSI generation logs: 30 days
- Error logs: 30 days
- Audit logs: Permanent (manual cleanup)

## Performance

- Asynchronous logging for performance
- Minimal impact on system operations
- Efficient rotation prevents disk issues
- Optimized for high-volume logging

## Security

- Logs contain no passwords
- Sensitive data is masked
- Write-only access for applications
- Read access restricted to admins
- Encrypted storage recommended

## Troubleshooting

### Common Issues

1. **Logs not creating**
   - Check `logs/` directory permissions
   - Verify disk space available
   - Ensure logger initialized

2. **Log rotation failing**
   - Check file permissions
   - Verify rotation settings
   - Clear old backup files

3. **Missing events**
   - Verify logging level
   - Check logger configuration
   - Ensure module imported

## Future Enhancements

- Log aggregation service
- Real-time alerting
- Dashboard visualization
- Log analysis tools
- External SIEM integration
- Metrics and monitoring