# WiX Toolset v6 Enterprise MSI Factory

A comprehensive enterprise-level MSI packaging solution for organizational application deployment across multiple environments.

## 🎯 Project Vision

Create a centralized **MSI Factory** system that automates the generation of Windows Installer packages for various application types across organizational environments (DEV, QA, UAT, PREPROD, PROD, SIT, DR).

## 🏗️ System Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   User Portal   │───▶│  MSI Factory     │───▶│  Environment    │
│  (Dashboard)    │    │    Engine        │    │   Deployment    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Auth System   │    │  Artifact Mgmt   │    │   Config API    │
│  (AD/Domain)    │    │    (JFrog)       │    │ (Transformation)│
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## 🚀 Core Features

### 1. Authentication & Authorization System
- **Domain Integration**: Connect to organizational Active Directory/Domain Controllers
- **Approval Workflow**: User access request system with admin approval
- **Application Verification**: Validate user access against external applications via API
- **Request Form**: Users submit access requests with AppShortKey validation

### 2. Central Dashboard
- **User Profile Management**: Profile pictures, full name management
- **Project Selection**: Multi-project support with AppShortKey association
- **Component Management**: Create and manage different component types
- **Onboarding**: First-time user project setup workflow

### 3. MSI Factory Engine
- **Multi-Environment Support**: DEV, QA, UAT, PREPROD, PROD, SIT, DR
- **Component Types**: WebApps, Websites, Windows Services, Task Schedulers
- **Framework Support**: .NET Framework, .NET Core, React, Angular
- **Automated MSI Generation**: Environment-specific package creation

### 4. Integration Layer
- **ServiceNow API**: Server name validation and dropdown population
- **JFrog Integration**: Artifact management with primary/fallback URLs
- **Configuration Transformation**: Environment-specific config generation
- **Polling System**: Automated artifact monitoring and download

## 📁 Project Structure

```
WixtoolsetCommandline/
├── README.md                          # This comprehensive guide
├── thoughts.txt                       # Development thoughts and ideas
├── TestWebAppMSI/                     # Web Application MSI Template
│   ├── Product.wxs                    # Web app infrastructure
│   ├── Files.wxs                      # Harvested web files
│   ├── generate_files.py             # Dynamic file harvesting
│   └── build.bat                      # Build automation
├── StandaloneWebSiteMSI/             # Standalone Website MSI Template
│   ├── Product.wxs                    # IIS website configuration
│   ├── Files.wxs                      # Website files
│   ├── ConfigureAppPoolWithCredentials.ps1  # AppPool setup
│   └── build.bat                      # Build automation
├── WindowsServiceMSI/                # Windows Service MSI Template
│   ├── Product.wxs                    # Service infrastructure
│   ├── Files.wxs                      # Service support files
│   ├── generate_files.py             # Service file harvesting
│   ├── ServiceFiles/                  # Sample service files
│   ├── build.bat                      # Build automation
│   └── install_elevated.bat          # Elevated installation
└── MSIFactory/                       # [Planned] Core MSI Factory Engine
    ├── config/                        # Component configurations
    ├── templates/                     # MSI templates library
    ├── engine/                        # Core factory logic
    └── integrations/                  # External API integrations
```

## 🛠️ Component Types Supported

### 1. Web Applications
- **Framework**: .NET Framework, .NET Core
- **Deployment**: Virtual Directory under IIS
- **Features**: Application Pool configuration, security settings
- **Template**: `TestWebAppMSI/`

### 2. Standalone Websites  
- **Framework**: React, Angular, Static HTML
- **Deployment**: Complete IIS Website on custom port
- **Features**: Full website configuration, SSL support
- **Template**: `StandaloneWebSiteMSI/`

### 3. Windows Services
- **Framework**: .NET Framework, .NET Core
- **Deployment**: Windows Service with configurable accounts
- **Features**: Service recovery, firewall exceptions, registry settings
- **Template**: `WindowsServiceMSI/`

### 4. Task Schedulers [Planned]
- **Framework**: PowerShell, .NET Console Applications
- **Deployment**: Windows Task Scheduler integration
- **Features**: Schedule configuration, credential management

## ⚙️ Configuration Schema

