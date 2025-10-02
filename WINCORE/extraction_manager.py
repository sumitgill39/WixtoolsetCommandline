"""
Extraction Manager Module
Handles .zip file extraction to artifact folders
"""

import os
import zipfile
import shutil
from pathlib import Path
from typing import Optional, Tuple
import logging
from db_helper import DatabaseHelper

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ExtractionManager:
    """Manages artifact extraction"""

    def __init__(self, db_helper: DatabaseHelper):
        """Initialize with database helper"""
        self.db = db_helper
        self.extraction_timeout = 300  # 5 minutes

    def extract_zip(self, zip_path: str, extraction_path: str) -> bool:
        """
        Extract .zip file to specified path
        Returns: True if successful, False otherwise
        """
        try:
            if not os.path.exists(zip_path):
                logger.error(f"Zip file not found: {zip_path}")
                return False

            # Verify it's a valid zip file
            if not zipfile.is_zipfile(zip_path):
                logger.error(f"Invalid zip file: {zip_path}")
                return False

            # Create extraction directory if it doesn't exist
            os.makedirs(extraction_path, exist_ok=True)

            logger.info(f"Extracting: {zip_path}")
            logger.info(f"Destination: {extraction_path}")

            # Extract all files
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                # Get total file count
                file_count = len(zip_ref.namelist())
                logger.info(f"Total files in archive: {file_count}")

                # Extract with progress logging
                extracted_count = 0
                for file in zip_ref.namelist():
                    zip_ref.extract(file, extraction_path)
                    extracted_count += 1

                    # Log progress every 100 files
                    if extracted_count % 100 == 0:
                        progress = (extracted_count / file_count * 100) if file_count > 0 else 0
                        logger.info(f"Extraction progress: {progress:.1f}%")

            logger.info(f"Extraction completed: {extracted_count} files extracted")
            return True

        except zipfile.BadZipFile:
            logger.error(f"Corrupted zip file: {zip_path}")
            return False

        except Exception as e:
            logger.error(f"Extraction failed: {str(e)}")
            return False

    def verify_extraction(self, extraction_path: str) -> bool:
        """Verify extraction was successful"""
        try:
            if not os.path.exists(extraction_path):
                logger.error(f"Extraction path does not exist: {extraction_path}")
                return False

            # Check if directory has files
            files = os.listdir(extraction_path)
            if not files:
                logger.error(f"Extraction path is empty: {extraction_path}")
                return False

            logger.info(f"Extraction verified: {len(files)} items found")
            return True

        except Exception as e:
            logger.error(f"Extraction verification failed: {str(e)}")
            return False

    def extract_artifact(self, component_id: int, branch_id: int, component_guid: str,
                        component_name: str, zip_path: str) -> Tuple[bool, Optional[str]]:
        """
        Extract artifact and update tracking
        Returns: (success, extraction_path)

        Extraction path format: BaseDrive:/WINCORE/{ComponentGUID}/a/{componentName}/
        """
        try:
            # Build extraction path
            base_drive = self.db.get_base_drive()
            extraction_path = os.path.join(
                base_drive,
                str(component_guid),
                'a',
                component_name
            )

            # Remove existing extraction if present
            if os.path.exists(extraction_path):
                logger.info(f"Removing existing extraction: {extraction_path}")
                shutil.rmtree(extraction_path)

            # Extract zip file
            success = self.extract_zip(zip_path, extraction_path)

            if not success:
                # Update status as failed
                self.db.execute_non_query(
                    """
                    UPDATE jfrog_build_tracking
                    SET extraction_status = 'failed',
                        error_message = 'Extraction failed',
                        updated_date = GETDATE()
                    WHERE component_id = ? AND branch_id = ?
                    """,
                    (component_id, branch_id)
                )
                return False, None

            # Verify extraction
            if not self.verify_extraction(extraction_path):
                logger.error("Extraction verification failed")
                return False, extraction_path

            # Update tracking with extraction info
            success = self.db.update_extraction_status(
                component_id, branch_id, extraction_path
            )

            if success:
                # Log activity
                self.db.log_polling_activity(
                    log_level='INFO',
                    log_message=f'Extracted artifact: {component_name}',
                    component_id=component_id,
                    branch_id=branch_id,
                    operation_type='extraction'
                )

                logger.info(f"Extraction tracked successfully for component {component_id}")
                return True, extraction_path
            else:
                logger.error("Failed to update extraction tracking")
                return False, extraction_path

        except Exception as e:
            logger.error(f"Extract artifact failed: {str(e)}")
            return False, None

    def get_extracted_files(self, extraction_path: str) -> list:
        """Get list of extracted files"""
        try:
            if not os.path.exists(extraction_path):
                return []

            files = []
            for root, dirs, filenames in os.walk(extraction_path):
                for filename in filenames:
                    file_path = os.path.join(root, filename)
                    files.append(file_path)

            return files

        except Exception as e:
            logger.error(f"Failed to get extracted files: {str(e)}")
            return []

    def get_extraction_size(self, extraction_path: str) -> int:
        """Calculate total size of extracted files"""
        try:
            total_size = 0
            for root, dirs, files in os.walk(extraction_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    if os.path.exists(file_path):
                        total_size += os.path.getsize(file_path)

            return total_size

        except Exception as e:
            logger.error(f"Failed to calculate extraction size: {str(e)}")
            return 0
