"""
HTMX Views Module
Handles HTMX requests for dynamic updates - replaces heavy JavaScript
"""

from flask import render_template, request, jsonify, session, flash
from core.utilities import (
    generate_guid, generate_project_component_guid,
    generate_default_values, get_framework_options,
    get_component_type_options, get_environment_options
)
from core.form_handlers import ComponentFormHandler, ProjectFormHandler
from core.validators import validate_form_data
from core.project_manager import add_component_to_project, get_project_components
from core.database_operations import get_db_connection
from logger import get_logger, log_info, log_error

logger = get_logger()

def register_htmx_routes(app, components):
    """Register all HTMX routes with the Flask app"""

    auth_system = components['auth_system']

    @app.route('/htmx/component/new-form')
    def htmx_new_component_form():
        """
        Return new component form fragment
        Replaces JavaScript addNewComponent()
        """
        if 'username' not in session or session.get('role') != 'admin':
            return '<div class="alert alert-danger">Unauthorized</div>', 401

        try:
            project_key = request.args.get('project_key', 'PROJ')
            component_counter = int(request.args.get('counter', 1))

            # Generate component GUID
            component_guid = generate_project_component_guid(project_key, component_counter)

            # Get options for dropdowns
            component_types = get_component_type_options()
            frameworks = get_framework_options()

            # Generate default values
            defaults = generate_default_values('webapp', f'Component{component_counter}', project_key)

            return render_template('fragments/new_component_form.html',
                                 component_counter=component_counter,
                                 component_guid=component_guid,
                                 project_key=project_key,
                                 component_types=component_types,
                                 frameworks=frameworks,
                                 defaults=defaults)

        except Exception as e:
            log_error(f"Error generating new component form: {e}")
            return '<div class="alert alert-danger">Error generating form</div>', 500

    @app.route('/htmx/component/validate', methods=['POST'])
    def htmx_validate_component():
        """
        Validate component data and return feedback
        Replaces JavaScript validation
        """
        try:
            component_data = {
                'component_name': request.form.get('component_name', ''),
                'component_type': request.form.get('component_type', ''),
                'framework': request.form.get('framework', ''),
            }

            # Get existing components for duplicate check
            project_id = request.form.get('project_id')
            existing_components = []
            if project_id:
                existing_components = [comp['component_name'] for comp in get_project_components(project_id)]

            # Validate
            validation_result = validate_form_data('component', component_data,
                                                 existing_components=existing_components)

            return render_template('fragments/validation_feedback.html',
                                 validation=validation_result,
                                 field_prefix='component')

        except Exception as e:
            log_error(f"Error validating component: {e}")
            return '<div class="alert alert-danger">Validation error</div>', 500

    @app.route('/htmx/component/config-fields')
    def htmx_component_config_fields():
        """
        Return component-specific configuration fields
        Replaces JavaScript toggleComponentFields()
        """
        try:
            component_type = request.args.get('component_type', '')
            component_id = request.args.get('component_id', 'new')

            return render_template('fragments/component_config_fields.html',
                                 component_type=component_type,
                                 component_id=component_id)

        except Exception as e:
            log_error(f"Error generating component config fields: {e}")
            return '<div class="alert alert-danger">Error generating fields</div>', 500

    @app.route('/htmx/component/add', methods=['POST'])
    def htmx_add_component():
        """
        Add component via HTMX
        Replaces JavaScript AJAX component addition
        """
        if 'username' not in session or session.get('role') != 'admin':
            return '<div class="alert alert-danger">Unauthorized</div>', 401

        try:
            project_id = request.form.get('project_id')
            project_key = request.form.get('project_key', 'PROJ')

            # Process form data
            handler = ComponentFormHandler()
            result = handler.process_add_component(request.form, project_id, project_key)

            if not result['success']:
                return f'<div class="alert alert-danger">{result["error"]}</div>', 400

            # Add to database
            success, component_id, message = add_component_to_project(
                project_id, result['component_data'], session.get('username')
            )

            if success:
                # Return new component card
                component_data = result['component_data']
                component_data['component_id'] = component_id

                return render_template('fragments/component_card.html',
                                     component=component_data,
                                     is_new=True)
            else:
                return f'<div class="alert alert-danger">{message}</div>', 400

        except Exception as e:
            log_error(f"Error adding component via HTMX: {e}")
            return '<div class="alert alert-danger">Error adding component</div>', 500

    @app.route('/htmx/component/search')
    def htmx_search_components():
        """
        Search components and return filtered results
        Replaces JavaScript filterComponents()
        """
        try:
            search_term = request.args.get('q', '').lower()
            component_type = request.args.get('type', 'all')
            status_filter = request.args.get('status', 'all')

            # Get all components (in real implementation, this would be from database)
            components = get_all_components_for_search()

            # Filter components
            filtered_components = []
            for component in components:
                # Search filter
                if search_term:
                    searchable_text = f"{component['component_name']} {component['project_name']}".lower()
                    if search_term not in searchable_text:
                        continue

                # Type filter
                if component_type != 'all' and component['component_type'] != component_type:
                    continue

                # Status filter
                component_status = 'configured' if component.get('config_id') else 'pending'
                if status_filter != 'all' and component_status != status_filter:
                    continue

                filtered_components.append(component)

            return render_template('fragments/component_grid.html',
                                 components=filtered_components)

        except Exception as e:
            log_error(f"Error searching components: {e}")
            return '<div class="alert alert-danger">Search error</div>', 500

    @app.route('/htmx/project/validate', methods=['POST'])
    def htmx_validate_project():
        """
        Validate project data and return feedback
        Replaces JavaScript validateAndSubmit()
        """
        try:
            project_data = {
                'project_name': request.form.get('project_name', ''),
                'project_key': request.form.get('project_key', ''),
                'project_type': request.form.get('project_type', ''),
                'owner_team': request.form.get('owner_team', ''),
                'project_guid': request.form.get('project_guid', ''),
                'color_primary': request.form.get('color_primary', ''),
                'color_secondary': request.form.get('color_secondary', ''),
            }

            # Validate
            validation_result = validate_form_data('project', project_data)

            return render_template('fragments/validation_feedback.html',
                                 validation=validation_result,
                                 field_prefix='project')

        except Exception as e:
            log_error(f"Error validating project: {e}")
            return '<div class="alert alert-danger">Validation error</div>', 500

    @app.route('/htmx/project/generate-guid', methods=['POST'])
    def htmx_generate_guid():
        """
        Generate new GUID
        Replaces JavaScript generateNewGuid()
        """
        try:
            new_guid = generate_guid()
            return f'<input type="text" class="form-control bg-light" id="project_guid" name="project_guid" value="{new_guid}" readonly>'

        except Exception as e:
            log_error(f"Error generating GUID: {e}")
            return '<div class="alert alert-danger">Error generating GUID</div>', 500

    @app.route('/htmx/project/key-from-name', methods=['POST'])
    def htmx_generate_key_from_name():
        """
        Generate project key from project name
        Replaces JavaScript auto-generation
        """
        try:
            project_name = request.form.get('project_name', '')
            project_key = project_name.upper().replace(' ', '').replace('-', '').replace('_', '')[:10]

            # Remove invalid characters
            import re
            project_key = re.sub(r'[^A-Z0-9]', '', project_key)

            return f'<input type="text" class="form-control" id="project_key" name="project_key" value="{project_key}" required pattern="[A-Z0-9]{{2,10}}" title="2-10 uppercase letters and numbers only" style="text-transform: uppercase;">'

        except Exception as e:
            log_error(f"Error generating project key: {e}")
            return '<input type="text" class="form-control" id="project_key" name="project_key" required>'

    @app.route('/htmx/user/search')
    def htmx_search_users():
        """
        Search users and return filtered results
        Replaces JavaScript user filtering
        """
        try:
            search_term = request.args.get('q', '').lower()

            # Get all users
            all_users = auth_system.load_users()

            # Filter users
            filtered_users = []
            for user in all_users:
                if search_term:
                    searchable_text = f"{user['username']} {user['first_name']} {user['last_name']} {user['email']}".lower()
                    if search_term not in searchable_text:
                        continue

                filtered_users.append(user)

            return render_template('fragments/user_table_rows.html',
                                 users=filtered_users)

        except Exception as e:
            log_error(f"Error searching users: {e}")
            return '<div class="alert alert-danger">Search error</div>', 500

    @app.route('/htmx/user/projects-modal/<username>')
    def htmx_user_projects_modal(username):
        """
        Return user projects management modal
        Replaces JavaScript modal generation
        """
        if 'username' not in session or session.get('role') != 'admin':
            return '<div class="alert alert-danger">Unauthorized</div>', 401

        try:
            # Get user info
            user = auth_system.check_user_login(username)
            if not user:
                return '<div class="alert alert-danger">User not found</div>', 404

            # Get all projects
            from core.database_operations import get_all_projects_from_database
            all_projects = get_all_projects_from_database()

            # Get user's current projects
            user_projects = user.get('approved_apps', [])
            has_all_access = '*' in user_projects

            return render_template('fragments/user_projects_modal.html',
                                 user=user,
                                 all_projects=all_projects,
                                 user_projects=user_projects,
                                 has_all_access=has_all_access)

        except Exception as e:
            log_error(f"Error generating user projects modal: {e}")
            return '<div class="alert alert-danger">Error loading user projects</div>', 500

    @app.route('/htmx/integration/test-connection', methods=['POST'])
    def htmx_test_integration_connection():
        """
        Test integration connection
        Replaces JavaScript connection testing
        """
        if 'username' not in session or session.get('role') != 'admin':
            return '<div class="alert alert-danger">Unauthorized</div>', 401

        try:
            integration_type = request.form.get('integration_type')

            if integration_type == 'servicenow':
                from core.integrations import test_servicenow_connection

                config_data = {
                    'instance': request.form.get('instance'),
                    'username': request.form.get('username'),
                    'password': request.form.get('password')
                }

                success, message = test_servicenow_connection(config_data)

            elif integration_type == 'vault':
                from core.integrations import test_vault_connection

                config_data = {
                    'url': request.form.get('url'),
                    'token': request.form.get('token')
                }

                success, message = test_vault_connection(config_data)

            else:
                return '<div class="alert alert-danger">Unknown integration type</div>', 400

            # Return status badge
            badge_class = 'success' if success else 'danger'
            icon = 'check-circle' if success else 'exclamation-circle'

            return f'''
            <div class="alert alert-{badge_class}">
                <i class="fas fa-{icon} me-2"></i>{message}
            </div>
            '''

        except Exception as e:
            log_error(f"Error testing integration connection: {e}")
            return '<div class="alert alert-danger">Connection test failed</div>', 500

    @app.route('/htmx/component/delete-confirm/<int:component_id>')
    def htmx_component_delete_confirm(component_id):
        """
        Show component deletion confirmation modal
        Enhanced confirmation with component details
        """
        if 'username' not in session or session.get('role') != 'admin':
            return '<div class="alert alert-danger">Unauthorized</div>', 401

        try:
            # Get component details for confirmation
            from core.project_manager import get_component_details
            component = get_component_details(component_id)

            if not component:
                return '<div class="alert alert-danger">Component not found</div>', 404

            # Check if component has MSI configurations
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM msi_configurations WHERE component_id = ?", (component_id,))
            has_configurations = cursor.fetchone()[0] > 0
            conn.close()

            return render_template('fragments/component_delete_confirm.html',
                                 component=component,
                                 has_configurations=has_configurations)

        except Exception as e:
            log_error(f"Error generating component delete confirmation: {e}")
            return '<div class="alert alert-danger">Error loading confirmation dialog</div>', 500

    @app.route('/htmx/component/toggle-status/<int:component_id>', methods=['POST'])
    def htmx_toggle_component_status(component_id):
        """
        Toggle component status (Active/Inactive) via HTMX
        """
        if 'username' not in session:
            return '<div class="alert alert-danger">Please log in</div>', 401

        # Check permissions - PowerUsers and Admins can toggle status
        user_role = session.get('role', 'user')
        if user_role not in ['admin', 'poweruser']:
            return '<div class="alert alert-danger">Insufficient permissions</div>', 403

        try:
            from core.component_manager import ComponentManager
            component_manager = ComponentManager()

            # Get current component status
            component = component_manager.get_component(component_id)
            if not component:
                return '<div class="alert alert-danger">Component not found</div>', 404

            # Toggle the status
            current_status = component.get('is_enabled', True)
            new_status = not current_status

            # Update component status
            success, message = component_manager.toggle_component_status(
                component_id,
                new_status,
                session.get('username', 'system')
            )

            if success:
                status_text = "activated" if new_status else "deactivated"
                log_info(f"Component '{component['component_name']}' {status_text} by {session.get('username')}")

                # Return updated component card
                updated_component = component_manager.get_component(component_id)
                return render_template('fragments/component_card.html',
                                     component=updated_component,
                                     is_new=False)
            else:
                return f'<div class="alert alert-danger"><i class="fas fa-exclamation-circle me-2"></i>{message}</div>'

        except Exception as e:
            log_error(f"Error toggling component status via HTMX: {e}")
            return '<div class="alert alert-danger">Error updating component status</div>', 500

    @app.route('/htmx/stats/refresh')
    def htmx_refresh_stats():
        """
        Refresh dashboard statistics
        Replaces JavaScript stats loading
        """
        try:
            # Get updated stats (this would pull from database)
            stats = {
                'total_projects': 0,
                'active_components': 0,
                'configured_components': 0,
                'pending_builds': 0
            }

            # In real implementation, fetch from database
            try:
                conn = get_db_connection()
                cursor = conn.cursor()

                # Get project count
                cursor.execute("SELECT COUNT(*) FROM projects WHERE is_active = 1")
                stats['total_projects'] = cursor.fetchone()[0]

                # Get component counts
                cursor.execute("SELECT COUNT(*) FROM components")
                stats['active_components'] = cursor.fetchone()[0]

                cursor.execute("SELECT COUNT(*) FROM msi_configurations")
                stats['configured_components'] = cursor.fetchone()[0]

                conn.close()

            except Exception as db_error:
                log_error(f"Database error in stats refresh: {db_error}")

            return render_template('fragments/dashboard_stats.html', stats=stats)

        except Exception as e:
            log_error(f"Error refreshing stats: {e}")
            return '<div class="alert alert-danger">Error refreshing statistics</div>', 500

    @app.route('/htmx/project/status-preview/<int:project_id>')
    def htmx_project_status_preview(project_id):
        """
        Preview component status changes when project status changes
        """
        if 'username' not in session:
            return '<div class="alert alert-warning">Please log in to preview changes</div>', 401

        try:
            new_status = request.args.get('status', 'active')

            # Get component count for this project
            conn = get_db_connection()
            cursor = conn.cursor()

            cursor.execute("SELECT COUNT(*) FROM components WHERE project_id = ?", (project_id,))
            component_count = cursor.fetchone()[0]

            if component_count == 0:
                return '<div class="alert alert-info"><i class="fas fa-info-circle me-2"></i>This project has no components.</div>'

            # Get currently enabled components
            cursor.execute("SELECT COUNT(*) FROM components WHERE project_id = ? AND is_enabled = 1", (project_id,))
            enabled_count = cursor.fetchone()[0]

            conn.close()

            if new_status in ['inactive', 'archived']:
                message = f"⚠️ Changing to '{new_status.title()}' will disable all {component_count} component(s) in this project."
                alert_class = "warning"
            elif new_status in ['active', 'maintenance']:
                disabled_count = component_count - enabled_count
                if disabled_count > 0:
                    message = f"✅ Changing to '{new_status.title()}' will enable all {component_count} component(s) in this project."
                else:
                    message = f"✅ All {component_count} component(s) will remain enabled for '{new_status.title()}' status."
                alert_class = "info"
            else:
                message = f"Status '{new_status}' - no component changes required."
                alert_class = "secondary"

            return f'<div class="alert alert-{alert_class}"><i class="fas fa-cubes me-2"></i>{message}</div>'

        except Exception as e:
            log_error(f"Error generating status preview: {e}")
            return '<div class="alert alert-danger">Error generating preview</div>', 500

    @app.route('/htmx/notification')
    def htmx_show_notification():
        """
        Show notification
        Replaces JavaScript showNotification()
        """
        message = request.args.get('message', 'Operation completed')
        type_arg = request.args.get('type', 'info')

        return render_template('fragments/notification.html',
                             message=message,
                             type=type_arg)