### Component Configuration Format
```json
{
  "componentId": "GUID-12345-67890",
  "appShortKey": "MYAPP",
  "componentName": "My Application Component",
  "componentType": "webapp|website|service|scheduler",
  "framework": "netframework|netcore|react|angular",
  "version": "1.0.0",
  "environments": {
    "DEV": {
      "servers": ["dev-server1.domain.com", "dev-server2.domain.com"],
      "installPath": "C:\\Apps\\MyApp\\Dev",
      "configOverrides": {
        "connectionString": "dev-connection-string",
        "apiEndpoint": "https://api-dev.company.com"
      }
    },
    "PROD": {
      "servers": ["prod-server1.domain.com", "prod-server2.domain.com"],
      "installPath": "C:\\Apps\\MyApp\\Prod",
      "configOverrides": {
        "connectionString": "prod-connection-string",
        "apiEndpoint": "https://api.company.com"
      }
    }
  },
  "artifactSources": {
    "primary": "https://jfrog.company.com/repo/myapp/",
    "fallback": [
      "https://backup-jfrog.company.com/repo/myapp/",
      "https://dr-jfrog.company.com/repo/myapp/"
    ],
    "pollingFrequency": "5m",
    "filePattern": "MyApp-*.zip"
  },
  "configTransformation": {
    "enabled": true,
    "apiEndpoint": "https://config-api.company.com/transform",
    "templateType": "web.config|appsettings.json",
    "transformationEngine": "msdeploy|custom"
  }
}
```

## 🔄 MSI Generation Workflow

### 1. Artifact Management
1. **Download**: Poll JFrog repositories for latest artifacts
2. **Validation**: Verify file integrity and version compatibility
3. **Extraction**: Unzip artifacts to temporary working directory
4. **Analysis**: Analyze file structure and dependencies

### 2. Configuration Transformation
1. **Environment Detection**: Identify target environment configuration
2. **API Integration**: Fetch environment-specific configurations
3. **Template Processing**: Apply transformations using MSDeploy/custom engine
4. **Validation**: Verify transformed configurations

### 3. MSI Generation
1. **Template Selection**: Choose appropriate WiX template based on component type
2. **File Harvesting**: Generate Files.wxs using dynamic file harvesting
3. **Product Configuration**: Generate environment-specific Product.wxs
4. **Build Process**: Compile MSI using WiX Toolset v6
5. **Validation**: Verify MSI package integrity

### 4. Multi-Environment Processing
1. **Batch Generation**: Create MSIs for all configured environments
2. **Naming Convention**: Apply consistent naming: `{AppShortKey}_{ComponentType}_{Environment}_{Version}.msi`
3. **Packaging**: Bundle MSIs with deployment documentation
4. **Distribution**: Prepare packages for deployment

## 🔌 External Integrations

### ServiceNow API Integration
- **Purpose**: Server name validation and dropdown population
- **Endpoint**: `/api/now/table/cmdb_ci_server`
- **Authentication**: OAuth 2.0 / Service Account
- **Features**: Server existence validation, environment mapping

### JFrog Artifactory Integration
- **Purpose**: Artifact management and polling
- **Authentication**: API Token / Service Account
- **Features**: Automated download, version management, failover support
- **Polling**: Configurable frequency monitoring

### Configuration API Integration  
- **Purpose**: Environment-specific configuration generation
- **Format**: RESTful API with JSON payloads
- **Features**: Template-based config generation, environment mapping
- **Security**: Encrypted configuration values, secure transmission

### External Application Verification
- **Purpose**: Validate user access to requested applications
- **Method**: API-based verification using AppShortKey
- **Response**: User authorization status and project details

## 🎭 User Roles & Permissions

### End Users
- **Access**: Submit MSI generation requests
- **Capabilities**: Select projects, configure components, monitor progress
- **Restrictions**: Limited to approved projects and environments

### Project Administrators
- **Access**: Manage project-level configurations and user approvals
- **Capabilities**: Component configuration, user access management
- **Scope**: Project-specific administration rights

### System Administrators
- **Access**: Full system configuration and management
- **Capabilities**: Global settings, integration management, user administration
- **Responsibilities**: System maintenance, security, monitoring

### Approval Managers
- **Access**: User access request review and approval
- **Capabilities**: Approve/deny access requests, manage approval workflows
- **Integration**: Connected to organizational approval systems

## 📊 Monitoring & Analytics

### Generation Metrics
- **Success Rate**: MSI generation success/failure rates
- **Performance**: Build time analytics across component types
- **Usage Statistics**: Most requested components and environments
- **Error Analysis**: Common failure patterns and resolutions

### User Analytics
- **Usage Patterns**: User activity and request frequency
- **Project Distribution**: Component distribution across projects
- **Environment Targeting**: Most commonly used environments
- **Access Patterns**: User access request patterns

## 🔒 Security Considerations

### Authentication Security
- **Multi-Factor Authentication**: Integration with organizational MFA systems
- **Session Management**: Secure session handling with timeout
- **Access Logging**: Comprehensive audit trails for all user actions

