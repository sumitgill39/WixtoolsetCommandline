"""
MSI Factory API Server Startup Script
Run this to start the independent API server
"""

import sys
import os

# Add the current directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import and run the API server
from api.api_server import api_app

if __name__ == '__main__':
    port = int(os.environ.get('API_PORT', 5001))
    debug = os.environ.get('API_DEBUG', 'False').lower() == 'true'
    
    print(f"""
    ╔══════════════════════════════════════════════════════╗
    ║         MSI Factory REST API Server                  ║
    ╠══════════════════════════════════════════════════════╣
    ║  Running on: http://localhost:{port}                   ║
    ║  API Docs: http://localhost:{port}/api/status          ║
    ║  Health: http://localhost:{port}/api/health            ║
    ║                                                      ║
    ║  Available Endpoints:                                ║
    ║  • GET    /api/projects                              ║
    ║  • POST   /api/projects                              ║
    ║  • GET    /api/projects/{{id}}                         ║
    ║  • PUT    /api/projects/{{id}}                         ║
    ║  • DELETE /api/projects/{{id}}                         ║
    ║  • GET    /api/projects/{{id}}/environments            ║
    ║  • POST   /api/projects/{{id}}/environments            ║
    ║  • DELETE /api/projects/{{id}}/environments/{{name}}    ║
    ║  • GET    /api/components                             ║
    ║  • POST   /api/components                             ║
    ║  • GET    /api/components/{{id}}                       ║
    ║  • PUT    /api/components/{{id}}                       ║
    ║  • DELETE /api/components/{{id}}                       ║
    ╚══════════════════════════════════════════════════════╝
    """)
    
    try:
        api_app.run(host='0.0.0.0', port=port, debug=debug)
    except KeyboardInterrupt:
        print("\n\nAPI Server stopped by user")
    except Exception as e:
        print(f"\nError starting API server: {e}")
        sys.exit(1)