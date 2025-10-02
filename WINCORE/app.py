"""
JFrog Polling System - Web UI
Flask web application for managing JFrog polling system
"""

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from datetime import datetime
import threading
from db_helper import DatabaseHelper
from jfrog_config import JFrogConfig
from polling_engine import PollingEngine
from cleanup_manager import CleanupManager
from jfrog_url_builder import JFrogUrlBuilder
from ssp_client import SSPClient

app = Flask(__name__)
app.secret_key = 'jfrog-polling-secret-key-change-in-production'

# Global instances
db = None
jfrog_config = None
polling_engine = None
cleanup_manager = None
polling_thread = None

def init_app():
    """Initialize application components"""
    global db, jfrog_config, polling_engine, cleanup_manager, url_builder, ssp_client

    db = DatabaseHelper()
    if db.connect():
        ssp_client = SSPClient()
        jfrog_config = JFrogConfig(db)
        polling_engine = PollingEngine(db)
        cleanup_manager = CleanupManager(db)
        url_builder = JFrogUrlBuilder(db, ssp_client)
        return True
    return False

@app.route('/')
def dashboard():
    """Main dashboard"""
    if not db:
        init_app()

    # Get statistics
    configs = db.get_active_polling_config()

    # Get recent logs
    recent_logs = db.execute_query("""
        SELECT TOP 10
            log_level, log_message, operation_type, log_date
        FROM jfrog_polling_log
        ORDER BY log_date DESC
    """)

    # Get build tracking summary
    build_summary = db.execute_query("""
        SELECT
            COUNT(*) as total_tracked,
            SUM(CASE WHEN download_status = 'completed' THEN 1 ELSE 0 END) as downloaded,
            SUM(CASE WHEN extraction_status = 'completed' THEN 1 ELSE 0 END) as extracted,
            SUM(CASE WHEN download_status = 'failed' THEN 1 ELSE 0 END) as failed
        FROM jfrog_build_tracking
    """)

    stats = {
        'active_components': len(configs),
        'recent_logs': recent_logs,
        'build_summary': build_summary[0] if build_summary else {},
        'polling_status': 'Running' if polling_engine and polling_engine.is_running else 'Stopped'
    }

    return render_template('dashboard.html', stats=stats)

@app.route('/url-preview')
def url_preview_page():
    """URL Preview Page"""
    if not db:
        init_app()

    # Get all active components with project info
    query = """
        SELECT 
            c.component_id,
            c.component_name,
            p.project_name
        FROM components c
        INNER JOIN projects p ON c.project_id = p.project_id
        WHERE c.is_enabled = 1
        ORDER BY p.project_name, c.component_name
    """
    components = db.execute_query(query)

    return render_template('url_preview.html', components=components)

@app.route('/api/component/<int:component_id>/jfrog_url_preview')
def preview_jfrog_url(component_id):
    """Preview JFrog URL for component"""
    if not db:
        init_app()

    try:
        branch = request.args.get('branch')
        build_number = request.args.get('build')
        if build_number:
            build_number = int(build_number)

        url_info = url_builder.build_url(
            component_id=component_id,
            branch=branch,
            build_number=build_number
        )

        # Don't include auth info in response
        url_info.pop('auth', None)
        return jsonify(url_info)

    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/config')
def config():
    """Configuration page"""
    if not db:
        init_app()

    # Get all system config
    system_config = db.execute_query("SELECT * FROM jfrog_system_config WHERE is_enabled = 1")

    config_dict = {}
    for item in system_config:
        key = item['config_key']
        value = item['config_value']
        if item['is_encrypted'] and value:
            value = '****'
        config_dict[key] = value

    # Get SSP config
    ssp_url, ssp_token = db.get_ssp_config()
    if ssp_url:
        config_dict['SSP_API_URL'] = ssp_url
        config_dict['SSP_API_TOKEN'] = '****' if ssp_token else ''
    config_dict['SSP_ENV'] = 'PROD'  # Fixed value
    config_dict['SSP_APP_NAME'] = 'WINCORE'  # Fixed value

    return render_template('config.html', config=config_dict)

