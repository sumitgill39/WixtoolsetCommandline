"""
Routes Module
Contains all Flask route definitions
"""

from flask import render_template, request, redirect, url_for, session, flash, jsonify
from core.database_operations import (
    update_user_projects_in_database,
    get_user_project_details_from_database,
    debug_user_project_access,
    get_all_components_from_database,
    get_component_by_id_from_database,
    get_component_branches,
    add_component_branch,
    update_component_branch,
    delete_component_branch
)
from core.permission_manager import (
    get_permission_presets,
    get_user_permissions,
    get_users_with_permissions,
    grant_user_permission,
    revoke_user_permission,
    user_has_permission
)
from core.form_handlers import ProjectFormHandler, ComponentFormHandler
from core.validators import validate_form_data
from core.project_manager import (
    get_project_components,
    get_project_build_history
)
from core.cmdb_manager import (
    get_cmdb_dashboard_stats,
    get_all_cmdb_servers,
    add_cmdb_server,
    get_cmdb_server_details,
    get_server_assignments,
    create_server_assignment,
    get_cmdb_utilization,
    get_cmdb_groups
)
from core.msi_generator import (
    save_msi_configuration,
    get_next_version,
    get_msi_configuration,
    generate_msi_package,
    get_msi_job_status,
    get_build_configurations
)
# Removed old integrations import - now using centralized integration_manager
from logger import log_info, log_error

