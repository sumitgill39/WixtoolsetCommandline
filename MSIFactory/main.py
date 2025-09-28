#!/usr/bin/env python3
"""
MSI Factory - Main Application (Refactored)
This is the main entry point that uses segregated modules
"""

import os
import sys
from core.app_factory import create_app, init_components, register_routes

def init_system():
    """Initialize the MSI Factory system on first run"""
    print("=" * 60)
    print("MSI Factory - System Initialization")
    print("=" * 60)

    # Create output directory if it doesn't exist
    if not os.path.exists('output'):
        os.makedirs('output')
        print("[OK] Created output directory")

    # Create logs directory if it doesn't exist
    if not os.path.exists('logs'):
        os.makedirs('logs')
        print("[OK] Created logs directory")

    print("[OK] System initialization complete")
    print("=" * 60)

def main():
    """Main application entry point"""
    # Initialize system on first run
    init_system()

    # Create Flask application
    app = create_app()

    # Initialize components
    components = init_components(app)

    # Register all routes
    register_routes(app, components)

    # Print startup information
    print("\n" + "=" * 60)
    print("MSI Factory - Refactored Version")
    print("=" * 60)
    print(f"Server: http://localhost:5000")
    print(f"Templates: {app.template_folder}")
    print(f"Static: {app.static_folder}")
    print("=" * 60 + "\n")

    # Run the application
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True
    )

if __name__ == '__main__':
    main()