### Configuration Security
- **Encrypted Storage**: Sensitive configuration data encryption
- **Secure Transmission**: HTTPS/TLS for all API communications  
- **Access Control**: Role-based access to sensitive configurations

### MSI Package Security
- **Code Signing**: Digital signatures for generated MSI packages
- **Integrity Validation**: Hash verification for downloaded artifacts
- **Secure Distribution**: Encrypted channels for MSI distribution

## 🚀 Implementation Phases

### Phase 1: MSI Factory Core Engine ⏳
**Status**: In Development
**Timeline**: Current Phase
**Deliverables**:
- [x] WiX v6 Templates (WebApp, Website, Service)
- [x] Dynamic File Harvesting System
- [ ] Component Configuration Schema
- [ ] Multi-Environment MSI Generation
- [ ] Artifact Management System

### Phase 2: Integration Layer 📋
**Status**: Planned
**Timeline**: Next Phase
**Deliverables**:
- [ ] ServiceNow API Integration
- [ ] JFrog Artifactory Integration
- [ ] Configuration Transformation Engine
- [ ] External Application Verification

### Phase 3: User Portal & Dashboard 🎨
**Status**: Planned  
**Timeline**: Future Phase
**Deliverables**:
- [ ] Authentication System
- [ ] User Dashboard
- [ ] Component Management Interface
- [ ] Request Approval Workflow

### Phase 4: Advanced Features 🔧
**Status**: Future
**Timeline**: Final Phase
**Deliverables**:
- [ ] Advanced Analytics
- [ ] Automated Testing Integration
- [ ] Custom Template Designer
- [ ] Enterprise Monitoring

## 🛡️ Quality Assurance

### Testing Strategy
- **Unit Testing**: Individual component testing
- **Integration Testing**: API and external system integration
- **End-to-End Testing**: Complete workflow validation
- **Security Testing**: Vulnerability assessment and penetration testing

### Validation Framework
- **MSI Validation**: Package integrity and installation testing
- **Configuration Validation**: Environment-specific configuration verification
- **Performance Testing**: Load testing for concurrent MSI generation
- **User Acceptance Testing**: End-user workflow validation

## 📚 Documentation Standards

### Code Documentation
- **Inline Comments**: Comprehensive code commenting
- **API Documentation**: RESTful API documentation with examples
- **Configuration Guides**: Environment setup and configuration guides
- **Troubleshooting Guides**: Common issues and resolution steps

### User Documentation  
- **User Manuals**: Step-by-step user guides
- **Administrator Guides**: System administration documentation
- **Integration Guides**: External system integration instructions
- **FAQ Documentation**: Frequently asked questions and answers

## 🔧 Development Environment

### Prerequisites
- **WiX Toolset v6.0.2+**: Windows Installer development framework
- **Python 3.8+**: Core scripting and automation
- **PowerShell 5.1+**: Windows automation and configuration
- **Git**: Version control and collaboration
- **Visual Studio Code**: Development environment

### Development Tools
- **WiX Extensions**: Util, Firewall, UI extensions
- **Python Libraries**: requests, json, pathlib, zipfile
- **PowerShell Modules**: WebAdministration, ActiveDirectory
- **Build Tools**: MSBuild, MSDeploy

## 🤝 Contributing

### Contribution Guidelines
1. **Code Standards**: Follow established coding conventions
2. **Testing Requirements**: Include tests for new features
3. **Documentation**: Update documentation for changes
4. **Security Review**: Security assessment for sensitive changes

### Development Workflow
1. **Feature Branches**: Create feature branches for development
2. **Code Review**: Peer review for all changes
3. **Testing**: Comprehensive testing before merge
4. **Deployment**: Staged deployment process

## 📞 Support & Contact

### Development Team
- **Architect**: MSI Factory System Design
- **Developers**: Core engine and integration development
- **QA Team**: Quality assurance and testing
- **DevOps**: Infrastructure and deployment

### Support Channels
- **Documentation**: Comprehensive guides and references
- **Issue Tracking**: GitHub Issues for bug reports and feature requests
- **Knowledge Base**: Internal knowledge sharing platform
- **Training**: User and administrator training programs

---

## 🎯 Current Focus: MSI Factory Core Engine

We are currently developing the **MSI Factory Core Engine** that will serve as the foundation for the entire system. This includes:

1. **Component Configuration System** - JSON-based component definitions
2. **Artifact Management** - JFrog integration with failover support
3. **Multi-Environment MSI Generation** - Automated environment-specific packaging
4. **Template Library** - Extensible WiX template system

**Next Steps**: Complete the core engine development and begin integration layer implementation.

---

*This document serves as the comprehensive planning and development guide for the WiX Toolset v6 Enterprise MSI Factory project.*