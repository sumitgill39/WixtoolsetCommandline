# Configuration settings for the WINCORE application

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Database Configuration
DB_CONFIG = {
    'driver': os.getenv('DB_DRIVER', '{ODBC Driver 17 for SQL Server}'),
    'server': os.getenv('DB_SERVER', 'localhost'),
    'database': os.getenv('DB_NAME', 'MSIFactory'),
    'trusted_connection': os.getenv('DB_TRUST_CONNECTION', 'yes'),
    'uid': os.getenv('DB_USERNAME', ''),
    'pwd': os.getenv('DB_PASSWORD', ''),
    'timeout': int(os.getenv('DB_CONNECTION_TIMEOUT', '30')),
    'port': int(os.getenv('DB_PORT', '1433'))
}

# File System Configuration
BASE_DRIVE = os.getenv('BASE_DRIVE', 'C:/WINCORE')

# Logging Configuration
LOG_CONFIG = {
    'level': os.getenv('LOG_LEVEL', 'INFO'),
    'format': os.getenv('LOG_FORMAT', '%(asctime)s - %(name)s - %(levelname)s - %(message)s'),
    'filename': os.getenv('LOG_FILE', 'wincore.log'),
    'maxBytes': int(os.getenv('LOG_FILE_MAX_SIZE', '10485760')),
    'backupCount': int(os.getenv('LOG_FILE_BACKUP_COUNT', '5'))
}

# SSP API Configuration
SSP_CONFIG = {
    'api_url': os.getenv('SSP_API_URL', ''),
    'token': os.getenv('SSP_API_TOKEN', ''),
    'env': os.getenv('SSP_ENV', 'PROD'),
    'app_name': os.getenv('SSP_APP_NAME', 'WINCORE'),
    'timeout': int(os.getenv('SSP_TIMEOUT', '30'))
}

# JFrog Configuration
JFROG_CONFIG = {
    'base_url': os.getenv('JFROG_BASE_URL', ''),
    'username': None,  # Will be fetched from SSP API
    'password': None,  # Will be fetched from SSP API
    'timeout': int(os.getenv('JFROG_TIMEOUT', '300')),
    'max_retries': int(os.getenv('JFROG_MAX_RETRIES', '3')),
    'verify_ssl': True
}

# Thread Configuration
THREAD_CONFIG = {
    'max_threads': int(os.getenv('MAX_CONCURRENT_THREADS', '100')),
    'default_polling_frequency': int(os.getenv('DEFAULT_POLLING_FREQUENCY', '300')),
    'thread_timeout': int(os.getenv('THREAD_TIMEOUT', '3600'))
}