def register_all_routes(app, components):
    """Register all application routes"""

    # Note: No longer using auth_system - SQL-only authentication
    logger = components['logger']
    api_client = components['api_client']

    # Home route
    @app.route('/')
    def home():
        if 'username' in session:
            return redirect(url_for('project_dashboard'))
        return redirect(url_for('login'))

    # Authentication routes
    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'POST':
            username = request.form['username']
            password = request.form.get('password', 'password123')  # Default password for testing
            domain = request.form.get('domain', 'COMPANY')
            ip_address = request.remote_addr

            # Import SQL authentication function
            from core.database_operations import authenticate_user_sql

            # Authenticate against SQL database
            user_data, message = authenticate_user_sql(username, password)

            if user_data:
                # Login successful - store user data in session
                session['username'] = user_data['username']
                session['email'] = user_data['email']
                session['first_name'] = user_data['first_name']
                session['last_name'] = user_data['last_name']
                session['role'] = user_data['role']
                session['user_id'] = user_data['user_id']

                # Get user's project assignments from SQL
                from sql_only_functions import get_user_projects_from_database_sql_only
                projects = get_user_projects_from_database_sql_only(username)
                session['approved_apps'] = [p['project_key'] for p in projects] if projects else []

                flash(f'Welcome to MSI Factory, {user_data["first_name"] or username}!', 'success')
                return redirect(url_for('project_dashboard'))
            else:
                flash(message or 'Access denied. Please contact administrator.', 'error')

        return render_template('login.html')

    @app.route('/logout')
    def logout():
        username = session.get('username', 'User')
        session.clear()
        flash(f'Goodbye, {username}! You have been logged out successfully.', 'info')
        return redirect(url_for('home'))

    # Dashboard routes
    @app.route('/dashboard')
    def project_dashboard():
        if 'username' not in session:
            return redirect(url_for('login'))

        username = session['username']
        user_role = session.get('role', 'user')

        # Get user's assigned project keys
        from sql_only_functions import get_user_project_details_from_database_sql_only
        user_project_details = get_user_project_details_from_database_sql_only(username)

        if not user_project_details:
            user_assigned_projects = []
        else:
            user_assigned_projects = user_project_details.get('projects', [])
            is_admin = user_project_details.get('all_projects', False)

        # Get detailed project information with components
        # Use ProjectManager API to get all projects with details
        from core.project_manager_api import get_all_projects
        # Admin users should see ALL projects regardless of status
        include_inactive = (user_role == 'admin')
        all_detailed_projects = get_all_projects(include_inactive=include_inactive)

        # Filter projects based on user access
        if user_role == 'admin' or (user_project_details and user_project_details.get('all_projects', False)):
            # Admin or user with all projects access
            user_projects = all_detailed_projects
        else:
            # Filter to only projects user has access to
            user_projects = [
                project for project in all_detailed_projects
                if project['project_key'] in user_assigned_projects
            ]

        return render_template('dashboard.html',
                             username=username,
                             applications=user_projects,
                             project_count=len(user_projects))

    @app.route('/factory-dashboard')
    def factory_dashboard():
        if 'username' not in session:
            return redirect(url_for('login'))
        return render_template('factory_dashboard.html')

    @app.route('/build-history')
    def build_history():
        """Build history page"""
        if 'username' not in session:
            return redirect(url_for('login'))

        # Mock build history data
        builds = []

        return render_template('build_history.html', builds=builds)

    # Project management routes
    @app.route('/project-management')
    def project_management():
        if 'username' not in session or session.get('role') != 'admin':
            flash('Admin access required', 'error')
            return redirect(url_for('login'))

        try:
            # Use ProjectManager API to get all projects
            from core.project_manager_api import get_all_projects, ProjectManager
            all_projects = get_all_projects(include_inactive=True)

            # Add components data for each project
            project_manager = ProjectManager()
            for project in all_projects:
                try:
                    project['components'] = project_manager.get_project_components(project['project_id'])
                except Exception as e:
                    logger.log_error(f"Error fetching components for project {project['project_id']}: {e}")
                    project['components'] = []

            return render_template('project_management_original.html', all_projects=all_projects)

        except Exception as e:
            logger.log_error(f"Error in project_management route: {e}")
            flash('Error loading project management dashboard', 'error')
            return render_template('project_management_original.html', all_projects=[])

    @app.route('/add-project-page')
    def add_project_page():
        if 'username' not in session or session.get('role') != 'admin':
            flash('Admin access required', 'error')
            return redirect(url_for('login'))
        return render_template('add_project.html')

    @app.route('/add-project', methods=['POST'])
    def add_project():
        if 'username' not in session or session.get('role') != 'admin':
            flash('Admin access required', 'error')
            return redirect(url_for('login'))

        # Use new form handler for enhanced processing and validation
        handler = ProjectFormHandler()
        result = handler.process_project_form(request.form, is_edit=False)

        if not result['success']:
            flash(f'Project validation failed: {result["error"]}', 'error')
            return redirect(url_for('add_new_project'))

        # Use ProjectManager API to create project
        from core.project_manager_api import create_project
        success, message, project_id = create_project(
            result['project_data'],
            session.get('username')
        )

        if success:
            flash(message, 'success')
        else:
            flash(message, 'error')

        return redirect(url_for('project_management'))

    @app.route('/edit-project', methods=['POST'])
    def edit_project():
        if 'username' not in session or session.get('role') != 'admin':
            flash('Admin access required', 'error')
            return redirect(url_for('login'))

        project_id = request.form.get('project_id')

        # Validate project ID
        if not project_id:
            flash('Project ID is required', 'error')
            return redirect(url_for('project_management'))

        try:
            project_id = int(project_id)
        except (ValueError, TypeError):
            flash('Invalid project ID', 'error')
            return redirect(url_for('project_management'))

        # Process form data
        project_data = {
            'project_name': request.form.get('project_name'),
            'description': request.form.get('description'),
            'project_type': request.form.get('project_type'),
            'owner_team': request.form.get('owner_team'),
            'status': request.form.get('status'),
            'color_primary': request.form.get('color_primary'),
            'color_secondary': request.form.get('color_secondary')
        }

        # Use ProjectManager API to update project
        from core.project_manager_api import update_project
        success, message = update_project(project_id, project_data, session.get('username'))

        if success:
            flash(message, 'success')
        else:
            flash(message, 'error')

        return redirect(url_for('edit_project_page', project_id=project_id))

    @app.route('/edit-project/<int:project_id>')
    def edit_project_page(project_id):
        if 'username' not in session or session.get('role') != 'admin':
            flash('Admin access required', 'error')
            return redirect(url_for('login'))

        # Use ProjectManager API to get project
        from core.project_manager_api import get_project
        project = get_project(project_id)
        if not project:
            flash('Project not found', 'error')
            return redirect(url_for('project_management'))

        components = get_project_components(project_id)

        return render_template('edit_project.html',
                             project=project,
                             components=components)

    @app.route('/delete-project', methods=['POST'])
    def delete_project():
        if 'username' not in session or session.get('role') != 'admin':
            return jsonify({'error': 'Admin access required'}), 401

        project_id = request.form.get('project_id')

        # Use ProjectManager API to delete project
        from core.project_manager_api import delete_project

        try:
            project_id = int(project_id)
        except (ValueError, TypeError):
            return jsonify({'error': 'Invalid project ID'}), 400

        success, message = delete_project(project_id, hard_delete=False, username=session.get('username'))

        if success:
            flash(message, 'success')
        else:
            flash(message, 'error')

        return redirect(url_for('project_management'))

    @app.route('/project/<int:project_id>')
    def project_detail(project_id):
        if 'username' not in session:
            return redirect(url_for('login'))

        username = session['username']
        user_role = session.get('role', 'user')

        # Get the project using ProjectManager API
        from core.project_manager_api import get_project
        project = get_project(project_id)
        if not project:
            flash('Project not found', 'error')
            return redirect(url_for('project_dashboard'))

        # Check if user has access to this project
        if user_role != 'admin':
            from sql_only_functions import get_user_project_details_from_database_sql_only
            user_project_details = get_user_project_details_from_database_sql_only(username)

            if not user_project_details:
                flash('Access denied', 'error')
                return redirect(url_for('project_dashboard'))

            user_projects = user_project_details.get('projects', [])
            has_all_access = user_project_details.get('all_projects', False)

            if not has_all_access and project['project_key'] not in user_projects:
                flash('You do not have access to this project', 'error')
                return redirect(url_for('project_dashboard'))

        # Get additional project details
        components = get_project_components(project_id)

        return render_template('project_detail.html',
                             project=project,
                             components=components,
                             username=username,
                             user_role=user_role)

    @app.route('/component/<int:component_id>')
    def component_detail(component_id):
        """Component detail page - Python-only approach"""
        if 'username' not in session:
            return redirect(url_for('login'))

        username = session['username']
        user_role = session.get('role', 'user')

        # Get the component details using ComponentManager
        from core.component_manager import ComponentManager
        component_manager = ComponentManager()
        component = component_manager.get_component_by_id(component_id)

        if not component:
            flash('Component not found', 'error')
            return redirect(url_for('project_dashboard'))

        # Get the project this component belongs to
        # Use ProjectManager API to get project
        from core.project_manager_api import get_project
        project = get_project(component['project_id'])
        if not project:
            flash('Associated project not found', 'error')
            return redirect(url_for('project_dashboard'))

        # Check if user has access to the project that contains this component
        if user_role != 'admin':
            from sql_only_functions import get_user_project_details_from_database_sql_only
            user_project_details = get_user_project_details_from_database_sql_only(username)

            if not user_project_details:
                flash('Access denied', 'error')
                return redirect(url_for('project_dashboard'))

            user_projects = user_project_details.get('projects', [])
            has_all_access = user_project_details.get('all_projects', False)

            if not has_all_access and project['project_key'] not in user_projects:
                flash('You do not have access to this component', 'error')
                return redirect(url_for('project_dashboard'))

        return render_template('component_detail.html',
                             component=component,
                             project=project,
                             username=username,
                             user_role=user_role)

    # Component management routes
    @app.route('/add-component', methods=['GET', 'POST'])
    def add_component():
        if 'username' not in session or session.get('role') != 'admin':
            flash('Admin access required', 'error')
            return redirect(url_for('login'))

        # Handle GET request - show form
        if request.method == 'GET':
            # Use ProjectManager API to get all projects
            from core.project_manager_api import get_all_projects
            projects = get_all_projects()
            return render_template('add_component.html', projects=projects)

        # Handle POST request - process form
        project_id = request.form.get('project_id')
        if not project_id:
            flash('Project selection is required', 'error')
            return redirect(url_for('add_component'))

        try:
            project_id = int(project_id)
        except (ValueError, TypeError):
            flash('Invalid project selected', 'error')
            return redirect(url_for('add_component'))

        # Get project key for GUID generation
        project_key = request.form.get('project_key', 'PROJ')

        # Use ComponentManager API for component creation
        from core.component_manager import create_component, validate_component

        # Process form data using form handler
        handler = ComponentFormHandler()
        result = handler.process_add_component(request.form, project_id, project_key)

        if not result['success']:
            flash(f"Error processing form: {result['error']}", 'error')
            return redirect(url_for('add_component'))

        # Validate component data
        is_valid, validation_errors = validate_component(result['component_data'])
        if not is_valid:
            error_message = "Validation errors: " + ", ".join(validation_errors)
            flash(error_message, 'error')
            return redirect(url_for('add_component'))

        # Create component using ComponentManager API
        success, message, component_id = create_component(
            project_id,
            result['component_data'],
            session.get('username')
        )

        if success:
            flash(f"Component '{result['component_data']['component_name']}' added successfully!", 'success')
        else:
            flash(f"Error creating component: {message}", 'error')

        return redirect(url_for('component_configuration'))

    @app.route('/edit-component/<int:component_id>', methods=['GET', 'POST'])
    def edit_component(component_id):
        if 'username' not in session or session.get('role') != 'admin':
            flash('Admin access required', 'error')
            return redirect(url_for('login'))

        # Get component details with project information
        from core.project_manager import get_component_details
        component = get_component_details(component_id)

        if not component:
            flash('Component not found', 'error')
            return redirect(url_for('component_configuration'))

        # Handle GET request - show form
        if request.method == 'GET':
            # Use ProjectManager API to get all projects
            from core.project_manager_api import get_all_projects
            projects = get_all_projects()
            return render_template('edit_component.html', component=component, projects=projects)

        # Handle POST request - update component
        component_data = {
            'component_name': request.form.get('component_name'),
            'component_type': request.form.get('component_type'),
            'framework': request.form.get('framework'),
            # component_guid is system-generated and immutable - not processed from form
            'description': request.form.get('description'),
            'app_name': request.form.get('app_name'),
            'app_version': request.form.get('app_version'),
            'manufacturer': request.form.get('manufacturer'),
            'install_folder': request.form.get('install_folder'),
            'target_server': request.form.get('target_server'),
            'artifact_url': request.form.get('artifact_url'),
            'iis_website_name': request.form.get('iis_website_name'),
            'iis_app_pool_name': request.form.get('iis_app_pool_name'),
            'port': request.form.get('port'),
            'service_name': request.form.get('service_name'),
            'service_display_name': request.form.get('service_display_name'),
            'is_enabled': bool(request.form.get('is_enabled'))
        }

        # Clean up empty string values
        for key, value in component_data.items():
            if value == '':
                component_data[key] = None

        # Convert port to integer if provided
        if component_data['port']:
            try:
                component_data['port'] = int(component_data['port'])
            except (ValueError, TypeError):
                component_data['port'] = None

        # Validate component data for the specific type
        from core.component_manager import ComponentManager
        component_manager = ComponentManager()
        component_type = component_data.get('component_type')
        is_valid, validation_errors = component_manager.validate_required_fields_for_type(component_data, component_type)

        if not is_valid:
            error_message = "Validation errors: " + "; ".join(validation_errors)
            flash(error_message, 'error')
            # Use ProjectManager API to get all projects
            from core.project_manager_api import get_all_projects
            projects = get_all_projects()
            return render_template('edit_component.html', component=component, projects=projects)

        # Update component using ComponentManager API
        success, message = component_manager.update_component(
            component_id,
            component['project_id'],
            component_data,
            session.get('username')
        )

        if success:
            flash('Component updated successfully!', 'success')
        else:
            flash(f'Error updating component: {message}', 'error')

        return redirect(url_for('component_configuration'))

    @app.route('/remove-component', methods=['POST'])
    def remove_component():
        if 'username' not in session or session.get('role') != 'admin':
            flash('Admin access required', 'error')
            return redirect(url_for('login'))

        component_id = request.form.get('component_id')

        # Enhanced validation for component deletion
        if not component_id:
            flash('Component ID is required', 'error')
            return redirect(url_for('component_configuration'))

        try:
            component_id = int(component_id)
        except (ValueError, TypeError):
            flash('Invalid component ID format', 'error')
            return redirect(url_for('component_configuration'))

        # Check if component exists using ComponentManager API
        from core.component_manager import ComponentManager
        component_manager = ComponentManager()
        component = component_manager.get_component_by_id(component_id)

        if not component:
            flash('Component not found', 'error')
            return redirect(url_for('component_configuration'))

        # Log deletion attempt
        log_info(f"User {session.get('username')} attempting to delete component {component['component_name']} (ID: {component_id})")

        # Delete component using ComponentManager API
        success, message = component_manager.delete_component(
            component_id,
            component['project_id'],
            session.get('username')
        )

        if success:
            log_info(f"Component {component['component_name']} successfully deleted by {session.get('username')}")
            flash(f"Component '{component['component_name']}' deleted successfully!", 'success')
        else:
            log_error(f"Failed to delete component {component['component_name']}: {message}")
            flash(f"Error deleting component: {message}", 'error')

        return redirect(url_for('component_configuration'))

    @app.route('/api/component/<int:component_id>/toggle-status', methods=['POST'])
    def api_toggle_component_status(component_id):
        """API endpoint to toggle component status (Active/Inactive)"""
        if 'username' not in session:
            return jsonify({'error': 'Authentication required'}), 401

        # Check permissions - PowerUsers and Admins can toggle status
        user_role = session.get('role', 'user')
        if user_role not in ['admin', 'poweruser']:
            return jsonify({'error': 'Insufficient permissions'}), 403

        try:
            # Get request data
            data = request.get_json()
            new_status = data.get('is_enabled', True)

            # Get component details
            from core.component_manager import ComponentManager
            component_manager = ComponentManager()
            component = component_manager.get_component_by_id(component_id)

            if not component:
                return jsonify({'error': 'Component not found'}), 404

            # Toggle component status
            success, message = component_manager.toggle_component_status(
                component_id,
                new_status,
                session.get('username')
            )

            if success:
                status_text = "activated" if new_status else "deactivated"
                log_info(f"Component '{component['component_name']}' {status_text} by {session.get('username')}")
                return jsonify({
                    'success': True,
                    'message': f"Component {status_text} successfully",
                    'is_enabled': new_status
                })
            else:
                return jsonify({'success': False, 'message': message}), 400

        except Exception as e:
            log_error(f"Error toggling component status: {e}")
            return jsonify({'error': 'Internal server error'}), 500

    @app.route('/api/test/component-status/<int:component_id>')
    def test_component_status(component_id):
        """Test endpoint to verify component is_enabled field is read correctly from database"""
        if 'username' not in session:
            return jsonify({'error': 'Authentication required'}), 401

        try:
            from core.component_manager import ComponentManager
            component_manager = ComponentManager()
            component = component_manager.get_component_by_id(component_id)

            if not component:
                return jsonify({'error': 'Component not found'}), 404

            # Also get raw SQL data for comparison
            import pyodbc
            from core.database_operations import get_db_connection

            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT component_id, component_name, is_enabled
                        FROM components
                        WHERE component_id = ?
                    """, (component_id,))

                    row = cursor.fetchone()
                    if row:
                        raw_data = {
                            'component_id': row[0],
                            'component_name': row[1],
                            'is_enabled': bool(row[2])
                        }
                    else:
                        raw_data = None

            return jsonify({
                'component_manager_data': {
                    'component_id': component.get('component_id'),
                    'component_name': component.get('component_name'),
                    'is_enabled': component.get('is_enabled')
                },
                'raw_sql_data': raw_data,
                'data_match': (
                    component.get('is_enabled') == raw_data.get('is_enabled')
                    if raw_data else False
                )
            })

        except Exception as e:
            log_error(f"Error in test endpoint: {e}")
            return jsonify({'error': f'Test failed: {str(e)}'}), 500

    @app.route('/update-component', methods=['POST'])
    def update_component():
        if 'username' not in session or session.get('role') != 'admin':
            return jsonify({'error': 'Admin access required'}), 401

        component_id = request.form.get('component_id')
        if not component_id:
            return jsonify({'error': 'Component ID is required'}), 400

        try:
            component_id = int(component_id)
        except (ValueError, TypeError):
            return jsonify({'error': 'Invalid component ID format'}), 400

        # Extract component data from form with dynamic field names
        component_data = {}
        for key, value in request.form.items():
            if key.startswith(f'component_') and key.endswith(f'_existing_{component_id}'):
                field_name = key.replace(f'_existing_{component_id}', '').replace('component_', '')
                if field_name == 'name':
                    component_data['component_name'] = value
                elif field_name == 'type':
                    component_data['component_type'] = value
                elif field_name == 'framework':
                    component_data['framework'] = value
                elif field_name == 'description':
                    component_data['description'] = value
                elif field_name == 'app_name':
                    component_data['app_name'] = value
                elif field_name == 'app_version':
                    component_data['app_version'] = value
                elif field_name == 'manufacturer':
                    component_data['manufacturer'] = value
                elif field_name == 'install_folder':
                    component_data['install_folder'] = value
                elif field_name == 'service_name':
                    component_data['service_name'] = value
                elif field_name == 'service_display':
                    component_data['service_display_name'] = value
                elif field_name == 'iis_website':
                    component_data['iis_website_name'] = value
                elif field_name == 'iis_app_pool':
                    component_data['iis_app_pool_name'] = value
                elif field_name == 'port':
                    component_data['port'] = int(value) if value and value.isdigit() else None

        # Set default enabled status
        component_data['is_enabled'] = True

        # Validate required fields
        if not component_data.get('component_name'):
            return jsonify({'error': 'Component name is required'}), 400

        # Log update attempt
        log_info(f"User {session.get('username')} attempting to update component ID: {component_id}")

        # Get component to find project_id using ComponentManager API
        from core.component_manager import ComponentManager
        component_manager = ComponentManager()
        component = component_manager.get_component_by_id(component_id)

        if not component:
            return jsonify({'error': 'Component not found'}), 404

        # Update component using ComponentManager API
        success, message = component_manager.update_component(
            component_id,
            component['project_id'],
            component_data,
            session.get('username')
        )

        if success:
            log_info(f"Component ID {component_id} successfully updated by {session.get('username')}")
            return jsonify({'success': True, 'message': message})
        else:
            log_error(f"Failed to update component ID {component_id}: {message}")
            return jsonify({'error': message}), 400

    # CMDB routes
    @app.route('/cmdb')
    @app.route('/cmdb/dashboard')
    def cmdb_dashboard():
        if 'username' not in session:
            return redirect(url_for('login'))

        stats = get_cmdb_dashboard_stats()
        if stats:
            return render_template('cmdb_dashboard.html', **stats)
        else:
            flash('Error loading CMDB dashboard', 'error')
            return redirect(url_for('project_dashboard'))

    @app.route('/cmdb/servers')
    def cmdb_servers():
        if 'username' not in session:
            return redirect(url_for('login'))

        servers = get_all_cmdb_servers()
        return render_template('cmdb_servers.html', servers=servers)

    @app.route('/cmdb/servers/add', methods=['GET', 'POST'])
    def cmdb_add_server():
        if 'username' not in session or session.get('role') != 'admin':
            flash('Admin access required', 'error')
            return redirect(url_for('login'))

        if request.method == 'GET':
            return render_template('cmdb_add_server.html')

        success, server_id, message = add_cmdb_server(
            request.form,
            session.get('username')
        )

        if success:
            flash(message, 'success')
            return redirect(url_for('cmdb_server_detail', server_id=server_id))
        else:
            flash(message, 'error')
            return redirect(url_for('cmdb_servers'))

    @app.route('/cmdb/servers/<int:server_id>')
    def cmdb_server_detail(server_id):
        if 'username' not in session:
            return redirect(url_for('login'))

        server = get_cmdb_server_details(server_id)
        if server:
            # Use ProjectManager API to get all projects
            from core.project_manager_api import get_all_projects
            projects = get_all_projects()
            return render_template('cmdb_server_detail.html',
                                 server=server,
                                 projects=projects)
        else:
            flash('Server not found', 'error')
            return redirect(url_for('cmdb_servers'))

    @app.route('/cmdb/assignments/create', methods=['POST'])
    def cmdb_create_assignment():
        if 'username' not in session or session.get('role') != 'admin':
            return jsonify({'error': 'Admin access required'}), 401

        assignment_data = {
            'server_id': request.form.get('server_id'),
            'project_id': request.form.get('project_id'),
            'environment': request.form.get('environment'),
            'deployment_type': request.form.get('deployment_type')
        }

        success, assignment_id, message = create_server_assignment(
            assignment_data,
            session.get('username')
        )

        if success:
            return jsonify({'success': True, 'message': message})
        else:
            return jsonify({'error': message}), 400

    # MSI generation routes
    @app.route('/generate-msi', methods=['GET', 'POST'])
    def generate_msi():
        if 'username' not in session:
            return redirect(url_for('login'))

        if request.method == 'GET':
            # Use ProjectManager API to get all projects (user filtering handled separately)
            from core.project_manager_api import get_all_projects
            projects = get_all_projects()
            return render_template('generate_msi.html', projects=projects)

        # Handle MSI generation request
        project_id = request.form.get('project_id')
        component_id = request.form.get('component_id')

        # Use ProjectManager API to get project
        from core.project_manager_api import get_project
        project = get_project(project_id)
        component_data = {'component_id': component_id}  # Get full component data
        msi_config = get_msi_configuration(component_id)

        success, job_id, message = generate_msi_package(
            project,
            component_data,
            msi_config,
            session.get('username')
        )

        if success:
            flash(message, 'success')
            return redirect(url_for('msi_status', job_id=job_id))
        else:
            flash(message, 'error')
            return redirect(url_for('generate_msi'))

    @app.route('/msi-status/<job_id>')
    def msi_status(job_id):
        if 'username' not in session:
            return redirect(url_for('login'))

        status = get_msi_job_status(job_id)
        if status:
            return render_template('msi_status.html', status=status)
        else:
            flash('Job not found', 'error')
            return redirect(url_for('generate_msi'))

    @app.route('/save-msi-config', methods=['POST'])
    def save_msi_config():
        if 'username' not in session or session.get('role') != 'admin':
            return jsonify({'error': 'Unauthorized'}), 401

        component_id = request.form.get('component_id')
        success, message = save_msi_configuration(
            component_id,
            request.form,
            session.get('username')
        )

        if success:
            return jsonify({'success': True, 'message': message})
        else:
            return jsonify({'success': False, 'message': message}), 500

    # Integration routes
    @app.route('/integrations')
    def integrations():
        if 'username' not in session or session.get('role') != 'admin':
            flash('Admin access required', 'error')
            return redirect(url_for('login'))

        try:
            from PackageBuilder.integration_manager import integration_manager
            integrations_result = integration_manager.get_all_integrations_status()

            if integrations_result['success']:
                integrations_list = integrations_result['integrations']
            else:
                integrations_list = []
                flash('Could not load integration status', 'warning')

            # Load JFrog configuration for form population
            jfrog_config = {}
            try:
                jfrog_result = integration_manager.get_integration_config('jfrog', 'Primary JFrog')
                if jfrog_result['success'] and jfrog_result.get('config'):
                    config = jfrog_result['config']
                    jfrog_config = {
                        'config_id': config.get('config_id'),
                        'base_url': config.get('base_url', ''),
                        'username': config.get('username', ''),
                        'curl_path': config.get('additional_config', {}).get('curl_path', ''),
                        'has_password': bool(config.get('password'))
                    }
                else:
                    # Fallback: Direct database query if integration manager fails
                    # Fallback: Direct database query if integration manager fails
                    from core.database_operations import get_db_connection
                    try:
                        with get_db_connection() as conn:
                            cursor = conn.cursor()
                            cursor.execute("""
                                SELECT config_id, base_url, username, password, additional_config
                                FROM [dbo].[integrations_config]
                                WHERE integration_type = 'jfrog' AND is_enabled = 1
                                ORDER BY created_date DESC
                            """)
                            row = cursor.fetchone()
                            if row:
                                import json
                                additional_config = json.loads(row.additional_config) if row.additional_config else {}
                                jfrog_config = {
                                    'config_id': row.config_id,
                                    'base_url': row.base_url or '',
                                    'username': row.username or '',
                                    'curl_path': additional_config.get('curl_path', ''),
                                    'has_password': bool(row.password)
                                }
                    except Exception as db_e:
                        logger.log_error(db_e, f"Error in database fallback: {db_e}")
            except Exception as e:
                logger.log_error(e, f"Error loading JFrog config: {e}")

        except Exception as e:
            logger.log_error(e, f"Error loading integrations: {e}")
            integrations_list = []
            jfrog_config = {}
            flash('Error loading integrations', 'error')

        # Check if URL edit mode is enabled
        jfrog_url_edit_mode = session.get('jfrog_url_edit_mode', False)
        jfrog_password_edit_mode = session.get('jfrog_password_edit_mode', False)

        return render_template('integrations.html',
                             integrations=integrations_list,
                             jfrog_config=jfrog_config,
                             jfrog_url_edit_mode=jfrog_url_edit_mode,
                             jfrog_password_edit_mode=jfrog_password_edit_mode)

    @app.route('/api/integrations/servicenow/config', methods=['GET', 'POST'])
    def servicenow_config():
        if 'username' not in session or session.get('role') != 'admin':
            return jsonify({'error': 'Admin access required'}), 401

        try:
            from PackageBuilder.integration_manager import integration_manager
        except ImportError:
            return jsonify({'error': 'Integration system not available'}), 500

        if request.method == 'GET':
            result = integration_manager.get_integration_config('servicenow')
            return jsonify(result)

        # POST - Save configuration
        form_data = request.form if request.content_type.startswith('multipart/form-data') else request.get_json()

        integration_data = {
            'integration_type': 'servicenow',
            'integration_name': 'Primary ServiceNow',
            'base_url': form_data.get('snow_instance_url'),
            'auth_type': 'username_password',
            'username': form_data.get('snow_username'),
            'password': form_data.get('snow_password'),
            'is_enabled': True,
            'config_details': {
                'table': form_data.get('snow_table', 'cmdb_ci_server'),
                'filter': form_data.get('snow_filter', ''),
                'auto_sync': form_data.get('snow_auto_sync', False),
                'sync_frequency': form_data.get('snow_sync_frequency', 'daily')
            }
        }

        result = integration_manager.save_integration_config(integration_data, session.get('username'))

        if result['success']:
            return jsonify({'success': True, 'message': result['message']})
        else:
            return jsonify({'error': result['error']}), 400

    @app.route('/api/integrations/servicenow/test', methods=['POST'])
    def test_servicenow():
        if 'username' not in session or session.get('role') != 'admin':
            return jsonify({'error': 'Admin access required'}), 401

        try:
            from PackageBuilder.integration_manager import integration_manager
        except ImportError:
            return jsonify({'error': 'Integration system not available'}), 500

        result = integration_manager.test_integration_connection(
            'servicenow', 'Primary ServiceNow', session.get('username')
        )

        return jsonify(result)

    @app.route('/api/integrations/servicenow/sync', methods=['POST'])
    def sync_servicenow():
        if 'username' not in session or session.get('role') != 'admin':
            return jsonify({'error': 'Admin access required'}), 401

        try:
            from PackageBuilder.integration_manager import integration_manager
        except ImportError:
            return jsonify({'error': 'Integration system not available'}), 500

        # For now, return a placeholder response since ServiceNow sync is not implemented in the new integration manager yet
        return jsonify({
            'success': True,
            'servers_synced': 0,
            'servers_added': 0,
            'servers_updated': 0,
            'errors': [],
            'message': 'ServiceNow sync functionality will be implemented in the new integration system'
        })

    # JFrog Integration API routes
    @app.route('/api/integrations/jfrog/config', methods=['GET', 'POST'])
    def jfrog_config():
        if 'username' not in session or session.get('role') != 'admin':
            return jsonify({'error': 'Admin access required'}), 401

        try:
            from PackageBuilder.integration_manager import integration_manager
        except ImportError:
            return jsonify({'error': 'Integration system not available'}), 500

        if request.method == 'GET':
            result = integration_manager.get_integration_config('jfrog', 'Primary JFrog')
            return jsonify(result)

        elif request.method == 'POST':
            form_data = request.form if request.content_type.startswith('multipart/form-data') else request.get_json()

            integration_data = {
                'integration_type': 'jfrog',
                'integration_name': 'Primary JFrog',
                'base_url': form_data.get('jfrog_base_url'),
                'auth_type': 'username_password',
                'username': form_data.get('jfrog_username'),
                'password': form_data.get('jfrog_password'),
                'is_enabled': True,
                'additional_config': {
                    'curl_path': form_data.get('jfrog_curl_path', ''),
                    'ssl_verify': True,
                    'timeout': 30
                }
            }

            result = integration_manager.save_integration_config(integration_data, session.get('username'))

            if result['success']:
                return jsonify({'success': True, 'message': result['message']})
            else:
                return jsonify({'error': result['error']}), 400


    # Python-only form handling routes (no JavaScript)
    @app.route('/integrations/jfrog/save', methods=['POST'])
    def jfrog_save_form():
        if 'username' not in session or session.get('role') != 'admin':
            flash('Admin access required', 'error')
            return redirect(url_for('login'))

        try:
            from PackageBuilder.integration_manager import integration_manager
        except ImportError:
            flash('Integration system not available', 'error')
            return redirect(url_for('integrations'))

        # Get form data from POST request
        form_data = request.form

        integration_data = {
            'integration_type': 'jfrog',
            'integration_name': 'Primary JFrog',
            'base_url': form_data.get('jfrog_base_url'),
            'auth_type': 'username_password',
            'username': form_data.get('jfrog_username'),
            'password': form_data.get('jfrog_password'),
            'is_enabled': True,
            'additional_config': {
                'curl_path': form_data.get('jfrog_curl_path', ''),
                'ssl_verify': True,
                'timeout': 30
            }
        }

        # Include config_id if provided to enable UPDATE instead of INSERT
        config_id = form_data.get('config_id')
        if config_id:
            try:
                integration_data['config_id'] = int(config_id)
            except (ValueError, TypeError):
                flash('Invalid configuration ID', 'error')
                return redirect(url_for('integrations'))

        result = integration_manager.save_integration_config(integration_data, session.get('username'))

        if result['success']:
            flash('JFrog configuration saved successfully!', 'success')
            # Keep edit modes active - user can continue editing or manually lock fields
        else:
            flash(f'Error saving JFrog configuration: {result.get("error", "Unknown error")}', 'error')

        return redirect(url_for('integrations'))

    @app.route('/integrations/jfrog/edit_url', methods=['POST'])
    def jfrog_edit_url():
        if 'username' not in session or session.get('role') != 'admin':
            flash('Admin access required', 'error')
            return redirect(url_for('login'))

        # Set a session flag to enable URL editing
        session['jfrog_url_edit_mode'] = True
        flash('JFrog URL is now unlocked for editing. You can modify the URL field.', 'info')
        return redirect(url_for('integrations'))

    @app.route('/integrations/jfrog/edit_password', methods=['POST'])
    def jfrog_edit_password():
        if 'username' not in session or session.get('role') != 'admin':
            flash('Admin access required', 'error')
            return redirect(url_for('login'))

        # Set a session flag to enable password editing
        session['jfrog_password_edit_mode'] = True
        flash('JFrog password field is now unlocked for editing.', 'info')
        return redirect(url_for('integrations'))

    @app.route('/integrations/jfrog/lock_url', methods=['POST'])
    def jfrog_lock_url():
        if 'username' not in session or session.get('role') != 'admin':
            flash('Admin access required', 'error')
            return redirect(url_for('login'))

        # Clear the session flag to lock URL editing
        session.pop('jfrog_url_edit_mode', None)
        flash('JFrog URL field is now locked.', 'success')
        return redirect(url_for('integrations'))

    @app.route('/integrations/jfrog/lock_password', methods=['POST'])
    def jfrog_lock_password():
        if 'username' not in session or session.get('role') != 'admin':
            flash('Admin access required', 'error')
            return redirect(url_for('login'))

        # Clear the session flag to lock password editing
        session.pop('jfrog_password_edit_mode', None)
        flash('JFrog password field is now locked.', 'success')
        return redirect(url_for('integrations'))

    # Vault Integration API routes
    @app.route('/api/integrations/vault/config', methods=['GET', 'POST'])
    def vault_config():
        if 'username' not in session or session.get('role') != 'admin':
            return jsonify({'error': 'Admin access required'}), 401

        try:
            from PackageBuilder.integration_manager import integration_manager
        except ImportError:
            return jsonify({'error': 'Integration system not available'}), 500

        if request.method == 'GET':
            result = integration_manager.get_integration_config('vault')
            return jsonify(result)

        elif request.method == 'POST':
            form_data = request.form if request.content_type.startswith('multipart/form-data') else request.get_json()

            integration_data = {
                'integration_type': 'vault',
                'integration_name': 'Primary Vault',
                'base_url': form_data.get('vault_url'),
                'auth_type': 'token',
                'token': form_data.get('vault_token'),
                'username': form_data.get('vault_username'),
                'password': form_data.get('vault_user_password'),
                'is_enabled': True,
                'config_details': {
                    'auth_method': form_data.get('vault_auth_method', 'token'),
                    'mount_path': form_data.get('vault_mount_path', 'secret'),
                    'app_path': form_data.get('vault_app_path', 'msifactory'),
                    'ssl_verify': form_data.get('vault_ssl_verify', True),
                    'auto_renew': form_data.get('vault_auto_renew', True),
                    'role_id': form_data.get('vault_role_id'),
                    'secret_id': form_data.get('vault_secret_id')
                }
            }

            result = integration_manager.save_integration_config(integration_data, session.get('username'))

            if result['success']:
                return jsonify({'success': True, 'message': result['message']})
            else:
                return jsonify({'error': result['error']}), 400

    @app.route('/api/integrations/vault/test', methods=['POST'])
    def test_vault():
        if 'username' not in session or session.get('role') != 'admin':
            return jsonify({'error': 'Admin access required'}), 401

        try:
            from PackageBuilder.integration_manager import integration_manager
        except ImportError:
            return jsonify({'error': 'Integration system not available'}), 500

        result = integration_manager.test_integration_connection(
            'vault', 'Primary Vault', session.get('username')
        )

        return jsonify(result)

    @app.route('/api/integrations/vault/secrets', methods=['GET'])
    def vault_secrets():
        if 'username' not in session or session.get('role') != 'admin':
            return jsonify({'error': 'Admin access required'}), 401

        try:
            from PackageBuilder.integration_manager import integration_manager
        except ImportError:
            return jsonify({'error': 'Integration system not available'}), 500

        # For now, return a placeholder response since we don't have Vault secrets management implemented yet
        return jsonify({
            'success': True,
            'secrets': [
                {
                    'path': 'msifactory/database',
                    'keys': ['username', 'password'],
                    'updated': '2025-01-01T00:00:00Z'
                },
                {
                    'path': 'msifactory/jfrog',
                    'keys': ['api_key'],
                    'updated': '2025-01-01T00:00:00Z'
                }
            ]
        })

    # Component Branches API
    @app.route('/api/components/<int:component_id>/branches', methods=['GET', 'POST'])
    def component_branches(component_id):
        if 'username' not in session:
            return jsonify({'error': 'Authentication required'}), 401

        if request.method == 'GET':
            try:
                branches = get_component_branches(component_id)
                return jsonify({'success': True, 'branches': branches})
            except Exception as e:
                return jsonify({'error': str(e)}), 500

        elif request.method == 'POST':
            if session.get('role') not in ['admin', 'poweruser']:
                return jsonify({'error': 'Insufficient permissions'}), 403

            try:
                data = request.get_json()
                branch_name = data.get('branch_name')
                branch_status = data.get('branch_status', 'active')

                if not branch_name:
                    return jsonify({'error': 'Branch name is required'}), 400

                success, message = add_component_branch(component_id, branch_name, branch_status, session.get('username'))
                if success:
                    return jsonify({'success': True, 'message': message})
                else:
                    return jsonify({'error': message}), 400

            except Exception as e:
                return jsonify({'error': str(e)}), 500

    @app.route('/api/components/<int:component_id>/branches/<int:branch_id>', methods=['PUT', 'DELETE'])
    def component_branch_detail(component_id, branch_id):
        if 'username' not in session:
            return jsonify({'error': 'Authentication required'}), 401

        if session.get('role') not in ['admin', 'poweruser']:
            return jsonify({'error': 'Insufficient permissions'}), 403

        if request.method == 'PUT':
            try:
                data = request.get_json()
                success, message = update_component_branch(branch_id, data, session.get('username'))
                if success:
                    return jsonify({'success': True, 'message': message})
                else:
                    return jsonify({'error': message}), 400
            except Exception as e:
                return jsonify({'error': str(e)}), 500

        elif request.method == 'DELETE':
            try:
                success, message = delete_component_branch(branch_id, session.get('username'))
                if success:
                    return jsonify({'success': True, 'message': message})
                else:
                    return jsonify({'error': message}), 400
            except Exception as e:
                return jsonify({'error': str(e)}), 500


    # Admin routes
    @app.route('/admin')
    def admin_panel():
        if 'username' not in session or session.get('role') != 'admin':
            flash('Admin access required', 'error')
            return redirect(url_for('login'))

        return render_template('admin.html')

    @app.route('/user-management')
    def user_management():
        """User Management page for admins"""
        if 'username' not in session or session.get('role') != 'admin':
            flash('Admin access required', 'error')
            return redirect(url_for('login'))

        # Import the new function
        from core.database_operations import get_all_users_with_sql_projects

        # Get users directly from SQL database (no JSON dependency)
        all_users = get_all_users_with_sql_projects()
        # Use ProjectManager API to get all projects
        from core.project_manager_api import get_all_projects
        all_projects = get_all_projects()

        # Calculate statistics from SQL data
        stats = {
            'total_users': len(all_users),
            'admin_users': len([u for u in all_users if u['role'] == 'admin']),
            'regular_users': len([u for u in all_users if u['role'] == 'user']),
            'active_users': len([u for u in all_users if u.get('is_active', True)])
        }

        return render_template('user_management.html',
                             all_users=all_users,
                             all_projects=all_projects,
                             **stats)

    # Validation API endpoints (for enhanced client-side validation)
    @app.route('/api/validate/project', methods=['POST'])
    def validate_project_api():
        """Server-side project validation endpoint"""
        if 'username' not in session:
            return jsonify({'error': 'Authentication required'}), 401

        project_data = {
            'project_name': request.form.get('project_name', ''),
            'project_key': request.form.get('project_key', ''),
            'project_type': request.form.get('project_type', ''),
            'owner_team': request.form.get('owner_team', ''),
            'project_guid': request.form.get('project_guid', ''),
        }

        validation_result = validate_form_data('project', project_data)
        return jsonify(validation_result.__dict__)

    @app.route('/api/validate/component-name', methods=['POST'])
    def validate_component_name():
        """Real-time component name validation endpoint"""
        if 'username' not in session:
            return jsonify({'error': 'Authentication required'}), 401

        try:
            data = request.get_json()
            component_name = data.get('component_name', '').strip()
            project_id = data.get('project_id')
            component_id = data.get('component_id')  # For edit operations

            # Use the utility function for validation
            from core.utilities import validate_component_name_unique, auto_populate_application_name
            validation_result = validate_component_name_unique(component_name, project_id, component_id)

            # Add auto-populated application name if component name is valid
            if validation_result['valid'] and component_name:
                validation_result['suggested_app_name'] = auto_populate_application_name(component_name)

            return jsonify(validation_result)

        except Exception as e:
            log_error(f"Error validating component name: {e}")
            return jsonify({'error': 'Validation error'}), 500

    @app.route('/api/suggest/component-names', methods=['POST'])
    def suggest_component_names():
        """Suggest alternative component names endpoint"""
        if 'username' not in session:
            return jsonify({'error': 'Authentication required'}), 401

        try:
            data = request.get_json()
            base_name = data.get('base_name', '').strip()
            project_id = data.get('project_id')

            if not base_name or not project_id:
                return jsonify({'suggestions': []})

            from core.utilities import suggest_component_name_alternatives
            suggestions = suggest_component_name_alternatives(base_name, project_id)

            return jsonify({'suggestions': suggestions})

        except Exception as e:
            log_error(f"Error suggesting component names: {e}")
            return jsonify({'error': 'Suggestion error'}), 500

    @app.route('/api/validate/component', methods=['POST'])
    def validate_component_api():
        """Server-side component validation endpoint"""
        if 'username' not in session:
            return jsonify({'error': 'Authentication required'}), 401

        component_data = {
            'component_name': request.form.get('component_name', ''),
            'component_type': request.form.get('component_type', ''),
            'framework': request.form.get('framework', ''),
        }

        # Get existing components for duplicate check
        project_id = request.form.get('project_id')
        existing_components = []
        if project_id:
            try:
                existing_components = [comp['component_name'] for comp in get_project_components(project_id)]
            except:
                pass

        validation_result = validate_form_data('component', component_data,
                                            existing_components=existing_components)
        return jsonify(validation_result.__dict__)

    # Testing routes (can be removed in production)
    @app.route('/test/component-cascade')
    def test_component_cascade():
        """Test route for component status cascading functionality"""
        if 'username' not in session or session.get('role') != 'admin':
            return jsonify({'error': 'Admin access required'}), 401

        from core.project_manager import test_component_cascade_logic
        result = test_component_cascade_logic()
        return jsonify(result)

    # Additional routes required by templates
    @app.route('/cmdb/assignments')
    def cmdb_assignments():
        """CMDB server assignments page"""
        if 'username' not in session or session.get('role') != 'admin':
            flash('Admin access required', 'error')
            return redirect(url_for('login'))
        return render_template('cmdb_assignments.html')

    @app.route('/cmdb/utilization')
    def cmdb_utilization():
        """CMDB utilization report page"""
        if 'username' not in session or session.get('role') != 'admin':
            flash('Admin access required', 'error')
            return redirect(url_for('login'))
        return render_template('cmdb_utilization.html')

    @app.route('/cmdb/groups')
    def cmdb_groups():
        """CMDB server groups page"""
        if 'username' not in session or session.get('role') != 'admin':
            flash('Admin access required', 'error')
            return redirect(url_for('login'))
        return render_template('cmdb_groups.html')

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

    @app.route('/component-configuration')
    def component_configuration():
        """Component configuration page with CRUD operations"""
        if 'username' not in session or session.get('role') != 'admin':
            flash('Admin access required', 'error')
            return redirect(url_for('login'))

        # Get all components with their project information
        components = get_all_components_from_database()

        # Get all projects for the "Add Component" form
        # Use ProjectManager API to get all projects
        from core.project_manager_api import get_all_projects
        projects = get_all_projects()

        return render_template('component_configuration.html',
                             components=components,
                             projects=projects)

    # HTMX Component CRUD Routes
    @app.route('/htmx/component/add-form', methods=['GET'])
    def htmx_component_add_form():
        """HTMX endpoint to show the add component form"""
        if 'username' not in session or session.get('role') != 'admin':
            return '<div class="alert alert-danger">Admin access required</div>'

        # Get all projects for the dropdown
        # Use ProjectManager API to get all projects
        from core.project_manager_api import get_all_projects
        projects = get_all_projects()
        return render_template('htmx/add_component_form.html', projects=projects)

    @app.route('/htmx/component/add', methods=['POST'])
    def htmx_component_add():
        """HTMX endpoint to add a new component"""
        if 'username' not in session or session.get('role') != 'admin':
            return '<div class="alert alert-danger">Admin access required</div>'

        try:
            # Extract form data
            project_id = request.form.get('project_id')
            component_name = request.form.get('component_name')
            component_type = request.form.get('component_type')
            framework = request.form.get('framework')
            component_guid = request.form.get('component_guid')

            # Validate required fields
            if not all([project_id, component_name, component_type, framework]):
                return '<div class="alert alert-danger">All required fields must be filled</div>'

            # Use ComponentFormHandler to process the component
            handler = ComponentFormHandler()
            result = handler.process_add_component(request.form, int(project_id), "")

            if result['success']:
                # Add component to database using ComponentManager API
                from core.component_manager import create_component
                component_data = result['component_data']
                success, message, component_id = create_component(
                    int(project_id),
                    component_data,
                    session.get('username')
                )

                if success:
                    # Return the new component card HTML using ComponentManager API
                    from core.component_manager import ComponentManager
                    component_manager = ComponentManager()
                    new_component = component_manager.get_component_by_id(component_id)
                    return render_template('htmx/component_card.html', component=new_component)
                else:
                    return f'<div class="alert alert-danger">Error adding component: {message}</div>'
            else:
                return f'<div class="alert alert-danger">Validation error: {result["message"]}</div>'

        except Exception as e:
            log_error(f"Error adding component: {str(e)}")
            return '<div class="alert alert-danger">An error occurred while adding the component</div>'

    @app.route('/htmx/component/search', methods=['POST'])
    def htmx_component_search():
        """HTMX endpoint to search components"""
        if 'username' not in session or session.get('role') != 'admin':
            return '<div class="alert alert-danger">Admin access required</div>'

        search_term = request.form.get('search', '').lower()
        components = get_all_components_from_database()

        # Filter components based on search term
        if search_term:
            filtered_components = []
            for component in components:
                if (search_term in component.get('component_name', '').lower() or
                    search_term in component.get('project_name', '').lower() or
                    search_term in component.get('component_guid', '').lower()):
                    filtered_components.append(component)
            components = filtered_components

        return render_template('htmx/components_grid.html', components=components)

    @app.route('/htmx/component/<int:component_id>/config', methods=['GET'])
    def htmx_component_config(component_id):
        """HTMX endpoint to show component configuration form"""
        if 'username' not in session or session.get('role') != 'admin':
            return '<div class="alert alert-danger">Admin access required</div>'

        from core.database_operations import get_component_by_id_from_database
        component = get_component_by_id_from_database(component_id)

        if not component:
            return '<div class="alert alert-danger">Component not found</div>'

        return render_template('htmx/component_config_form.html', component=component)


    @app.route('/htmx/component/<int:component_id>/details', methods=['GET'])
    def htmx_component_details(component_id):
        """HTMX endpoint to show component details modal"""
        if 'username' not in session or session.get('role') != 'admin':
            return '<div class="alert alert-danger">Admin access required</div>'

        from core.database_operations import get_component_by_id_from_database
        component = get_component_by_id_from_database(component_id)

        if not component:
            return '<div class="alert alert-danger">Component not found</div>'

        return render_template('htmx/component_details_modal.html', component=component)

    @app.route('/htmx/component/hide-form', methods=['GET'])
    def htmx_component_hide_form():
        """HTMX endpoint to hide the add component form"""
        return ''  # Return empty content to clear the form

    @app.route('/htmx/component/generate-guid', methods=['POST'])
    def htmx_component_generate_guid():
        """HTMX endpoint to generate component GUID"""
        import uuid
        import random

        project_id = request.form.get('project_id')
        if project_id:
            # Get project key for generating project-specific GUID
            # Use ProjectManager API to get project
            from core.project_manager_api import get_project
            project = get_project(int(project_id))
            if project and project.get('project_key'):
                project_key = project['project_key']

                # Generate project-specific component GUID
                clean_project_key = project_key[:8].ljust(8, '0')
                section1 = f"{random.randint(0, 65535):04X}"
                section2 = f"{random.randint(0, 65535):04X}"
                section3 = f"{random.randint(0, 65535):04X}"

                component_guid = f"{clean_project_key}-{section1}-{section2}-{section3}"
            else:
                # Generate standard UUID if project not found
                component_guid = str(uuid.uuid4())
        else:
            # Generate standard UUID if no project selected
            component_guid = str(uuid.uuid4())

        return f'<input type="text" name="component_guid" id="componentGuidInput" class="form-control bg-light" readonly value="{component_guid}">'

    @app.route('/htmx/component/toggle-fields', methods=['POST'])
    def htmx_component_toggle_fields():
        """HTMX endpoint to show/hide type-specific fields"""
        component_type = request.form.get('component_type')

        if component_type in ['webapp', 'website', 'api']:
            return '''
            <div class="mb-3">
                <h6 class="text-primary mb-2"><i class="fas fa-globe me-1"></i>IIS Configuration</h6>
                <div class="row">
                    <div class="col-md-4">
                        <label class="form-label">Website Name</label>
                        <input type="text" name="iis_website_name" class="form-control" placeholder="Default Web Site">
                    </div>
                    <div class="col-md-4">
                        <label class="form-label">Application Pool</label>
                        <input type="text" name="iis_app_pool_name" class="form-control" placeholder="DefaultAppPool">
                    </div>
                    <div class="col-md-4">
                        <label class="form-label">Port</label>
                        <input type="number" name="iis_port" class="form-control" placeholder="80">
                    </div>
                </div>
            </div>
            '''
        elif component_type in ['service', 'scheduler']:
            return '''
            <div class="mb-3">
                <h6 class="text-primary mb-2"><i class="fas fa-cog me-1"></i>Service Configuration</h6>
                <div class="row">
                    <div class="col-md-6">
                        <label class="form-label">Service Name</label>
                        <input type="text" name="service_name" class="form-control" placeholder="MyService">
                    </div>
                    <div class="col-md-6">
                        <label class="form-label">Service Display Name</label>
                        <input type="text" name="service_display_name" class="form-control" placeholder="My Application Service">
                    </div>
                </div>
            </div>
            '''
        else:
            return ''  # No type-specific fields

    # Access request routes
    @app.route('/access-request/<username>', methods=['GET', 'POST'])
    def access_request(username):
        """Access request page and form handling"""
        if request.method == 'POST':
            # Handle access request form submission
            try:
                # Get form data including new role fields
                request_data = {
                    'username': request.form.get('username'),
                    'email': request.form.get('email'),
                    'first_name': request.form.get('first_name'),
                    'middle_name': request.form.get('middle_name', ''),
                    'last_name': request.form.get('last_name'),
                    'department': request.form.get('department', ''),
                    'requested_role': request.form.get('requested_role', 'user'),
                    'manager_email': request.form.get('manager_email', ''),
                    'app_short_key': request.form.get('app_short_key'),
                    'reason': request.form.get('reason')
                }

                # Basic validation
                if not all([request_data['username'], request_data['email'],
                           request_data['first_name'], request_data['last_name'],
                           request_data['department'], request_data['app_short_key'],
                           request_data['reason']]):
                    flash('All required fields must be filled out', 'error')
                    return render_template('access_request.html', username=username)

                # Validate requested role
                valid_roles = ['user', 'poweruser', 'admin']
                if request_data['requested_role'] not in valid_roles:
                    request_data['requested_role'] = 'user'

                # Create new user in database with pending status
                try:
                    conn_str = (
                        "DRIVER={ODBC Driver 17 for SQL Server};"
                        "SERVER=SUMEETGILL7E47\\MSSQLSERVER01;"
                        "DATABASE=MSIFactory;"
                        "Trusted_Connection=yes;"
                        "Connection Timeout=10;"
                    )

                    with pyodbc.connect(conn_str) as conn:
                        with conn.cursor() as cursor:
                            # Check if username already exists
                            cursor.execute("SELECT username FROM users WHERE username = ?",
                                         (request_data['username'],))
                            if cursor.fetchone():
                                flash('Username already exists. Please choose a different username.', 'error')
                                return render_template('access_request.html', username=username, applications=applications)

                            # Check if email already exists
                            cursor.execute("SELECT email FROM users WHERE email = ?",
                                         (request_data['email'],))
                            if cursor.fetchone():
                                flash('Email already registered. Please use a different email address.', 'error')
                                return render_template('access_request.html', username=username, applications=applications)

                            # Insert new user with pending status
                            # Start with 'user' role regardless of request - admin will approve role later
                            insert_sql = """
                                INSERT INTO users (username, email, first_name, middle_name, last_name,
                                                 role, status, is_active, created_date)
                                VALUES (?, ?, ?, ?, ?, ?, 'pending', 1, GETDATE())
                            """

                            cursor.execute(insert_sql, (
                                request_data['username'],
                                request_data['email'],
                                request_data['first_name'],
                                request_data['middle_name'],
                                request_data['last_name'],
                                'user'  # Always start as user, admin can promote later
                            ))

                            # Get the new user ID for logging
                            user_id = cursor.lastrowid
                            conn.commit()

                            # Log the access request with role information
                            role_info = f"Requested role: {request_data['requested_role'].upper()}"
                            if request_data['requested_role'] == 'poweruser':
                                role_info += " (Technical Project Manager)"
                            elif request_data['requested_role'] == 'admin':
                                role_info += " (Full Administrator Access)"

                            logging.info(f"ACCESS_REQUEST: User {request_data['username']} requested access to {request_data['app_short_key']} | {role_info} | Department: {request_data['department']}")

                except pyodbc.Error as db_error:
                    logging.error(f"Database error creating user: {str(db_error)}")
                    flash('Error creating user account. Please try again.', 'error')
                    return render_template('access_request.html', username=username)

                # Success message with role information
                role_msg = ""
                if request_data['requested_role'] == 'poweruser':
                    role_msg = " Your PowerUser role request (Technical Project Manager) will be reviewed for component CRUD permissions."
                elif request_data['requested_role'] == 'admin':
                    role_msg = " Your Administrator role request will require additional approval."

                flash(f"Access request submitted successfully for {request_data['username']}!{role_msg} You will receive an email notification once approved.", 'success')
                return redirect(url_for('login'))

            except Exception as e:
                logging.error(f"Error processing access request: {str(e)}")
                flash('Error processing your request. Please try again.', 'error')

        # Get available applications for the form
        try:
            # Use ProjectManager API to get all projects
            from core.project_manager_api import get_all_projects
            applications = get_all_projects()
        except:
            applications = [
                {'app_short_key': 'WEBAPP01', 'app_name': 'Web Application 01', 'description': 'Main web application', 'owner_team': 'Development', 'status': 'Active'},
                {'app_short_key': 'API01', 'app_name': 'API Service 01', 'description': 'Core API service', 'owner_team': 'Backend', 'status': 'Active'},
                {'app_short_key': 'PORTAL', 'app_name': 'User Portal', 'description': 'Customer portal application', 'owner_team': 'Frontend', 'status': 'Active'}
            ]

        # Auto-populate Windows username if this is a new user request
        auto_populated_data = {}
        if username == 'new_user':
            from core.utilities import get_auto_populated_user_data
            auto_populated_data = get_auto_populated_user_data('company.com')

        return render_template('access_request.html',
                             username=username,
                             applications=applications,
                             auto_populated_data=auto_populated_data)

    @app.route('/update-user-projects', methods=['POST'])
    def update_user_projects():
        """Update user's project access"""
        if 'username' not in session or session.get('role') != 'admin':
            flash('Admin access required', 'error')
            return redirect(url_for('login'))

        username = request.form['username']
        all_projects_access = 'all_projects_access' in request.form
        project_keys = request.form.getlist('project_keys')

        from sql_only_functions import update_user_projects_in_database_sql_only
        success, message = update_user_projects_in_database_sql_only(username, project_keys, all_projects_access)

        if success:
            log_info(f"USER_PROJECTS_UPDATED: User: {username}, Updated by: {session.get('username')}")
            flash(message, 'success')
        else:
            flash(message, 'error')

        return redirect(url_for('user_management'))

    @app.route('/edit-user-projects/<username>')
    def edit_user_projects(username):
        """Python-only page for editing user projects (no JavaScript)"""
        if 'username' not in session or session.get('role') != 'admin':
            flash('Admin access required', 'error')
            return redirect(url_for('login'))

        # Get user's current project assignments
        from sql_only_functions import get_user_project_details_from_database_sql_only
        user_details = get_user_project_details_from_database_sql_only(username)

        if not user_details:
            flash(f'User {username} not found', 'error')
            return redirect(url_for('user_management'))

        # Get all available projects
        # Use ProjectManager API to get all projects
        from core.project_manager_api import get_all_projects
        all_projects = get_all_projects()

        # Get user info for display
        from core.database_operations import get_user_by_username_sql
        user_info = get_user_by_username_sql(username)

        return render_template('edit_user_projects.html',
                             user_details=user_details,
                             user_info=user_info,
                             all_projects=all_projects)

    @app.route('/api/user-projects/<username>')
    def api_user_projects(username):
        """API endpoint to get user's project details"""
        if 'username' not in session or session.get('role') != 'admin':
            return jsonify({'error': 'Unauthorized'}), 401

        from sql_only_functions import get_user_project_details_from_database_sql_only
        project_details = get_user_project_details_from_database_sql_only(username)
        return jsonify(project_details)

    @app.route('/api/toggle-user-status/<username>', methods=['POST'])
    def api_toggle_user_status(username):
        """API endpoint to toggle user status"""
        if 'username' not in session or session.get('role') != 'admin':
            return jsonify({'error': 'Unauthorized'}), 401

        # Import SQL function
        from core.database_operations import toggle_user_status_sql

        success, message = toggle_user_status_sql(username)

        if success:
            log_info(f"USER_STATUS_TOGGLED: User: {username}, Changed by: {session.get('username')}")

        return jsonify({'success': success, 'message': message})

    @app.route('/cmdb/servers/add', methods=['POST'])
    def cmdb_add_server_submit():
        """Handle server creation form submission"""
        if 'username' not in session or session.get('role') != 'admin':
            flash('Admin access required', 'error')
            return redirect(url_for('login'))

        success, server_id, message = add_cmdb_server(
            request.form,
            session.get('username')
        )

        if success:
            flash(message, 'success')
            return redirect(url_for('cmdb_server_detail', server_id=server_id))
        else:
            flash(message, 'error')
            return redirect(url_for('cmdb_add_server'))

    # Permission Control Routes
    @app.route('/permission_control')
    def permission_control():
        """Display permission control page for admins"""
        if 'username' not in session or session.get('role') != 'admin':
            flash('Admin access required', 'error')
            return redirect(url_for('login'))

        user_id = request.args.get('user_id')
        selected_user = None
        current_permissions = []

        # Get all non-admin users
        from core.database_operations import get_all_users_with_sql_projects
        all_users = get_all_users_with_sql_projects()
        users = [u for u in all_users if u.get('role') != 'admin']

        # Get permission presets using API-first pattern
        presets = get_permission_presets(api_client)

        # If a user is selected, get their details and permissions
        if user_id:
            try:
                user_id = int(user_id)
                selected_user = next((u for u in users if u.get('user_id') == user_id), None)
                if selected_user:
                    current_permissions = get_user_permissions(user_id, api_client)
            except (ValueError, TypeError):
                pass

        # Get all users with special permissions using API-first pattern
        users_with_permissions = get_users_with_permissions(api_client)

        return render_template('permission_control.html',
                             users=users,
                             selected_user=selected_user,
                             current_permissions=current_permissions,
                             presets=presets,
                             users_with_permissions=users_with_permissions)

    @app.route('/permission_control/grant', methods=['POST'])
    def grant_permission():
        """Grant permissions to a user"""
        if 'username' not in session or session.get('role') != 'admin':
            flash('Admin access required', 'error')
            return redirect(url_for('login'))

        user_id = request.form.get('user_id')
        permissions = request.form.getlist('permissions')
        expires_date = request.form.get('expires_date')
        description = request.form.get('description')

        if not user_id or not permissions:
            flash('Please select a user and at least one permission', 'error')
            return redirect(url_for('permission_control', user_id=user_id))

        try:
            user_id = int(user_id)
            granted_by = session.get('username')

            # Grant each permission
            for permission_type in permissions:
                success, message = grant_user_permission(
                    user_id, permission_type, granted_by,
                    expires_date, description
                )
                if not success:
                    flash(f'Error granting {permission_type}: {message}', 'error')

            flash('Permissions granted successfully', 'success')
            log_info(f"PERMISSIONS_GRANTED: User ID: {user_id}, Permissions: {permissions}, Granted by: {granted_by}")

        except Exception as e:
            flash(f'Error granting permissions: {str(e)}', 'error')
            log_error(f"Error granting permissions: {str(e)}")

        return redirect(url_for('permission_control', user_id=user_id))

    @app.route('/permission_control/revoke', methods=['POST'])
    def revoke_permission():
        """Revoke a permission from a user"""
        if 'username' not in session or session.get('role') != 'admin':
            flash('Admin access required', 'error')
            return redirect(url_for('login'))

        permission_id = request.form.get('permission_id')
        user_id = request.form.get('user_id')

        if not permission_id:
            flash('Invalid permission ID', 'error')
            return redirect(url_for('permission_control'))

        try:
            permission_id = int(permission_id)
            success, message = revoke_user_permission(permission_id)

            if success:
                flash('Permission revoked successfully', 'success')
                log_info(f"PERMISSION_REVOKED: Permission ID: {permission_id}, Revoked by: {session.get('username')}")
            else:
                flash(f'Error revoking permission: {message}', 'error')

        except Exception as e:
            flash(f'Error revoking permission: {str(e)}', 'error')
            log_error(f"Error revoking permission: {str(e)}")

        return redirect(url_for('permission_control', user_id=user_id))

    # Error handlers
    @app.errorhandler(404)
    def not_found(e):
        return render_template('error.html', error='Page not found'), 404

    @app.errorhandler(500)
    def server_error(e):
        return render_template('error.html', error='Internal server error'), 500