# MSI Factory System Architecture

## 📊 System Components Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    MSI FACTORY MAIN                          │
│                      (main.py)                               │
│                                                              │
│  Entry Point for Complete MSI Factory System                │
│  - Routes all web requests                                   │
│  - Manages user sessions                                     │
│  - Coordinates between all components                        │
│  - Multi-component project management                       │
└──────────────┬──────────────────────────┬───────────────────┘
               │                          │
               ▼                          ▼
┌──────────────────────────┐  ┌──────────────────────────────┐
│   AUTHENTICATION MODULE  │  │    MSI GENERATION ENGINE     │
│   (auth/simple_auth.py)  │  │  (engine/msi_factory_core)   │
│                          │  │                              │
│  • Domain-based Login    │  │  • Multi-Component Support   │
│  • Role-based Access     │  │  • Download Artifacts        │
│  • Project Permissions   │  │  • Dynamic Environments     │
│  • Admin Approval        │  │  • Generate WiX Files        │
│  • User Management       │  │  • Build Component MSIs      │
└──────────────────────────┘  └──────────────────────────────┘
               │                          │
               ▼                          ▼
┌──────────────────────────────────────────────────────────┐
│                 DATABASE LAYER                            │
│                 (MS SQL Server)                          │
│                                                           │
│  • users                    - User accounts & roles      │
│  • projects                 - Project definitions        │
│  • components              - Multi-component support     │
│  • component_environments  - Environment configurations  │
│  • project_environments    - Environment definitions     │
│  • user_projects           - User-project permissions    │
│  • msi_builds              - Build history & status      │
│  • system_logs             - Comprehensive audit trail   │
│  • user_sessions           - Active session management   │
└───────────────────────────────────────────────────────────┘
```

## 🔄 Request Flow

### 1. **User Authentication Flow**
```
User → Domain Login → main.py → auth/simple_auth.py → Database Verification → Session Creation → Project Dashboard
```

### 2. **Multi-Component Project Creation Flow**
```
Admin → Add Project → Define Components → Configure Environments → Database Storage → Project Available
```

### 3. **MSI Generation Flow**
```
User → Select Project → Choose Components → Select Environments → engine/msi_factory_core.py → Generate Component MSIs
```

### 4. **Environment Management Flow**
```
Admin → Project Settings → Add/Remove Environments (DEV1, QA2, PROD_USA, etc.) → Database Update → Available for MSI Generation
```

### 5. **User Access Control Flow**
```
New User → Access Request → Admin Approval → Project Assignment → Component Access → MSI Generation Rights
```

## 📁 Complete File Structure

```
MSIFactory/
│
├── main.py                    ← 🎯 MAIN APPLICATION (Start here!)
├── config.py                 ← Simple configuration management
├── logger.py                 ← Simplified logging system
│
├── auth/                      ← Authentication Module
│   └── simple_auth.py        ← Authentication with database integration
│
├── database/                  ← Database Layer
│   ├── schema.sql            ← Complete MS SQL Server schema (v2.0)
│   └── connection_manager.py ← Database connections (no pooling)
│
├── webapp/                    ← Web Application UI
│   ├── templates/            ← HTML templates
│   │   ├── base_sidebar.html ← Main layout template
│   │   ├── add_project.html  ← Multi-component project creation
│   │   ├── edit_project.html ← Project/component editing
│   │   ├── project_management.html ← Project overview
│   │   ├── user_management.html    ← User administration
│   │   ├── dashboard.html    ← Main user dashboard
│   │   └── login.html        ← Authentication interface
│   └── static/               ← CSS, JS, Bootstrap assets
│
├── engine/                    ← MSI Generation Engine
│   ├── msi_factory_core.py   ← Advanced multi-component MSI generation
│   └── simple_msi_factory.py ← Basic MSI generation
│
├── config/                    ← Component Configurations & Validation
│   ├── config-validator.py   ← JSON schema validation
│   ├── component-schema.json ← Configuration schema
│   └── *.json                ← Component configurations
│
├── samples/                   ← Sample Configurations
│   ├── webapp-sample.json    ← Web application example
│   ├── service-sample.json   ← Windows service example
│   └── website-sample.json   ← Website example
│
├── logs/                      ← Application Logs
│   ├── system.log           ← System operations
│   ├── access.log           ← User access logs
│   ├── security.log         ← Security events
│   └── error.log            ← Error tracking
│
├── output/                    ← Generated MSI Files
│   └── (Generated component MSI packages)
│
├── batch_files/              ← Startup Scripts
│   ├── start.bat            ← Development server with browser
│   ├── start_dev.bat        ← Development without warnings
│   ├── start_production.bat ← Production Waitress server
│   ├── stop.bat             ← Stop all processes
│   └── restart.bat          ← Restart with browser
│
└── Documentation/
    ├── ARCHITECTURE.md       ← This file
    ├── PROJECT_STRUCTURE.md  ← Project organization
    └── LOGGING.md           ← Logging system details
