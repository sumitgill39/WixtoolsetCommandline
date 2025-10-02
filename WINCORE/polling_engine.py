"""
Multi-threaded Polling Engine
Handles concurrent polling of JFrog artifacts across multiple components and branches
Supports 10K+ concurrent threads with thread pool management
"""

import threading
import time
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Optional
import logging
from db_helper import DatabaseHelper
from jfrog_config import JFrogConfig
from download_manager import DownloadManager
from extraction_manager import ExtractionManager
from cleanup_manager import CleanupManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PollingEngine:
    """Multi-threaded polling engine for JFrog artifacts"""

    def __init__(self, db_helper: DatabaseHelper):
        """Initialize polling engine"""
        self.db = db_helper
        self.jfrog = JFrogConfig(db_helper)
        self.download_mgr = DownloadManager(db_helper, self.jfrog)
        self.extract_mgr = ExtractionManager(db_helper)
        self.cleanup_mgr = CleanupManager(db_helper)

        self.max_threads = self.db.get_max_threads()
        self.is_running = False
        self.executor = None
        self.active_threads = {}
        self.thread_lock = threading.Lock()

    def start(self):
        """Start the polling engine"""
        if self.is_running:
            logger.warning("Polling engine is already running")
            return

        logger.info(f"Starting polling engine with max {self.max_threads} threads")
        self.is_running = True

        # Create JFrog session
        self.jfrog.create_session()

        # Test JFrog connection
        success, message = self.jfrog.test_connection()
        if not success:
            logger.error(f"JFrog connection failed: {message}")
            self.is_running = False
            return

        # Initialize thread pool executor
        self.executor = ThreadPoolExecutor(max_workers=self.max_threads)

        logger.info("Polling engine started successfully")

    def stop(self):
        """Stop the polling engine"""
        if not self.is_running:
            logger.warning("Polling engine is not running")
            return

        logger.info("Stopping polling engine...")
        self.is_running = False

        if self.executor:
            self.executor.shutdown(wait=True)
            logger.info("Thread pool executor shutdown complete")

        logger.info("Polling engine stopped")

    def poll_component_branch(self, config: Dict) -> Dict[str, any]:
        """
        Poll a single component/branch for new builds
        Returns: Result dictionary with status and details
        """
        component_id = config['component_id']
        branch_id = config['branch_id']
        component_guid = config['component_guid']
        component_name = config['component_name']
        project_key = config['project_key']
        branch_name = config['branch_name']
        polling_interval = config.get('polling_interval_seconds', 300)

        start_time = time.time()

        try:
            logger.info(f"Polling: {component_name} - {branch_name}")

            # Get current build tracking
            current_tracking = self.db.get_build_tracking(component_id, branch_id)

            # Determine starting point for search
            if current_tracking:
                start_date = current_tracking.get('latest_build_date')
                start_build = current_tracking.get('latest_build_number', 1)
            else:
                start_date = datetime.now().strftime('%Y%m%d')
                start_build = 1

            # Find latest build
            latest_build = self.jfrog.find_latest_build(
                project_key, component_guid, branch_name,
                component_name, start_date, start_build
            )

            if not latest_build:
                logger.debug(f"No new builds found for {component_name} - {branch_name}")
                duration_ms = int((time.time() - start_time) * 1000)
                return {
                    'success': True,
                    'new_build': False,
                    'component_id': component_id,
                    'branch_id': branch_id,
                    'duration_ms': duration_ms
                }

            build_date, build_number = latest_build

            # Check if this is a new build
            is_new_build = False
            if not current_tracking:
                is_new_build = True
            elif (build_date > current_tracking.get('latest_build_date') or
                  (build_date == current_tracking.get('latest_build_date') and
                   build_number > current_tracking.get('latest_build_number'))):
                is_new_build = True

            if not is_new_build:
                logger.debug(f"No new builds for {component_name} - {branch_name}")
                duration_ms = int((time.time() - start_time) * 1000)
                return {
                    'success': True,
                    'new_build': False,
                    'component_id': component_id,
                    'branch_id': branch_id,
                    'duration_ms': duration_ms
                }

            # New build found!
            logger.info(f"New build found: {component_name} - Build{build_date}.{build_number}")

            # Build download URL
            download_url = self.jfrog.build_artifact_url(
                project_key, component_guid, branch_name,
                build_date, build_number, component_name
            )

            # Update build tracking
            self.db.update_build_tracking(
                component_id, branch_id, build_date, build_number,
                download_url, 'downloading', 'pending'
            )

            # Download artifact
            download_success, download_path = self.download_mgr.download_and_track(
                component_id, branch_id, component_guid, component_name,
                download_url, build_date, build_number
            )

            if not download_success:
                logger.error(f"Download failed for {component_name}")
                duration_ms = int((time.time() - start_time) * 1000)
                return {
                    'success': False,
                    'new_build': True,
                    'component_id': component_id,
                    'branch_id': branch_id,
                    'error': 'Download failed',
                    'duration_ms': duration_ms
                }

            # Extract artifact
            extract_success, extraction_path = self.extract_mgr.extract_artifact(
                component_id, branch_id, component_guid,
                component_name, download_path
            )

            if not extract_success:
                logger.error(f"Extraction failed for {component_name}")
                duration_ms = int((time.time() - start_time) * 1000)
                return {
                    'success': False,
                    'new_build': True,
                    'component_id': component_id,
                    'branch_id': branch_id,
                    'error': 'Extraction failed',
                    'duration_ms': duration_ms
                }

            # Insert into build history
            file_size = self.download_mgr.calculate_checksum(download_path) if download_path else 0
            checksum = self.download_mgr.calculate_checksum(download_path)

            self.db.insert_build_history(
                component_id, branch_id, build_date, build_number,
                download_url, download_path, extraction_path,
                file_size, checksum
            )

            # Cleanup old builds
            cleanup_result = self.cleanup_mgr.cleanup_old_builds(component_id, branch_id)
            logger.info(f"Cleanup: {cleanup_result.get('deleted_count', 0)} items deleted")

            duration_ms = int((time.time() - start_time) * 1000)

            # Log successful polling
            self.db.log_polling_activity(
                log_level='INFO',
                log_message=f'New build processed: Build{build_date}.{build_number}',
                component_id=component_id,
                branch_id=branch_id,
                build_date=build_date,
                build_number=build_number,
                operation_type='poll',
                duration_ms=duration_ms
            )

            logger.info(f"Polling completed successfully: {component_name} - Build{build_date}.{build_number}")

            return {
                'success': True,
                'new_build': True,
                'component_id': component_id,
                'branch_id': branch_id,
                'build_date': build_date,
                'build_number': build_number,
                'download_path': download_path,
                'extraction_path': extraction_path,
                'duration_ms': duration_ms
            }

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            logger.error(f"Polling failed for {component_name}: {str(e)}")

            # Log error
            self.db.log_polling_activity(
                log_level='ERROR',
                log_message=f'Polling failed: {str(e)}',
                component_id=component_id,
                branch_id=branch_id,
                operation_type='poll',
                duration_ms=duration_ms
            )

            return {
                'success': False,
                'new_build': False,
                'component_id': component_id,
                'branch_id': branch_id,
                'error': str(e),
                'duration_ms': duration_ms
            }

    def poll_all_components(self) -> List[Dict]:
        """
        Poll all active components/branches concurrently
        Returns: List of results
        """
        if not self.is_running:
            logger.error("Polling engine is not running")
            return []

        # Get active polling configurations
        configs = self.db.get_active_polling_config()

        if not configs:
            logger.warning("No active polling configurations found")
            return []

        logger.info(f"Polling {len(configs)} component/branch combinations")

        # Submit polling tasks to thread pool
        futures = []
        for config in configs:
            future = self.executor.submit(self.poll_component_branch, config)
            futures.append(future)

        # Collect results
        results = []
        for future in as_completed(futures):
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                logger.error(f"Thread execution failed: {str(e)}")

        # Log summary
        successful = sum(1 for r in results if r.get('success'))
        new_builds = sum(1 for r in results if r.get('new_build'))
        failed = sum(1 for r in results if not r.get('success'))

        logger.info(f"Polling cycle complete: {successful} successful, {new_builds} new builds, {failed} failed")

        return results

    def run_continuous_polling(self, interval_seconds: int = 300):
        """
        Run continuous polling at specified interval
        Default: 5 minutes (300 seconds)
        """
        self.start()

        try:
            while self.is_running:
                logger.info("=" * 60)
                logger.info(f"Starting polling cycle at {datetime.now()}")

                # Poll all components
                results = self.poll_all_components()

                # Wait for next cycle
                logger.info(f"Waiting {interval_seconds} seconds for next cycle...")
                time.sleep(interval_seconds)

        except KeyboardInterrupt:
            logger.info("Polling interrupted by user")
        finally:
            self.stop()

    def get_engine_status(self) -> Dict[str, any]:
        """Get current engine status"""
        return {
            'is_running': self.is_running,
            'max_threads': self.max_threads,
            'active_threads': len(self.active_threads),
            'jfrog_connected': self.jfrog.session is not None
        }