@app.route('/config/update', methods=['POST'])
def update_config():
    """Update configuration"""
    if not db:
        init_app()

    # Get form data
    jfrog_url = request.form.get('JFrogBaseURL')
    ssp_api_url = request.form.get('SSP_API_URL')
    ssp_api_token = request.form.get('SSP_API_TOKEN')
    base_drive = request.form.get('BaseDrive')

    # Update JFrog URL
    if jfrog_url:
        db.update_system_config('JFrogBaseURL', jfrog_url, 'web_ui')

    # Update SSP config
    if ssp_api_url:
        db.update_ssp_config(ssp_api_url, ssp_api_token if ssp_api_token else None)

    # Update base drive
    if base_drive:
        db.update_system_config('BaseDrive', base_drive, 'web_ui')
    max_threads = request.form.get('MaxConcurrentThreads')
    max_builds = request.form.get('MaxBuildsToKeep')

    if jfrog_url:
        db.update_system_config('JFrogBaseURL', jfrog_url, 'web_ui')
    if username:
        db.update_system_config('SVCJFROGUSR', username, 'web_ui')
    if password:
        db.update_system_config('SVCJFROGPAS', password, 'web_ui')
    if base_drive:
        db.update_system_config('BaseDrive', base_drive, 'web_ui')
    if max_threads:
        db.update_system_config('MaxConcurrentThreads', max_threads, 'web_ui')
    if max_builds:
        db.update_system_config('MaxBuildsToKeep', max_builds, 'web_ui')

    flash('Configuration updated successfully!', 'success')
    return redirect(url_for('config'))

@app.route('/config/test')
def test_connection():
    """Test JFrog connection"""
    if not jfrog_config:
        init_app()

    jfrog_config.load_config()
    success, message = jfrog_config.test_connection()

    if success:
        flash(f'Connection test successful: {message}', 'success')
    else:
        flash(f'Connection test failed: {message}', 'error')

    return redirect(url_for('config'))

@app.route('/components')
def components():
    """View all components"""
    if not db:
        init_app()

    components_list = db.execute_query("""
        SELECT
            c.component_id,
            c.component_name,
            c.component_guid,
            p.project_name,
            p.project_key,
            c.polling_enabled,
            c.is_enabled,
            bt.latest_build_date,
            bt.latest_build_number,
            bt.download_status,
            bt.extraction_status
        FROM components c
        INNER JOIN projects p ON c.project_id = p.project_id
        LEFT JOIN jfrog_build_tracking bt ON c.component_id = bt.component_id
        WHERE c.is_enabled = 1
        ORDER BY c.component_name
    """)

    return render_template('components.html', components=components_list)

@app.route('/component/<int:component_id>')
def component_detail(component_id):
    """Component detail page"""
    if not db:
        init_app()

    # Get component details
    component = db.execute_query("""
        SELECT
            c.*,
            p.project_name,
            p.project_key
        FROM components c
        INNER JOIN projects p ON c.project_id = p.project_id
        WHERE c.component_id = ?
    """, (component_id,))

    # Get branches
    branches = db.execute_query("""
        SELECT
            cb.*,
            bt.latest_build_date,
            bt.latest_build_number,
            bt.download_status,
            bt.extraction_status,
            bt.last_checked_time
        FROM component_branches cb
        LEFT JOIN jfrog_build_tracking bt ON cb.branch_id = bt.branch_id
        WHERE cb.component_id = ?
        ORDER BY cb.branch_name
    """, (component_id,))

    # Get build history
    history = db.execute_query("""
        SELECT TOP 10 *
        FROM jfrog_build_history
        WHERE component_id = ?
        ORDER BY created_date DESC
    """, (component_id,))

    return render_template('component_detail.html',
                         component=component[0] if component else None,
                         branches=branches,
                         history=history)

@app.route('/logs')
def logs():
    """View polling logs"""
    if not db:
        init_app()

    # Get filter parameters
    log_level = request.args.get('level', 'all')
    limit = int(request.args.get('limit', 100))

    query = "SELECT TOP ? * FROM jfrog_polling_log"
    params = [limit]

    if log_level != 'all':
        query += " WHERE log_level = ?"
        params.append(log_level)

    query += " ORDER BY log_date DESC"

    logs_list = db.execute_query(query, tuple(params))

    return render_template('logs.html', logs=logs_list, current_level=log_level)

