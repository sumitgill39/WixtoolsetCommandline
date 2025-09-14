# Advanced Application Pool Configuration Script - Fixed Version
# This script configures advanced settings that are not available in WiX v6 natively

param(
    [Parameter(Mandatory=$true)]
    [string]$AppPoolName,
    
    [Parameter(Mandatory=$false)]
    [int]$PrivateMemoryLimit = 1048576,  # 1GB in KB
    
    [Parameter(Mandatory=$false)]
    [int]$VirtualMemoryLimit = 2097152,  # 2GB in KB
    
    [Parameter(Mandatory=$false)]
    [int]$QueueLength = 1000,
    
    [Parameter(Mandatory=$false)]
    [int]$MaxProcesses = 1,
    
    [Parameter(Mandatory=$false)]
    [int]$CpuLimit = 0,  # 0 = unlimited
    
    [Parameter(Mandatory=$false)]
    [bool]$LoadUserProfile = $true,
    
    [Parameter(Mandatory=$false)]
    [bool]$SetProfileEnvironment = $true
)

# Import WebAdministration module
try {
    Import-Module WebAdministration -ErrorAction Stop
} catch {
    Write-Host "Warning: Cannot import WebAdministration module. This usually means:" -ForegroundColor Yellow
    Write-Host "1. PowerShell is not running as Administrator" -ForegroundColor Yellow
    Write-Host "2. IIS Management Tools are not installed" -ForegroundColor Yellow
    Write-Host "The MSI installation will continue, but advanced AppPool settings won't be applied." -ForegroundColor Yellow
    Write-Host "To apply advanced settings manually, run this script as Administrator after installation." -ForegroundColor Yellow
    exit 0  # Exit with success code to not fail the installation
}

try {
    Write-Host "Configuring advanced settings for Application Pool: $AppPoolName"
    
    # Check if app pool exists
    $appPool = Get-WebAppPool -Name $AppPoolName -ErrorAction SilentlyContinue
    if (!$appPool) {
        Write-Error "Application Pool '$AppPoolName' does not exist!"
        exit 1
    }
    
    Write-Host "Application Pool found, applying advanced configuration..."
    
    # Configure Process Model Settings using WebAdministration cmdlets
    Write-Host "Setting process model settings..."
    
    # Memory Limits
    if ($PrivateMemoryLimit -gt 0) {
        Set-ItemProperty -Path "IIS:\AppPools\$AppPoolName" -Name processModel.privateMemoryLimit -Value $PrivateMemoryLimit
        Write-Host "  Private Memory Limit: $($PrivateMemoryLimit)KB"
    }
    
    if ($VirtualMemoryLimit -gt 0) {
        Set-ItemProperty -Path "IIS:\AppPools\$AppPoolName" -Name processModel.virtualMemoryLimit -Value $VirtualMemoryLimit
        Write-Host "  Virtual Memory Limit: $($VirtualMemoryLimit)KB"
    }
    
    # Process Configuration
    Set-ItemProperty -Path "IIS:\AppPools\$AppPoolName" -Name processModel.maxProcesses -Value $MaxProcesses
    Write-Host "  Max Processes: $MaxProcesses"
    
    Set-ItemProperty -Path "IIS:\AppPools\$AppPoolName" -Name processModel.loadUserProfile -Value $LoadUserProfile
    Write-Host "  Load User Profile: $LoadUserProfile"
    
    Set-ItemProperty -Path "IIS:\AppPools\$AppPoolName" -Name processModel.setProfileEnvironment -Value $SetProfileEnvironment
    Write-Host "  Set Profile Environment: $SetProfileEnvironment"
    
    # CPU Configuration
    if ($CpuLimit -gt 0) {
        Set-ItemProperty -Path "IIS:\AppPools\$AppPoolName" -Name cpu.limit -Value $CpuLimit
        Write-Host "  CPU Limit: $CpuLimit%"
        
        Set-ItemProperty -Path "IIS:\AppPools\$AppPoolName" -Name cpu.action -Value "NoAction"
        Write-Host "  CPU Action: NoAction"
    }
    
    # Queue Configuration - Fixed property name
    Set-ItemProperty -Path "IIS:\AppPools\$AppPoolName" -Name processModel.requestQueueLimit -Value $QueueLength
    Write-Host "  Request Queue Limit: $QueueLength"
    
    # Basic Recycling Conditions
    Write-Host "Setting recycling conditions..."
    
    # Rapid-Fail Protection
    Set-ItemProperty -Path "IIS:\AppPools\$AppPoolName" -Name failure.rapidFailProtection -Value $true
    Set-ItemProperty -Path "IIS:\AppPools\$AppPoolName" -Name failure.rapidFailProtectionInterval -Value "00:05:00"
    Set-ItemProperty -Path "IIS:\AppPools\$AppPoolName" -Name failure.rapidFailProtectionMaxCrashes -Value 5
    Write-Host "  Rapid-Fail Protection: Enabled (5 crashes in 5 minutes)"
    
    # Basic Ping Settings
    Set-ItemProperty -Path "IIS:\AppPools\$AppPoolName" -Name processModel.pingEnabled -Value $true
    Set-ItemProperty -Path "IIS:\AppPools\$AppPoolName" -Name processModel.pingInterval -Value "00:00:30"
    Set-ItemProperty -Path "IIS:\AppPools\$AppPoolName" -Name processModel.pingResponseTime -Value "00:01:30"
    Write-Host "  Ping: Every 30 seconds, 90 second timeout"
    
    # Startup and Shutdown Timeouts
    Set-ItemProperty -Path "IIS:\AppPools\$AppPoolName" -Name processModel.startupTimeLimit -Value "00:01:30"
    Set-ItemProperty -Path "IIS:\AppPools\$AppPoolName" -Name processModel.shutdownTimeLimit -Value "00:01:30"
    Write-Host "  Startup/Shutdown timeout: 90 seconds each"
    
    Write-Host "Advanced Application Pool configuration completed successfully!" -ForegroundColor Green
    
} catch {
    Write-Host "Error occurred: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "Stack trace: $($_.ScriptStackTrace)" -ForegroundColor Red
    exit 1
}