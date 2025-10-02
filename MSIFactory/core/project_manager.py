"""
Project Manager Module
Handles all project-related operations including CRUD operations on projects and components
"""

from flask import session, flash, redirect, url_for
from sqlalchemy import text
from database.connection_manager import execute_with_retry
from logger import get_logger, log_info, log_error
from core.database_operations import get_db_connection
import pyodbc

def add_project_to_database(form_data, username):
    """Add new project to database"""
    try:
        # Check for duplicate project key first
        project_key = form_data.get('project_key', '').upper().strip()
        if project_key:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM projects WHERE project_key = ?", (project_key,))
            count = cursor.fetchone()[0]
            conn.close()

            if count > 0:
                return False, None, f"Project key '{project_key}' already exists. Please choose a different project key."

        # Get selected environments
        selected_environments = form_data.getlist('environments')
        if not selected_environments:
            selected_environments = []

        # Extract component data
        components_data = []
        component_counter = 1
        while True:
            component_name = form_data.get(f'component_name_{component_counter}')
            if not component_name:
                break

            component_data = {
                'component_guid': form_data.get(f'component_guid_{component_counter}'),
                'component_name': component_name,
                'component_type': form_data.get(f'component_type_{component_counter}'),
                'framework': form_data.get(f'component_framework_{component_counter}'),
                'artifact_source': form_data.get(f'component_artifact_{component_counter}', ''),
            }
            components_data.append(component_data)
            component_counter += 1

        log_info(f"DEBUG: Selected environments: {selected_environments}")
        log_info(f"DEBUG: Components data: {components_data}")

        def create_project_in_db(db_session):
            # Insert main project with artifact information
            project_insert = """
                INSERT INTO projects (project_name, project_key, project_guid, description, project_type,
                                    owner_team, color_primary, color_secondary, status, created_by,
                                    artifact_source_type, artifact_url, artifact_username, artifact_password)
                OUTPUT INSERTED.project_id
                VALUES (:project_name, :project_key, :project_guid, :description, :project_type,
                       :owner_team, :color_primary, :color_secondary, :status, :created_by,
                       :artifact_source_type, :artifact_url, :artifact_username, :artifact_password)
            """

            # Handle project_guid properly - convert empty string to None for SQL Server
            project_guid_value = form_data.get('project_guid')
            if project_guid_value == '':
                project_guid_value = None

            result = db_session.execute(text(project_insert), {
                'project_name': form_data.get('project_name'),
                'project_key': form_data.get('project_key', '').upper(),
                'project_guid': project_guid_value,
                'description': form_data.get('description', ''),
                'project_type': form_data.get('project_type'),
                'owner_team': form_data.get('owner_team'),
                'color_primary': form_data.get('color_primary', '#2c3e50'),
                'color_secondary': form_data.get('color_secondary', '#3498db'),
                'status': form_data.get('status', 'active'),
                'created_by': username,
                'artifact_source_type': form_data.get('artifact_source_type', ''),
                'artifact_url': form_data.get('artifact_url', ''),
                'artifact_username': form_data.get('artifact_username', ''),
                'artifact_password': form_data.get('artifact_password', '')
            })

            # Get the project ID from the OUTPUT clause
            project_id = result.fetchone()[0]

            # Environment functionality disabled - no environment operations

            # Insert components if any (check for duplicates first)
            inserted_components = set()
            for comp_data in components_data:
                comp_name = comp_data['component_name']

                # Skip if we already inserted a component with this name
                if comp_name in inserted_components:
                    log_info(f"Skipping duplicate component '{comp_name}' in project creation")
                    continue

                comp_insert = """
                    INSERT INTO components (project_id, component_name, component_type,
                                          framework, artifact_source, created_by)
                    VALUES (:project_id, :component_name, :component_type,
                           :framework, :artifact_source, :created_by)
                """
                try:
                    db_session.execute(text(comp_insert), {
                        'project_id': project_id,
                        'component_name': comp_name,
                        'component_type': comp_data['component_type'],
                        'framework': comp_data['framework'],
                        'artifact_source': comp_data['artifact_source'],
                        'created_by': username
                    })
                    inserted_components.add(comp_name)
                except Exception as comp_error:
                    log_error(f"Error inserting component '{comp_name}': {comp_error}")
                    # Continue with other components if one fails

            return project_id

        # Execute database operations
        log_info("DEBUG: About to execute database operations...")
        project_id = execute_with_retry(create_project_in_db)

        log_info(f"DEBUG: Project created successfully with ID: {project_id}")
        return True, project_id, f'Project "{form_data.get("project_name")}" created successfully!'

    except Exception as e:
        log_error(f"ERROR creating project: {e}")
        import traceback
        traceback.print_exc()
        return False, None, f"Error creating project: {str(e)}"

