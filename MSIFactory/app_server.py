#!/usr/bin/env python3
"""
Production WSGI Server for MSI Factory
Uses Waitress for production deployment
"""

import sys
import os
from waitress import serve
from main import app, init_system

def start_production_server():
    """Start production WSGI server"""
    print("============================================================")
    print("MSI FACTORY - Production Server")
    print("============================================================")
    
    # Initialize system
    init_system()
    
    # Server configuration
    host = '0.0.0.0'
    port = 5000
    threads = 4
    
    print(f"\nStarting Waitress WSGI Server...")
    print(f"Host: {host}")
    print(f"Port: {port}")
    print(f"Threads: {threads}")
    print(f"URL: http://localhost:{port}")
    print("\nPress Ctrl+C to stop the server")
    print("============================================================\n")
    
    # Start production server
    serve(app, host=host, port=port, threads=threads)

if __name__ == '__main__':
    try:
        start_production_server()
    except KeyboardInterrupt:
        print("\n\nServer stopped by user")
    except Exception as e:
        print(f"\nError starting server: {e}")
        sys.exit(1)