import requests

# Login first
session = requests.Session()
login_data = {'username': 'admin', 'password': 'admin123'}
login_response = session.post('http://localhost:5000/login', data=login_data)

# Test direct submission to edit-project
test_data = {
    'project_id': '16',
    'project_name': 'Demo E-commerce Platform',
    'project_key': 'DEMO',
    'description': 'Test',
    'project_type': 'webapp',
    'owner_team': 'Test Team',
    'color_primary': '#2c3e50',
    'color_secondary': '#3498db',
    'status': 'active',
    'new_component_guid_4': 'TEST-1234-5678-9999',
    'new_component_name_4': 'Test Component From Script',
    'new_component_type_4': 'webapp',
    'new_component_framework_4': 'react',
    'new_component_app_name_4': 'Test App',
    'new_component_version_4': '1.0.0.0',
    'new_component_manufacturer_4': 'Test Company',
    'new_component_target_server_4': 'TESTSERVER',
    'new_component_install_folder_4': 'C:\\test',
    'new_component_iis_website_4': 'Default Web Site',
    'new_component_app_pool_4': 'DefaultAppPool',
    'new_component_port_4': '80',
    'new_component_artifact_4': ''
}

response = session.post('http://localhost:5000/edit-project', data=test_data)
print(f"Status Code: {response.status_code}")
print(f"Response URL: {response.url}")
print("Response Headers:", response.headers)