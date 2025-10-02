# Package Builder - Branch Management Routes
# Version: 1.0
# Description: Flask routes for branch management functionality
# Author: MSI Factory Team

import logging
from flask import Blueprint, jsonify, request, render_template, session
from typing import Dict, Any

# Import the branch API
from PackageBuilder.branch_api import branch_api

# Set up logging
logger = logging.getLogger(__name__)

# Create Blueprint for branch management routes
branch_blueprint = Blueprint('branch_management', __name__)

def get_current_user() -> str:
    """
    Get the current user from session.

    Returns:
        str: Username of the current user or 'system' as default
    """
    return session.get('username', 'system')

def validate_user_permissions(required_permission: str = 'component_read') -> bool:
    """
    Validate if the current user has the required permissions.

    Args:
        required_permission (str): The permission to check for

    Returns:
        bool: True if user has permission, False otherwise
    """
    # For now, return True - in production this should check against the user permission system
    # This would integrate with the authorization system from the database schema
    user_role = session.get('role', 'user')

    # Basic role-based check
    if user_role == 'admin':
        return True
    elif user_role == 'poweruser':
        # PowerUsers can manage components and branches
        return required_permission in ['component_read', 'component_update', 'component_create', 'component_delete']
    else:
        # Regular users can only read
        return required_permission == 'component_read'

@branch_blueprint.route('/branch_management')
def branch_management_page():
    """
    Render the branch management page.

    Returns:
        str: Rendered HTML template
    """
    try:
        # Check user permissions
        if not validate_user_permissions('component_read'):
            return render_template('error.html',
                                   error_message="Access denied. Insufficient permissions."), 403

        # Get components for the dropdown
        components_response = branch_api.get_components_for_dropdown()

        # Get projects for the dropdown
        projects_response = branch_api.get_projects_for_dropdown()

        return render_template('branch_management.html',
                             components=components_response.get('components', []),
                             projects=projects_response.get('projects', []))

    except Exception as e:
        logger.error(f"Error loading branch management page: {str(e)}")
        return render_template('error.html',
                               error_message="Failed to load branch management page"), 500

# ============================================================
# API ENDPOINTS FOR BRANCH MANAGEMENT
# ============================================================

@branch_blueprint.route('/api/branches/all', methods=['GET'])
def api_get_all_branches():
    """
    API endpoint to get all branches.

    Returns:
        JSON response with branches data
    """
    try:
        # Check user permissions
        if not validate_user_permissions('component_read'):
            return jsonify({
                'success': False,
                'error': 'Access denied. Insufficient permissions.'
            }), 403

        # Get all branches
        response = branch_api.get_all_branches()

        if response['success']:
            return jsonify(response), 200
        else:
            return jsonify(response), 500

    except Exception as e:
        logger.error(f"Error in API get all branches: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Internal server error: {str(e)}'
        }), 500

@branch_blueprint.route('/api/branches/<int:branch_id>', methods=['GET'])
def api_get_branch(branch_id: int):
    """
    API endpoint to get a specific branch by ID.

    Args:
        branch_id (int): The ID of the branch to retrieve

    Returns:
        JSON response with branch data
    """
    try:
        # Check user permissions
        if not validate_user_permissions('component_read'):
            return jsonify({
                'success': False,
                'error': 'Access denied. Insufficient permissions.'
            }), 403

        # Get branch by ID
        response = branch_api.get_branch_by_id(branch_id)

        if response['success']:
            return jsonify(response), 200
        else:
            return jsonify(response), 404 if 'not found' in response.get('error', '').lower() else 500

    except Exception as e:
        logger.error(f"Error in API get branch {branch_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Internal server error: {str(e)}'
        }), 500

@branch_blueprint.route('/api/branches', methods=['POST'])
def api_create_branch():
    """
    API endpoint to create a new branch.

    Returns:
        JSON response with creation status
    """
    try:
        # Check user permissions
        if not validate_user_permissions('component_create'):
            return jsonify({
                'success': False,
                'error': 'Access denied. Insufficient permissions to create branches.'
            }), 403

        # Get JSON data from request
        branch_data = request.get_json()

        if not branch_data:
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400

        # Get current user
        current_user = get_current_user()

        # Create branch
        response = branch_api.create_branch(branch_data, created_by=current_user)

        if response['success']:
            return jsonify(response), 201
        else:
            return jsonify(response), 400

    except Exception as e:
        logger.error(f"Error in API create branch: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Internal server error: {str(e)}'
        }), 500

