#!/usr/bin/env python3
"""
MSI Factory - Main Application
This is the main entry point that combines authentication and MSI generation
"""

import os
import sys
import json
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from sqlalchemy import text

# Import our authentication system
sys.path.append('auth')
from simple_auth import SimpleAuth

# Import database connection
sys.path.append('database')
from database.connection_manager import execute_with_retry, get_db_connection_info

# Import our MSI generation engine
sys.path.append('engine')

# Import logging module
from logger import get_logger, log_info, log_error, log_security

app = Flask(__name__, template_folder='webapp/templates', static_folder='webapp/static')
app.secret_key = 'msi_factory_main_secret_key_change_in_production'

# Initialize components
auth_system = SimpleAuth()
logger = get_logger()

@app.route('/')
def home():
    """Main entry point - redirect based on login status"""
    if 'username' in session:
        return redirect(url_for('project_dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page (uses authentication system)"""
    if request.method == 'POST':
        username = request.form['username']
        domain = request.form.get('domain', 'COMPANY')
        ip_address = request.remote_addr
        
        user = auth_system.check_user_login(username, domain)
        
        if user and user['status'] == 'approved':
            # Login successful
            session['username'] = user['username']
            session['email'] = user['email']
            session['first_name'] = user['first_name']
            session['last_name'] = user['last_name']
            session['role'] = user['role']
            session['approved_apps'] = user['approved_apps']
            
            # Log successful login
            logger.log_user_login(username, success=True, ip_address=ip_address)
            logger.log_system_event("USER_SESSION_START", f"User: {username}, Role: {user['role']}")
            
            flash(f'Welcome to MSI Factory, {user["first_name"]}', 'success')
            return redirect(url_for('project_dashboard'))
        else:
            # Log failed login
            logger.log_user_login(username, success=False, ip_address=ip_address)
            logger.log_security_violation("LOGIN_FAILED", username, f"Domain: {domain}")
            
            flash('Access denied. Please contact administrator.', 'error')
    
    return render_template('login.html')

@app.route('/dashboard')
def project_dashboard():
    """Main Project Dashboard"""
    if 'username' not in session:
        return redirect(url_for('login'))
    
    username = session.get('username')
    
    # Get user's projects
    projects = auth_system.get_user_projects(username)
    
    # Calculate statistics
    active_projects_count = len([p for p in projects if p['status'] == 'active'])
    recent_builds_count = 0  # Would connect to actual build history
    user_project_count = len(projects)
    
    # Get recent activities (mock data for now)
    recent_activities = [
        {
            'title': 'MSI Generated',
            'description': 'Successfully generated MSI for WEBAPP01 in PROD environment',
            'timestamp': '2 hours ago',
            'icon': 'fa-rocket',
            'color': '#27ae60'
        },
        {
            'title': 'Project Updated',
            'description': 'Updated configuration for Data Sync Service',
            'timestamp': '1 day ago',
            'icon': 'fa-edit',
            'color': '#3498db'
        }
    ]
    
    return render_template('project_dashboard.html', 
                         projects=projects,
                         active_projects_count=active_projects_count,
                         recent_builds_count=recent_builds_count,
                         user_project_count=user_project_count,
                         recent_activities=recent_activities)

@app.route('/factory-dashboard')
def factory_dashboard():
    """Legacy MSI Factory Dashboard (redirect to new dashboard)"""
    return redirect(url_for('project_dashboard'))

@app.route('/generate-msi', methods=['GET', 'POST'])
def generate_msi():
    """MSI Generation page"""
    if 'username' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'GET':
        # Show MSI generation form
        app_key = request.args.get('app_key')
        
        # Check if user has access to this project
        username = session.get('username')
        user_projects = auth_system.get_user_projects(username)
        
        has_access = False
        project = None
        for user_project in user_projects:
            if user_project['project_key'] == app_key:
                has_access = True
                project = user_project
                break
        
        if not has_access:
            flash('You do not have access to this project', 'error')
            return redirect(url_for('project_dashboard'))
        
        # Load component configuration if exists
        config_file = f'config/{app_key.lower()}-config.json'
        config = None
        if os.path.exists(config_file):
            import json
            with open(config_file, 'r') as f:
                config = json.load(f)
        
        return render_template('generate_msi.html', app_key=app_key, config=config, project=project)
    
    elif request.method == 'POST':
        # Process MSI generation request
        app_key = request.form['app_key']
        component_type = request.form['component_type']
        environments = request.form.getlist('environments')
        username = session.get('username')
        
        # Log MSI generation start
        job_id = logger.log_msi_generation_start(username, app_key, environments)
        logger.log_system_event("MSI_REQUEST", f"User: {username}, App: {app_key}, Envs: {environments}")
        
        # Here we would call the MSI Factory engine
        results = {
            'job_id': job_id,
            'app_key': app_key,
            'component_type': component_type,
            'environments': environments,
            'status': 'queued',
            'message': 'MSI generation has been queued'
        }
        
        flash(f'MSI generation started for {app_key}', 'success')
        return jsonify(results)

@app.route('/msi-status/<job_id>')
def msi_status(job_id):
    """Check MSI generation status"""
    if 'username' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    # This would check actual job status
    status = {
        'job_id': job_id,
        'status': 'in_progress',
        'progress': 50,
        'message': 'Generating MSI for PROD environment...'
    }
    
    return jsonify(status)

@app.route('/admin')
def admin_panel():
    """Admin panel for user management"""
    if 'username' not in session or session.get('role') != 'admin':
        flash('Admin access required', 'error')
        return redirect(url_for('login'))
    
    # Get all pending requests
    pending_requests = auth_system.get_pending_requests()
    
    # Get system statistics
    stats = {
        'total_users': len(auth_system.load_users()),
        'pending_requests': len(pending_requests),
        'total_applications': len(auth_system.load_applications()),
        'msi_generated_today': 0  # Would connect to actual stats
    }
    
    return render_template('admin_panel.html', requests=pending_requests, stats=stats)

@app.route('/project-management')
def project_management():
    """Project Management page for admins"""
    if 'username' not in session or session.get('role') != 'admin':
        flash('Admin access required', 'error')
        return redirect(url_for('login'))
    
    all_projects = auth_system.get_all_projects()
    username = session.get('username')
    projects = auth_system.get_user_projects(username)
    
    return render_template('project_management.html', all_projects=all_projects, projects=projects)

@app.route('/add-project-page')
def add_project_page():
    """Show add project page"""
    if 'username' not in session or session.get('role') != 'admin':
        flash('Admin access required', 'error')
        return redirect(url_for('login'))
    
    return render_template('add_project.html')

@app.route('/add-project-simple')
def add_project_simple():
    """Simple test version of add project page"""
    if 'username' not in session or session.get('role') != 'admin':
        flash('Admin access required', 'error')
        return redirect(url_for('login'))
    
    return render_template('add_project_simple.html')

@app.route('/add-project', methods=['POST'])
def add_project():
    """Add new project with database integration"""
    if 'username' not in session or session.get('role') != 'admin':
        flash('Admin access required', 'error')
        return redirect(url_for('login'))
    
    try:
        # Debug: Print all form data
        print(f"DEBUG: Form data received: {dict(request.form)}")
        
        # Get selected environments (might be empty)
        selected_environments = request.form.getlist('environments')
        if not selected_environments:
            selected_environments = []  # Default to empty list if none selected
        
        # Extract component data
        components_data = []
        component_counter = 1
        while True:
            component_name = request.form.get(f'component_name_{component_counter}')
            if not component_name:
                break
                
            component_data = {
                'component_guid': request.form.get(f'component_guid_{component_counter}'),
                'component_name': component_name,
                'component_type': request.form.get(f'component_type_{component_counter}'),
                'framework': request.form.get(f'component_framework_{component_counter}'),
                'artifact_source': request.form.get(f'component_artifact_{component_counter}', ''),
            }
            components_data.append(component_data)
            component_counter += 1
        
        # Debug: Print project data
        print(f"DEBUG: Selected environments: {selected_environments}")
        print(f"DEBUG: Components data: {components_data}")
        
        def create_project_in_db(db_session):
            # Insert main project with artifact information
            project_insert = """
                INSERT INTO projects (project_name, project_key, description, project_type, 
                                    owner_team, color_primary, color_secondary, status, created_by,
                                    artifact_source_type, artifact_url, artifact_username, artifact_password)
                OUTPUT INSERTED.project_id
                VALUES (:project_name, :project_key, :description, :project_type, 
                       :owner_team, :color_primary, :color_secondary, :status, :created_by,
                       :artifact_source_type, :artifact_url, :artifact_username, :artifact_password)
            """
            
            result = db_session.execute(text(project_insert), {
                'project_name': request.form.get('project_name'),
                'project_key': request.form.get('project_key', '').upper(),
                'description': request.form.get('description', ''),
                'project_type': request.form.get('project_type'),
                'owner_team': request.form.get('owner_team'),
                'color_primary': request.form.get('color_primary', '#2c3e50'),
                'color_secondary': request.form.get('color_secondary', '#3498db'),
                'status': request.form.get('status', 'active'),
                'created_by': session.get('username'),
                'artifact_source_type': request.form.get('artifact_source_type', ''),
                'artifact_url': request.form.get('artifact_url', ''),
                'artifact_username': request.form.get('artifact_username', ''),
                'artifact_password': request.form.get('artifact_password', '')
            })
            
            # Get the project ID from the OUTPUT clause
            project_id = result.fetchone()[0]
            
            # Insert project environments with servers and region
            for env in selected_environments:
                servers_text = request.form.get(f'servers_{env}', '')
                region = request.form.get(f'region_{env}', '').upper()
                
                env_insert = """
                    INSERT INTO project_environments (project_id, environment_name, environment_description, servers, region)
                    VALUES (:project_id, :environment_name, :environment_description, :servers, :region)
                """
                db_session.execute(text(env_insert), {
                    'project_id': project_id, 
                    'environment_name': env, 
                    'environment_description': f"{env} Environment",
                    'servers': servers_text,
                    'region': region
                })
            
            # Insert components if any
            for comp_data in components_data:
                comp_insert = """
                    INSERT INTO components (project_id, component_name, component_type, 
                                          framework, artifact_source, created_by)
                    VALUES (:project_id, :component_name, :component_type, 
                           :framework, :artifact_source, :created_by)
                """
                db_session.execute(text(comp_insert), {
                    'project_id': project_id,
                    'component_name': comp_data['component_name'],
                    'component_type': comp_data['component_type'],
                    'framework': comp_data['framework'],
                    'artifact_source': comp_data['artifact_source'],
                    'created_by': session.get('username')
                })
            
            return project_id
        
        # Execute database operations
        print("DEBUG: About to execute database operations...")
        project_id = execute_with_retry(create_project_in_db)
        
        print(f"DEBUG: Project created successfully with ID: {project_id}")
        flash(f'Project "{request.form["project_name"]}" created successfully!', 'success')
        
    except Exception as e:
        print(f"ERROR creating project: {e}")
        import traceback
        traceback.print_exc()
        flash(f"Error creating project: {str(e)}", 'error')
    
    return redirect(url_for('project_management'))

@app.route('/edit-project', methods=['POST'])
def edit_project():
    """Edit existing project"""
    if 'username' not in session or session.get('role') != 'admin':
        flash('Admin access required', 'error')
        return redirect(url_for('login'))
    
    project_id = request.form['project_id']
    project_data = {
        'project_name': request.form['project_name'],
        'project_key': request.form['project_key'].upper(),
        'description': request.form['description'],
        'project_type': request.form['project_type'],
        'owner_team': request.form['owner_team'],
        'color_primary': request.form['color_primary'],
        'color_secondary': request.form['color_secondary'],
        'status': request.form['status']
    }
    
    success, message = auth_system.update_project(project_id, project_data)
    
    if success:
        logger.log_system_event("PROJECT_UPDATED", f"Project ID: {project_id}, Updated by: {session.get('username')}")
        flash(message, 'success')
    else:
        flash(message, 'error')
    
    return redirect(url_for('project_management'))

@app.route('/delete-project', methods=['POST'])
def delete_project():
    """Delete project"""
    if 'username' not in session or session.get('role') != 'admin':
        flash('Admin access required', 'error')
        return redirect(url_for('login'))
    
    project_id = request.form['project_id']
    
    success, message = auth_system.delete_project(project_id)
    
    if success:
        logger.log_system_event("PROJECT_DELETED", f"Project ID: {project_id}, Deleted by: {session.get('username')}")
        flash(message, 'success')
    else:
        flash(message, 'error')
    
    return redirect(url_for('project_management'))

@app.route('/project/<int:project_id>')
def project_detail(project_id):
    """Project detail page"""
    if 'username' not in session:
        return redirect(url_for('login'))
    
    project = auth_system.get_project_by_id(project_id)
    if not project:
        flash('Project not found', 'error')
        return redirect(url_for('project_dashboard'))
    
    # Check if user has access to this project
    username = session.get('username')
    user_projects = auth_system.get_user_projects(username)
    
    has_access = False
    for user_project in user_projects:
        if user_project['project_id'] == project_id:
            has_access = True
            break
    
    if not has_access and session.get('role') != 'admin':
        flash('You do not have access to this project', 'error')
        return redirect(url_for('project_dashboard'))
    
    return render_template('project_detail.html', project=project)

@app.route('/project/<int:project_id>/settings')
def project_settings(project_id):
    """Project settings page"""
    if 'username' not in session:
        return redirect(url_for('login'))
    
    project = auth_system.get_project_by_id(project_id)
    if not project:
        flash('Project not found', 'error')
        return redirect(url_for('project_dashboard'))
    
    return render_template('project_settings.html', project=project)

@app.route('/build-history')
def build_history():
    """Build history page"""
    if 'username' not in session:
        return redirect(url_for('login'))
    
    # Mock build history data
    builds = []
    
    return render_template('build_history.html', builds=builds)

@app.route('/templates')
def templates_library():
    """Templates library page"""
    if 'username' not in session:
        return redirect(url_for('login'))
    
    # Mock templates data
    templates = []
    
    return render_template('templates_library.html', templates=templates)

@app.route('/system-settings')
def system_settings():
    """System settings page (admin only)"""
    if 'username' not in session or session.get('role') != 'admin':
        flash('Admin access required', 'error')
        return redirect(url_for('login'))
    
    return render_template('system_settings.html')

@app.route('/user-management')
def user_management():
    """User Management page for admins"""
    if 'username' not in session or session.get('role') != 'admin':
        flash('Admin access required', 'error')
        return redirect(url_for('login'))
    
    all_users = auth_system.get_all_users()
    all_projects = auth_system.get_all_projects()
    stats = auth_system.get_user_statistics()
    
    return render_template('user_management.html', 
                         all_users=all_users, 
                         all_projects=all_projects,
                         **stats)

@app.route('/update-user-projects', methods=['POST'])
def update_user_projects():
    """Update user's project access"""
    if 'username' not in session or session.get('role') != 'admin':
        flash('Admin access required', 'error')
        return redirect(url_for('login'))
    
    username = request.form['username']
    all_projects_access = 'all_projects_access' in request.form
    project_keys = request.form.getlist('project_keys')
    
    success, message = auth_system.update_user_projects(username, project_keys, all_projects_access)
    
    if success:
        logger.log_system_event("USER_PROJECTS_UPDATED", f"User: {username}, Updated by: {session.get('username')}")
        flash(message, 'success')
    else:
        flash(message, 'error')
    
    return redirect(url_for('user_management'))

@app.route('/api/user-projects/<username>')
def api_user_projects(username):
    """API endpoint to get user's project details"""
    if 'username' not in session or session.get('role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 401
    
    project_details = auth_system.get_user_project_details(username)
    return jsonify(project_details)

@app.route('/api/toggle-user-status/<username>', methods=['POST'])
def api_toggle_user_status(username):
    """API endpoint to toggle user status"""
    if 'username' not in session or session.get('role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 401
    
    success, message = auth_system.toggle_user_status(username)
    
    if success:
        logger.log_system_event("USER_STATUS_TOGGLED", f"User: {username}, Changed by: {session.get('username')}")
    
    return jsonify({'success': success, 'message': message})

@app.route('/api/applications')
def api_applications():
    """API endpoint to get applications"""
    if 'username' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    applications = auth_system.load_applications()
    return jsonify(applications)

@app.route('/api/generate-msi', methods=['POST'])
def api_generate_msi():
    """API endpoint for MSI generation"""
    if 'username' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.json
    app_key = data.get('app_key')
    environments = data.get('environments', [])
    
    # Validate user has access
    user_apps = session.get('approved_apps', [])
    if app_key not in user_apps and '*' not in user_apps:
        return jsonify({'error': 'Access denied for this application'}), 403
    
    # Queue MSI generation job
    job_id = f"JOB_{app_key}_{len(environments)}"
    
    return jsonify({
        'job_id': job_id,
        'status': 'queued',
        'message': f'MSI generation queued for {len(environments)} environments'
    })

@app.route('/logout')
def logout():
    """Logout user"""
    username = session.get('username')
    if username:
        logger.log_user_logout(username)
        logger.log_system_event("USER_SESSION_END", f"User: {username}")
    
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('login'))

# Error handlers
@app.errorhandler(404)
def not_found(e):
    return render_template('error.html', error='Page not found'), 404

@app.errorhandler(500)
def server_error(e):
    return render_template('error.html', error='Internal server error'), 500

def init_system():
    """Initialize the MSI Factory system"""
    print("=" * 60)
    print("MSI FACTORY - Enterprise MSI Generation System")
    print("=" * 60)
    
    # Create necessary directories
    directories = ['webapp/templates', 'webapp/static', 'config', 'output', 'logs']
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
    
    # Initialize logging
    logger.log_system_start()
    logger.log_system_event("INITIALIZATION", "System directories created")
    logger.log_system_event("INITIALIZATION", "Authentication system loaded")
    
    print("[OK] System initialized")
    print("[OK] Directories created")
    print("[OK] Authentication system loaded")
    print("[OK] Logging system active")
    print("[OK] Ready to generate MSIs")
    print("=" * 60)

if __name__ == '__main__':
    # Initialize system
    init_system()
    
    print("\nStarting MSI Factory Server...")
    print("URL: http://localhost:5000")
    print("Admin: admin")
    print("User: john.doe")
    print("\nPress CTRL+C to stop the server")
    print("-" * 60)
    
    # Run the application
    app.run(debug=True, host='0.0.0.0', port=5000)