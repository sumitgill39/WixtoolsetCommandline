# Package Builder - Integration Management Routes
# Version: 1.0
# Description: Flask routes for centralized integration management
# Author: MSI Factory Team

import logging
from flask import Blueprint, jsonify, request, session
from typing import Dict, Any

# Import the integration manager
from PackageBuilder.integration_manager import integration_manager

# Set up logging
logger = logging.getLogger(__name__)

# Create Blueprint for integration management routes
integration_blueprint = Blueprint('integration_management', __name__)

def get_current_user() -> str:
    """Get the current user from session."""
    return session.get('username', 'system')

def validate_admin_permissions() -> bool:
    """Validate if the current user has admin permissions."""
    user_role = session.get('role', 'user')
    return user_role == 'admin'

def validate_integration_permissions() -> bool:
    """Validate if the current user can manage integrations."""
    user_role = session.get('role', 'user')
    return user_role in ['admin', 'poweruser']

# ============================================================
# INTEGRATION CONFIGURATION API ENDPOINTS
# ============================================================

@integration_blueprint.route('/api/integrations/config/<integration_type>', methods=['GET'])
def api_get_integration_configs(integration_type: str):
    """
    Get all configurations for a specific integration type.

    Args:
        integration_type (str): Type of integration (jfrog, servicenow, vault)

    Returns:
        JSON response with integration configurations
    """
    try:
        # Check user permissions
        if not validate_integration_permissions():
            return jsonify({
                'success': False,
                'error': 'Access denied. Admin or PowerUser permissions required.'
            }), 403

        # Get configurations
        result = integration_manager.get_integration_config(integration_type)

        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 404

    except Exception as e:
        logger.error(f"Error in API get integration configs: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Internal server error: {str(e)}'
        }), 500

@integration_blueprint.route('/api/integrations/config/<integration_type>/<integration_name>', methods=['GET'])
def api_get_integration_config(integration_type: str, integration_name: str):
    """
    Get specific integration configuration.

    Args:
        integration_type (str): Type of integration
        integration_name (str): Name of the integration

    Returns:
        JSON response with integration configuration
    """
    try:
        # Check user permissions
        if not validate_integration_permissions():
            return jsonify({
                'success': False,
                'error': 'Access denied. Admin or PowerUser permissions required.'
            }), 403

        # Get specific configuration
        result = integration_manager.get_integration_config(integration_type, integration_name)

        if result['success']:
            # Remove sensitive information for non-admin users
            if not validate_admin_permissions() and 'config' in result:
                config = result['config']
                # Mask sensitive fields
                if 'password' in config:
                    config['password'] = '***MASKED***' if config['password'] else None
                if 'token' in config:
                    config['token'] = '***MASKED***' if config['token'] else None
                # api_key removed from schema

            return jsonify(result), 200
        else:
            return jsonify(result), 404

    except Exception as e:
        logger.error(f"Error in API get integration config: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Internal server error: {str(e)}'
        }), 500

@integration_blueprint.route('/api/integrations/config', methods=['POST'])
def api_create_integration_config():
    """
    Create new integration configuration.

    Returns:
        JSON response with creation status
    """
    try:
        # Check admin permissions for creating integrations
        if not validate_admin_permissions():
            return jsonify({
                'success': False,
                'error': 'Access denied. Admin permissions required to create integrations.'
            }), 403

        # Get JSON data from request
        integration_data = request.get_json()

        if not integration_data:
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400

        # Validate required fields
        required_fields = ['integration_type', 'integration_name', 'base_url', 'auth_type']
        for field in required_fields:
            if field not in integration_data:
                return jsonify({
                    'success': False,
                    'error': f'Missing required field: {field}'
                }), 400

        # Get current user
        current_user = get_current_user()

        # Save configuration
        result = integration_manager.save_integration_config(integration_data, current_user)

        if result['success']:
            return jsonify(result), 201
        else:
            return jsonify(result), 400

    except Exception as e:
        logger.error(f"Error in API create integration config: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Internal server error: {str(e)}'
        }), 500