def edit_project_in_database(form_data, project_id, username=None):
    """Edit existing project in database"""
    try:
        # Debug logging to check form data
        status_value = form_data.get('status', 'active')
        log_info(f"DEBUG: Editing project {project_id}, received status: '{status_value}'")
        log_info(f"DEBUG: All form data keys: {list(form_data.keys())}")

        # Get selected environments
        selected_environments = form_data.getlist('environments')
        if not selected_environments:
            selected_environments = []

        def update_project_in_db(db_session):
            # Update main project
            project_update = """
                UPDATE projects
                SET project_name = :project_name,
                    project_key = :project_key,
                    project_guid = :project_guid,
                    description = :description,
                    project_type = :project_type,
                    owner_team = :owner_team,
                    color_primary = :color_primary,
                    color_secondary = :color_secondary,
                    status = :status,
                    artifact_source_type = :artifact_source_type,
                    artifact_url = :artifact_url,
                    artifact_username = :artifact_username,
                    artifact_password = :artifact_password
                WHERE project_id = :project_id
            """

            # Handle project_guid properly - convert empty string to None for SQL Server
            project_guid_value = form_data.get('project_guid')
            if project_guid_value == '':
                project_guid_value = None

            db_session.execute(text(project_update), {
                'project_id': project_id,
                'project_name': form_data.get('project_name'),
                'project_key': form_data.get('project_key', '').upper(),
                'project_guid': project_guid_value,
                'description': form_data.get('description', ''),
                'project_type': form_data.get('project_type'),
                'owner_team': form_data.get('owner_team'),
                'color_primary': form_data.get('color_primary', '#2c3e50'),
                'color_secondary': form_data.get('color_secondary', '#3498db'),
                'status': form_data.get('status', 'active'),
                'artifact_source_type': form_data.get('artifact_source_type', ''),
                'artifact_url': form_data.get('artifact_url', ''),
                'artifact_username': form_data.get('artifact_username', ''),
                'artifact_password': form_data.get('artifact_password', '')
            })

            # Environment functionality disabled - no environment operations

        # Execute database operations
        execute_with_retry(update_project_in_db)

        # Verify the status was actually updated in the database
        def verify_status_update(db_session):
            result = db_session.execute(
                text("SELECT status FROM projects WHERE project_id = :project_id"),
                {'project_id': project_id}
            )
            return result.fetchone()[0]

        actual_status = execute_with_retry(verify_status_update)
        log_info(f"DEBUG: After update, database status for project {project_id}: '{actual_status}'")

        if actual_status != status_value:
            log_error(f"ERROR: Status mismatch! Expected: '{status_value}', Actual: '{actual_status}'")

        # Handle component status cascading based on project status
        cascade_result = cascade_component_status_for_project(project_id, status_value, username)

        # Create enhanced success message with component status information
        base_message = f'Project "{form_data.get("project_name")}" updated successfully!'

        if cascade_result['success'] and cascade_result['details']['action'] != 'none':
            details = cascade_result['details']
            if details['action'] == 'disabled':
                base_message += f" All {details['count']} components have been disabled due to project status change."
            elif details['action'] == 'restored':
                base_message += f" All {details['total_count']} components have been enabled for the active project."
        elif not cascade_result['success']:
            log_error(f"Component status cascade warning: {cascade_result['message']}")
            base_message += " Warning: Component status update encountered issues."

        return True, base_message

    except Exception as e:
        log_error(f"ERROR updating project {project_id}: {e}")
        return False, f"Error updating project: {str(e)}"


