"""
SSP (Self-Service Portal) API Client
Handles fetching JFrog credentials from SSP API
"""

import requests
from config import SSP_CONFIG
import logging

logger = logging.getLogger(__name__)

class SSPClient:
    def __init__(self):
        self.api_url = SSP_CONFIG['api_url']
        self.token = SSP_CONFIG['token']
        self.env = SSP_CONFIG['env']
        self.app_name = SSP_CONFIG['app_name']
        self.timeout = SSP_CONFIG['timeout']

    def get_jfrog_credentials(self):
        """
        Fetch JFrog credentials from SSP API
        Returns:
            tuple: (username, password) if successful, (None, None) if failed
        """
        try:
            headers = {
                'Authorization': f'Bearer {self.token}',
                'Content-Type': 'application/json'
            }
            
            payload = {
                'ENV': self.env,
                'APPName': self.app_name
            }

            response = requests.get(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=self.timeout
            )

            if response.status_code == 200:
                data = response.json()
                username = data.get('SVCJFROGUSR')
                password = data.get('SVCJFROGPAS')
                
                if username and password:
                    logger.info("Successfully retrieved JFrog credentials from SSP")
                    return username, password
                else:
                    logger.error("SSP API response missing required credentials")
                    return None, None
            else:
                logger.error(f"SSP API request failed with status code: {response.status_code}")
                return None, None

        except requests.RequestException as e:
            logger.error(f"Error fetching JFrog credentials from SSP: {str(e)}")
            return None, None