@integration_blueprint.route('/api/integrations/config/<int:config_id>', methods=['PUT'])
def api_update_integration_config(config_id: int):
    """
    Update existing integration configuration.

    Args:
        config_id (int): ID of the configuration to update

    Returns:
        JSON response with update status
    """
    try:
        # Check admin permissions for updating integrations
        if not validate_admin_permissions():
            return jsonify({
                'success': False,
                'error': 'Access denied. Admin permissions required to update integrations.'
            }), 403

        # Get JSON data from request
        integration_data = request.get_json()

        if not integration_data:
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400

        # Add config_id to the data
        integration_data['config_id'] = config_id

        # Get current user
        current_user = get_current_user()

        # Update configuration
        result = integration_manager.save_integration_config(integration_data, current_user)

        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400

    except Exception as e:
        logger.error(f"Error in API update integration config: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Internal server error: {str(e)}'
        }), 500

@integration_blueprint.route('/api/integrations/test/<integration_type>/<integration_name>', methods=['POST'])
def api_test_integration_connection(integration_type: str, integration_name: str):
    """
    Test connection to an integration service.

    Args:
        integration_type (str): Type of integration
        integration_name (str): Name of the integration

    Returns:
        JSON response with test results
    """
    try:
        # Check user permissions
        if not validate_integration_permissions():
            return jsonify({
                'success': False,
                'error': 'Access denied. Admin or PowerUser permissions required.'
            }), 403

        # Get current user
        current_user = get_current_user()

        # Test connection
        result = integration_manager.test_integration_connection(
            integration_type, integration_name, current_user
        )

        return jsonify(result), 200

    except Exception as e:
        logger.error(f"Error in API test integration connection: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Internal server error: {str(e)}'
        }), 500

@integration_blueprint.route('/api/integrations/status', methods=['GET'])
def api_get_all_integrations_status():
    """
    Get status of all configured integrations.

    Returns:
        JSON response with all integration statuses
    """
    try:
        # Check user permissions
        if not validate_integration_permissions():
            return jsonify({
                'success': False,
                'error': 'Access denied. Admin or PowerUser permissions required.'
            }), 403

        # Get all integrations status
        result = integration_manager.get_all_integrations_status()

        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 500

    except Exception as e:
        logger.error(f"Error in API get integrations status: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Internal server error: {str(e)}'
        }), 500

# ============================================================
# SPECIFIC INTEGRATION API ENDPOINTS
# ============================================================

@integration_blueprint.route('/api/integrations/jfrog/base-url', methods=['GET'])
def api_get_jfrog_base_url():
    """
    Get JFrog base URL for use in application features.

    Returns:
        JSON response with JFrog base URL
    """
    try:
        # This endpoint can be accessed by any authenticated user
        if not session.get('username'):
            return jsonify({
                'success': False,
                'error': 'Authentication required'
            }), 401

        # Get JFrog base URL
        jfrog_base_url = integration_manager.get_jfrog_base_url()

        return jsonify({
            'success': True,
            'base_url': jfrog_base_url
        }), 200

    except Exception as e:
        logger.error(f"Error in API get JFrog base URL: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Internal server error: {str(e)}'
        }), 500

@integration_blueprint.route('/api/integrations/jfrog/validate', methods=['POST'])
def api_validate_jfrog_config():
    """
    Validate JFrog configuration without saving.

    Returns:
        JSON response with validation results
    """
    try:
        # Check admin permissions
        if not validate_admin_permissions():
            return jsonify({
                'success': False,
                'error': 'Access denied. Admin permissions required.'
            }), 403

        # Get JSON data from request
        config_data = request.get_json()

        if not config_data:
            return jsonify({
                'success': False,
                'error': 'No configuration data provided'
            }), 400

        # Validate required JFrog fields
        required_fields = ['base_url']
        for field in required_fields:
            if field not in config_data:
                return jsonify({
                    'success': False,
                    'error': f'Missing required field: {field}'
                }), 400

        # Perform basic validation
        base_url = config_data['base_url']
        if not (base_url.startswith('http://') or base_url.startswith('https://')):
            return jsonify({
                'success': False,
                'error': 'Base URL must start with http:// or https://'
            }), 400

        auth_type = config_data.get('auth_type', 'username_password')
        if auth_type == 'username_password':
            if not config_data.get('username') or not config_data.get('password'):
                return jsonify({
                    'success': False,
                    'error': 'Username and password required for username_password authentication'
                }), 400
        # api_key auth type removed - not supported anymore

        return jsonify({
            'success': True,
            'message': 'JFrog configuration validation passed'
        }), 200

    except Exception as e:
        logger.error(f"Error in API validate JFrog config: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Internal server error: {str(e)}'
        }), 500

