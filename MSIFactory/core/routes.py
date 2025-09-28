"""
Routes Module
Contains all Flask route definitions
"""

from flask import render_template, request, redirect, url_for, session, flash, jsonify
from core.database_operations import (
    simple_delete_project_from_database,
    delete_project_from_database,
    get_user_projects_from_database,
    get_all_projects_from_database,
    update_user_projects_in_database,
    get_user_project_details_from_database,
    get_project_by_id_from_database,
    debug_user_project_access,
    get_detailed_projects,
    get_all_components_from_database
)
from core.form_handlers import ProjectFormHandler, ComponentFormHandler
from core.validators import validate_form_data
from core.project_manager import (
    add_project_to_database,
    edit_project_in_database,
    add_component_to_project,
    update_component_in_project,
    remove_component_from_project,
    get_project_components,
    get_project_environments,
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
from core.integrations import (
    get_integration_config,
    save_integration_config,
    test_servicenow_connection,
    sync_servicenow_servers,
    test_vault_connection,
    get_vault_secrets,
    list_vault_secrets,
    get_all_integrations_status
)
from logger import log_info

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
        all_detailed_projects = get_detailed_projects()

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

        all_projects = get_detailed_projects()
        return render_template('project_management.html', all_projects=all_projects)

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

        # Process with the database function
        success, project_id, message = add_project_to_database(
            request.form,
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

        # Debug logging for status field
        status_in_form = request.form.get('status')
        log_info(f"DEBUG: Route received project_id: {project_id}, status: '{status_in_form}'")
        log_info(f"DEBUG: Route form keys: {list(request.form.keys())}")

        success, message = edit_project_in_database(request.form, project_id, session.get('username'))

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

        project = get_project_by_id_from_database(project_id)
        if not project:
            flash('Project not found', 'error')
            return redirect(url_for('project_management'))

        components = get_project_components(project_id)
        environments = get_project_environments(project_id)

        return render_template('edit_project.html',
                             project=project,
                             components=components,
                             environments=environments)

    @app.route('/delete-project', methods=['POST'])
    def delete_project():
        if 'username' not in session or session.get('role') != 'admin':
            return jsonify({'error': 'Admin access required'}), 401

        project_id = request.form.get('project_id')

        # Try simple deletion first
        success, message = simple_delete_project_from_database(project_id)
        if not success:
            # If simple deletion fails, try complex deletion
            success, message = delete_project_from_database(project_id)

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

        # Get the project
        project = get_project_by_id_from_database(project_id)
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
        environments = get_project_environments(project_id)

        return render_template('project_detail.html',
                             project=project,
                             components=components,
                             environments=environments,
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
        project = get_project_by_id_from_database(component['project_id'])
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
    @app.route('/add-component', methods=['POST'])
    def add_component():
        if 'username' not in session or session.get('role') != 'admin':
            return jsonify({'error': 'Admin access required'}), 401

        project_id = request.form.get('project_id')
        project_key = request.form.get('project_key', 'PROJ')

        # Use new component form handler for enhanced processing
        handler = ComponentFormHandler()
        result = handler.process_add_component(request.form, project_id, project_key)

        if not result['success']:
            return jsonify({'error': result['error']}), 400

        success, component_id, message = add_component_to_project(
            project_id,
            result['component_data'],
            session.get('username')
        )

        if success:
            return jsonify({'success': True, 'message': message})
        else:
            return jsonify({'error': message}), 400

    @app.route('/remove-component', methods=['POST'])
    def remove_component():
        if 'username' not in session or session.get('role') != 'admin':
            return jsonify({'error': 'Admin access required'}), 401

        component_id = request.form.get('component_id')

        # Enhanced validation for component deletion
        if not component_id:
            return jsonify({'error': 'Component ID is required'}), 400

        try:
            component_id = int(component_id)
        except (ValueError, TypeError):
            return jsonify({'error': 'Invalid component ID format'}), 400

        # Check if component exists
        from core.project_manager import get_component_details
        component = get_component_details(component_id)
        if not component:
            return jsonify({'error': 'Component not found'}), 404

        # Check for active dependencies
        from core.htmx_views import check_component_dependencies
        dependencies = check_component_dependencies(component_id)
        if dependencies['has_dependencies']:
            return jsonify({
                'error': f'Cannot delete component "{component["component_name"]}" - it has active dependencies',
                'dependencies': dependencies
            }), 409

        # Log deletion attempt
        log_info(f"User {session.get('username')} attempting to delete component {component['component_name']} (ID: {component_id})")

        success, message = remove_component_from_project(component_id)

        if success:
            log_info(f"Component {component['component_name']} successfully deleted by {session.get('username')}")
            return jsonify({'success': True, 'message': message})
        else:
            log_error(f"Failed to delete component {component['component_name']}: {message}")
            return jsonify({'error': message}), 400

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

        success, message = update_component_in_project(component_id, component_data, session.get('username'))

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
            projects = get_all_projects_from_database()
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
            projects = get_user_projects_from_database(session['username'], None)
            return render_template('generate_msi.html', projects=projects)

        # Handle MSI generation request
        project_id = request.form.get('project_id')
        component_id = request.form.get('component_id')

        project = get_project_by_id_from_database(project_id)
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

        integrations_list = get_all_integrations_status()
        return render_template('integrations.html', integrations=integrations_list)

    @app.route('/api/integrations/servicenow/config', methods=['GET', 'POST'])
    def servicenow_config():
        if 'username' not in session or session.get('role') != 'admin':
            return jsonify({'error': 'Admin access required'}), 401

        if request.method == 'GET':
            config = get_integration_config('servicenow')
            return jsonify(config)

        success, message = save_integration_config(
            'servicenow',
            request.json,
            session.get('username')
        )

        if success:
            return jsonify({'success': True, 'message': message})
        else:
            return jsonify({'error': message}), 400

    @app.route('/api/integrations/servicenow/test', methods=['POST'])
    def test_servicenow():
        if 'username' not in session or session.get('role') != 'admin':
            return jsonify({'error': 'Admin access required'}), 401

        config = request.json
        success, message = test_servicenow_connection(config)

        if success:
            return jsonify({'success': True, 'message': message})
        else:
            return jsonify({'error': message}), 400

    @app.route('/api/integrations/servicenow/sync', methods=['POST'])
    def sync_servicenow():
        if 'username' not in session or session.get('role') != 'admin':
            return jsonify({'error': 'Admin access required'}), 401

        config = get_integration_config('servicenow')
        success, count, message = sync_servicenow_servers(config)

        if success:
            return jsonify({'success': True, 'count': count, 'message': message})
        else:
            return jsonify({'error': message}), 400

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
        all_projects = get_all_projects_from_database()

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
        """Component configuration page"""
        if 'username' not in session or session.get('role') != 'admin':
            flash('Admin access required', 'error')
            return redirect(url_for('login'))

        components = get_all_components_from_database()
        return render_template('component_configuration.html', components=components)

    # Access request routes
    @app.route('/access-request/<username>', methods=['GET', 'POST'])
    def access_request(username):
        """Access request page and form handling"""
        if request.method == 'POST':
            # Handle access request form submission
            try:
                # Get form data
                request_data = {
                    'username': request.form.get('username'),
                    'email': request.form.get('email'),
                    'first_name': request.form.get('first_name'),
                    'middle_name': request.form.get('middle_name', ''),
                    'last_name': request.form.get('last_name'),
                    'app_short_key': request.form.get('app_short_key'),
                    'reason': request.form.get('reason')
                }

                # Basic validation
                if not all([request_data['username'], request_data['email'],
                           request_data['first_name'], request_data['last_name'],
                           request_data['app_short_key'], request_data['reason']]):
                    flash('All required fields must be filled out', 'error')
                    return render_template('access_request.html', username=username)

                # Log the access request
                logging.info(f"ACCESS_REQUEST: User {request_data['username']} requested access to {request_data['app_short_key']}")

                # In a real system, this would save to database and send notifications
                # For now, just show success message
                flash(f"Access request submitted successfully for {request_data['username']}. An administrator will review your request.", 'success')
                return redirect(url_for('login'))

            except Exception as e:
                logging.error(f"Error processing access request: {str(e)}")
                flash('Error processing your request. Please try again.', 'error')

        # Get available applications for the form
        try:
            from core.database_operations import get_projects_simple
            applications = get_projects_simple()
        except:
            applications = [
                {'app_short_key': 'WEBAPP01', 'app_name': 'Web Application 01', 'description': 'Main web application', 'owner_team': 'Development', 'status': 'Active'},
                {'app_short_key': 'API01', 'app_name': 'API Service 01', 'description': 'Core API service', 'owner_team': 'Backend', 'status': 'Active'},
                {'app_short_key': 'PORTAL', 'app_name': 'User Portal', 'description': 'Customer portal application', 'owner_team': 'Frontend', 'status': 'Active'}
            ]

        return render_template('access_request.html', username=username, applications=applications)

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
        all_projects = get_all_projects_from_database()

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

    # Error handlers
    @app.errorhandler(404)
    def not_found(e):
        return render_template('error.html', error='Page not found'), 404

    @app.errorhandler(500)
    def server_error(e):
        return render_template('error.html', error='Internal server error'), 500