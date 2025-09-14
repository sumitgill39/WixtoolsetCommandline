#!/usr/bin/env python3
"""
Python MSI Generator - Web Application
A Flask-based web interface for generating MSI packages using WiX Toolset v6

Requirements:
- Python 3.7+
- Flask
- WiX Toolset v6 (wix.exe must be available in PATH)

Usage:
    python run.py

Then open: http://localhost:5000
"""

import os
import sys
from app import app

if __name__ == '__main__':
    # Check if wix.exe is available
    try:
        import subprocess
        result = subprocess.run(['wix', '--version'], capture_output=True, text=True)
        print(f"✅ WiX Toolset detected: {result.stdout.strip()}")
    except FileNotFoundError:
        print("❌ ERROR: WiX Toolset not found!")
        print("Please install WiX Toolset v6:")
        print("  dotnet tool install --global wix")
        sys.exit(1)
    
    print("🚀 Starting Python MSI Generator...")
    print("📡 Server will be available at: http://localhost:5001")
    print("📁 Upload directory: temp_uploads/")
    
    # Create upload directory
    os.makedirs('temp_uploads', exist_ok=True)
    
    # Run the Flask app
    app.run(
        debug=True,
        host='0.0.0.0',
        port=5001,
        threaded=True
    )