@integration_blueprint.route('/api/integrations/jfrog/artifacts/list', methods=['POST'])
def api_list_jfrog_artifacts():
    """
    List artifacts from JFrog for a specific component.

    Returns:
        JSON response with artifact list
    """
    try:
        # Check user permissions
        if not validate_integration_permissions():
            return jsonify({
                'success': False,
                'error': 'Access denied. Admin or PowerUser permissions required.'
            }), 403

        # Get JSON data from request
        request_data = request.get_json()

        if not request_data:
            return jsonify({
                'success': False,
                'error': 'No request data provided'
            }), 400

        # Validate required fields
        required_fields = ['project_name', 'component_name']
        for field in required_fields:
            if field not in request_data:
                return jsonify({
                    'success': False,
                    'error': f'Missing required field: {field}'
                }), 400

        project_name = request_data['project_name']
        component_name = request_data['component_name']
        branch = request_data.get('branch')  # Optional
        integration_name = request_data.get('integration_name', 'Primary JFrog')

        # List artifacts using integration manager
        result = integration_manager.list_jfrog_artifacts(
            project_name, component_name, branch, integration_name
        )

        return jsonify(result), 200

    except Exception as e:
        logger.error(f"Error in API list JFrog artifacts: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Internal server error: {str(e)}'
        }), 500

@integration_blueprint.route('/api/integrations/jfrog/artifacts/download', methods=['POST'])
def api_download_jfrog_artifact():
    """
    Download artifact from JFrog using curl.

    Returns:
        JSON response with download results
    """
    try:
        # Check user permissions
        if not validate_integration_permissions():
            return jsonify({
                'success': False,
                'error': 'Access denied. Admin or PowerUser permissions required.'
            }), 403

        # Get JSON data from request
        request_data = request.get_json()

        if not request_data:
            return jsonify({
                'success': False,
                'error': 'No request data provided'
            }), 400

        # Validate required fields
        required_fields = ['project_name', 'component_name', 'branch', 'build_date', 'build_number', 'download_path']
        for field in required_fields:
            if field not in request_data:
                return jsonify({
                    'success': False,
                    'error': f'Missing required field: {field}'
                }), 400

        project_name = request_data['project_name']
        component_name = request_data['component_name']
        branch = request_data['branch']
        build_date = request_data['build_date']
        build_number = request_data['build_number']
        download_path = request_data['download_path']
        integration_name = request_data.get('integration_name', 'Primary JFrog')
        curl_path = request_data.get('curl_path')  # Optional curl.exe path

        # Download artifact using integration manager
        result = integration_manager.download_jfrog_artifact(
            project_name, component_name, branch, build_date, build_number,
            download_path, integration_name, curl_path
        )

        return jsonify(result), 200

    except Exception as e:
        logger.error(f"Error in API download JFrog artifact: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Internal server error: {str(e)}'
        }), 500

@integration_blueprint.route('/api/integrations/jfrog/artifacts/url', methods=['POST'])
def api_build_jfrog_artifact_url():
    """
    Build JFrog artifact URL for a specific component and build.

    Returns:
        JSON response with artifact URL
    """
    try:
        # Check user permissions
        if not validate_integration_permissions():
            return jsonify({
                'success': False,
                'error': 'Access denied. Admin or PowerUser permissions required.'
            }), 403

        # Get JSON data from request
        request_data = request.get_json()

        if not request_data:
            return jsonify({
                'success': False,
                'error': 'No request data provided'
            }), 400

        # Validate required fields
        required_fields = ['project_name', 'component_name', 'branch', 'build_date', 'build_number']
        for field in required_fields:
            if field not in request_data:
                return jsonify({
                    'success': False,
                    'error': f'Missing required field: {field}'
                }), 400

        project_name = request_data['project_name']
        component_name = request_data['component_name']
        branch = request_data['branch']
        build_date = request_data['build_date']
        build_number = request_data['build_number']
        integration_name = request_data.get('integration_name', 'Primary JFrog')

        # Build artifact URL using integration manager
        artifact_url = integration_manager.build_jfrog_artifact_url(
            project_name, component_name, branch, build_date, build_number, integration_name
        )

        if artifact_url == '{baseURL}':
            return jsonify({
                'success': False,
                'error': 'JFrog base URL not configured'
            }), 400

        return jsonify({
            'success': True,
            'artifact_url': artifact_url,
            'message': 'Artifact URL built successfully'
        }), 200

    except Exception as e:
        logger.error(f"Error in API build JFrog artifact URL: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Internal server error: {str(e)}'
        }), 500