def check_component_dependencies(component_id):
    """
    Check if component has dependencies that prevent deletion
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        dependencies = {
            'has_dependencies': False,
            'msi_configurations': 0,
            'active_builds': 0,
            'deployment_records': 0
        }

        # Check MSI configurations
        cursor.execute("SELECT COUNT(*) FROM msi_configurations WHERE component_id = ?", (component_id,))
        dependencies['msi_configurations'] = cursor.fetchone()[0]

        # Check active builds (if build_jobs table exists)
        try:
            cursor.execute("SELECT COUNT(*) FROM build_jobs WHERE component_id = ? AND status IN ('pending', 'running')", (component_id,))
            dependencies['active_builds'] = cursor.fetchone()[0]
        except:
            dependencies['active_builds'] = 0

        # Check deployment records (if deployments table exists)
        try:
            cursor.execute("SELECT COUNT(*) FROM deployments WHERE component_id = ?", (component_id,))
            dependencies['deployment_records'] = cursor.fetchone()[0]
        except:
            dependencies['deployment_records'] = 0

        conn.close()

        # Determine if component has blocking dependencies
        dependencies['has_dependencies'] = (
            dependencies['active_builds'] > 0
            # Note: MSI configurations and deployment records are informational, not blocking
        )

        return dependencies

    except Exception as e:
        log_error(f"Error checking component dependencies: {e}")
        return {'has_dependencies': False, 'error': str(e)}


def get_all_components_for_search():
    """
    Get all components for search functionality
    This would typically query the database
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                c.component_id,
                c.component_name,
                c.component_type,
                c.framework,
                p.project_name,
                p.project_key,
                mc.config_id
            FROM components c
            INNER JOIN projects p ON c.project_id = p.project_id
            LEFT JOIN msi_configurations mc ON c.component_id = mc.component_id
            WHERE c.is_active = 1
            ORDER BY c.component_name
        """)

        components = []
        for row in cursor.fetchall():
            components.append({
                'component_id': row[0],
                'component_name': row[1],
                'component_type': row[2],
                'framework': row[3],
                'project_name': row[4],
                'project_key': row[5],
                'config_id': row[6]
            })

        conn.close()
        return components

    except Exception as e:
        log_error(f"Error fetching components for search: {e}")
        return []