def cascade_component_status_for_project(project_id, project_status, username=None):
    """
    Cascade project status changes to components
    - inactive/archived projects: disable all components
    - active/maintenance projects: restore components to their configured state
    """
    try:
        log_info(f"Cascading project status '{project_status}' to components for project {project_id}")

        def update_component_status_in_db(db_session):
            if project_status in ['inactive', 'archived']:
                # Disable all components for inactive/archived projects
                log_info(f"Disabling all components for {project_status} project {project_id}")

                # Disable all components for inactive/archived projects
                db_session.execute(text("""
                    UPDATE components
                    SET is_enabled = 0,
                        updated_date = GETDATE(),
                        updated_by = :username
                    WHERE project_id = :project_id
                """), {
                    'project_id': project_id,
                    'username': username or 'system'
                })

                # Get count of affected components
                result = db_session.execute(text("""
                    SELECT COUNT(*) FROM components WHERE project_id = :project_id
                """), {'project_id': project_id})

                component_count = result.fetchone()[0]
                log_info(f"Disabled {component_count} components for project {project_id}")

                return {'action': 'disabled', 'count': component_count}

            elif project_status in ['active', 'maintenance']:
                # Restore components to their previous state or enable by default
                log_info(f"Restoring component states for {project_status} project {project_id}")

                # Enable all components for active/maintenance projects
                # Users can manually disable specific components if needed
                db_session.execute(text("""
                    UPDATE components
                    SET is_enabled = 1,
                        updated_date = GETDATE(),
                        updated_by = :username
                    WHERE project_id = :project_id
                """), {
                    'project_id': project_id,
                    'username': username or 'system'
                })

                # Get count of restored components
                result = db_session.execute(text("""
                    SELECT COUNT(*) FROM components WHERE project_id = :project_id AND is_enabled = 1
                """), {'project_id': project_id})

                enabled_count = result.fetchone()[0]

                result = db_session.execute(text("""
                    SELECT COUNT(*) FROM components WHERE project_id = :project_id
                """), {'project_id': project_id})

                total_count = result.fetchone()[0]

                log_info(f"Restored components for project {project_id}: {enabled_count} enabled, {total_count - enabled_count} disabled")

                return {'action': 'restored', 'enabled_count': enabled_count, 'total_count': total_count}

            else:
                log_info(f"No component status change needed for project status: {project_status}")
                return {'action': 'none', 'count': 0}

        result = execute_with_retry(update_component_status_in_db)

        return {
            'success': True,
            'message': f"Component status cascade completed: {result['action']}",
            'details': result
        }

    except Exception as e:
        log_error(f"Error cascading component status for project {project_id}: {e}")
        return {
            'success': False,
            'message': f"Error cascading component status: {str(e)}"
        }

def add_component_to_project(project_id, component_data, username):
    """Add a component to an existing project"""
    try:
        component_name = component_data.get('component_name')

        def add_component_in_db(db_session):
            # First check if component with same name already exists in this project
            check_query = """
                SELECT COUNT(*) FROM components
                WHERE project_id = :project_id AND component_name = :component_name
            """
            result = db_session.execute(text(check_query), {
                'project_id': project_id,
                'component_name': component_name
            })

            if result.fetchone()[0] > 0:
                raise ValueError(f"Component '{component_name}' already exists in this project")

            # If not exists, insert the new component with all form fields
            comp_insert = """
                INSERT INTO components (
                    project_id, component_name, component_type, framework, description,
                    artifact_source, created_by, is_enabled,
                    app_name, app_version, manufacturer,
                    target_server, install_folder,
                    iis_website_name, iis_app_pool_name, port,
                    service_name, service_display_name,
                    artifact_url
                )
                OUTPUT INSERTED.component_id
                VALUES (
                    :project_id, :component_name, :component_type, :framework, :description,
                    :artifact_source, :created_by, :is_enabled,
                    :app_name, :app_version, :manufacturer,
                    :target_server, :install_folder,
                    :iis_website_name, :iis_app_pool_name, :port,
                    :service_name, :service_display_name,
                    :artifact_url
                )
            """
            result = db_session.execute(text(comp_insert), {
                'project_id': project_id,
                'component_name': component_name,
                'component_type': component_data.get('component_type'),
                'framework': component_data.get('framework'),
                'description': component_data.get('description', ''),
                'artifact_source': component_data.get('artifact_source', ''),
                'created_by': username,
                'is_enabled': component_data.get('is_enabled', True),
                'app_name': component_data.get('app_name'),
                'app_version': component_data.get('app_version', '1.0.0.0'),
                'manufacturer': component_data.get('manufacturer'),
                'target_server': component_data.get('target_server'),
                'install_folder': component_data.get('install_folder'),
                'iis_website_name': component_data.get('iis_website_name'),
                'iis_app_pool_name': component_data.get('iis_app_pool_name'),
                'port': component_data.get('port'),
                'service_name': component_data.get('service_name'),
                'service_display_name': component_data.get('service_display_name'),
                'artifact_url': component_data.get('artifact_url')
            })

            component_id = result.fetchone()[0]
            return component_id

        component_id = execute_with_retry(add_component_in_db)
        log_info(f"Component added successfully with ID: {component_id}")
        return True, component_id, "Component added successfully"

    except ValueError as ve:
        log_info(f"Component validation error: {ve}")
        return False, None, str(ve)
    except Exception as e:
        log_error(f"ERROR adding component to project {project_id}: {e}")
        # Check if it's a unique constraint violation
        if "UK_components_project_name" in str(e) or "duplicate key" in str(e).lower():
            return False, None, f"Component '{component_data.get('component_name')}' already exists in this project"
        return False, None, f"Error adding component: {str(e)}"

