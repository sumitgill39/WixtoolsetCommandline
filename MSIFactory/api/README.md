# MSI Factory Independent API System

This directory contains a completely independent REST API system for MSI Factory database operations.

## Architecture

```
api/
├── __init__.py              # Package initialization
├── api_server.py           # Standalone Flask REST API server
├── api_client.py           # Python client library for API
├── project_api.py          # Project management API logic
├── component_api.py        # Component management API logic
└── README.md              # This documentation
```

## Features

### ✅ **Completely Independent**
- Runs as a separate Flask server (port 5001)
- Can be deployed independently from main application
- Uses its own database connections
- RESTful API design with JSON responses

### ✅ **Comprehensive Project Management**
- Create, Read, Update, Delete (CRUD) operations for projects
- Environment management per project
- Soft delete (archive) and hard delete options
- Full validation and error handling

### ✅ **Complete Component Management**
- Full CRUD operations for components
- Component-to-project relationships
- Support for file paths, install paths, GUIDs
- Component type classification (File, Registry, etc.)
- Project-specific component filtering
- Soft delete and hard delete options

### ✅ **Production Ready**
- Proper error handling and logging
- CORS support for cross-origin requests
- Health check endpoints
- Environment variable configuration

## Quick Start

### 1. Start the API Server

```bash
# Method 1: Direct execution
cd MSIFactory
python start_api.py

# Method 2: Using module
cd MSIFactory/api
python api_server.py

# Method 3: With custom port
API_PORT=8000 python start_api.py
```

### 2. Test the API

```bash
# Check health
curl http://localhost:5001/api/health

# Get all projects
curl http://localhost:5001/api/projects

# Get specific project
curl http://localhost:5001/api/projects/1

# Create new project
curl -X POST http://localhost:5001/api/projects \
  -H "Content-Type: application/json" \
  -d '{
    "project_name": "My New Project",
    "project_key": "MNP001",
    "description": "A test project",
    "project_type": "WebApp",
    "owner_team": "Development"
  }'
```

### 3. Use Python Client

```python
from api.api_client import get_api_client

# Initialize client
client = get_api_client()

# Check API health
if client.check_health():
    print("API is healthy!")

# Get all projects
response = client.get_all_projects()
if response['success']:
    projects = response['data']
    print(f"Found {len(projects)} projects")

# Create a project
new_project = {
    'project_name': 'Test Project',
    'project_key': 'TEST001',
    'description': 'Created via API',
    'project_type': 'WebApp',
    'owner_team': 'Development'
}
response = client.create_project(new_project)
print(response['message'])

# Delete a project
response = client.delete_project(project_id=1, hard_delete=True)
print(response['message'])

# Get all components
response = client.get_all_components()
if response['success']:
    components = response['data']
    print(f"Found {len(components)} components")

# Get components for specific project
response = client.get_all_components(project_id=1)
if response['success']:
    project_components = response['data']
    print(f"Found {len(project_components)} components for project")

# Create a component
new_component = {
    'component_name': 'Application Executable',
    'component_key': 'APP_EXE_001',
    'description': 'Main application executable file',
    'component_type': 'File',
    'file_path': 'C:\\MyApp\\app.exe',
    'install_path': 'C:\\Program Files\\MyApp\\',
    'guid': '{12345678-1234-1234-1234-123456789012}',
    'project_id': 1
}
response = client.create_component(new_component)
print(response['message'])

# Update a component
update_data = {
    'description': 'Updated description',
    'file_path': 'C:\\MyApp\\v2\\app.exe'
}
response = client.update_component(component_id=1, component_data=update_data)
print(response['message'])

# Delete a component
response = client.delete_component(component_id=1, hard_delete=False)  # Soft delete
print(response['message'])
```

## API Endpoints

### Projects

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/projects` | Get all projects |
| `POST` | `/api/projects` | Create new project |
| `GET` | `/api/projects/{id}` | Get specific project |
| `PUT` | `/api/projects/{id}` | Update project |
| `DELETE` | `/api/projects/{id}` | Delete project |
| `GET` | `/api/projects/key/{key}` | Get project by key |

### Environments

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/projects/{id}/environments` | Get project environments |
| `POST` | `/api/projects/{id}/environments` | Add environment |
| `DELETE` | `/api/projects/{id}/environments/{name}` | Remove environment |

