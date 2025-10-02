"""
WINCORE Web Interface - Route Definitions
Handles all web routes for JFrog polling system management
"""

from flask import (
    render_template, request, jsonify, flash,
    redirect, url_for, session
)
import logging
from datetime import datetime
from db_helper import DatabaseHelper
from polling_engine import PollingEngine
from download_manager import DownloadManager
from extraction_manager import ExtractionManager
from cleanup_manager import CleanupManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def register_routes(app):
    db = DatabaseHelper()
    polling_engine = PollingEngine(db)

    @app.route('/')
    @app.route('/dashboard')
    def dashboard():
        """Main dashboard showing polling system status"""
        if 'username' not in session:
            return redirect(url_for('login'))

        # Get polling statistics
        stats = db.get_polling_statistics()
        return render_template('dashboard.html', stats=stats)

    @app.route('/components')
    def components():
        """Component management page"""
        if 'username' not in session:
            return redirect(url_for('login'))

        components = db.get_all_components_with_status()
        return render_template('components.html', components=components)

    @app.route('/api/components/<int:component_id>/polling', methods=['GET', 'POST'])
    def component_polling(component_id):
        """Manage polling settings for a component"""
        if 'username' not in session:
            return jsonify({'error': 'Authentication required'}), 401

        if request.method == 'GET':
            polling_config = db.get_component_polling_config(component_id)
            return jsonify(polling_config)

        elif request.method == 'POST':
            if session.get('role') not in ['admin', 'poweruser']:
                return jsonify({'error': 'Insufficient permissions'}), 403

            data = request.json
            success = db.update_polling_config(
                component_id=component_id,
                frequency=data.get('polling_frequency_seconds'),
                is_enabled=data.get('is_enabled'),
                updated_by=session.get('username')
            )

            return jsonify({
                'success': success,
                'message': 'Polling configuration updated successfully'
            })

    @app.route('/api/components/<int:component_id>/threads')
    def component_threads(component_id):
        """Get active polling threads for a component"""
        if 'username' not in session:
            return jsonify({'error': 'Authentication required'}), 401

        threads = db.get_component_threads(component_id)
        return jsonify(threads)

    @app.route('/api/polling/start', methods=['POST'])
    def start_polling():
        """Start the polling engine"""
        if 'username' not in session or session.get('role') != 'admin':
            return jsonify({'error': 'Admin access required'}), 403

        try:
            polling_engine.start()
            return jsonify({
                'success': True,
                'message': 'Polling engine started successfully'
            })
        except Exception as e:
            logger.error(f"Error starting polling engine: {str(e)}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/polling/stop', methods=['POST'])
    def stop_polling():
        """Stop the polling engine"""
        if 'username' not in session or session.get('role') != 'admin':
            return jsonify({'error': 'Admin access required'}), 403

        try:
            polling_engine.stop()
            return jsonify({
                'success': True,
                'message': 'Polling engine stopped successfully'
            })
        except Exception as e:
            logger.error(f"Error stopping polling engine: {str(e)}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/logs')
    def view_logs():
        """View system logs page"""
        if 'username' not in session:
            return redirect(url_for('login'))

        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        log_level = request.args.get('level', 'ALL')
        component_id = request.args.get('component_id')
        
        logs = db.get_polling_logs(
            page=page,
            per_page=per_page,
            log_level=log_level,
            component_id=component_id
        )
        
        return render_template('logs.html', logs=logs)

    @app.route('/builds')
    def build_history():
        """View build history page"""
        if 'username' not in session:
            return redirect(url_for('login'))

        component_id = request.args.get('component_id')
        branch_id = request.args.get('branch_id')
        
        builds = db.get_build_history(
            component_id=component_id,
            branch_id=branch_id
        )
        
        return render_template('builds.html', builds=builds)

    @app.route('/api/builds/<int:build_id>/retry', methods=['POST'])
    def retry_build(build_id):
        """Retry a failed build download/extraction"""
        if 'username' not in session or session.get('role') not in ['admin', 'poweruser']:
            return jsonify({'error': 'Insufficient permissions'}), 403

        try:
            build_info = db.get_build_info(build_id)
            if not build_info:
                return jsonify({'error': 'Build not found'}), 404

            # Retry download if it failed
            if build_info['download_status'] == 'failed':
                download_manager = DownloadManager(db)
                success, path = download_manager.download_and_track(
                    component_id=build_info['component_id'],
                    branch_id=build_info['branch_id'],
                    component_guid=build_info['component_guid'],
                    component_name=build_info['component_name'],
                    url=build_info['build_url'],
                    build_date=build_info['build_date'],
                    build_number=build_info['build_number']
                )
                if not success:
                    return jsonify({'error': 'Download retry failed'}), 500

            # Retry extraction if it failed
            if build_info['extraction_status'] == 'failed':
                extraction_manager = ExtractionManager(db)
                success = extraction_manager.extract_zip(
                    zip_path=build_info['download_path'],
                    extraction_path=build_info['extraction_path']
                )
                if not success:
                    return jsonify({'error': 'Extraction retry failed'}), 500

            return jsonify({
                'success': True,
                'message': 'Build retry initiated successfully'
            })

        except Exception as e:
            logger.error(f"Error retrying build: {str(e)}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/cleanup/trigger', methods=['POST'])
    def trigger_cleanup():
        """Trigger manual cleanup of old builds"""
        if 'username' not in session or session.get('role') != 'admin':
            return jsonify({'error': 'Admin access required'}), 403

        try:
            cleanup_manager = CleanupManager(db)
            result = cleanup_manager.run_cleanup()
            return jsonify(result)
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")
            return jsonify({'error': str(e)}), 500

    @app.route('/settings')
    def settings():
        """System settings page"""
        if 'username' not in session or session.get('role') != 'admin':
            flash('Admin access required', 'error')
            return redirect(url_for('login'))

        config = db.get_system_config()
        return render_template('settings.html', config=config)

    @app.route('/settings/save', methods=['POST'])
    def save_settings():
        """Save system settings"""
        if 'username' not in session or session.get('role') != 'admin':
            return jsonify({'error': 'Admin access required'}), 403

        try:
            settings = {
                'JFrogBaseURL': request.form.get('jfrog_base_url'),
                'MaxConcurrentThreads': request.form.get('max_threads'),
                'DefaultPollingFrequency': request.form.get('default_polling_frequency'),
                'MaxBuildsToKeep': request.form.get('max_builds_to_keep'),
                'LogRetentionDays': request.form.get('log_retention_days')
            }

            db.save_system_config(settings, session.get('username'))
            flash('Settings saved successfully', 'success')
            return redirect(url_for('settings'))

        except Exception as e:
            logger.error(f"Error saving settings: {str(e)}")
            flash('Error saving settings', 'error')
            return redirect(url_for('settings'))

    # Error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        logger.error(f"Internal server error: {str(error)}")
        return render_template('errors/500.html'), 500