#!/usr/bin/env python3
"""
Simple MSI Factory Logger
Basic logging for system activities
"""

import os
import json
from datetime import datetime
from pathlib import Path

class MSIFactoryLogger:
    def __init__(self, log_dir="logs"):
        """Setup simple logging"""
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        # Single log files for simplicity
        self.system_log = self.log_dir / "system.log"
        self.access_log = self.log_dir / "access.log"
        self.error_log = self.log_dir / "error.log"
    
    def write_log(self, filename, message):
        """Write a log entry to file"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"{timestamp} | {message}\n"
        
        try:
            with open(filename, 'a') as f:
                f.write(log_entry)
        except Exception as e:
            print(f"Error writing log: {e}")
    
    def log_system_event(self, event_type, message):
        """Log system events"""
        log_message = f"SYSTEM | {event_type} | {message}"
        self.write_log(self.system_log, log_message)
    
    def log_user_login(self, username, success=True, ip_address=None):
        """Log user login attempts"""
        status = "SUCCESS" if success else "FAILED"
        ip = ip_address or "unknown"
        log_message = f"LOGIN | {status} | User: {username} | IP: {ip}"
        self.write_log(self.access_log, log_message)
    
    def log_user_logout(self, username):
        """Log user logout"""
        log_message = f"LOGOUT | User: {username}"
        self.write_log(self.access_log, log_message)
    
    def log_error(self, error_type, message):
        """Log errors"""
        log_message = f"ERROR | {error_type} | {message}"
        self.write_log(self.error_log, log_message)
    
    def log_msi_generation(self, app_name, environment, status):
        """Log MSI generation activities"""
        log_message = f"MSI | {app_name} | {environment} | {status}"
        self.write_log(self.system_log, log_message)
    
    def log_security_violation(self, violation_type, username, details):
        """Log security violations"""
        log_message = f"SECURITY | {violation_type} | User: {username} | {details}"
        self.write_log(self.access_log, log_message)
    
    def log_system_start(self):
        """Log system startup"""
        self.log_system_event("STARTUP", "MSI Factory system started")
    
    def log_system_stop(self):
        """Log system shutdown"""
        self.log_system_event("SHUTDOWN", "MSI Factory system stopped")

# Simple helper functions for easy use
def get_logger():
    """Get logger instance"""
    return MSIFactoryLogger()

def log_info(message):
    """Simple info logging"""
    logger = MSIFactoryLogger()
    logger.log_system_event("INFO", message)

def log_error(message):
    """Simple error logging"""
    logger = MSIFactoryLogger()
    logger.log_error("ERROR", message)

def log_security(message):
    """Simple security logging"""
    logger = MSIFactoryLogger()
    logger.log_system_event("SECURITY", message)

if __name__ == "__main__":
    # Test the logger
    logger = MSIFactoryLogger()
    
    print("Testing MSI Factory Logger...")
    logger.log_system_start()
    logger.log_user_login("admin", success=True, ip_address="127.0.0.1")
    logger.log_msi_generation("WEBAPP01", "PROD", "SUCCESS")
    logger.log_error("CONFIG", "Configuration file missing")
    logger.log_system_stop()
    
    print("Log files created in 'logs' directory")
    print("Check: system.log, access.log, error.log")