### Components

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/components` | Get all components (optional `?project_id=` filter) |
| `POST` | `/api/components` | Create new component |
| `GET` | `/api/components/{id}` | Get specific component |
| `PUT` | `/api/components/{id}` | Update component |
| `DELETE` | `/api/components/{id}` | Delete component |
| `GET` | `/api/components/key/{key}` | Get component by key |

### Utility

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/health` | Health check |
| `GET` | `/api/status` | API status and info |

## Configuration

### Environment Variables

```bash
# API server configuration
export API_PORT=5001              # API server port (default: 5001)
export API_DEBUG=false            # Debug mode (default: false)
export API_SECRET_KEY=your_key     # Flask secret key

# Database configuration (uses existing database settings)
export MSI_FACTORY_API_URL=http://localhost:5001/api  # API base URL
```

## Integration with Main Application

The main Flask application (`main.py`) automatically tries to use the API:

1. **API First**: Attempts to connect to API server
2. **Graceful Fallback**: Falls back to file-based system if API unavailable
3. **Transparent Operation**: UI works the same regardless of backend

### Main App Integration

```python
# In main.py
from api.api_client import get_api_client

# Initialize API client
api_client = get_api_client()

# Use in route handlers
@app.route('/delete-project', methods=['POST'])
def delete_project():
    if api_client:
        # Use API
        response = api_client.delete_project(project_id)
        success = response.get('success', False)
        message = response.get('message', '')
    else:
        # Fallback to file system
        success, message = auth_system.delete_project(project_id)
```

## Production Deployment

### Option 1: Separate Services
```bash
# Terminal 1: Start API server
python start_api.py

# Terminal 2: Start main application
python main.py
```

### Option 2: Docker Compose
```yaml
version: '3.8'
services:
  api:
    build: .
    command: python start_api.py
    ports:
      - "5001:5001"
    environment:
      - API_PORT=5001
      
  web:
    build: .
    command: python main.py
    ports:
      - "5000:5000"
    environment:
      - MSI_FACTORY_API_URL=http://api:5001/api
    depends_on:
      - api
```

### Option 3: Load Balancer
```
┌─────────────┐    ┌─────────────┐
│   Web App   │    │   Web App   │
│  (Port 5000)│    │  (Port 5002)│
└─────────────┘    └─────────────┘
       │                  │
       └──────────────────┘
              │
    ┌─────────────────┐
    │  Load Balancer  │
    └─────────────────┘
              │
    ┌─────────────────┐
    │   API Server    │
    │   (Port 5001)   │
    └─────────────────┘
```

## Benefits of Independent API

1. **Scalability**: API can be scaled independently
2. **Microservices**: Clean separation of concerns
3. **Multiple Clients**: Web app, mobile app, CLI tools can all use same API
4. **Technology Freedom**: API could be rewritten in different language
5. **Testing**: API can be tested independently
6. **Deployment**: Different deployment strategies for API vs UI

## Testing

```bash
# Test API health
python -c "from api.api_client import get_api_client; print('Healthy' if get_api_client().check_health() else 'Unhealthy')"

# Run API client test
cd api
python api_client.py

# Manual API testing
curl -X GET http://localhost:5001/api/status

# Test component endpoints
curl -X GET http://localhost:5001/api/components
curl -X GET "http://localhost:5001/api/components?project_id=1"
curl -X GET http://localhost:5001/api/components/1
curl -X POST http://localhost:5001/api/components \
  -H "Content-Type: application/json" \
  -d '{
    "component_name": "Test Component",
    "component_key": "TEST_COMP_001",
    "description": "A test component",
    "component_type": "File",
    "file_path": "C:\\test\\file.exe",
    "install_path": "C:\\Program Files\\TestApp\\",
    "project_id": 1
  }'
```

This independent API system provides a robust, scalable foundation for the MSI Factory application while maintaining backward compatibility with existing functionality.