@branch_blueprint.route('/api/branches/<int:branch_id>', methods=['PUT'])
def api_update_branch(branch_id: int):
    """
    API endpoint to update an existing branch.

    Args:
        branch_id (int): The ID of the branch to update

    Returns:
        JSON response with update status
    """
    try:
        # Check user permissions
        if not validate_user_permissions('component_update'):
            return jsonify({
                'success': False,
                'error': 'Access denied. Insufficient permissions to update branches.'
            }), 403

        # Get JSON data from request
        branch_data = request.get_json()

        if not branch_data:
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400

        # Get current user
        current_user = get_current_user()

        # Update branch
        response = branch_api.update_branch(branch_id, branch_data, updated_by=current_user)

        if response['success']:
            return jsonify(response), 200
        else:
            return jsonify(response), 400 if 'not found' not in response.get('error', '').lower() else 404

    except Exception as e:
        logger.error(f"Error in API update branch {branch_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Internal server error: {str(e)}'
        }), 500

@branch_blueprint.route('/api/branches/<int:branch_id>', methods=['DELETE'])
def api_delete_branch(branch_id: int):
    """
    API endpoint to delete a branch (soft delete).

    Args:
        branch_id (int): The ID of the branch to delete

    Returns:
        JSON response with deletion status
    """
    try:
        # Check user permissions
        if not validate_user_permissions('component_delete'):
            return jsonify({
                'success': False,
                'error': 'Access denied. Insufficient permissions to delete branches.'
            }), 403

        # Get current user
        current_user = get_current_user()

        # Delete branch (soft delete)
        response = branch_api.delete_branch(branch_id, deleted_by=current_user)

        if response['success']:
            return jsonify(response), 200
        else:
            return jsonify(response), 404 if 'not found' in response.get('error', '').lower() else 500

    except Exception as e:
        logger.error(f"Error in API delete branch {branch_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Internal server error: {str(e)}'
        }), 500

@branch_blueprint.route('/api/components/dropdown', methods=['GET'])
def api_get_components_dropdown():
    """
    API endpoint to get components for dropdown selection.

    Returns:
        JSON response with components list
    """
    try:
        # Check user permissions
        if not validate_user_permissions('component_read'):
            return jsonify({
                'success': False,
                'error': 'Access denied. Insufficient permissions.'
            }), 403

        # Get components for dropdown
        response = branch_api.get_components_for_dropdown()

        if response['success']:
            return jsonify(response), 200
        else:
            return jsonify(response), 500

    except Exception as e:
        logger.error(f"Error in API get components dropdown: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Internal server error: {str(e)}'
        }), 500

@branch_blueprint.route('/api/projects/dropdown', methods=['GET'])
def api_get_projects_dropdown():
    """
    API endpoint to get projects for dropdown selection.

    Returns:
        JSON response with projects list
    """
    try:
        # Check user permissions
        if not validate_user_permissions('component_read'):
            return jsonify({
                'success': False,
                'error': 'Access denied. Insufficient permissions.'
            }), 403

        # Get projects for dropdown
        response = branch_api.get_projects_for_dropdown()

        if response['success']:
            return jsonify(response), 200
        else:
            return jsonify(response), 500

    except Exception as e:
        logger.error(f"Error in API get projects dropdown: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Internal server error: {str(e)}'
        }), 500

@branch_blueprint.route('/api/components/by_project/<int:project_id>', methods=['GET'])
def api_get_components_by_project(project_id: int):
    """
    API endpoint to get components for a specific project.

    Args:
        project_id (int): The ID of the project

    Returns:
        JSON response with components list
    """
    try:
        # Check user permissions
        if not validate_user_permissions('component_read'):
            return jsonify({
                'success': False,
                'error': 'Access denied. Insufficient permissions.'
            }), 403

        # Get components by project
        response = branch_api.get_components_by_project(project_id)

        if response['success']:
            return jsonify(response), 200
        else:
            return jsonify(response), 500

    except Exception as e:
        logger.error(f"Error in API get components by project {project_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Internal server error: {str(e)}'
        }), 500

# ============================================================
# ERROR HANDLERS
# ============================================================

@branch_blueprint.errorhandler(404)
def not_found_error(error):
    """Handle 404 errors for branch management routes."""
    return jsonify({
        'success': False,
        'error': 'Endpoint not found'
    }), 404

@branch_blueprint.errorhandler(405)
def method_not_allowed_error(error):
    """Handle 405 errors for branch management routes."""
    return jsonify({
        'success': False,
        'error': 'Method not allowed'
    }), 405

@branch_blueprint.errorhandler(500)
def internal_error(error):
    """Handle 500 errors for branch management routes."""
    logger.error(f"Internal server error in branch management: {str(error)}")
    return jsonify({
        'success': False,
        'error': 'Internal server error'
    }), 500