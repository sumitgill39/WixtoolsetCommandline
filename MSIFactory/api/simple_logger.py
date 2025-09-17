"""
Simple Action Logger
Basic logging for API operations - using existing logs directory
"""

import logging
import os
import json
from datetime import datetime
from typing import Dict, Any, Optional

class SimpleLogger:
    """Simple logger for API actions"""
    
    def __init__(self):
        """Initialize simple logger using existing logs directory"""
        # Use existing logs directory
        self.log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
        
        # Ensure logs directory exists (should already exist)
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)
            
        # Setup simple file logger
        self.logger = logging.getLogger('msi_factory_actions')
        self.logger.setLevel(logging.INFO)
        
        # Clear existing handlers
        self.logger.handlers.clear()
        
        # Create file handler for actions
        log_file = os.path.join(self.log_dir, 'api_actions.log')
        handler = logging.FileHandler(log_file, encoding='utf-8')
        
        # Simple format
        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        
        self.logger.info("Simple Logger initialized")
    
    def log_action(self, action: str, entity_type: str, entity_id: str = None, 
                   user: str = 'system', success: bool = True, error: str = None):
        """Log an action - simple version"""
        
        log_data = {
            'action': action,
            'entity_type': entity_type,
            'entity_id': entity_id,
            'user': user,
            'success': success,
            'timestamp': datetime.now().isoformat()
        }
        
        if error:
            log_data['error'] = error
            
        # Create simple log message
        message = f"{action} {entity_type}"
        if entity_id:
            message += f" (ID: {entity_id})"
        message += f" - {'SUCCESS' if success else 'FAILED'}"
        if error:
            message += f" - {error}"
            
        # Log based on success
        if success:
            self.logger.info(message)
        else:
            self.logger.error(message)
    
    def log_request(self, method: str, endpoint: str, status_code: int, user: str = 'anonymous'):
        """Log API request - simple version"""
        message = f"API {method} {endpoint} - {status_code} - User: {user}"
        self.logger.info(message)

# Global instance
_simple_logger = None

def get_simple_logger():
    """Get or create simple logger instance"""
    global _simple_logger
    if _simple_logger is None:
        _simple_logger = SimpleLogger()
    return _simple_logger