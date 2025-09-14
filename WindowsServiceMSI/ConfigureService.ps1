# Advanced Windows Service Configuration Script
# This script configures advanced service settings not available in WiX natively

param(
    [Parameter(Mandatory=$true)]
    [string]$ServiceName,
    
    [Parameter(Mandatory=$false)]
    [string]$ServiceAccount = "LocalSystem",
    
    [Parameter(Mandatory=$false)]
    [string]$Password = "",
    
    [Parameter(Mandatory=$false)]
    [ValidateSet("Auto", "Manual", "Disabled", "DelayedAuto")]
    [string]$StartType = "Auto",
    
    [Parameter(Mandatory=$false)]
    [int]$StartupDelaySeconds = 0,
    
    [Parameter(Mandatory=$false)]
    [bool]$EnableFailureRecovery = $true,
    
    [Parameter(Mandatory=$false)]
    [string[]]$Dependencies = @(),
    
    [Parameter(Mandatory=$false)]
    [int]$ServiceTimeoutSeconds = 30
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Windows Service Advanced Configuration" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if service exists
$service = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
if (!$service) {
    Write-Error "Service '$ServiceName' not found!"
    exit 1
}

Write-Host "Configuring service: $ServiceName" -ForegroundColor Green

# Stop the service if running
if ($service.Status -eq 'Running') {
    Write-Host "Stopping service..."
    Stop-Service -Name $ServiceName -Force
    Start-Sleep -Seconds 2
}

# Configure Service Account
Write-Host ""
Write-Host "Setting service account..."
if ($ServiceAccount -eq "LocalSystem") {
    $credential = $null
    Write-Host "  Account: LocalSystem"
} elseif ($ServiceAccount -eq "LocalService") {
    $credential = $null
    Write-Host "  Account: NT AUTHORITY\LocalService"
} elseif ($ServiceAccount -eq "NetworkService") {
    $credential = $null
    Write-Host "  Account: NT AUTHORITY\NetworkService"
} else {
    # Custom account
    if ($Password) {
        $securePassword = ConvertTo-SecureString $Password -AsPlainText -Force
        $credential = New-Object System.Management.Automation.PSCredential($ServiceAccount, $securePassword)
        Write-Host "  Account: $ServiceAccount"
    } else {
        Write-Warning "No password provided for custom account!"
    }
}

# Configure Start Type
Write-Host ""
Write-Host "Setting startup type..."
switch ($StartType) {
    "Auto" {
        Set-Service -Name $ServiceName -StartupType Automatic
        Write-Host "  Startup: Automatic"
    }
    "Manual" {
        Set-Service -Name $ServiceName -StartupType Manual
        Write-Host "  Startup: Manual"
    }
    "Disabled" {
        Set-Service -Name $ServiceName -StartupType Disabled
        Write-Host "  Startup: Disabled"
    }
    "DelayedAuto" {
        # Delayed start requires registry modification
        $regPath = "HKLM:\SYSTEM\CurrentControlSet\Services\$ServiceName"
        Set-ItemProperty -Path $regPath -Name "DelayedAutostart" -Value 1 -Type DWord
        Set-ItemProperty -Path $regPath -Name "Start" -Value 2 -Type DWord
        Write-Host "  Startup: Automatic (Delayed Start)"
    }
}

# Configure Service Dependencies
if ($Dependencies.Count -gt 0) {
    Write-Host ""
    Write-Host "Setting service dependencies..."
    $regPath = "HKLM:\SYSTEM\CurrentControlSet\Services\$ServiceName"
    Set-ItemProperty -Path $regPath -Name "DependOnService" -Value $Dependencies -Type MultiString
    foreach ($dep in $Dependencies) {
        Write-Host "  Depends on: $dep"
    }
}

# Configure Failure Recovery Actions
if ($EnableFailureRecovery) {
    Write-Host ""
    Write-Host "Configuring failure recovery actions..."
    
    # Using sc.exe for failure actions (more reliable than WMI)
    $failureCommand = "sc.exe failure `"$ServiceName`" reset= 86400 actions= restart/60000/restart/60000/restart/60000"
    Invoke-Expression $failureCommand | Out-Null
    
    Write-Host "  First Failure: Restart after 60 seconds"
    Write-Host "  Second Failure: Restart after 60 seconds"
    Write-Host "  Subsequent Failures: Restart after 60 seconds"
    Write-Host "  Reset Failure Count: After 24 hours"
}

# Configure Service Timeout
Write-Host ""
Write-Host "Setting service timeout..."
$regPath = "HKLM:\SYSTEM\CurrentControlSet\Control"
$currentTimeout = (Get-ItemProperty -Path $regPath -Name ServicesPipeTimeout -ErrorAction SilentlyContinue).ServicesPipeTimeout
if (!$currentTimeout -or $currentTimeout -lt ($ServiceTimeoutSeconds * 1000)) {
    Set-ItemProperty -Path $regPath -Name ServicesPipeTimeout -Value ($ServiceTimeoutSeconds * 1000) -Type DWord
    Write-Host "  Service timeout: $ServiceTimeoutSeconds seconds"
}

# Configure Service Description (Enhanced)
Write-Host ""
Write-Host "Setting enhanced service description..."
$description = @"
$ServiceName - Enterprise Service
Version: 1.0.0
Configured: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")
Account: $ServiceAccount
Startup: $StartType
"@
Set-Service -Name $ServiceName -Description $description

# Configure Service Priority (Optional)
Write-Host ""
Write-Host "Setting service priority..."
$regPath = "HKLM:\SYSTEM\CurrentControlSet\Services\$ServiceName"
# Priority: 0x00000020 = Normal, 0x00000080 = High, 0x00000100 = Realtime
Set-ItemProperty -Path $regPath -Name "ServicesPriorityClass" -Value 0x00000020 -Type DWord -ErrorAction SilentlyContinue
Write-Host "  Priority: Normal"

# Grant Required Privileges
if ($ServiceAccount -notin @("LocalSystem", "LocalService", "NetworkService")) {
    Write-Host ""
    Write-Host "Granting service privileges to $ServiceAccount..."
    
    # Grant "Log on as a service" right using secedit
    $tempFile = [System.IO.Path]::GetTempFileName()
    $configContent = @"
[Unicode]
Unicode=yes
[Privilege Rights]
SeServiceLogonRight = *$ServiceAccount
"@
    Set-Content -Path $tempFile -Value $configContent
    
    try {
        secedit /configure /db secedit.sdb /cfg $tempFile /quiet
        Write-Host "  Granted 'Log on as a service' right"
    } catch {
        Write-Warning "Could not grant privileges: $_"
    } finally {
        Remove-Item $tempFile -Force -ErrorAction SilentlyContinue
    }
}

# Create Service-specific Event Log
Write-Host ""
Write-Host "Creating event log source..."
if (![System.Diagnostics.EventLog]::SourceExists($ServiceName)) {
    [System.Diagnostics.EventLog]::CreateEventSource($ServiceName, "Application")
    Write-Host "  Event source created: $ServiceName"
} else {
    Write-Host "  Event source already exists"
}

# Set Environment Variables for Service
Write-Host ""
Write-Host "Setting service environment variables..."
$regPath = "HKLM:\SYSTEM\CurrentControlSet\Services\$ServiceName"
$envVars = @(
    "SERVICE_NAME=$ServiceName",
    "SERVICE_HOME=%ProgramFiles%\MyCompany\$ServiceName",
    "SERVICE_LOG_LEVEL=Information"
)
Set-ItemProperty -Path $regPath -Name "Environment" -Value $envVars -Type MultiString
Write-Host "  Environment variables configured"

# Start the service if it was set to Auto
if ($StartType -in @("Auto", "DelayedAuto")) {
    Write-Host ""
    Write-Host "Starting service..."
    try {
        Start-Service -Name $ServiceName -ErrorAction Stop
        Write-Host "  Service started successfully" -ForegroundColor Green
    } catch {
        Write-Warning "Could not start service: $_"
    }
}

# Display Final Status
Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "Service Configuration Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Service Status:"
$finalService = Get-Service -Name $ServiceName
Write-Host "  Name: $($finalService.Name)"
Write-Host "  Display Name: $($finalService.DisplayName)"
Write-Host "  Status: $($finalService.Status)"
Write-Host "  Start Type: $($finalService.StartType)"
Write-Host ""
Write-Host "To verify configuration, check:"
Write-Host "  - Services console (services.msc)"
Write-Host "  - Event Viewer for service logs"
Write-Host "  - Registry: HKLM\SYSTEM\CurrentControlSet\Services\$ServiceName"