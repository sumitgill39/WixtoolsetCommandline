import requests
import sys

# Simple test script
session = requests.Session()

# Login first
login_data = {'username': 'admin', 'password': 'admin123'}
login_response = session.post('http://localhost:5000/login', data=login_data)
print(f"Login Status: {login_response.status_code}")

# Test the new API test endpoint
test_data = {'test_field': 'test_value', 'project_id': '16'}
test_response = session.post('http://localhost:5000/api/test-submit', data=test_data)
print(f"Test Submit Status: {test_response.status_code}")

if test_response.status_code == 200:
    print("SUCCESS: Test endpoint is working!")
else:
    print(f"FAILED: Status {test_response.status_code}")

# Test the add component API
component_data = {
    'project_id': '16',
    'component_name': 'API Test Component',
    'component_type': 'webapp',
    'component_framework': 'react',
    'component_app_name': 'API Test App',
    'component_version': '1.0.0.0',
    'component_manufacturer': 'Test Company',
    'component_target_server': 'TESTSERVER',
    'component_install_folder': 'C:\\test',
    'component_iis_website': 'Default Web Site',
    'component_app_pool': 'DefaultAppPool',
    'component_port': '80'
}

component_response = session.post('http://localhost:5000/api/add-component', data=component_data)
print(f"Add Component Status: {component_response.status_code}")

# Test the original edit-project endpoint
edit_data = {
    'project_id': '16',
    'project_name': 'Demo E-commerce Platform',
    'project_key': 'DEMO',
    'description': 'Test',
    'project_type': 'webapp',
    'owner_team': 'Test Team',
    'color_primary': '#2c3e50',
    'color_secondary': '#3498db',
    'status': 'active'
}

edit_response = session.post('http://localhost:5000/edit-project', data=edit_data)
print(f"Edit Project Status: {edit_response.status_code}")
print(f"Edit Project Final URL: {edit_response.url}")
print(f"Edit Project Response Length: {len(edit_response.text)}")
print(f"Edit Project Redirects: {edit_response.history}")

# If redirected, that explains why no EDIT_PROJECT_START log appears
if edit_response.history:
    print("EDIT PROJECT WAS REDIRECTED - this means user isn't admin or not logged in properly!")