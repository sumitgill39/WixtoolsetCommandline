import requests

# Simple test to avoid encoding issues
session = requests.Session()

# Login
login_data = {'username': 'admin', 'password': 'admin123'}
login_response = session.post('http://localhost:5000/login', data=login_data)
print(f"Login Status: {login_response.status_code}")

# Check session debug endpoint
session_response = session.get('http://localhost:5000/api/session-debug')
print(f"Session Debug Status: {session_response.status_code}")

if session_response.status_code == 200:
    import json
    session_data = session_response.json()
    print("Session Debug SUCCESS!")
    print(f"Username: {session_data.get('username')}")
    print(f"Role: {session_data.get('role')}")
    print(f"Is Admin: {session_data.get('is_admin')}")
    print(f"Has Username: {session_data.get('has_username')}")
else:
    print("Session Debug endpoint NOT FOUND - still using old code!")

# Try edit project without redirects
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

edit_response = session.post('http://localhost:5000/edit-project', data=edit_data, allow_redirects=False)
print(f"Edit Project Status: {edit_response.status_code}")
if edit_response.status_code == 302:
    print(f"REDIRECTED to: {edit_response.headers.get('Location')}")
    print("Authentication failed!")
elif edit_response.status_code == 200:
    print("SUCCESS: Edit project processed!")