@integration_blueprint.route('/api/integrations/jfrog/credentials', methods=['GET'])
def api_get_jfrog_credentials():
    """
    Get JFrog credentials (for testing/debugging - admin only).

    Returns:
        JSON response with masked credentials
    """
    try:
        # Check admin permissions only
        if not validate_admin_permissions():
            return jsonify({
                'success': False,
                'error': 'Access denied. Admin permissions required.'
            }), 403

        integration_name = request.args.get('integration_name', 'Primary JFrog')

        # Get credentials (but mask sensitive data)
        credentials = integration_manager.get_jfrog_credentials(integration_name)

        # Mask password for security
        masked_credentials = {
            'username': credentials.get('username', ''),
            'password': '***MASKED***' if credentials.get('password') else '',
            'base_url': credentials.get('base_url', ''),
            'has_credentials': bool(credentials.get('username') and credentials.get('password'))
        }

        return jsonify({
            'success': True,
            'credentials': masked_credentials
        }), 200

    except Exception as e:
        logger.error(f"Error in API get JFrog credentials: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Internal server error: {str(e)}'
        }), 500

@integration_blueprint.route('/api/integrations/jfrog/curl/check', methods=['GET'])
def api_check_curl_installation():
    """
    Check curl.exe installation and availability on Windows.

    Returns:
        JSON response with curl.exe status and path
    """
    try:
        import os
        import subprocess

        # Find curl.exe using integration manager
        curl_path = integration_manager._find_curl_exe()

        if curl_path and os.path.exists(curl_path):
            # Test curl.exe with version command
            try:
                result = subprocess.run(
                    [curl_path, '--version'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )

                if result.returncode == 0:
                    version_info = result.stdout.split('\n')[0] if result.stdout else 'Unknown version'

                    return jsonify({
                        'success': True,
                        'curl_found': True,
                        'curl_path': curl_path,
                        'curl_version': version_info,
                        'message': 'curl.exe is properly installed and working'
                    }), 200
                else:
                    return jsonify({
                        'success': False,
                        'curl_found': True,
                        'curl_path': curl_path,
                        'error': 'curl.exe found but not working properly',
                        'details': result.stderr
                    }), 200

            except subprocess.TimeoutExpired:
                return jsonify({
                    'success': False,
                    'curl_found': True,
                    'curl_path': curl_path,
                    'error': 'curl.exe found but timed out during version check'
                }), 200
            except Exception as e:
                return jsonify({
                    'success': False,
                    'curl_found': True,
                    'curl_path': curl_path,
                    'error': f'curl.exe found but error during test: {str(e)}'
                }), 200
        else:
            # Provide helpful information about curl installation
            return jsonify({
                'success': False,
                'curl_found': False,
                'curl_path': None,
                'error': 'curl.exe not found on this system',
                'suggestions': [
                    'Windows 10/11: curl.exe should be at C:\\Windows\\System32\\curl.exe',
                    'Install Git for Windows which includes curl',
                    'Download curl from https://curl.se/windows/',
                    'Or specify custom curl path in download request'
                ],
                'checked_locations': [
                    r"C:\Windows\System32\curl.exe",
                    r"C:\Program Files\Git\mingw64\bin\curl.exe",
                    r"C:\ProgramData\chocolatey\bin\curl.exe"
                ]
            }), 200

    except Exception as e:
        logger.error(f"Error checking curl installation: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Internal server error: {str(e)}'
        }), 500

# ============================================================
# ERROR HANDLERS
# ============================================================

@integration_blueprint.errorhandler(404)
def not_found_error(error):
    """Handle 404 errors for integration management routes."""
    return jsonify({
        'success': False,
        'error': 'Integration endpoint not found'
    }), 404

@integration_blueprint.errorhandler(405)
def method_not_allowed_error(error):
    """Handle 405 errors for integration management routes."""
    return jsonify({
        'success': False,
        'error': 'Method not allowed'
    }), 405

@integration_blueprint.errorhandler(500)
def internal_error(error):
    """Handle 500 errors for integration management routes."""
    logger.error(f"Internal server error in integration management: {str(error)}")
    return jsonify({
        'success': False,
        'error': 'Internal server error'
    }), 500