"""
Download Manager Module
Handles artifact downloading with folder structure creation
"""

import os
import requests
import hashlib
from pathlib import Path
from typing import Optional, Tuple
import logging
from db_helper import DatabaseHelper
from jfrog_config import JFrogConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DownloadManager:
    """Manages artifact downloads and folder structure"""

    def __init__(self, db_helper: DatabaseHelper, jfrog_config: JFrogConfig):
        """Initialize with database helper and JFrog config"""
        self.db = db_helper
        self.jfrog = jfrog_config
        self.base_drive = self.db.get_base_drive()
        self.download_timeout = 600  # 10 minutes

    def create_folder_structure(self, component_guid: str) -> Tuple[str, str]:
        """
        Create folder structure for component
        Returns: (source_folder_path, artifact_folder_path)

        Structure:
        BaseDrive:/WINCORE/{ComponentGUID}/s/  (source/download folder)
        BaseDrive:/WINCORE/{ComponentGUID}/a/  (artifact/extraction folder)
        """
        try:
            # Create base component folder
            component_base = os.path.join(self.base_drive, str(component_guid))

            # Create 's' folder for downloaded .zip files
            source_folder = os.path.join(component_base, 's')
            os.makedirs(source_folder, exist_ok=True)

            # Create 'a' folder for extracted artifacts
            artifact_folder = os.path.join(component_base, 'a')
            os.makedirs(artifact_folder, exist_ok=True)

            logger.info(f"Folder structure created for component {component_guid}")
            logger.debug(f"Source folder: {source_folder}")
            logger.debug(f"Artifact folder: {artifact_folder}")

            return source_folder, artifact_folder

        except Exception as e:
            logger.error(f"Failed to create folder structure: {str(e)}")
            raise

    def download_artifact(self, url: str, component_guid: str, component_name: str,
                         build_date: str, build_number: int) -> Optional[str]:
        """
        Download artifact from JFrog URL
        Returns: download_path or None if failed
        """
        try:
            # Create folder structure
            source_folder, artifact_folder = self.create_folder_structure(component_guid)

            # Build download file path
            filename = f"{component_name}.zip"
            download_path = os.path.join(source_folder, filename)

            logger.info(f"Starting download: {url}")
            logger.info(f"Download path: {download_path}")

            # Ensure session exists
            if not self.jfrog.session:
                self.jfrog.create_session()

            # Download with streaming for large files
            response = self.jfrog.session.get(url, stream=True, timeout=self.download_timeout)

            if response.status_code == 200:
                # Get file size
                file_size = int(response.headers.get('Content-Length', 0))

                # Download and save file
                with open(download_path, 'wb') as file:
                    downloaded = 0
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            file.write(chunk)
                            downloaded += len(chunk)

                            # Log progress every 10MB
                            if downloaded % (10 * 1024 * 1024) == 0:
                                progress = (downloaded / file_size * 100) if file_size > 0 else 0
                                logger.info(f"Download progress: {progress:.1f}%")

                logger.info(f"Download completed: {download_path}")
                logger.info(f"File size: {file_size} bytes")

                return download_path

            else:
                logger.error(f"Download failed with status code: {response.status_code}")
                return None

        except requests.exceptions.Timeout:
            logger.error("Download timeout exceeded")
            return None

        except Exception as e:
            logger.error(f"Download failed: {str(e)}")
            return None

    def calculate_checksum(self, file_path: str, algorithm: str = 'sha256') -> Optional[str]:
        """Calculate file checksum"""
        try:
            hash_obj = hashlib.new(algorithm)

            with open(file_path, 'rb') as file:
                for chunk in iter(lambda: file.read(8192), b''):
                    hash_obj.update(chunk)

            checksum = hash_obj.hexdigest()
            logger.debug(f"Checksum ({algorithm}): {checksum}")
            return checksum

        except Exception as e:
            logger.error(f"Checksum calculation failed: {str(e)}")
            return None

    def verify_download(self, file_path: str, expected_size: int = None) -> bool:
        """Verify downloaded file"""
        try:
            if not os.path.exists(file_path):
                logger.error(f"File does not exist: {file_path}")
                return False

            actual_size = os.path.getsize(file_path)

            if expected_size and actual_size != expected_size:
                logger.error(f"File size mismatch. Expected: {expected_size}, Actual: {actual_size}")
                return False

            logger.info("Download verification successful")
            return True

        except Exception as e:
            logger.error(f"Download verification failed: {str(e)}")
            return False

    def download_and_track(self, component_id: int, branch_id: int, component_guid: str,
                          component_name: str, url: str, build_date: str,
                          build_number: int) -> Tuple[bool, Optional[str]]:
        """
        Download artifact and update tracking in database
        Returns: (success, download_path)
        """
        try:
            # Download artifact
            download_path = self.download_artifact(
                url, component_guid, component_name, build_date, build_number
            )

            if not download_path:
                # Update status as failed
                self.db.execute_non_query(
                    """
                    UPDATE jfrog_build_tracking
                    SET download_status = 'failed',
                        error_message = 'Download failed',
                        updated_date = GETDATE()
                    WHERE component_id = ? AND branch_id = ?
                    """,
                    (component_id, branch_id)
                )
                return False, None

            # Get file size and checksum
            file_size = os.path.getsize(download_path)
            checksum = self.calculate_checksum(download_path)

            # Update tracking with download info
            success = self.db.update_download_status(
                component_id, branch_id, download_path, file_size, checksum
            )

            if success:
                # Log activity
                self.db.log_polling_activity(
                    log_level='INFO',
                    log_message=f'Downloaded artifact: {component_name}',
                    component_id=component_id,
                    branch_id=branch_id,
                    build_date=build_date,
                    build_number=build_number,
                    operation_type='download'
                )

                logger.info(f"Download tracked successfully for component {component_id}")
                return True, download_path
            else:
                logger.error("Failed to update download tracking")
                return False, download_path

        except Exception as e:
            logger.error(f"Download and track failed: {str(e)}")
            return False, None

    def get_artifact_folder(self, component_guid: str) -> str:
        """Get artifact folder path for a component"""
        _, artifact_folder = self.create_folder_structure(component_guid)
        return artifact_folder