@app.route('/polling/start')
def start_polling():
    """Start polling"""
    global polling_thread

    if not polling_engine:
        init_app()

    if polling_engine.is_running:
        flash('Polling is already running', 'warning')
    else:
        def run_polling():
            polling_engine.run_continuous_polling(300)

        polling_thread = threading.Thread(target=run_polling, daemon=True)
        polling_thread.start()
        flash('Polling started successfully', 'success')

    return redirect(url_for('dashboard'))

@app.route('/polling/stop')
def stop_polling():
    """Stop polling"""
    if not polling_engine:
        init_app()

    if polling_engine.is_running:
        polling_engine.stop()
        flash('Polling stopped successfully', 'success')
    else:
        flash('Polling is not running', 'warning')

    return redirect(url_for('dashboard'))

@app.route('/polling/run')
def run_single_poll():
    """Run single poll cycle"""
    if not polling_engine:
        init_app()

    polling_engine.start()
    results = polling_engine.poll_all_components()
    polling_engine.stop()

    successful = sum(1 for r in results if r.get('success'))
    new_builds = sum(1 for r in results if r.get('new_build'))

    flash(f'Poll completed: {successful} successful, {new_builds} new builds found', 'success')
    return redirect(url_for('dashboard'))

@app.route('/cleanup/run')
def run_cleanup():
    """Run cleanup"""
    if not cleanup_manager:
        init_app()

    result = cleanup_manager.cleanup_all_components()

    if result['success']:
        flash(f"Cleanup completed: {result['total_deleted']} items deleted, "
              f"{result['total_space_freed'] / (1024*1024):.2f} MB freed", 'success')
    else:
        flash(f"Cleanup failed: {result.get('error')}", 'error')

    return redirect(url_for('dashboard'))

@app.route('/api/stats')
def api_stats():
    """API endpoint for statistics"""
    if not db:
        init_app()

    stats = db.execute_query("""
        SELECT
            COUNT(*) as total_components,
            SUM(CASE WHEN polling_enabled = 1 THEN 1 ELSE 0 END) as polling_enabled_count
        FROM components
        WHERE is_enabled = 1
    """)

    return jsonify(stats[0] if stats else {})

@app.route('/api/recent_activity')
def api_recent_activity():
    """API endpoint for recent activity"""
    if not db:
        init_app()

    activity = db.execute_query("""
        SELECT TOP 20
            log_level,
            log_message,
            operation_type,
            log_date
        FROM jfrog_polling_log
        ORDER BY log_date DESC
    """)

    # Convert datetime to string for JSON serialization
    for item in activity:
        if item.get('log_date'):
            item['log_date'] = item['log_date'].strftime('%Y-%m-%d %H:%M:%S')

    return jsonify(activity)

@app.route('/component/<int:component_id>/toggle')
def toggle_component(component_id):
    """Toggle component polling enabled/disabled"""
    if not db:
        init_app()

    # Get current status
    component = db.execute_query(
        "SELECT polling_enabled FROM components WHERE component_id = ?",
        (component_id,)
    )

    if component:
        new_status = 0 if component[0]['polling_enabled'] else 1
        db.execute_non_query(
            "UPDATE components SET polling_enabled = ? WHERE component_id = ?",
            (new_status, component_id)
        )

        status_text = 'enabled' if new_status else 'disabled'
        flash(f'Component polling {status_text}', 'success')

    return redirect(url_for('components'))

if __name__ == '__main__':
    if init_app():
        print("=" * 60)
        print("JFrog Polling System - Web UI")
        print("=" * 60)
        print("\nStarting web server on http://localhost:5050")
        print("\nAccess the dashboard at: http://localhost:5050")
        print("\nPress CTRL+C to stop")
        print("=" * 60)
        app.run(debug=True, host='0.0.0.0', port=5050)
    else:
        print("ERROR: Failed to initialize application. Check database connection.")
