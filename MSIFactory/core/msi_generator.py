"""
MSI Generator Module
Handles all MSI generation and configuration operations
"""

import os
import json
from datetime import datetime
from sqlalchemy import text
from database.connection_manager import execute_with_retry
from logger import get_logger, log_info, log_error
from core.database_operations import get_db_connection
from core.utilities import generate_guid

def save_msi_configuration(component_id, config_data, username):
    """Save MSI configuration for a component"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if configuration exists
        cursor.execute("SELECT config_id FROM msi_configurations WHERE component_id = ?", (component_id,))
        existing_config = cursor.fetchone()

        if existing_config:
            # Update existing configuration
            update_sql = """
                UPDATE msi_configurations SET
                    app_name = ?,
                    app_version = ?,
                    manufacturer = ?,
                    upgrade_code = ?,
                    install_folder = ?,
                    target_server = ?,
                    target_environment = ?,
                    auto_increment_version = ?,
                    iis_website_name = ?,
                    iis_app_pool_name = ?,
                    app_pool_dotnet_version = ?,
                    app_pool_pipeline_mode = ?,
                    app_pool_identity = ?,
                    app_pool_enable_32bit = ?,
                    service_name = ?,
                    service_display_name = ?,
                    service_description = ?,
                    service_start_type = ?,
                    service_account = ?,
                    updated_date = GETDATE(),
                    updated_by = ?
                WHERE component_id = ?
            """
            cursor.execute(update_sql, (
                config_data.get('app_name'),
                config_data.get('app_version'),
                config_data.get('manufacturer'),
                config_data.get('upgrade_code'),
                config_data.get('install_folder'),
                config_data.get('target_server'),
                config_data.get('target_environment'),
                1 if config_data.get('auto_increment_version') == 'on' else 0,
                config_data.get('iis_website_name'),
                config_data.get('iis_app_pool_name'),
                config_data.get('app_pool_dotnet_version'),
                config_data.get('app_pool_pipeline_mode'),
                config_data.get('app_pool_identity'),
                1 if config_data.get('app_pool_enable_32bit') == 'on' else 0,
                config_data.get('service_name'),
                config_data.get('service_display_name'),
                config_data.get('service_description'),
                config_data.get('service_start_type'),
                config_data.get('service_account'),
                username,
                component_id
            ))
        else:
            # Insert new configuration
            insert_sql = """
                INSERT INTO msi_configurations (
                    component_id, app_name, app_version, manufacturer, upgrade_code,
                    install_folder, target_server, target_environment, auto_increment_version,
                    iis_website_name, iis_app_pool_name, app_pool_dotnet_version,
                    app_pool_pipeline_mode, app_pool_identity, app_pool_enable_32bit,
                    service_name, service_display_name, service_description,
                    service_start_type, service_account, created_by, updated_by
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            cursor.execute(insert_sql, (
                component_id,
                config_data.get('app_name'),
                config_data.get('app_version'),
                config_data.get('manufacturer'),
                config_data.get('upgrade_code'),
                config_data.get('install_folder'),
                config_data.get('target_server'),
                config_data.get('target_environment'),
                1 if config_data.get('auto_increment_version') == 'on' else 0,
                config_data.get('iis_website_name'),
                config_data.get('iis_app_pool_name'),
                config_data.get('app_pool_dotnet_version'),
                config_data.get('app_pool_pipeline_mode'),
                config_data.get('app_pool_identity'),
                1 if config_data.get('app_pool_enable_32bit') == 'on' else 0,
                config_data.get('service_name'),
                config_data.get('service_display_name'),
                config_data.get('service_description'),
                config_data.get('service_start_type'),
                config_data.get('service_account'),
                username,
                username
            ))

        conn.commit()
        conn.close()

        return True, 'MSI configuration saved successfully'

    except Exception as e:
        log_error(f"Failed to save MSI configuration: {e}")
        return False, f'Error saving configuration: {str(e)}'

def get_next_version(component_id):
    """Get the next version number for a component"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Get current version from msi_configurations
        cursor.execute("""
            SELECT app_version, auto_increment_version
            FROM msi_configurations
            WHERE component_id = ?
        """, (component_id,))

        row = cursor.fetchone()
        if row:
            current_version = row[0]
            auto_increment = row[1]

            if auto_increment and current_version:
                # Parse version and increment
                version_parts = current_version.split('.')
                if len(version_parts) >= 3:
                    try:
                        # Increment the build number (third part)
                        version_parts[2] = str(int(version_parts[2]) + 1)
                        next_version = '.'.join(version_parts)
                    except:
                        next_version = current_version
                else:
                    next_version = current_version
            else:
                next_version = current_version
        else:
            next_version = "1.0.0"

        conn.close()
        return next_version

    except Exception as e:
        log_error(f"Error getting next version: {e}")
        return "1.0.0"

def get_msi_configuration(component_id):
    """Get MSI configuration for a component"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                app_name, app_version, manufacturer, upgrade_code,
                install_folder, target_server, target_environment,
                auto_increment_version, iis_website_name, iis_app_pool_name,
                app_pool_dotnet_version, app_pool_pipeline_mode, app_pool_identity,
                app_pool_enable_32bit, service_name, service_display_name,
                service_description, service_start_type, service_account
            FROM msi_configurations
            WHERE component_id = ?
        """, (component_id,))

        row = cursor.fetchone()
        if row:
            config = {
                'app_name': row[0],
                'app_version': row[1],
                'manufacturer': row[2],
                'upgrade_code': row[3],
                'install_folder': row[4],
                'target_server': row[5],
                'target_environment': row[6],
                'auto_increment_version': row[7],
                'iis_website_name': row[8],
                'iis_app_pool_name': row[9],
                'app_pool_dotnet_version': row[10],
                'app_pool_pipeline_mode': row[11],
                'app_pool_identity': row[12],
                'app_pool_enable_32bit': row[13],
                'service_name': row[14],
                'service_display_name': row[15],
                'service_description': row[16],
                'service_start_type': row[17],
                'service_account': row[18]
            }
            conn.close()
            return config
        else:
            conn.close()
            return None

    except Exception as e:
        log_error(f"Error fetching MSI configuration: {e}")
        return None

def generate_msi_package(project_data, component_data, msi_config, username):
    """Generate MSI package for a project component"""
    try:
        job_id = generate_guid()

        # Create job record in database
        def create_job_in_db(db_session):
            job_insert = """
                INSERT INTO msi_generation_jobs (
                    job_id, project_id, component_id, status,
                    requested_by, request_date
                )
                VALUES (:job_id, :project_id, :component_id, 'pending',
                       :requested_by, GETDATE())
            """
            db_session.execute(text(job_insert), {
                'job_id': job_id,
                'project_id': project_data['project_id'],
                'component_id': component_data['component_id'],
                'requested_by': username
            })

        execute_with_retry(create_job_in_db)

        # Here you would trigger the actual MSI generation process
        # This could be a background task, API call to generation service, etc.

        log_info(f"MSI generation job {job_id} created for project {project_data['project_name']}")

        return True, job_id, "MSI generation started successfully"

    except Exception as e:
        log_error(f"Error generating MSI: {e}")
        return False, None, f"Error generating MSI: {str(e)}"

def get_msi_job_status(job_id):
    """Get status of MSI generation job"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                j.job_id, j.status, j.request_date, j.start_date,
                j.completion_date, j.error_message, j.output_path,
                p.project_name, c.component_name
            FROM msi_generation_jobs j
            INNER JOIN projects p ON j.project_id = p.project_id
            INNER JOIN components c ON j.component_id = c.component_id
            WHERE j.job_id = ?
        """, (job_id,))

        row = cursor.fetchone()
        if row:
            status = {
                'job_id': row[0],
                'status': row[1],
                'request_date': row[2],
                'start_date': row[3],
                'completion_date': row[4],
                'error_message': row[5],
                'output_path': row[6],
                'project_name': row[7],
                'component_name': row[8]
            }
            conn.close()
            return status
        else:
            conn.close()
            return None

    except Exception as e:
        log_error(f"Error fetching job status: {e}")
        return None

def get_build_configurations():
    """Get all available build configurations"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                mc.config_id,
                p.project_name,
                c.component_name,
                mc.app_name,
                mc.app_version,
                mc.target_environment,
                mc.updated_date
            FROM msi_configurations mc
            INNER JOIN components c ON mc.component_id = c.component_id
            INNER JOIN projects p ON c.project_id = p.project_id
            ORDER BY mc.updated_date DESC
        """)

        configurations = []
        for row in cursor.fetchall():
            configurations.append({
                'config_id': row[0],
                'project_name': row[1],
                'component_name': row[2],
                'app_name': row[3],
                'app_version': row[4],
                'target_environment': row[5],
                'updated_date': row[6]
            })

        conn.close()
        return configurations

    except Exception as e:
        log_error(f"Error fetching build configurations: {e}")
        return []

def validate_msi_configuration(config_data):
    """Validate MSI configuration data"""
    errors = []

    # Required fields
    required_fields = ['app_name', 'app_version', 'manufacturer', 'upgrade_code']
    for field in required_fields:
        if not config_data.get(field):
            errors.append(f"{field.replace('_', ' ').title()} is required")

    # Version format validation
    version = config_data.get('app_version', '')
    if version and not all(part.isdigit() for part in version.split('.')):
        errors.append("Version must be in format X.Y.Z where X, Y, Z are numbers")

    # GUID format validation
    upgrade_code = config_data.get('upgrade_code', '')
    if upgrade_code:
        try:
            uuid.UUID(upgrade_code)
        except ValueError:
            errors.append("Upgrade code must be a valid GUID")

    return errors