# MSI Factory System Architecture

## 📊 System Components Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    MSI FACTORY MAIN                          │
│                      (main.py)                               │
│                                                              │
│  Entry Point for Complete MSI Factory System                │
│  - Routes all requests                                      │
│  - Manages sessions                                         │
│  - Coordinates between components                           │
└──────────────┬──────────────────────────┬───────────────────┘
               │                          │
               ▼                          ▼
┌──────────────────────────┐  ┌──────────────────────────────┐
│   AUTHENTICATION MODULE  │  │    MSI GENERATION ENGINE     │
│   (auth/simple_auth.py)  │  │  (engine/simple_msi_factory) │
│                          │  │                              │
│  • User Login            │  │  • Download Artifacts        │
│  • Access Requests       │  │  • Extract Files             │
│  • Admin Approval        │  │  • Config Transformation     │
│  • Session Management    │  │  • Generate WiX Files        │
│  • User Dashboard        │  │  • Build MSI Packages        │
└──────────────────────────┘  └──────────────────────────────┘
               │                          │
               ▼                          ▼
┌──────────────────────────────────────────────────────────┐
│                    DATA LAYER                             │
│                                                           │
│  • database/users.json       - User accounts             │
│  • database/applications.json - Application registry     │
│  • database/access_requests.json - Pending requests      │
│  • config/*.json             - Component configurations   │
└───────────────────────────────────────────────────────────┘
```

## 🔄 Request Flow

### 1. **User Login Flow**
```
User → main.py → auth/simple_auth.py → Verify → Session → Dashboard
```

### 2. **MSI Generation Flow**
```
User → main.py → Select App → Configure → engine/simple_msi_factory.py → Generate MSI
```

### 3. **Admin Approval Flow**
```
New User → Access Request → Admin Panel → Approve → User Login Enabled
```

## 📁 Complete File Structure

```
MSIFactory/
│
├── main.py                    ← 🎯 MAIN APPLICATION (Start here!)
│
├── auth/                      ← Authentication Module
│   ├── simple_auth.py        ← Authentication logic
│   ├── templates/            ← HTML templates for auth
│   └── database/             ← User/app JSON databases
│
├── engine/                    ← MSI Generation Engine
│   ├── simple_msi_factory.py ← MSI generation logic
│   └── msi_factory_core.py   ← Advanced MSI features
│
├── webapp/                    ← Main Web Application
│   ├── templates/            ← HTML templates for main app
│   └── static/               ← CSS, JS, images
│
├── config/                    ← Component Configurations
│   ├── component-schema.json ← Configuration schema
│   └── *.json                ← Component configs
│
├── samples/                   ← Sample Configurations
│   ├── webapp-sample.json
│   ├── service-sample.json
│   └── website-sample.json
│
├── templates/                 ← WiX Templates
│   └── (WiX template files)
│
└── output/                    ← Generated MSI Files
    └── (Generated MSI packages)
```

## 🚀 How to Run the Complete System

### Option 1: Run Main Application (Includes Everything)
```bash
cd C:\Git\WixtoolsetCommandline\MSIFactory
py main.py
```

### Option 2: Run Individual Components (Development/Testing)
```bash
# Just Authentication
cd auth
py simple_auth.py

# Just MSI Engine
cd engine
py simple_msi_factory.py config.json
```

## 🔑 Key Features by Module

### **main.py** (Main Application)
- Central routing system
- Combines all modules
- API endpoints
- Web interface coordination

### **auth/simple_auth.py** (Authentication Only)
- User authentication
- Access request workflow
- Admin approval system
- Session management

### **engine/simple_msi_factory.py** (MSI Generation Only)
- Artifact download
- Configuration transformation
- WiX file generation
- MSI building

## 🎯 System Capabilities

1. **Authentication & Authorization**
   - Domain-based login
   - Role-based access control
   - Application-level permissions

2. **MSI Generation**
   - Multi-environment support (DEV, QA, PROD, etc.)
   - Component types (WebApp, Service, Website)
   - Configuration transformation
   - Batch generation

3. **Administration**
   - User management
   - Access request approval
   - Application registry
   - System monitoring

## 🔄 Integration Points

- **ServiceNow API** → Server validation
- **JFrog Artifactory** → Artifact management
- **Configuration API** → Environment configs
- **Active Directory** → User authentication (future)

---

**The system is modular**: Each component can run independently for testing, but `main.py` brings everything together for the complete MSI Factory experience!