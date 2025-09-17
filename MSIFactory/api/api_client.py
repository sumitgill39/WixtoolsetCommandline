"""
API Client Module
Client library for interacting with MSI Factory API
Can be used by main.py or any other module
"""

import requests
import logging
from typing import Dict, List, Optional, Tuple

class MSIFactoryAPIClient:
    """Client for MSI Factory API"""
    
    def __init__(self, base_url: str = "http://localhost:5001/api"):
        """
        Initialize API client
        
        Args:
            base_url: Base URL of the API server
        """
        self.base_url = base_url
        self.logger = logging.getLogger(__name__)
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json'
        })
    
    def _make_request(self, method: str, endpoint: str, data: Dict = None, params: Dict = None) -> Dict:
        """
        Make HTTP request to API
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint
            data: Request body data
            params: Query parameters
        
        Returns:
            Response JSON
        """
        url = f"{self.base_url}{endpoint}"
        
        try:
            response = self.session.request(
                method=method,
                url=url,
                json=data,
                params=params
            )
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.ConnectionError:
            self.logger.error(f"Cannot connect to API at {url}")
            return {
                'success': False,
                'message': f'Cannot connect to API server at {self.base_url}'
            }
        except requests.exceptions.HTTPError as e:
            self.logger.error(f"HTTP error: {e}")
            try:
                return response.json()
            except:
                return {
                    'success': False,
                    'message': str(e)
                }
        except Exception as e:
            self.logger.error(f"Request error: {e}")
            return {
                'success': False,
                'message': str(e)
            }
    
    # ==================== PROJECT METHODS ====================
    
    def get_all_projects(self) -> Dict:
        """Get all projects"""
        return self._make_request('GET', '/projects')
    
    def get_project(self, project_id: int) -> Dict:
        """Get project by ID"""
        return self._make_request('GET', f'/projects/{project_id}')
    
    def get_project_by_key(self, project_key: str) -> Dict:
        """Get project by key"""
        return self._make_request('GET', f'/projects/key/{project_key}')
    
    def create_project(self, project_data: Dict) -> Dict:
        """Create new project"""
        return self._make_request('POST', '/projects', data=project_data)
    
    def update_project(self, project_id: int, project_data: Dict) -> Dict:
        """Update existing project"""
        return self._make_request('PUT', f'/projects/{project_id}', data=project_data)
    
    def delete_project(self, project_id: int, hard_delete: bool = False) -> Dict:
        """Delete project"""
        params = {'hard': 'true'} if hard_delete else {}
        return self._make_request('DELETE', f'/projects/{project_id}', params=params)
    
    # ==================== ENVIRONMENT METHODS ====================
    
    def get_project_environments(self, project_id: int) -> Dict:
        """Get all environments for a project"""
        return self._make_request('GET', f'/projects/{project_id}/environments')
    
    def add_environment(self, project_id: int, env_name: str, description: str = '') -> Dict:
        """Add environment to project"""
        data = {
            'environment_name': env_name,
            'description': description
        }
        return self._make_request('POST', f'/projects/{project_id}/environments', data=data)
    
    def remove_environment(self, project_id: int, env_name: str) -> Dict:
        """Remove environment from project"""
        return self._make_request('DELETE', f'/projects/{project_id}/environments/{env_name}')
    
    # ==================== COMPONENT METHODS ====================
    
    def get_all_components(self, project_id: int = None) -> Dict:
        """Get all components or components for specific project"""
        params = {'project_id': project_id} if project_id else {}
        return self._make_request('GET', '/components', params=params)
    
    def get_component(self, component_id: int) -> Dict:
        """Get component by ID"""
        return self._make_request('GET', f'/components/{component_id}')
    
    def get_component_by_key(self, component_key: str) -> Dict:
        """Get component by key"""
        return self._make_request('GET', f'/components/key/{component_key}')
    
    def create_component(self, component_data: Dict) -> Dict:
        """Create new component"""
        return self._make_request('POST', '/components', data=component_data)
    
    def update_component(self, component_id: int, component_data: Dict) -> Dict:
        """Update existing component"""
        return self._make_request('PUT', f'/components/{component_id}', data=component_data)
    
    def delete_component(self, component_id: int, hard_delete: bool = False) -> Dict:
        """Delete component"""
        params = {'hard': 'true'} if hard_delete else {}
        return self._make_request('DELETE', f'/components/{component_id}', params=params)
    
    # ==================== UTILITY METHODS ====================
    
    def check_health(self) -> bool:
        """Check if API is healthy"""
        try:
            response = self._make_request('GET', '/health')
            return response.get('status') == 'healthy'
        except:
            return False
    
    def get_api_status(self) -> Dict:
        """Get API status information"""
        return self._make_request('GET', '/status')


# ==================== CONVENIENCE FUNCTIONS ====================

def get_api_client(base_url: str = None) -> MSIFactoryAPIClient:
    """
    Get configured API client instance
    
    Args:
        base_url: Optional base URL override
    
    Returns:
        MSIFactoryAPIClient instance
    """
    import os
    
    if base_url is None:
        # Check environment variable first
        base_url = os.environ.get('MSI_FACTORY_API_URL', 'http://localhost:5001/api')
    
    return MSIFactoryAPIClient(base_url)


# Example usage for testing
if __name__ == "__main__":
    # Create API client
    client = get_api_client()
    
    # Check health
    print("Checking API health...")
    if client.check_health():
        print("✓ API is healthy")
    else:
        print("✗ API is not responding")
    
    # Get API status
    print("\nGetting API status...")
    status = client.get_api_status()
    print(f"Status: {status}")
    
    # Get all projects
    print("\nGetting all projects...")
    response = client.get_all_projects()
    if response.get('success'):
        projects = response.get('data', [])
        print(f"Found {len(projects)} projects")
        for project in projects:
            print(f"  - {project['project_name']} ({project['project_key']})")
    else:
        print(f"Error: {response.get('message')}")
    
    # Get all components
    print("\nGetting all components...")
    response = client.get_all_components()
    if response.get('success'):
        components = response.get('data', [])
        print(f"Found {len(components)} components")
        for component in components:
            print(f"  - {component['component_name']} ({component['component_key']}) - Project: {component.get('project_name', 'N/A')}")
    else:
        print(f"Error: {response.get('message')}")
    
    # Example: Create a project
    # print("\nCreating test project...")
    # new_project = {
    #     'project_name': 'Test Project',
    #     'project_key': 'TEST001',
    #     'description': 'Test project created via API',
    #     'project_type': 'WebApp',
    #     'owner_team': 'Development',
    #     'created_by': 'api_test'
    # }
    # response = client.create_project(new_project)
    # print(f"Create response: {response}")
    
    # Example: Create a component
    # print("\nCreating test component...")
    # new_component = {
    #     'component_name': 'Test Component',
    #     'component_key': 'TESTCOMP001',
    #     'description': 'Test component created via API',
    #     'component_type': 'File',
    #     'file_path': 'C:\\test\\file.exe',
    #     'install_path': 'C:\\Program Files\\TestApp\\',
    #     'project_id': 1
    # }
    # response = client.create_component(new_component)
    # print(f"Create component response: {response}")