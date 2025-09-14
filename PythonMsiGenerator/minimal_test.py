#!/usr/bin/env python3
import sys
import os

print("=== Minimal Flask Test ===")
print(f"Python: {sys.executable}")
print(f"Directory: {os.getcwd()}")

try:
    from flask import Flask
    print("✅ Flask imported successfully")
    
    app = Flask(__name__)
    
    @app.route('/')
    def home():
        return "<h1>IT WORKS!</h1><p>Flask server is running on port 6000</p>"
    
    print("✅ Flask app created")
    print("🚀 Starting server on http://localhost:6000")
    print("👉 OPEN YOUR BROWSER TO: http://localhost:6000")
    print("👉 OR TRY: http://127.0.0.1:6000")
    print("=" * 50)
    
    app.run(host='127.0.0.1', port=6000, debug=False)
    
except Exception as e:
    print(f"❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
    input("Press Enter to exit...")