def update_component_in_project(component_id, component_data, username):
    """Update an existing component in a project"""
    try:
        # Validate component_id
        if not component_id:
            return False, "Component ID is required"

        # Convert to int if needed
        try:
            component_id = int(component_id)
        except (ValueError, TypeError):
            return False, "Invalid component ID format"

        component_name = component_data.get('component_name')
        if not component_name:
            return False, "Component name is required"

        def update_component_in_db(db_session):
            # First verify the component exists and get current project_id
            check_result = db_session.execute(
                text("SELECT component_name, project_id FROM components WHERE component_id = :component_id"),
                {'component_id': component_id}
            ).fetchone()

            if not check_result:
                raise ValueError(f"Component with ID {component_id} not found")

            current_name = check_result[0]
            project_id = check_result[1]

            # Check if new name conflicts with other components in the same project (if name changed)
            if current_name != component_name:
                name_check = db_session.execute(
                    text("""
                        SELECT COUNT(*) FROM components
                        WHERE project_id = :project_id
                        AND component_name = :component_name
                        AND component_id != :component_id
                    """),
                    {
                        'project_id': project_id,
                        'component_name': component_name,
                        'component_id': component_id
                    }
                ).fetchone()[0]

                if name_check > 0:
                    raise ValueError(f"Component '{component_name}' already exists in this project")

            log_info(f"Updating component '{current_name}' (ID: {component_id})")

            # Update the component with all available fields
            update_sql = """
                UPDATE components
                SET component_name = :component_name,
                    component_type = :component_type,
                    framework = :framework,
                    description = :description,
                    app_name = :app_name,
                    app_version = :app_version,
                    manufacturer = :manufacturer,
                    install_folder = :install_folder,
                    service_name = :service_name,
                    service_display_name = :service_display_name,
                    iis_website_name = :iis_website_name,
                    iis_app_pool_name = :iis_app_pool_name,
                    port = :port,
                    is_enabled = :is_enabled
                WHERE component_id = :component_id
            """

            # Prepare parameters, handling None values appropriately
            params = {
                'component_id': component_id,
                'component_name': component_name,
                'component_type': component_data.get('component_type'),
                'framework': component_data.get('framework'),
                'description': component_data.get('description', ''),
                'app_name': component_data.get('app_name'),
                'app_version': component_data.get('app_version'),
                'manufacturer': component_data.get('manufacturer'),
                'install_folder': component_data.get('install_folder'),
                'service_name': component_data.get('service_name'),
                'service_display_name': component_data.get('service_display_name'),
                'iis_website_name': component_data.get('iis_website_name'),
                'iis_app_pool_name': component_data.get('iis_app_pool_name'),
                'port': component_data.get('port'),
                'is_enabled': component_data.get('is_enabled', True)
            }

            result = db_session.execute(text(update_sql), params)

            if result.rowcount == 0:
                raise ValueError(f"Component with ID {component_id} could not be updated")

            log_info(f"Successfully updated component '{component_name}' (ID: {component_id})")
            return component_name

        updated_name = execute_with_retry(update_component_in_db)
        return True, f"Component '{updated_name}' updated successfully"

    except ValueError as ve:
        log_error(f"Validation error updating component {component_id}: {ve}")
        return False, str(ve)
    except Exception as e:
        log_error(f"ERROR updating component {component_id}: {e}")
        # Check if it's a unique constraint violation
        if "UK_components_project_name" in str(e) or "duplicate key" in str(e).lower():
            return False, f"Component '{component_data.get('component_name')}' already exists in this project"
        return False, f"Error updating component: {str(e)}"

