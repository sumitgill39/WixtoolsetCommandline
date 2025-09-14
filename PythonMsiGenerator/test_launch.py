#!/usr/bin/env python3
import os
import sys

print("=== Python MSI Generator Launch Test ===")
print(f"Python version: {sys.version}")
print(f"Current directory: {os.getcwd()}")
print(f"Python path: {sys.executable}")

# Test imports
try:
    import flask
    print(f"✅ Flask version: {flask.__version__}")
except ImportError as e:
    print(f"❌ Flask import failed: {e}")
    sys.exit(1)

try:
    from app import app
    print("✅ App import successful")
except Exception as e:
    print(f"❌ App import failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test WiX
try:
    import subprocess
    result = subprocess.run(['wix', '--version'], capture_output=True, text=True, timeout=10)
    if result.returncode == 0:
        print(f"✅ WiX Toolset detected: {result.stdout.strip()}")
    else:
        print(f"❌ WiX command failed: {result.stderr}")
except FileNotFoundError:
    print("❌ WiX not found in PATH")
except Exception as e:
    print(f"❌ WiX test failed: {e}")

print("\n🚀 Starting Flask app...")
try:
    app.run(debug=True, host='0.0.0.0', port=6000, threaded=True)
except Exception as e:
    print(f"❌ Flask launch failed: {e}")
    import traceback
    traceback.print_exc()