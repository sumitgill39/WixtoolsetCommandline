"""
MSI Factory REST API Server
Independent REST API server for all database operations
Can run standalone on a different port or be imported
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
from .project_api import ProjectAPI
from .component_api import ComponentAPI
from .simple_logger import get_simple_logger
import logging
import os
import time
from functools import wraps

# Initialize Flask app for API
api_app = Flask(__name__)
api_app.secret_key = os.environ.get('API_SECRET_KEY', 'msi_factory_api_secret_key_change_in_production')

# Enable CORS for API access from different origins
CORS(api_app)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize simple logger
try:
    simple_logger = get_simple_logger()
except Exception as e:
    logger.warning(f"Failed to initialize simple logger: {e}")
    simple_logger = None

# Initialize API handlers
project_api = ProjectAPI()
component_api = ComponentAPI()

# Request logging decorator
def log_api_request(f):
    """Decorator to log all API requests"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        start_time = time.time()
        
        # Get request details
        method = request.method
        endpoint = request.endpoint or request.path
        full_url = request.url
        user_agent = request.headers.get('User-Agent', '')
        ip_address = request.environ.get('REMOTE_ADDR', 'unknown')
        referrer = request.headers.get('Referer', '')
        
        # Sanitize request data (don't log sensitive information)
        request_data = {}
        if request.is_json:
            try:
                request_data = request.get_json() or {}
                # Remove any sensitive fields
                sensitive_fields = ['password', 'secret', 'token', 'key', 'auth']
                for field in sensitive_fields:
                    if field in request_data:
                        request_data[field] = '***REDACTED***'
            except Exception:
                request_data = {'error': 'Failed to parse JSON'}
        elif request.form:
            request_data = dict(request.form)
            # Remove sensitive fields
            for field in ['password', 'secret', 'token', 'key', 'auth']:
                if field in request_data:
                    request_data[field] = '***REDACTED***'
        
        # Execute the function
        try:
            response = f(*args, **kwargs)
            
            # Calculate response time
            response_time = time.time() - start_time
            response_time_ms = int(response_time * 1000)
            
            # Get status code from response
            if isinstance(response, tuple):
                status_code = response[1] if len(response) > 1 else 200
            else:
                status_code = 200
            
            # Log the request
            if system_logger:
                system_logger.log_request(
                    method=method,
                    endpoint=endpoint,
                    full_url=full_url,
                    status_code=status_code,
                    user_agent=user_agent,
                    ip_address=ip_address,
                    referrer=referrer,
                    request_data=request_data,
                    response_time_ms=response_time_ms
                )
            
            return response
            
        except Exception as e:
            # Calculate response time for errors
            response_time = time.time() - start_time
            response_time_ms = int(response_time * 1000)
            
            # Log the failed request
            if system_logger:
                system_logger.log_request(
                    method=method,
                    endpoint=endpoint,
                    full_url=full_url,
                    status_code=500,
                    user_agent=user_agent,
                    ip_address=ip_address,
                    referrer=referrer,
                    request_data=request_data,
                    response_time_ms=response_time_ms
                )
                
                # Log the error
                system_logger.log_error(
                    error=e,
                    module_name=__name__,
                    function_name=f.__name__,
                    context={
                        'method': method,
                        'endpoint': endpoint,
                        'request_data': request_data
                    }
                )
            
            raise  # Re-raise the exception
    
    return decorated_function

# ==================== PROJECT ENDPOINTS ====================