```

## 🚀 How to Run the Complete System

### Recommended: Use Batch Files (Production Ready)
```cmd
# Start development server with browser auto-launch
start.bat

# Start development server without warnings
start_dev.bat

# Start production server (Waitress WSGI)
start_production.bat

# Stop all MSI Factory processes
stop.bat

# Restart with browser launch
restart.bat
```

### Manual Startup Options
```bash
# Option 1: Main Application (Development)
cd C:\Git\WixtoolsetCommandline\MSIFactory
py main.py

# Option 2: Production Server (Waitress)
cd C:\Git\WixtoolsetCommandline\MSIFactory
waitress-serve --host=127.0.0.1 --port=5000 main:app
```

### Database Setup
```sql
# Execute the complete schema on MS SQL Server
sqlcmd -i database/schema.sql

# Or use SQL Server Management Studio to run:
# database/schema.sql
```

## 🔑 Key Features by Module

### **main.py** (Main Application)
- Multi-component project management
- Dynamic environment configuration
- User session management
- RESTful API endpoints
- Integrated authentication and MSI generation

### **database/schema.sql** (Database Schema v2.0)
- Complete MS SQL Server schema
- Multi-component project support
- Dynamic environment management
- User access control
- Comprehensive audit trails

### **webapp/templates/add_project.html** (Project Creation)
- Dynamic component addition
- Custom environment configuration
- JFrog Artifactory integration
- Server region management
- Real-time validation

### **auth/simple_auth.py** (Authentication System)
- Database-integrated authentication
- Role-based access control
- Project-level permissions
- Session management with database tracking

### **engine/msi_factory_core.py** (MSI Generation Engine)
- Multi-component MSI generation
- Environment-specific configurations
- Artifact source management
- WiX template processing

## 🎯 System Capabilities

### 1. **Multi-Component Project Management**
   - Support for mixed technology stacks
   - Component types: WebApp, API, Service, Scheduler, Website, Desktop
   - Frameworks: .NET Framework, .NET Core, React, Angular, Vue, Python, Static
   - Individual component MSI generation

### 2. **Dynamic Environment Configuration**
   - Unlimited custom environments (DEV1, DEV2, QA1, QA2, PROD_USA, PROD_EMEA, etc.)
   - Region-based server grouping
   - Environment-specific component configurations
   - Server list management per environment

### 3. **Advanced Authentication & Authorization**
   - Domain-based Windows authentication
   - Role-based access (Admin, User)
   - Project-level permissions
   - Session tracking with database persistence

### 4. **Enterprise-Grade Database Integration**
   - MS SQL Server with Windows Authentication
   - Comprehensive audit logging
   - Database triggers for automatic updates
   - Performance-optimized indexing

### 5. **Artifact Management Integration**
   - JFrog Artifactory support with credentials
   - UNC network path support
   - HTTP/HTTPS artifact sources
   - Component-specific artifact URLs

## 🔄 Integration Points

- **MS SQL Server** → Primary data persistence
- **Windows Authentication** → Domain-based security
- **JFrog Artifactory** → Artifact repository integration
- **UNC Network Shares** → File-based artifact storage
- **Bootstrap 5.1.3** → Modern responsive UI
- **WiX Toolset v6** → MSI package generation

## 🗄️ Database Architecture

### Core Tables:
- **users** → User accounts and authentication
- **projects** → Project definitions with GUIDs
- **components** → Multi-component support with GUIDs
- **component_environments** → Environment-specific component settings
- **project_environments** → Available environments per project
- **user_projects** → Project access permissions
- **msi_builds** → Build history and status tracking
- **system_logs** → Comprehensive audit trail

### Key Features:
- GUID-based unique identification
- Foreign key constraints for data integrity
- Database triggers for automatic updates
- Performance indexes for fast queries
- Comprehensive logging and audit trails

---

**The system provides enterprise-grade multi-component MSI generation with dynamic environment support, comprehensive database integration, and modern web UI for complete project lifecycle management.**