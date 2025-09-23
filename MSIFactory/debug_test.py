import requests
import json

# Comprehensive debug test
session = requests.Session()
print("=== MSI Factory Session Debug Test ===")

# Step 1: Login
print("\n1. Testing Login...")
login_data = {'username': 'admin', 'password': 'admin123'}
login_response = session.post('http://localhost:5000/login', data=login_data)
print(f"Login Status: {login_response.status_code}")
print(f"Login Final URL: {login_response.url}")

# Step 2: Check session state immediately after login
print("\n2. Checking Session State After Login...")
session_response = session.get('http://localhost:5000/api/session-debug')
print(f"Session Debug Status: {session_response.status_code}")
if session_response.status_code == 200:
    session_data = session_response.json()
    print(f"Session Data: {json.dumps(session_data, indent=2)}")
else:
    print(f"Session Debug Failed: {session_response.text}")

# Step 3: Try edit project POST
print("\n3. Testing Edit Project POST...")
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

# Don't follow redirects so we can see what happens
edit_response = session.post('http://localhost:5000/edit-project', data=edit_data, allow_redirects=False)
print(f"Edit Project Status: {edit_response.status_code}")
print(f"Edit Project Headers: {dict(edit_response.headers)}")

if edit_response.status_code == 302:
    print(f"REDIRECT to: {edit_response.headers.get('Location')}")
    print("This means authentication failed!")

    # Check session again to see if it changed
    print("\n4. Checking Session State After Edit Attempt...")
    session_response2 = session.get('http://localhost:5000/api/session-debug')
    if session_response2.status_code == 200:
        session_data2 = session_response2.json()
        print(f"Session Data After Edit: {json.dumps(session_data2, indent=2)}")

print("\n=== Debug Complete ===")