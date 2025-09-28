"""
Flask Application Factory
Creates and configures the Flask application
"""

from flask import Flask
import sys
import os

def create_app():
    """Create and configure the Flask application"""

    # Create Flask app
    app = Flask(__name__,
                template_folder='../webapp/templates',
                static_folder='../webapp/static')

    # Configure secret key
    app.secret_key = os.environ.get('SECRET_KEY', 'msi_factory_main_secret_key_change_in_production')

    # Configure upload limits
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

    # Configure session
    app.config['SESSION_TYPE'] = 'filesystem'
    app.config['PERMANENT_SESSION_LIFETIME'] = 3600  # 1 hour

    # Add paths for imports
    sys.path.append('auth')
    sys.path.append('database')
    sys.path.append('api')
    sys.path.append('engine')

    return app

def init_components(app):
    """Initialize application components"""
    from auth.simple_auth import SimpleAuth
    from logger import get_logger
    from api.api_client import get_api_client

    # Initialize components
    auth_system = SimpleAuth()
    logger = get_logger()

    # Initialize API client
    try:
        api_client = get_api_client()
        if api_client and api_client.check_health():
            print("[INFO] Connected to MSI Factory API")
        else:
            print("[WARNING] API server not responding, using fallback methods")
            api_client = None
    except Exception as e:
        print(f"[WARNING] Could not initialize API client: {e}")
        api_client = None

    return {
        'auth_system': auth_system,
        'logger': logger,
        'api_client': api_client
    }

def register_routes(app, components):
    """Register all application routes"""
    from core.routes import register_all_routes
    from core.htmx_views import register_htmx_routes

    # Register main routes
    register_all_routes(app, components)

    # Register HTMX routes for dynamic updates
    register_htmx_routes(app, components)