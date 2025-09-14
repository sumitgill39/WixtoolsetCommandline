# Advanced Application Pool Configuration with Credential Management
# This script configures AppPool with various identity options

param(
    [Parameter(Mandatory=$true)]
    [string]$AppPoolName,
    
    [Parameter(Mandatory=$false)]
    [ValidateSet("ApplicationPoolIdentity", "LocalSystem", "LocalService", "NetworkService", "SpecificUser")]
    [string]$IdentityType = "ApplicationPoolIdentity",
    
    [Parameter(Mandatory=$false)]
    [string]$UserName = "",
    
    [Parameter(Mandatory=$false)]
    [string]$Password = "",
    
    [Parameter(Mandatory=$false)]
    [string]$Domain = "",
    
    [Parameter(Mandatory=$false)]
    [int]$PrivateMemoryLimit = 1048576,  # 1GB in KB
    
    [Parameter(Mandatory=$false)]
    [int]$VirtualMemoryLimit = 2097152,  # 2GB in KB
    
    [Parameter(Mandatory=$false)]
    [int]$QueueLength = 1000,
    
    [Parameter(Mandatory=$false)]
    [int]$MaxProcesses = 1,
    
    [Parameter(Mandatory=$false)]
    [bool]$LoadUserProfile = $true,
    
    [Parameter(Mandatory=$false)]
    [bool]$SetProfileEnvironment = $true
)

# Function to set AppPool identity
function Set-AppPoolIdentity {
    param(
        [string]$PoolName,
        [string]$Type,
        [string]$User,
        [string]$Pass,
        [string]$Dom
    )
    
    Write-Host "Setting Application Pool Identity..."
    
    switch ($Type) {
        "ApplicationPoolIdentity" {
            # Most secure - each app pool gets its own virtual account
            Set-ItemProperty -Path "IIS:\AppPools\$PoolName" -Name processModel.identityType -Value "ApplicationPoolIdentity"
            Write-Host "  Identity: ApplicationPoolIdentity (IIS AppPool\$PoolName)"
            Write-Host "  Note: This is the most secure option with automatic password management"
        }
        
        "LocalSystem" {
            # Highest privileges - use with caution
            Set-ItemProperty -Path "IIS:\AppPools\$PoolName" -Name processModel.identityType -Value "LocalSystem"
            Write-Host "  Identity: LocalSystem (SYSTEM account)"
            Write-Host "  WARNING: This account has full system privileges!"
        }
        
        "LocalService" {
            # Limited local privileges
            Set-ItemProperty -Path "IIS:\AppPools\$PoolName" -Name processModel.identityType -Value "LocalService"
            Write-Host "  Identity: LocalService"
            Write-Host "  Note: Limited privileges, no network access"
        }
        
        "NetworkService" {
            # Limited privileges with network access
            Set-ItemProperty -Path "IIS:\AppPools\$PoolName" -Name processModel.identityType -Value "NetworkService"
            Write-Host "  Identity: NetworkService"
            Write-Host "  Note: Limited privileges with network access"
        }
        
        "SpecificUser" {
            # Custom user account
            if ([string]::IsNullOrEmpty($User)) {
                Write-Error "Username is required when using SpecificUser identity type!"
                return $false
            }
            
            Set-ItemProperty -Path "IIS:\AppPools\$PoolName" -Name processModel.identityType -Value "SpecificUser"
            
            # Build the full username with domain if provided
            $fullUserName = if ($Dom) { "$Dom\$User" } else { $User }
            
            Set-ItemProperty -Path "IIS:\AppPools\$PoolName" -Name processModel.userName -Value $fullUserName
            
            # Set password if provided
            if ($Pass) {
                Set-ItemProperty -Path "IIS:\AppPools\$PoolName" -Name processModel.password -Value $Pass
                Write-Host "  Identity: Custom User - $fullUserName"
                Write-Host "  Note: Password has been set (hidden for security)"
            } else {
                Write-Host "  Identity: Custom User - $fullUserName"
                Write-Host "  WARNING: No password provided - you may need to set it manually"
            }
            
            # Grant necessary permissions to the user
            Write-Host "  Granting necessary permissions to $fullUserName..."
            
            # Grant IIS_IUSRS membership (optional, depends on requirements)
            try {
                $iisUsersGroup = [ADSI]"WinNT://./IIS_IUSRS,group"
                $userAccount = [ADSI]"WinNT://$fullUserName,user"
                $iisUsersGroup.Add($userAccount.Path)
                Write-Host "    Added to IIS_IUSRS group"
            } catch {
                Write-Host "    Note: Could not add to IIS_IUSRS group (may already be member)"
            }
        }
    }
    
    return $true
}

