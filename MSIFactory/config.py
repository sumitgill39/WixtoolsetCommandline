#!/usr/bin/env python3
"""
Simple MSI Factory Configuration
"""

import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()

class Config:
    """Simple configuration for MSI Factory"""
    
    # Database Settings
    DB_SERVER = os.getenv('DB_SERVER', 'localhost')
    DB_NAME = os.getenv('DB_NAME', 'MSIFactory')
    DB_USERNAME = os.getenv('DB_USERNAME', '')
    DB_PASSWORD = os.getenv('DB_PASSWORD', '')
    DB_DRIVER = os.getenv('DB_DRIVER', 'ODBC Driver 17 for SQL Server')
    DB_TRUST_CONNECTION = os.getenv('DB_TRUST_CONNECTION', 'yes')
    DB_PORT = int(os.getenv('DB_PORT', '1433'))
    
    # Basic App Settings
    APP_NAME = os.getenv('APP_NAME', 'MSI Factory')
    SECRET_KEY = os.getenv('SECRET_KEY', 'change_me_in_production')
    FLASK_DEBUG = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'
    
    # Simple logging setting
    SQLALCHEMY_ECHO = os.getenv('SQLALCHEMY_ECHO', 'False').lower() == 'true'
    
    @property
    def database_url(self):
        """Build database connection string"""
        driver_str = self.DB_DRIVER.replace(' ', '+')
        
        if self.DB_USERNAME and self.DB_PASSWORD:
            # SQL Server Authentication
            if '\\' in self.DB_SERVER:
                return f"mssql+pyodbc://{self.DB_USERNAME}:{self.DB_PASSWORD}@{self.DB_SERVER}/{self.DB_NAME}?driver={driver_str}"
            else:
                return f"mssql+pyodbc://{self.DB_USERNAME}:{self.DB_PASSWORD}@{self.DB_SERVER}:{self.DB_PORT}/{self.DB_NAME}?driver={driver_str}"
        else:
            # Windows Authentication
            if '\\' in self.DB_SERVER:
                return f"mssql+pyodbc://{self.DB_SERVER}/{self.DB_NAME}?driver={driver_str}&trusted_connection={self.DB_TRUST_CONNECTION}"
            else:
                return f"mssql+pyodbc://{self.DB_SERVER}:{self.DB_PORT}/{self.DB_NAME}?driver={driver_str}&trusted_connection={self.DB_TRUST_CONNECTION}"

def get_config():
    """Get configuration class"""
    return Config

if __name__ == '__main__':
    config = Config()
    print(f"App Name: {config.APP_NAME}")
    print(f"Database Server: {config.DB_SERVER}")
    print(f"Database Name: {config.DB_NAME}")
    print("Configuration loaded successfully")