@api_app.route('/api/projects', methods=['GET'])
@log_api_request
def get_projects():
    """Get all projects"""
    try:
        success, message, projects = project_api.get_all_projects()
        if success:
            return jsonify({
                'success': True,
                'message': message,
                'data': projects
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': message
            }), 500
    except Exception as e:
        logger.error(f"Error in get_projects: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@api_app.route('/api/projects/<int:project_id>', methods=['GET'])
def get_project(project_id):
    """Get specific project by ID"""
    try:
        success, message, project = project_api.get_project_by_id(project_id)
        if success:
            return jsonify({
                'success': True,
                'message': message,
                'data': project
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': message
            }), 404
    except Exception as e:
        logger.error(f"Error in get_project: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@api_app.route('/api/projects/key/<string:project_key>', methods=['GET'])
def get_project_by_key(project_key):
    """Get specific project by key"""
    try:
        success, message, project = project_api.get_project_by_key(project_key)
        if success:
            return jsonify({
                'success': True,
                'message': message,
                'data': project
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': message
            }), 404
    except Exception as e:
        logger.error(f"Error in get_project_by_key: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@api_app.route('/api/projects', methods=['POST'])
@log_api_request
def create_project():
    """Create new project"""
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data.get('project_name') or not data.get('project_key'):
            return jsonify({
                'success': False,
                'message': 'project_name and project_key are required'
            }), 400
        
        success, message, project_id = project_api.create_project(data)
        
        if success:
            return jsonify({
                'success': True,
                'message': message,
                'data': {'project_id': project_id}
            }), 201
        else:
            return jsonify({
                'success': False,
                'message': message
            }), 400
    except Exception as e:
        logger.error(f"Error in create_project: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@api_app.route('/api/projects/<int:project_id>', methods=['PUT', 'PATCH'])
def update_project(project_id):
    """Update existing project"""
    try:
        data = request.get_json()
        success, message = project_api.update_project(project_id, data)
        
        if success:
            return jsonify({
                'success': True,
                'message': message
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': message
            }), 404
    except Exception as e:
        logger.error(f"Error in update_project: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@api_app.route('/api/projects/<int:project_id>', methods=['DELETE'])
def delete_project(project_id):
    """Delete project"""
    try:
        # Check for hard delete flag
        hard_delete = request.args.get('hard', 'false').lower() == 'true'
        
        success, message = project_api.delete_project(project_id, hard_delete)
        
        if success:
            return jsonify({
                'success': True,
                'message': message
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': message
            }), 404
    except Exception as e:
        logger.error(f"Error in delete_project: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

# ==================== ENVIRONMENT ENDPOINTS ====================

@api_app.route('/api/projects/<int:project_id>/environments', methods=['GET'])
def get_project_environments(project_id):
    """Get all environments for a project"""
    try:
        success, message, environments = project_api.get_project_environments(project_id)
        
        if success:
            return jsonify({
                'success': True,
                'message': message,
                'data': environments
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': message
            }), 404
    except Exception as e:
        logger.error(f"Error in get_project_environments: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@api_app.route('/api/projects/<int:project_id>/environments', methods=['POST'])
def add_environment(project_id):
    """Add environment to project"""
    try:
        data = request.get_json()
        
        if not data.get('environment_name'):
            return jsonify({
                'success': False,
                'message': 'environment_name is required'
            }), 400
        
        success, message = project_api.add_environment(
            project_id,
            data['environment_name'],
            data.get('description', '')
        )
        
        if success:
            return jsonify({
                'success': True,
                'message': message
            }), 201
        else:
            return jsonify({
                'success': False,
                'message': message
            }), 400
    except Exception as e:
        logger.error(f"Error in add_environment: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@api_app.route('/api/projects/<int:project_id>/environments/<string:env_name>', methods=['DELETE'])
def remove_environment(project_id, env_name):
    """Remove environment from project"""
    try:
        success, message = project_api.remove_environment(project_id, env_name)
        
        if success:
            return jsonify({
                'success': True,
                'message': message
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': message
            }), 404
    except Exception as e:
        logger.error(f"Error in remove_environment: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

# ==================== COMPONENT ENDPOINTS ====================

@api_app.route('/api/components', methods=['GET'])
def get_components():
    """Get all components or components for specific project"""
    try:
        project_id = request.args.get('project_id', type=int)
        success, message, components = component_api.get_all_components(project_id)
        
        if success:
            return jsonify({
                'success': True,
                'message': message,
                'data': components
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': message
            }), 500
    except Exception as e:
        logger.error(f"Error in get_components: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@api_app.route('/api/components/<int:component_id>', methods=['GET'])
def get_component(component_id):
    """Get specific component by ID"""
    try:
        success, message, component = component_api.get_component_by_id(component_id)
        if success:
            return jsonify({
                'success': True,
                'message': message,
                'data': component
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': message
            }), 404
    except Exception as e:
        logger.error(f"Error in get_component: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@api_app.route('/api/components/key/<string:component_key>', methods=['GET'])
def get_component_by_key(component_key):
    """Get specific component by key"""
    try:
        success, message, component = component_api.get_component_by_key(component_key)
        if success:
            return jsonify({
                'success': True,
                'message': message,
                'data': component
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': message
            }), 404
    except Exception as e:
        logger.error(f"Error in get_component_by_key: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@api_app.route('/api/components', methods=['POST'])
@log_api_request
def create_component():
    """Create new component"""
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data.get('component_name') or not data.get('component_key') or not data.get('project_id'):
            return jsonify({
                'success': False,
                'message': 'component_name, component_key, and project_id are required'
            }), 400
        
        success, message, component_id = component_api.create_component(data)
        
        if success:
            return jsonify({
                'success': True,
                'message': message,
                'data': {'component_id': component_id}
            }), 201
        else:
            return jsonify({
                'success': False,
                'message': message
            }), 400
    except Exception as e:
        logger.error(f"Error in create_component: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@api_app.route('/api/components/<int:component_id>', methods=['PUT', 'PATCH'])
def update_component(component_id):
    """Update existing component"""
    try:
        data = request.get_json()
        success, message = component_api.update_component(component_id, data)
        
        if success:
            return jsonify({
                'success': True,
                'message': message
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': message
            }), 404
    except Exception as e:
        logger.error(f"Error in update_component: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@api_app.route('/api/components/<int:component_id>', methods=['DELETE'])
def delete_component(component_id):
    """Delete component"""
    try:
        # Check for hard delete flag
        hard_delete = request.args.get('hard', 'false').lower() == 'true'
        
        success, message = component_api.delete_component(component_id, hard_delete)
        
        if success:
            return jsonify({
                'success': True,
                'message': message
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': message
            }), 404
    except Exception as e:
        logger.error(f"Error in delete_component: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

# ==================== HEALTH CHECK ====================

@api_app.route('/api/health', methods=['GET'])
def health_check():
    """API health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'MSI Factory API',
        'version': '1.0.0'
    }), 200

@api_app.route('/api/status', methods=['GET'])
def api_status():
    """Get API status and database connection"""
    try:
        # Check database connection
        db_connected = project_api.db is not None
        
        return jsonify({
            'status': 'running',
            'database_connected': db_connected,
            'endpoints': {
                'projects': '/api/projects',
                'environments': '/api/projects/{id}/environments',
                'components': '/api/components',
                'health': '/api/health'
            }
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

# ==================== ERROR HANDLERS ====================

@api_app.errorhandler(404)
def not_found(error):
    return jsonify({
        'success': False,
        'message': 'Endpoint not found'
    }), 404

@api_app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {error}")
    return jsonify({
        'success': False,
        'message': 'Internal server error'
    }), 500

# ==================== MAIN ====================

if __name__ == '__main__':
    """Run API server standalone"""
    port = int(os.environ.get('API_PORT', 5001))
    debug = os.environ.get('API_DEBUG', 'False').lower() == 'true'
    
    print(f"""
    ╔══════════════════════════════════════════════════════╗
    ║         MSI Factory REST API Server                  ║
    ╠══════════════════════════════════════════════════════╣
    ║  Running on: http://localhost:{port}                   ║
    ║  API Docs: http://localhost:{port}/api/status          ║
    ║  Health: http://localhost:{port}/api/health            ║
    ╚══════════════════════════════════════════════════════╝
    """)
    
    api_app.run(host='0.0.0.0', port=port, debug=debug)