def remove_component_from_project(component_id):
    """Remove a component from a project with enhanced validation"""
    try:
        # Validate component_id
        if not component_id:
            return False, "Component ID is required"

        # Convert to int if needed
        try:
            component_id = int(component_id)
        except (ValueError, TypeError):
            return False, "Invalid component ID format"

        def remove_component_in_db(db_session):
            # First verify the component exists
            check_result = db_session.execute(
                text("SELECT component_name, is_enabled FROM components WHERE component_id = :component_id"),
                {'component_id': component_id}
            ).fetchone()

            if not check_result:
                raise ValueError(f"Component with ID {component_id} not found")

            component_name = check_result[0]
            log_info(f"Starting deletion of component '{component_name}' (ID: {component_id})")

            # Check for active builds (if build_jobs table exists)
            try:
                active_builds = db_session.execute(
                    text("SELECT COUNT(*) FROM build_jobs WHERE component_id = :component_id AND status IN ('pending', 'running')"),
                    {'component_id': component_id}
                ).fetchone()[0]

                if active_builds > 0:
                    raise ValueError(f"Cannot delete component '{component_name}' - it has {active_builds} active build(s)")
            except Exception as build_check_error:
                # If build_jobs table doesn't exist, that's OK
                if "Invalid object name 'build_jobs'" not in str(build_check_error):
                    log_error(f"Error checking active builds: {build_check_error}")

            # Delete related MSI configurations first
            msi_deleted = db_session.execute(
                text("DELETE FROM msi_configurations WHERE component_id = :component_id"),
                {'component_id': component_id}
            ).rowcount

            if msi_deleted > 0:
                log_info(f"Deleted {msi_deleted} MSI configuration(s) for component '{component_name}'")

            # Delete the component
            component_deleted = db_session.execute(
                text("DELETE FROM components WHERE component_id = :component_id"),
                {'component_id': component_id}
            ).rowcount

            if component_deleted == 0:
                raise ValueError(f"Component '{component_name}' could not be deleted - it may have been already removed")

            log_info(f"Successfully deleted component '{component_name}' (ID: {component_id})")
            return component_name

        component_name = execute_with_retry(remove_component_in_db)
        return True, f"Component '{component_name}' removed successfully"

    except ValueError as ve:
        log_error(f"Validation error removing component {component_id}: {ve}")
        return False, str(ve)
    except Exception as e:
        log_error(f"ERROR removing component {component_id}: {e}")
        return False, f"Error removing component: {str(e)}"

def get_project_components(project_id):
    """Get all components for a project"""
    try:
        def fetch_components(db_session):
            result = db_session.execute(
                text("""
                    SELECT component_id, component_name, component_type, framework,
                           artifact_source, created_date, created_by, is_enabled, component_guid,
                           description, app_name, app_version, manufacturer, install_folder,
                           iis_website_name, iis_app_pool_name, port, service_name, service_display_name
                    FROM components
                    WHERE project_id = :project_id
                    ORDER BY component_name
                """),
                {'project_id': project_id}
            )

            components = []
            for row in result:
                components.append({
                    'component_id': row[0],
                    'component_name': row[1],
                    'component_type': row[2],
                    'framework': row[3],
                    'artifact_source': row[4],
                    'created_date': row[5],
                    'created_by': row[6],
                    'is_enabled': bool(row[7]) if row[7] is not None else True,
                    'component_guid': row[8],
                    'description': row[9],
                    'app_name': row[10],
                    'app_version': row[11],
                    'manufacturer': row[12],
                    'install_folder': row[13],
                    'iis_website_name': row[14],
                    'iis_app_pool_name': row[15],
                    'port': row[16],
                    'service_name': row[17],
                    'service_display_name': row[18]
                })
            return components

        return execute_with_retry(fetch_components)

    except Exception as e:
        log_error(f"ERROR fetching components for project {project_id}: {e}")
        return []


