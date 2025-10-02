"""
JFrog URL Builder Module
Handles construction of JFrog artifact URLs using project/component patterns
"""

from datetime import datetime
from typing import Optional, Dict, Union
import logging
from urllib.parse import urljoin, quote
from db_helper import DatabaseHelper
from ssp_client import SSPClient

logger = logging.getLogger(__name__)

class JFrogUrlBuilder:
    """Builds JFrog URLs based on component and pattern information"""

    DEFAULT_PATTERN = "{ProjectShortKey}/{ComponentName}/{branch}/Build{date}.{buildNumber}/{componentName}.zip"
    DATE_FORMAT = "%Y%m%d"

    def __init__(self, db_helper: DatabaseHelper, ssp_client: SSPClient):
        """Initialize with database helper and SSP client"""
        self.db = db_helper
        self.ssp_client = ssp_client
        self._base_url = None
        self._credentials = None
        self._last_cred_fetch = None

    def _get_jfrog_base_url(self) -> str:
        """Get JFrog base URL from system config"""
        if not self._base_url:
            base_url = self.db.get_system_config('JFrogBaseURL')
            if not base_url:
                raise ValueError("JFrog base URL not configured in system")
            # Ensure URL ends with /
            self._base_url = base_url if base_url.endswith('/') else base_url + '/'
        return self._base_url

    def _get_component_info(self, component_id: int) -> Dict:
        """Get component and project information"""
        info = self.db.get_component_info(component_id)
        if not info:
            raise ValueError(f"Component {component_id} not found")
        return info

    def _get_pattern(self, component_id: int, branch: str) -> str:
        """Get URL pattern for component/branch"""
        pattern = self.db.get_branch_pattern(component_id, branch)
        return pattern if pattern else self.DEFAULT_PATTERN

    def _get_build_number(self, component_id: int) -> int:
        """Get next build number for component"""
        latest = self.db.get_latest_build_number(component_id)
        return (latest + 1) if latest is not None else 1

    def _get_credentials(self) -> Dict[str, str]:
        """Get JFrog credentials from SSP"""
        # Check if we have cached credentials
        now = datetime.now()
        if (self._credentials and self._last_cred_fetch and 
            (now - self._last_cred_fetch).total_seconds() < 900):  # 15 min cache
            return self._credentials

        username, password = self.ssp_client.get_jfrog_credentials()
        if not username or not password:
            raise RuntimeError("Failed to get JFrog credentials from SSP")

        self._credentials = {'username': username, 'password': password}
        self._last_cred_fetch = now
        return self._credentials

    def build_url(self, 
                 component_id: int, 
                 branch: Optional[str] = None,
                 build_number: Optional[int] = None,
                 date: Optional[datetime] = None) -> Dict[str, Union[str, Dict]]:
        """
        Build complete JFrog URL for component and branch.
        Returns dict with url and auth info.
        """
        try:
            # Get component info
            info = self._get_component_info(component_id)
            project_key = info['project_key']
            component_name = info['component_name']
            
            # Use provided branch or default from component
            branch = branch or info.get('default_branch', 'main')
            
            # Get pattern
            pattern = self._get_pattern(component_id, branch)
            
            # Get current date if not provided
            date = date or datetime.now()
            date_str = date.strftime(self.DATE_FORMAT)
            
            # Get build number
            build_num = build_number or self._get_build_number(component_id)
            
            # Substitute variables in pattern
            path = pattern.format(
                ProjectShortKey=project_key,
                ComponentName=component_name,
                branch=branch,
                date=date_str,
                buildNumber=build_num,
                componentName=component_name.lower()
            )
            
            # URL encode path segments
            encoded_path = '/'.join(quote(part) for part in path.split('/'))
            
            # Join with base URL
            base_url = self._get_jfrog_base_url()
            full_url = urljoin(base_url, encoded_path)
            
            # Get credentials
            auth = self._get_credentials()
            
            return {
                'url': full_url,
                'pattern': pattern,
                'auth': auth,
                'build_info': {
                    'date': date_str,
                    'build_number': build_num
                }
            }
            
        except Exception as e:
            logger.error(f"Error building JFrog URL for component {component_id}: {str(e)}")
            raise