# Function to grant folder permissions
function Grant-FolderPermissions {
    param(
        [string]$FolderPath,
        [string]$Identity
    )
    
    if (Test-Path $FolderPath) {
        Write-Host "Granting permissions on $FolderPath to $Identity..."
        
        try {
            $acl = Get-Acl $FolderPath
            $permission = $Identity, "ReadAndExecute,Write", "ContainerInherit,ObjectInherit", "None", "Allow"
            $accessRule = New-Object System.Security.AccessControl.FileSystemAccessRule $permission
            $acl.SetAccessRule($accessRule)
            Set-Acl $FolderPath $acl
            Write-Host "  Permissions granted successfully"
        } catch {
            Write-Host "  Warning: Could not set folder permissions: $_"
        }
    }
}

# Main script execution
try {
    # Import WebAdministration module
    Import-Module WebAdministration -ErrorAction Stop
    
    Write-Host "==========================================" -ForegroundColor Cyan
    Write-Host "Application Pool Credential Configuration" -ForegroundColor Cyan
    Write-Host "==========================================" -ForegroundColor Cyan
    Write-Host ""
    
    # Check if app pool exists
    $appPool = Get-WebAppPool -Name $AppPoolName -ErrorAction SilentlyContinue
    if (!$appPool) {
        Write-Error "Application Pool '$AppPoolName' does not exist!"
        exit 1
    }
    
    Write-Host "Configuring Application Pool: $AppPoolName" -ForegroundColor Green
    Write-Host ""
    
    # Set the identity
    $identitySet = Set-AppPoolIdentity -PoolName $AppPoolName -Type $IdentityType -User $UserName -Pass $Password -Dom $Domain
    
    if (!$identitySet) {
        Write-Error "Failed to set Application Pool identity"
        exit 1
    }
    
    # Configure additional identity-related settings
    Write-Host ""
    Write-Host "Configuring identity-related settings..."
    
    # Load User Profile - important for certain applications
    Set-ItemProperty -Path "IIS:\AppPools\$AppPoolName" -Name processModel.loadUserProfile -Value $LoadUserProfile
    Write-Host "  Load User Profile: $LoadUserProfile"
    
    # Set Profile Environment
    Set-ItemProperty -Path "IIS:\AppPools\$AppPoolName" -Name processModel.setProfileEnvironment -Value $SetProfileEnvironment
    Write-Host "  Set Profile Environment: $SetProfileEnvironment"
    
    # Logon Type (batch or service)
    Set-ItemProperty -Path "IIS:\AppPools\$AppPoolName" -Name processModel.logonType -Value "LogonBatch"
    Write-Host "  Logon Type: LogonBatch"
    
    # Configure Process Model Settings
    Write-Host ""
    Write-Host "Configuring process model settings..."
    
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
    
    # Queue Configuration
    Set-ItemProperty -Path "IIS:\AppPools\$AppPoolName" -Name processModel.requestQueueLimit -Value $QueueLength
    Write-Host "  Request Queue Limit: $QueueLength"
    
    # Grant permissions to website folder based on identity
    Write-Host ""
    Write-Host "Setting folder permissions..."
    
    # Get the website path (you may need to adjust this based on your setup)
    $sitePath = "C:\Websites\MyWebSite"  # Or use a parameter
    
    switch ($IdentityType) {
        "ApplicationPoolIdentity" {
            Grant-FolderPermissions -FolderPath $sitePath -Identity "IIS AppPool\$AppPoolName"
        }
        "SpecificUser" {
            $fullUserName = if ($Domain) { "$Domain\$UserName" } else { $UserName }
            Grant-FolderPermissions -FolderPath $sitePath -Identity $fullUserName
        }
        default {
            Write-Host "  Using built-in account, standard permissions apply"
        }
    }
    
    # Restart the Application Pool to apply changes
    Write-Host ""
    Write-Host "Restarting Application Pool to apply changes..."
    Restart-WebAppPool -Name $AppPoolName
    Write-Host "  Application Pool restarted successfully"
    
    Write-Host ""
    Write-Host "==========================================" -ForegroundColor Green
    Write-Host "Configuration completed successfully!" -ForegroundColor Green
    Write-Host "==========================================" -ForegroundColor Green
    
    # Display security recommendations
    Write-Host ""
    Write-Host "SECURITY RECOMMENDATIONS:" -ForegroundColor Yellow
    Write-Host "1. Use ApplicationPoolIdentity when possible (most secure)" -ForegroundColor Yellow
    Write-Host "2. If using custom user, ensure it has minimal required permissions" -ForegroundColor Yellow
    Write-Host "3. Never use LocalSystem unless absolutely necessary" -ForegroundColor Yellow
    Write-Host "4. Regularly rotate passwords for custom user accounts" -ForegroundColor Yellow
    Write-Host "5. Enable and review IIS logs regularly" -ForegroundColor Yellow
    
} catch {
    Write-Host "Error occurred: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "Stack trace: $($_.ScriptStackTrace)" -ForegroundColor Red
    exit 1
}