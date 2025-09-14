#!/usr/bin/env python3
"""
MSI Factory - Main Application
This is the main entry point that combines authentication and MSI generation
"""

import os
import sys
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify

# Import our authentication system
sys.path.append('auth')
from simple_auth import SimpleAuth

# Import our MSI generation engine
sys.path.append('engine')

app = Flask(__name__, template_folder='webapp/templates', static_folder='webapp/static')
app.secret_key = 'msi_factory_main_secret_key_change_in_production'

# Initialize components
auth_system = SimpleAuth()

@app.route('/')
def home():
    """Main entry point - redirect based on login status"""
    if 'username' in session:
        return redirect(url_for('factory_dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page (uses authentication system)"""
    if request.method == 'POST':
        username = request.form['username']
        domain = request.form.get('domain', 'COMPANY')
        
        user = auth_system.check_user_login(username, domain)
        
        if user and user['status'] == 'approved':
            # Login successful
            session['username'] = user['username']
            session['email'] = user['email']
            session['first_name'] = user['first_name']
            session['last_name'] = user['last_name']
            session['role'] = user['role']
            session['approved_apps'] = user['approved_apps']
            
            flash(f'Welcome to MSI Factory, {user["first_name"]}!', 'success')
            return redirect(url_for('factory_dashboard'))
        else:
            flash('Access denied. Please contact administrator.', 'error')
    
    return render_template('login.html')

@app.route('/dashboard')
def factory_dashboard():
    """Main MSI Factory Dashboard"""
    if 'username' not in session:
        return redirect(url_for('login'))
    
    # Get user's applications
    user_apps = session.get('approved_apps', [])
    applications = auth_system.load_applications()
    
    user_applications = []
    for app in applications:
        if app['app_short_key'] in user_apps or '*' in user_apps:
            user_applications.append(app)
    
    return render_template('factory_dashboard.html', applications=user_applications)

@app.route('/generate-msi', methods=['GET', 'POST'])
def generate_msi():
    """MSI Generation page"""
    if 'username' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'GET':
        # Show MSI generation form
        app_key = request.args.get('app_key')
        
        # Check if user has access to this app
        user_apps = session.get('approved_apps', [])
        if app_key not in user_apps and '*' not in user_apps:
            flash('You do not have access to this application', 'error')
            return redirect(url_for('factory_dashboard'))
        
        # Load component configuration if exists
        config_file = f'config/{app_key.lower()}-config.json'
        config = None
        if os.path.exists(config_file):
            import json
            with open(config_file, 'r') as f:
                config = json.load(f)
        
        return render_template('generate_msi.html', app_key=app_key, config=config)
    
    elif request.method == 'POST':
        # Process MSI generation request
        app_key = request.form['app_key']
        component_type = request.form['component_type']
        environments = request.form.getlist('environments')
        
        # Here we would call the MSI Factory engine
        results = {
            'app_key': app_key,
            'component_type': component_type,
            'environments': environments,
            'status': 'queued',
            'message': 'MSI generation has been queued'
        }
        
        flash(f'MSI generation started for {app_key}', 'success')
        return jsonify(results)

@app.route('/msi-status/<job_id>')
def msi_status(job_id):
    """Check MSI generation status"""
    if 'username' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    # This would check actual job status
    status = {
        'job_id': job_id,
        'status': 'in_progress',
        'progress': 50,
        'message': 'Generating MSI for PROD environment...'
    }
    
    return jsonify(status)

@app.route('/admin')
def admin_panel():
    """Admin panel for user management"""
    if 'username' not in session or session.get('role') != 'admin':
        flash('Admin access required', 'error')
        return redirect(url_for('login'))
    
    # Get all pending requests
    pending_requests = auth_system.get_pending_requests()
    
    # Get system statistics
    stats = {
        'total_users': len(auth_system.load_users()),
        'pending_requests': len(pending_requests),
        'total_applications': len(auth_system.load_applications()),
        'msi_generated_today': 0  # Would connect to actual stats
    }
    
    return render_template('admin_panel.html', requests=pending_requests, stats=stats)

@app.route('/api/applications')
def api_applications():
    """API endpoint to get applications"""
    if 'username' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    applications = auth_system.load_applications()
    return jsonify(applications)

@app.route('/api/generate-msi', methods=['POST'])
def api_generate_msi():
    """API endpoint for MSI generation"""
    if 'username' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.json
    app_key = data.get('app_key')
    environments = data.get('environments', [])
    
    # Validate user has access
    user_apps = session.get('approved_apps', [])
    if app_key not in user_apps and '*' not in user_apps:
        return jsonify({'error': 'Access denied for this application'}), 403
    
    # Queue MSI generation job
    job_id = f"JOB_{app_key}_{len(environments)}"
    
    return jsonify({
        'job_id': job_id,
        'status': 'queued',
        'message': f'MSI generation queued for {len(environments)} environments'
    })

@app.route('/logout')
def logout():
    """Logout user"""
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('login'))

# Error handlers
@app.errorhandler(404)
def not_found(e):
    return render_template('error.html', error='Page not found'), 404

@app.errorhandler(500)
def server_error(e):
    return render_template('error.html', error='Internal server error'), 500

def initialize_system():
    """Initialize the MSI Factory system"""
    print("=" * 60)
    print("🏭 MSI FACTORY - Enterprise MSI Generation System")
    print("=" * 60)
    
    # Create necessary directories
    directories = ['webapp/templates', 'webapp/static', 'config', 'output', 'logs']
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
    
    print("✅ System initialized")
    print("📁 Directories created")
    print("🔐 Authentication system loaded")
    print("🚀 Ready to generate MSIs!")
    print("=" * 60)

if __name__ == '__main__':
    # Initialize system
    initialize_system()
    
    print("\n🌐 Starting MSI Factory Server...")
    print("📍 URL: http://localhost:5000")
    print("👤 Admin: admin")
    print("👤 User: john.doe")
    print("\nPress CTRL+C to stop the server")
    print("-" * 60)
    
    # Run the application
    app.run(debug=True, host='0.0.0.0', port=5000)