def get_project_build_history(project_id):
    """Get build history for a project"""
    try:
        def fetch_build_history(db_session):
            result = db_session.execute(
                text("""
                    SELECT build_id, build_number, build_status, build_type,
                           environment, triggered_by, start_time, end_time,
                           output_path, log_path
                    FROM build_history
                    WHERE project_id = :project_id
                    ORDER BY start_time DESC
                    OFFSET 0 ROWS FETCH NEXT 100 ROWS ONLY
                """),
                {'project_id': project_id}
            )

            builds = []
            for row in result:
                builds.append({
                    'build_id': row[0],
                    'build_number': row[1],
                    'build_status': row[2],
                    'build_type': row[3],
                    'environment': row[4],
                    'triggered_by': row[5],
                    'start_time': row[6],
                    'end_time': row[7],
                    'output_path': row[8],
                    'log_path': row[9]
                })
            return builds

        return execute_with_retry(fetch_build_history)

    except Exception as e:
        log_error(f"ERROR fetching build history for project {project_id}: {e}")
        return []


def get_component_details(component_id):
    """Get complete component information for editing and operations"""
    try:
        def get_component_from_db(db_session):
            query = text("""
                SELECT c.component_id, c.component_name, c.component_type,
                       c.framework, c.component_guid, c.install_folder,
                       p.project_name, p.project_key, c.created_date,
                       c.created_by, c.is_enabled,
                       c.description, c.app_name, c.app_version,
                       c.manufacturer, c.target_server, c.artifact_url,
                       c.iis_website_name, c.iis_app_pool_name, c.port,
                       c.service_name, c.service_display_name,
                       c.artifact_source, c.branch_name, c.dependencies,
                       p.project_id, c.updated_date, c.updated_by
                FROM components c
                INNER JOIN projects p ON c.project_id = p.project_id
                WHERE c.component_id = :component_id
            """)
            return db_session.execute(query, {'component_id': component_id}).fetchone()

        component_data = execute_with_retry(get_component_from_db)

        if component_data:
            return {
                'component_id': component_data[0],
                'component_name': component_data[1],
                'component_type': component_data[2],
                'framework': component_data[3],
                'component_guid': component_data[4],
                'install_folder': component_data[5],
                'project_name': component_data[6],
                'project_key': component_data[7],
                'created_date': component_data[8],
                'created_by': component_data[9],
                'is_enabled': component_data[10],
                'description': component_data[11],
                'app_name': component_data[12],
                'app_version': component_data[13],
                'manufacturer': component_data[14],
                'target_server': component_data[15],
                'artifact_url': component_data[16],
                'iis_website_name': component_data[17],
                'iis_app_pool_name': component_data[18],
                'port': component_data[19],
                'service_name': component_data[20],
                'service_display_name': component_data[21],
                'artifact_source': component_data[22],
                'branch_name': component_data[23],
                'dependencies': component_data[24],
                'project_id': component_data[25],
                'updated_date': component_data[26],
                'updated_by': component_data[27]
            }
        else:
            return None

    except Exception as e:
        log_error(f"Error getting component details for component {component_id}: {e}")
        return None


def test_component_cascade_logic():
    """
    Test function to verify component status cascading works properly
    This can be called from a route for testing purposes
    """
    try:
        # Get a test project
        def get_test_project(db_session):
            result = db_session.execute(
                text("SELECT TOP 1 project_id, project_name FROM projects WHERE is_active = 1")
            )
            return result.fetchone()

        test_project = execute_with_retry(get_test_project)
        if not test_project:
            return {"success": False, "message": "No active projects found for testing"}

        project_id = test_project[0]
        project_name = test_project[1]

        log_info(f"Testing component cascade with project: {project_name} (ID: {project_id})")

        # Test 1: Set to inactive and check components are disabled
        result1 = cascade_component_status_for_project(project_id, 'inactive', 'test_user')

        # Test 2: Set back to active and check components are enabled
        result2 = cascade_component_status_for_project(project_id, 'active', 'test_user')

        return {
            "success": True,
            "message": "Component cascade test completed",
            "test_project": project_name,
            "inactive_result": result1,
            "active_result": result2
        }

    except Exception as e:
        log_error(f"Error in component cascade test: {e}")
        return {"success": False, "message": f"Test failed: {str(e)}"}