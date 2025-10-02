"""
JFrog Configuration Management Module
Handles JFrog credentials, URL construction, and authentication
"""

import requests
from typing import Optional, Tuple
from datetime import datetime
import logging
from db_helper import DatabaseHelper
from ssp_client import SSPClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class JFrogConfig:
    """JFrog configuration and credential management"""

    def __init__(self, db_helper: DatabaseHelper):
        """Initialize with database helper"""
        self.db = db_helper
        self.base_url = None
        self.username = None
        self.password = None
        self.session = None
        self.ssp_client = SSPClient()
        self.load_config()

    def load_config(self) -> bool:
        """Load JFrog configuration from database and SSP"""
        try:
            # Get base URL from database
            self.base_url, _, _ = self.db.get_jfrog_credentials()

            if not self.base_url:
                logger.warning("JFrog Base URL not configured")
                return False

            # Get credentials from SSP
            self.username, self.password = self.ssp_client.get_jfrog_credentials()

            if not self.username or not self.password:
                logger.warning("Failed to get JFrog credentials from SSP")
                return False

            logger.info(f"JFrog configuration loaded: {self.base_url}")
            return True

        except Exception as e:
            logger.error(f"Failed to load JFrog configuration: {str(e)}")
            return False

    def create_session(self) -> bool:
        """Create authenticated requests session"""
        try:
            self.session = requests.Session()
            self.session.auth = (self.username, self.password)
            self.session.headers.update({
                'Content-Type': 'application/json'
            })
            logger.info("JFrog session created successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to create JFrog session: {str(e)}")
            return False

    def test_connection(self) -> Tuple[bool, str]:
        """Test JFrog connection and credentials"""
        try:
            if not self.session:
                self.create_session()

            # Test with a simple API call
            test_url = f"{self.base_url}/api/system/ping"
            response = self.session.get(test_url, timeout=10)

            if response.status_code == 200:
                logger.info("JFrog connection test successful")
                return True, "Connection successful"
            else:
                error_msg = f"Connection failed with status code: {response.status_code}"
                logger.error(error_msg)
                return False, error_msg

        except requests.exceptions.RequestException as e:
            error_msg = f"Connection test failed: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    def build_artifact_url(self, project_key: str, component_guid: str,
                          branch: str, build_date: str, build_number: int,
                          component_name: str) -> str:
        """
        Build JFrog artifact URL
        Format: https://{JFROGBaseURL}/{ProjectShortKey}/{ComponentGUID}/{branch}/Build{date}.{buildNumber}/{componentName}.zip
        """
        url = (
            f"{self.base_url}/"
            f"{project_key}/"
            f"{component_guid}/"
            f"{branch}/"
            f"Build{build_date}.{build_number}/"
            f"{component_name}.zip"
        )
        return url

    def check_artifact_exists(self, url: str) -> bool:
        """Check if artifact exists at given URL"""
        try:
            if not self.session:
                self.create_session()

            response = self.session.head(url, timeout=10)

            if response.status_code == 200:
                logger.debug(f"Artifact found: {url}")
                return True
            elif response.status_code == 404:
                logger.debug(f"Artifact not found: {url}")
                return False
            else:
                logger.warning(f"Unexpected status code {response.status_code} for: {url}")
                return False

        except requests.exceptions.RequestException as e:
            logger.error(f"Error checking artifact: {str(e)}")
            return False

    def find_latest_build(self, project_key: str, component_guid: str,
                         branch: str, component_name: str,
                         start_date: str = None, start_build: int = 1) -> Optional[Tuple[str, int]]:
        """
        Find the latest available build by incrementing build numbers
        Returns: (build_date, build_number) or None
        """
        if not start_date:
            start_date = datetime.now().strftime('%Y%m%d')

        current_date = start_date
        current_build = start_build
        latest_found = None
        consecutive_misses = 0
        max_consecutive_misses = 10  # Stop after 10 consecutive misses

        # Try incrementing build numbers
        while consecutive_misses < max_consecutive_misses and current_build <= 1000:
            url = self.build_artifact_url(
                project_key, component_guid, branch,
                current_date, current_build, component_name
            )

            if self.check_artifact_exists(url):
                latest_found = (current_date, current_build)
                consecutive_misses = 0
                current_build += 1
            else:
                consecutive_misses += 1
                current_build += 1

        if latest_found:
            logger.info(f"Latest build found: Build{latest_found[0]}.{latest_found[1]}")

        return latest_found

    def get_artifact_info(self, url: str) -> Optional[dict]:
        """Get artifact metadata"""
        try:
            if not self.session:
                self.create_session()

            response = self.session.head(url, timeout=10)

            if response.status_code == 200:
                info = {
                    'url': url,
                    'size': int(response.headers.get('Content-Length', 0)),
                    'last_modified': response.headers.get('Last-Modified', ''),
                    'content_type': response.headers.get('Content-Type', '')
                }
                return info
            else:
                return None

        except requests.exceptions.RequestException as e:
            logger.error(f"Error getting artifact info: {str(e)}")
            return None

    def update_config(self, base_url: str = None, username: str = None,
                     password: str = None, updated_by: str = 'admin') -> bool:
        """Update JFrog configuration in database"""
        try:
            if base_url:
                self.db.update_system_config('JFrogBaseURL', base_url, updated_by)
                self.base_url = base_url

            if username:
                self.db.update_system_config('SVCJFROGUSR', username, updated_by)
                self.username = username

            if password:
                self.db.update_system_config('SVCJFROGPAS', password, updated_by)
                self.password = password

            # Recreate session with new credentials
            self.create_session()

            logger.info("JFrog configuration updated successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to update JFrog configuration: {str(e)}")
            return False

    def validate_url_pattern(self, pattern: str) -> bool:
        """Validate JFrog URL pattern"""
        required_placeholders = [
            '{branch}',
            'Build{date}',
            '{buildNumber}',
            '{componentName}'
        ]

        for placeholder in required_placeholders:
            if placeholder not in pattern:
                logger.error(f"Missing required placeholder: {placeholder}")
                return False

        return True
