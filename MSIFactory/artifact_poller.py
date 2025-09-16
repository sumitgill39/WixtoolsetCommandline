#!/usr/bin/env python3
"""
JFrog Artifact Polling System with GitFlow Support
Monitors JFrog repositories for new artifacts based on branch patterns
Handles multi-threaded polling for multiple components across projects
"""

import os
import sys
import time
import json
import threading
import queue
import hashlib
import zipfile
import shutil
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import requests
from requests.auth import HTTPBasicAuth
import pyodbc
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(threadName)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('artifact_poller.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class JFrogArtifactPoller:
    """Handles polling JFrog for artifacts with GitFlow branch support"""
    
    def __init__(self, config_file: str = "jfrog_config.json"):
        """Initialize the artifact poller with configuration"""
        self.config = self.load_config(config_file)
        self.db_connection_string = (
            "DRIVER={ODBC Driver 17 for SQL Server};"
            "SERVER=SUMEETGILL7E47\\MSSQLSERVER01;"
            "DATABASE=MSIFactory;"
            "Trusted_Connection=yes;"
        )
        self.polling_threads = {}
        self.stop_polling = threading.Event()
        self.artifact_queue = queue.Queue()
        self.download_base_path = Path("C:\\Temp")
        
    def load_config(self, config_file: str) -> dict:
        """Load JFrog configuration from file"""
        default_config = {
            "jfrog_url": "https://artifactory.example.com",
            "username": "",
            "password": "",
            "polling_interval": 60,  # seconds
            "max_threads": 10,
            "download_timeout": 300,  # seconds
            "retry_attempts": 3
        }
        
        config_path = Path(config_file)
        if config_path.exists():
            with open(config_path, 'r') as f:
                loaded_config = json.load(f)
                default_config.update(loaded_config)
        else:
            # Create default config file
            with open(config_path, 'w') as f:
                json.dump(default_config, f, indent=4)
                
        return default_config
    
    def get_components_to_monitor(self) -> List[Dict]:
        """Get all active components with their branch configurations from database"""
        components = []
        try:
            conn = pyodbc.connect(self.db_connection_string)
            cursor = conn.cursor()
            
            # Get components with branch tracking enabled
            query = """
                SELECT 
                    c.component_id,
                    c.component_name,
                    c.component_guid,
                    c.project_id,
                    c.artifact_source,
                    c.branch_name,
                    c.polling_enabled,
                    c.last_poll_time,
                    c.last_artifact_version,
                    p.project_name,
                    p.artifact_url,
                    p.artifact_username,
                    p.artifact_password
                FROM components c
                INNER JOIN projects p ON c.project_id = p.project_id
                WHERE c.polling_enabled = 1 
                AND p.is_active = 1
                AND c.branch_name IS NOT NULL
            """
            
            cursor.execute(query)
            rows = cursor.fetchall()
            
            for row in rows:
                component = {
                    'component_id': row[0],
                    'component_name': row[1],
                    'component_guid': row[2] or self.generate_guid(row[0], row[1]),
                    'project_id': row[3],
                    'artifact_source': row[4],
                    'branch_name': row[5],
                    'polling_enabled': row[6],
                    'last_poll_time': row[7],
                    'last_artifact_version': row[8],
                    'project_name': row[9],
                    'artifact_url': row[10] or self.config['jfrog_url'],
                    'username': row[11] or self.config['username'],
                    'password': row[12] or self.config['password']
                }
                components.append(component)
                
            conn.close()
            logger.info(f"Found {len(components)} components to monitor")
            
        except Exception as e:
            logger.error(f"Error getting components: {e}")
            
        return components
    
    def generate_guid(self, component_id: int, component_name: str) -> str:
        """Generate a unique GUID for a component"""
        unique_string = f"{component_id}_{component_name}_{datetime.now().isoformat()}"
        return hashlib.md5(unique_string.encode()).hexdigest()
    
    def construct_artifact_url(self, component: Dict) -> str:
        """Construct the JFrog URL for a component based on GitFlow branch"""
        base_url = component['artifact_url'].rstrip('/')
        
        # GitFlow branch patterns
        branch = component['branch_name']
        
        # Construct path based on branch type
        if branch.startswith('feature/'):
            path_pattern = f"/feature-builds/{branch.replace('/', '-')}"
        elif branch.startswith('release/'):
            path_pattern = f"/release-candidates/{branch.replace('/', '-')}"
        elif branch.startswith('hotfix/'):
            path_pattern = f"/hotfixes/{branch.replace('/', '-')}"
        elif branch == 'develop':
            path_pattern = "/snapshots/develop"
        elif branch == 'master' or branch == 'main':
            path_pattern = "/releases/stable"
        else:
            # Custom branch
            path_pattern = f"/custom-builds/{branch.replace('/', '-')}"
        
        # Add component specific path
        artifact_path = f"{path_pattern}/{component['component_name']}"
        
        return f"{base_url}{artifact_path}"
    
    def poll_component_artifacts(self, component: Dict):
        """Poll JFrog for new artifacts for a specific component"""
        thread_name = f"Poller-{component['component_name']}-{component['branch_name']}"
        logger.info(f"Starting polling for {component['component_name']} on branch {component['branch_name']}")
        
        while not self.stop_polling.is_set():
            try:
                # Construct the artifact URL
                artifact_url = self.construct_artifact_url(component)
                
                # Check for new artifacts
                new_artifacts = self.check_for_new_artifacts(
                    artifact_url,
                    component['username'],
                    component['password'],
                    component['last_artifact_version']
                )
                
                if new_artifacts:
                    for artifact in new_artifacts:
                        # Add to download queue
                        self.artifact_queue.put({
                            'component': component,
                            'artifact': artifact,
                            'timestamp': datetime.now()
                        })
                        logger.info(f"Found new artifact: {artifact['name']} for {component['component_name']}")
                
                # Update last poll time
                self.update_poll_status(component['component_id'], datetime.now())
                
            except Exception as e:
                logger.error(f"Error polling {component['component_name']}: {e}")
            
            # Wait for next polling interval
            time.sleep(self.config['polling_interval'])
    
    def check_for_new_artifacts(self, url: str, username: str, password: str, 
                                last_version: Optional[str]) -> List[Dict]:
        """Check JFrog repository for new ZIP artifacts"""
        new_artifacts = []
        
        try:
            # Make API request to JFrog
            response = requests.get(
                f"{url}/",
                auth=HTTPBasicAuth(username, password),
                timeout=30
            )
            
            if response.status_code == 200:
                # Parse response (assuming JFrog API returns JSON)
                data = response.json()
                
                # Look for ZIP files
                for item in data.get('children', []):
                    if item['uri'].endswith('.zip'):
                        artifact_info = {
                            'name': item['uri'].replace('/', ''),
                            'url': f"{url}{item['uri']}",
                            'size': item.get('size', 0),
                            'last_modified': item.get('lastModified', ''),
                            'sha256': item.get('sha256', '')
                        }
                        
                        # Check if this is newer than last known version
                        if self.is_newer_artifact(artifact_info, last_version):
                            new_artifacts.append(artifact_info)
                            
        except requests.RequestException as e:
            logger.error(f"Error checking artifacts at {url}: {e}")
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing JFrog response: {e}")
            
        return new_artifacts
    
    def is_newer_artifact(self, artifact: Dict, last_version: Optional[str]) -> bool:
        """Check if artifact is newer than the last known version"""
        if not last_version:
            return True
            
        # Compare by modification time or version number in filename
        artifact_name = artifact['name']
        
        # Extract version from filename (e.g., component-1.2.3.zip)
        import re
        version_pattern = r'(\d+\.?\d*\.?\d*)'
        
        artifact_match = re.search(version_pattern, artifact_name)
        last_match = re.search(version_pattern, last_version)
        
        if artifact_match and last_match:
            artifact_version = artifact_match.group(1)
            last_version_num = last_match.group(1)
            
            # Simple version comparison
            return artifact_version > last_version_num
            
        # Fallback to name comparison
        return artifact_name > last_version
    
    def download_artifact(self, artifact_info: Dict):
        """Download and extract artifact to specified location"""
        component = artifact_info['component']
        artifact = artifact_info['artifact']
        
        try:
            # Create directory structure: C:\Temp\Component_guid\a
            component_dir = self.download_base_path / f"Component_{component['component_guid']}"
            download_dir = component_dir / "a"
            extract_dir = component_dir / "S"
            
            # Create directories
            download_dir.mkdir(parents=True, exist_ok=True)
            extract_dir.mkdir(parents=True, exist_ok=True)
            
            # Download file
            zip_path = download_dir / artifact['name']
            
            logger.info(f"Downloading {artifact['name']} to {zip_path}")
            
            response = requests.get(
                artifact['url'],
                auth=HTTPBasicAuth(component['username'], component['password']),
                stream=True,
                timeout=self.config['download_timeout']
            )
            
            if response.status_code == 200:
                with open(zip_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                
                logger.info(f"Downloaded {artifact['name']} successfully")
                
                # Extract ZIP file
                self.extract_artifact(zip_path, extract_dir)
                
                # Update database with new artifact version
                self.update_artifact_version(
                    component['component_id'],
                    artifact['name'],
                    str(zip_path),
                    str(extract_dir)
                )
                
                # Trigger MSI build if needed
                self.trigger_msi_build(component, extract_dir)
                
            else:
                logger.error(f"Failed to download {artifact['name']}: HTTP {response.status_code}")
                
        except Exception as e:
            logger.error(f"Error downloading artifact: {e}")
    
    def extract_artifact(self, zip_path: Path, extract_dir: Path):
        """Extract ZIP artifact to specified directory"""
        try:
            # Clear existing contents in extract directory
            if extract_dir.exists():
                shutil.rmtree(extract_dir)
            extract_dir.mkdir(parents=True, exist_ok=True)
            
            # Extract ZIP
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
                
            logger.info(f"Extracted {zip_path.name} to {extract_dir}")
            
        except Exception as e:
            logger.error(f"Error extracting {zip_path}: {e}")
    
    def update_poll_status(self, component_id: int, poll_time: datetime):
        """Update the last poll time for a component"""
        try:
            conn = pyodbc.connect(self.db_connection_string)
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE components 
                SET last_poll_time = ?
                WHERE component_id = ?
            """, (poll_time, component_id))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error updating poll status: {e}")
    
    def update_artifact_version(self, component_id: int, version: str, 
                                download_path: str, extract_path: str):
        """Update component with new artifact version and paths"""
        try:
            conn = pyodbc.connect(self.db_connection_string)
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE components 
                SET last_artifact_version = ?,
                    last_download_path = ?,
                    last_extract_path = ?,
                    last_artifact_time = ?
                WHERE component_id = ?
            """, (version, download_path, extract_path, datetime.now(), component_id))
            
            # Log artifact history
            cursor.execute("""
                INSERT INTO artifact_history 
                (component_id, artifact_version, download_path, extract_path, download_time)
                VALUES (?, ?, ?, ?, ?)
            """, (component_id, version, download_path, extract_path, datetime.now()))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Updated component {component_id} with version {version}")
            
        except Exception as e:
            logger.error(f"Error updating artifact version: {e}")
    
    def trigger_msi_build(self, component: Dict, extract_path: Path):
        """Trigger MSI build for the downloaded component"""
        try:
            # Add to MSI build queue
            conn = pyodbc.connect(self.db_connection_string)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO msi_build_queue 
                (component_id, project_id, source_path, status, queued_time)
                VALUES (?, ?, ?, 'pending', ?)
            """, (component['component_id'], component['project_id'], 
                  str(extract_path), datetime.now()))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Added {component['component_name']} to MSI build queue")
            
        except Exception as e:
            logger.error(f"Error triggering MSI build: {e}")
    
    def start_polling(self):
        """Start multi-threaded polling for all components"""
        logger.info("Starting JFrog Artifact Polling System")
        
        # Get components to monitor
        components = self.get_components_to_monitor()
        
        if not components:
            logger.warning("No components found to monitor")
            return
        
        # Start download processor thread
        download_thread = threading.Thread(target=self.process_downloads, daemon=True)
        download_thread.start()
        
        # Create thread pool for polling
        with ThreadPoolExecutor(max_workers=self.config['max_threads']) as executor:
            futures = []
            
            for component in components:
                future = executor.submit(self.poll_component_artifacts, component)
                futures.append(future)
                
            # Wait for all threads or stop signal
            try:
                while not self.stop_polling.is_set():
                    time.sleep(1)
            except KeyboardInterrupt:
                logger.info("Received interrupt signal, stopping polling...")
                self.stop_polling.set()
                
            # Wait for threads to complete
            for future in as_completed(futures, timeout=10):
                try:
                    future.result()
                except Exception as e:
                    logger.error(f"Polling thread error: {e}")
    
    def process_downloads(self):
        """Process download queue in separate thread"""
        while not self.stop_polling.is_set():
            try:
                # Get artifact from queue (timeout to check stop signal)
                artifact_info = self.artifact_queue.get(timeout=1)
                self.download_artifact(artifact_info)
                
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Error processing download: {e}")
    
    def stop(self):
        """Stop all polling threads"""
        logger.info("Stopping artifact polling system")
        self.stop_polling.set()


def create_database_tables():
    """Create required database tables for artifact polling"""
    try:
        conn_str = (
            "DRIVER={ODBC Driver 17 for SQL Server};"
            "SERVER=SUMEETGILL7E47\\MSSQLSERVER01;"
            "DATABASE=MSIFactory;"
            "Trusted_Connection=yes;"
        )
        
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        
        # Add columns to components table if they don't exist
        cursor.execute("""
            IF NOT EXISTS (SELECT * FROM sys.columns 
                          WHERE object_id = OBJECT_ID('components') 
                          AND name = 'branch_name')
            BEGIN
                ALTER TABLE components ADD 
                    branch_name VARCHAR(100),
                    component_guid VARCHAR(50),
                    polling_enabled BIT DEFAULT 1,
                    last_poll_time DATETIME,
                    last_artifact_version VARCHAR(100),
                    last_download_path VARCHAR(500),
                    last_extract_path VARCHAR(500),
                    last_artifact_time DATETIME
            END
        """)
        
        # Create artifact history table
        cursor.execute("""
            IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'artifact_history')
            BEGIN
                CREATE TABLE artifact_history (
                    history_id INT IDENTITY(1,1) PRIMARY KEY,
                    component_id INT,
                    artifact_version VARCHAR(100),
                    download_path VARCHAR(500),
                    extract_path VARCHAR(500),
                    download_time DATETIME,
                    FOREIGN KEY (component_id) REFERENCES components(component_id)
                )
            END
        """)
        
        # Create MSI build queue table
        cursor.execute("""
            IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'msi_build_queue')
            BEGIN
                CREATE TABLE msi_build_queue (
                    queue_id INT IDENTITY(1,1) PRIMARY KEY,
                    component_id INT,
                    project_id INT,
                    source_path VARCHAR(500),
                    status VARCHAR(50),
                    queued_time DATETIME,
                    start_time DATETIME,
                    end_time DATETIME,
                    error_message TEXT,
                    FOREIGN KEY (component_id) REFERENCES components(component_id),
                    FOREIGN KEY (project_id) REFERENCES projects(project_id)
                )
            END
        """)
        
        conn.commit()
        conn.close()
        
        logger.info("Database tables created/verified successfully")
        
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")


if __name__ == "__main__":
    # Create required tables
    create_database_tables()
    
    # Initialize and start poller
    poller = JFrogArtifactPoller()
    
    try:
        poller.start_polling()
    except KeyboardInterrupt:
        poller.stop()
        print("\nArtifact polling stopped.")