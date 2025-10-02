"""
Cleanup Manager Module
Handles cleanup of old builds (keeps last 5 builds only)
"""

import os
import shutil
from typing import List, Dict
import logging
from db_helper import DatabaseHelper

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CleanupManager:
    """Manages cleanup of old builds"""

    def __init__(self, db_helper: DatabaseHelper):
        """Initialize with database helper"""
        self.db = db_helper
        self.max_builds_to_keep = self.db.get_max_builds_to_keep()

    def delete_file_or_folder(self, path: str) -> bool:
        """Delete file or folder safely"""
        try:
            if not path or not os.path.exists(path):
                logger.debug(f"Path does not exist: {path}")
                return True

            if os.path.isfile(path):
                os.remove(path)
                logger.info(f"Deleted file: {path}")
            elif os.path.isdir(path):
                shutil.rmtree(path)
                logger.info(f"Deleted folder: {path}")

            return True

        except Exception as e:
            logger.error(f"Failed to delete {path}: {str(e)}")
            return False

    def cleanup_old_builds(self, component_id: int, branch_id: int) -> Dict[str, any]:
        """
        Cleanup old builds for a component/branch
        Keeps only the last N builds (configurable, default 5)
        Returns: Dictionary with cleanup statistics
        """
        try:
            # Get list of builds to delete from database
            builds_to_delete = self.db.cleanup_old_builds(
                component_id, branch_id, self.max_builds_to_keep
            )

            if not builds_to_delete:
                logger.debug(f"No builds to cleanup for component {component_id}, branch {branch_id}")
                return {
                    'success': True,
                    'deleted_count': 0,
                    'failed_count': 0,
                    'space_freed': 0
                }

            deleted_count = 0
            failed_count = 0
            space_freed = 0

            for build in builds_to_delete:
                download_path = build.get('download_path')
                extraction_path = build.get('extraction_path')

                # Calculate space before deletion
                if download_path and os.path.exists(download_path):
                    space_freed += os.path.getsize(download_path)

                if extraction_path and os.path.exists(extraction_path):
                    space_freed += self.get_folder_size(extraction_path)

                # Delete download file (.zip)
                if download_path:
                    if self.delete_file_or_folder(download_path):
                        deleted_count += 1
                    else:
                        failed_count += 1

                # Delete extraction folder
                if extraction_path:
                    if self.delete_file_or_folder(extraction_path):
                        deleted_count += 1
                    else:
                        failed_count += 1

            # Log cleanup activity
            self.db.log_polling_activity(
                log_level='INFO',
                log_message=f'Cleanup completed: {deleted_count} items deleted, {space_freed} bytes freed',
                component_id=component_id,
                branch_id=branch_id,
                operation_type='cleanup'
            )

            logger.info(f"Cleanup completed for component {component_id}, branch {branch_id}")
            logger.info(f"Deleted: {deleted_count}, Failed: {failed_count}, Space freed: {space_freed} bytes")

            return {
                'success': True,
                'deleted_count': deleted_count,
                'failed_count': failed_count,
                'space_freed': space_freed
            }

        except Exception as e:
            logger.error(f"Cleanup failed: {str(e)}")
            return {
                'success': False,
                'deleted_count': 0,
                'failed_count': 0,
                'space_freed': 0,
                'error': str(e)
            }

    def get_folder_size(self, folder_path: str) -> int:
        """Calculate total size of a folder"""
        try:
            total_size = 0
            for root, dirs, files in os.walk(folder_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    if os.path.exists(file_path):
                        total_size += os.path.getsize(file_path)
            return total_size

        except Exception as e:
            logger.error(f"Failed to calculate folder size: {str(e)}")
            return 0

    def cleanup_all_components(self) -> Dict[str, any]:
        """Cleanup old builds for all components"""
        try:
            # Get all active components
            query = """
                SELECT DISTINCT c.component_id, cb.branch_id
                FROM components c
                INNER JOIN component_branches cb ON c.component_id = cb.component_id
                WHERE c.is_enabled = 1 AND cb.is_active = 1
            """
            components = self.db.execute_query(query)

            total_deleted = 0
            total_failed = 0
            total_space_freed = 0
            components_processed = 0

            for component in components:
                component_id = component['component_id']
                branch_id = component['branch_id']

                result = self.cleanup_old_builds(component_id, branch_id)

                if result['success']:
                    total_deleted += result['deleted_count']
                    total_failed += result['failed_count']
                    total_space_freed += result['space_freed']
                    components_processed += 1

            logger.info(f"Global cleanup completed: {components_processed} components processed")
            logger.info(f"Total deleted: {total_deleted}, Total failed: {total_failed}")
            logger.info(f"Total space freed: {total_space_freed} bytes ({total_space_freed / (1024*1024):.2f} MB)")

            return {
                'success': True,
                'components_processed': components_processed,
                'total_deleted': total_deleted,
                'total_failed': total_failed,
                'total_space_freed': total_space_freed
            }

        except Exception as e:
            logger.error(f"Global cleanup failed: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    def cleanup_component_folder(self, component_guid: str) -> bool:
        """Completely remove component folder (for decommissioned components)"""
        try:
            base_drive = self.db.get_base_drive()
            component_folder = os.path.join(base_drive, str(component_guid))

            if os.path.exists(component_folder):
                shutil.rmtree(component_folder)
                logger.info(f"Component folder deleted: {component_folder}")
                return True
            else:
                logger.debug(f"Component folder does not exist: {component_folder}")
                return True

        except Exception as e:
            logger.error(f"Failed to delete component folder: {str(e)}")
            return False

    def get_storage_statistics(self, component_id: int = None) -> Dict[str, any]:
        """Get storage statistics for components"""
        try:
            if component_id:
                query = """
                    SELECT
                        c.component_id,
                        c.component_name,
                        c.component_guid,
                        COUNT(bh.history_id) as total_builds,
                        SUM(bh.file_size) as total_size
                    FROM components c
                    LEFT JOIN jfrog_build_history bh ON c.component_id = bh.component_id
                    WHERE c.component_id = ? AND bh.is_deleted = 0
                    GROUP BY c.component_id, c.component_name, c.component_guid
                """
                params = (component_id,)
            else:
                query = """
                    SELECT
                        c.component_id,
                        c.component_name,
                        c.component_guid,
                        COUNT(bh.history_id) as total_builds,
                        SUM(bh.file_size) as total_size
                    FROM components c
                    LEFT JOIN jfrog_build_history bh ON c.component_id = bh.component_id
                    WHERE c.is_enabled = 1 AND (bh.is_deleted = 0 OR bh.is_deleted IS NULL)
                    GROUP BY c.component_id, c.component_name, c.component_guid
                """
                params = None

            results = self.db.execute_query(query, params)
            return {
                'success': True,
                'statistics': results
            }

        except Exception as e:
            logger.error(f"Failed to get storage statistics: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
