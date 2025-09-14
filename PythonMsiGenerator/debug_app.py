#!/usr/bin/env python3
from flask import Flask, render_template
import os

app = Flask(__name__)

@app.route('/')
def index():
    try:
        print("Route / accessed")
        template_path = os.path.join('templates', 'index.html')
        if os.path.exists(template_path):
            print(f"✅ Template found: {template_path}")
        else:
            print(f"❌ Template NOT found: {template_path}")
            return "<h1>Template Missing</h1><p>index.html not found in templates folder</p>"
        
        return render_template('index.html')
    except Exception as e:
        print(f"❌ Error in route: {e}")
        import traceback
        traceback.print_exc()
        return f"<h1>Error</h1><pre>{str(e)}</pre>"

@app.route('/test')
def test():
    return "<h1>Test Route Works!</h1>"

if __name__ == '__main__':
    print("=== Debug App ===")
    print(f"Templates folder exists: {os.path.exists('templates')}")
    print(f"Index.html exists: {os.path.exists('templates/index.html')}")
    print("Starting debug server...")
    app.run(host='127.0.0.1', port=6000, debug=True)