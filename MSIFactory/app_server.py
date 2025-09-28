#!/usr/bin/env python3
"""
Production WSGI Server for MSI Factory
Uses Waitress for production deployment with comprehensive logging
"""

import sys
import os
import logging
from waitress import serve
from main import init_system
from core.app_factory import create_app, init_components, register_routes
from core.logging_config import setup_comprehensive_logging, configure_flask_app_logging

def start_production_server():
    """Start production WSGI server with comprehensive logging"""
    print("============================================================")
    print("MSI FACTORY - Production Server")
    print("============================================================")

    # Initialize comprehensive logging FIRST
    print("Initializing comprehensive logging system...")
    logger_system = setup_comprehensive_logging()

    # Get system logger
    system_logger = logging.getLogger('system')
    error_logger = logging.getLogger('errors')

    try:
        # Initialize system
        system_logger.info("Initializing MSI Factory system...")
        init_system()

        # Create and configure the Flask application using factory pattern
        system_logger.info("Creating Flask application...")
        app = create_app()

        # Configure Flask app with comprehensive logging
        app = configure_flask_app_logging(app, logger_system)

        system_logger.info("Initializing components...")
        components = init_components(app)

        system_logger.info("Registering routes...")
        register_routes(app, components)

        # Server configuration
        host = '0.0.0.0'
        port = 5000
        threads = 4

        # Configure Waitress logging
        waitress_logger = logging.getLogger('waitress')

        system_logger.info("=" * 60)
        system_logger.info(f"Starting Waitress WSGI Server")
        system_logger.info(f"Host: {host}")
        system_logger.info(f"Port: {port}")
        system_logger.info(f"Threads: {threads}")
        system_logger.info(f"URL: http://localhost:{port}")
        system_logger.info("=" * 60)

        print(f"\nStarting Waitress WSGI Server...")
        print(f"Host: {host}")
        print(f"Port: {port}")
        print(f"Threads: {threads}")
        print(f"URL: http://localhost:{port}")
        print(f"\nLogs are being written to: logs/system.log and logs/error.log")
        print("Press Ctrl+C to stop the server")
        print("============================================================\n")

        # Start production server with logging
        serve(app, host=host, port=port, threads=threads,
              _quiet=False,  # Don't suppress Waitress logs
              connection_limit=1000,
              cleanup_interval=10,
              channel_timeout=120)

    except Exception as e:
        error_logger.error(f"Failed to start production server: {str(e)}", exc_info=True)
        system_logger.error(f"CRITICAL: Server startup failed: {str(e)}")
        print(f"\nError starting server: {e}")
        print("Check logs/error.log for details")
        raise

if __name__ == '__main__':
    try:
        start_production_server()
    except KeyboardInterrupt:
        print("\n\nServer stopped by user")
    except Exception as e:
        print(f"\nError starting server: {e}")
        sys.exit(1)