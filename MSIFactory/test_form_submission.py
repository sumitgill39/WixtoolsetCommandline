import requests

# Test script to verify form submission works
session = requests.Session()

# Login first
login_data = {'username': 'admin', 'password': 'admin123'}
login_response = session.post('http://localhost:5000/login', data=login_data)
print(f"Login Status: {login_response.status_code}")

# Test 1: Simple API test endpoint
test_data = {'test_field': 'test_value', 'project_id': '16'}
test_response = session.post('http://localhost:5000/api/test-submit', data=test_data)
print(f"Test Submit Status: {test_response.status_code}")
print(f"Test Submit Response: {test_response.text}")

# Test 2: Test add component API
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
print(f"Add Component Response: {component_response.text}")

# Test 3: Try the original edit-project endpoint with minimal data
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
print(f"Edit Project URL: {edit_response.url}")