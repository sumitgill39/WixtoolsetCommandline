"""
Action Logger Module
Comprehensive logging system for MSI Factory API operations
"""

import logging
import os
import json
from datetime import datetime
from typing import Dict, Any, Optional
from functools import wraps
import traceback

class ActionLogger:
    """Centralized action logging system for API operations"""
    
    def __init__(self, log_dir: str = "logs"):
        """
        Initialize ActionLogger
        
        Args:
            log_dir: Directory to store log files
        """
        self.log_dir = log_dir
        self.ensure_log_directory()
        self.setup_loggers()
    
    def ensure_log_directory(self):
        """Create log directory if it doesn't exist"""
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)
    
    def setup_loggers(self):
        """Setup different loggers for different types of actions"""
        
        # Main action logger
        self.action_logger = logging.getLogger('msi_factory.actions')
        self.action_logger.setLevel(logging.INFO)
        
        # API request logger
        self.request_logger = logging.getLogger('msi_factory.requests')
        self.request_logger.setLevel(logging.INFO)
        
        # Error logger
        self.error_logger = logging.getLogger('msi_factory.errors')
        self.error_logger.setLevel(logging.ERROR)
        
        # Security/audit logger
        self.audit_logger = logging.getLogger('msi_factory.audit')
        self.audit_logger.setLevel(logging.INFO)
        
        # Clear existing handlers to avoid duplicates
        for logger in [self.action_logger, self.request_logger, self.error_logger, self.audit_logger]:
            logger.handlers.clear()
        
        # Create formatters
        detailed_formatter = logging.Formatter(
            '%(asctime)s | %(levelname)s | %(name)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        json_formatter = JsonFormatter()
        
        # Setup file handlers
        self._setup_file_handler(self.action_logger, 'actions.log', detailed_formatter)
        self._setup_file_handler(self.request_logger, 'requests.log', json_formatter)
        self._setup_file_handler(self.error_logger, 'errors.log', detailed_formatter)
        self._setup_file_handler(self.audit_logger, 'audit.log', json_formatter)
        
        # Setup console handler for development
        if os.environ.get('API_DEBUG', 'False').lower() == 'true':
            self._setup_console_handler(self.action_logger, detailed_formatter)
    
    def _setup_file_handler(self, logger, filename: str, formatter):
        """Setup file handler for a logger"""
        handler = logging.FileHandler(os.path.join(self.log_dir, filename), encoding='utf-8')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    
    def _setup_console_handler(self, logger, formatter):
        """Setup console handler for a logger"""
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    
    def log_action(self, action: str, entity_type: str, entity_id: Optional[str] = None, 
                   user: Optional[str] = None, details: Optional[Dict] = None, 
                   success: bool = True, error: Optional[str] = None):
        """
        Log an action performed in the system
        
        Args:
            action: Action performed (CREATE, UPDATE, DELETE, READ)
            entity_type: Type of entity (project, component, environment)
            entity_id: ID of the entity (if applicable)
            user: User performing the action
            details: Additional details about the action
            success: Whether the action was successful
            error: Error message if action failed
        """
        log_data = {
            'timestamp': datetime.now().isoformat(),
            'action': action,
            'entity_type': entity_type,
            'entity_id': entity_id,
            'user': user or 'api_user',
            'success': success,
            'details': details or {},
        }
        
        if error:
            log_data['error'] = error
        
        # Log to action logger
        level = logging.INFO if success else logging.WARNING
        message = f"{action} {entity_type}"
        if entity_id:
            message += f" (ID: {entity_id})"
        message += f" - {'SUCCESS' if success else 'FAILED'}"
        if error:
            message += f" - {error}"
        
        self.action_logger.log(level, message)
        
        # Log to audit logger with full details
        self.audit_logger.info(json.dumps(log_data))
    
    def log_request(self, method: str, endpoint: str, status_code: int, 
                   user: Optional[str] = None, ip_address: Optional[str] = None,
                   request_data: Optional[Dict] = None, response_time: Optional[float] = None):
        """
        Log API request
        
        Args:
            method: HTTP method
            endpoint: API endpoint
            status_code: Response status code
            user: User making the request
            ip_address: Client IP address
            request_data: Request payload (sanitized)
            response_time: Request processing time in seconds
        """
        log_data = {
            'timestamp': datetime.now().isoformat(),
            'method': method,
            'endpoint': endpoint,
            'status_code': status_code,
            'user': user or 'anonymous',
            'ip_address': ip_address,
            'request_data': self._sanitize_request_data(request_data),
            'response_time': response_time
        }
        
        self.request_logger.info(json.dumps(log_data))
    
    def log_error(self, error: Exception, context: Optional[Dict] = None, 
                  user: Optional[str] = None):
        """
        Log error with context
        
        Args:
            error: Exception that occurred
            context: Additional context about the error
            user: User associated with the error
        """
        error_data = {
            'timestamp': datetime.now().isoformat(),
            'error_type': type(error).__name__,
            'error_message': str(error),
            'user': user or 'unknown',
            'context': context or {},
            'traceback': traceback.format_exc()
        }
        
        self.error_logger.error(json.dumps(error_data))
    
    def _sanitize_request_data(self, data: Optional[Dict]) -> Optional[Dict]:
        """
        Sanitize request data to remove sensitive information
        
        Args:
            data: Request data to sanitize
            
        Returns:
            Sanitized data
        """
        if not data:
            return None
        
        # List of fields to redact
        sensitive_fields = [
            'password', 'secret', 'token', 'key', 'auth',
            'credential', 'private', 'confidential'
        ]
        
        sanitized = {}
        for key, value in data.items():
            if any(field in key.lower() for field in sensitive_fields):
                sanitized[key] = '***REDACTED***'
            elif isinstance(value, dict):
                sanitized[key] = self._sanitize_request_data(value)
            else:
                sanitized[key] = value
        
        return sanitized


class JsonFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging"""
    
    def format(self, record):
        """Format log record as JSON"""
        # For records that are already JSON strings, return as-is
        if hasattr(record, 'getMessage'):
            message = record.getMessage()
            try:
                # Try to parse as JSON to validate
                json.loads(message)
                return message
            except json.JSONDecodeError:
                # If not JSON, wrap in JSON structure
                return json.dumps({
                    'timestamp': datetime.fromtimestamp(record.created).isoformat(),
                    'level': record.levelname,
                    'logger': record.name,
                    'message': message
                })
        return json.dumps({'message': str(record)})


def log_action_decorator(action: str, entity_type: str):
    """
    Decorator to automatically log actions
    
    Args:
        action: Action being performed
        entity_type: Type of entity being acted upon
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Get logger instance
            logger = get_action_logger()
            
            # Extract entity_id from arguments if possible
            entity_id = None
            if len(args) > 1:
                # Assume second argument is entity_id for most methods
                entity_id = str(args[1]) if args[1] is not None else None
            
            try:
                # Execute the function
                result = func(*args, **kwargs)
                
                # Determine success based on result format
                success = True
                error = None
                if isinstance(result, tuple) and len(result) >= 1:
                    success = result[0] if isinstance(result[0], bool) else True
                    if len(result) >= 2 and not success:
                        error = result[1]
                
                # Log the action
                logger.log_action(
                    action=action,
                    entity_type=entity_type,
                    entity_id=entity_id,
                    success=success,
                    error=error
                )
                
                return result
                
            except Exception as e:
                # Log the error
                logger.log_action(
                    action=action,
                    entity_type=entity_type,
                    entity_id=entity_id,
                    success=False,
                    error=str(e)
                )
                logger.log_error(e, context={
                    'function': func.__name__,
                    'args': str(args)[:200],  # Limit arg length
                    'kwargs': str(kwargs)[:200]
                })
                raise
        
        return wrapper
    return decorator


# Global logger instance
_action_logger = None

def get_action_logger() -> ActionLogger:
    """Get or create global action logger instance"""
    global _action_logger
    if _action_logger is None:
        log_dir = os.environ.get('MSI_FACTORY_LOG_DIR', 'logs')
        _action_logger = ActionLogger(log_dir)
    return _action_logger


def setup_api_logging():
    """Setup logging for the API system"""
    # Initialize the logger
    logger = get_action_logger()
    
    # Log system startup
    logger.log_action(
        action='SYSTEM_START',
        entity_type='api_server',
        details={'version': '1.0.0', 'startup_time': datetime.now().isoformat()}
    )
    
    return logger


# Convenience functions for common logging operations
def log_project_action(action: str, project_id: Optional[str] = None, 
                      user: Optional[str] = None, success: bool = True, 
                      error: Optional[str] = None, details: Optional[Dict] = None):
    """Log project-related action"""
    logger = get_action_logger()
    logger.log_action(action, 'project', project_id, user, details, success, error)


def log_component_action(action: str, component_id: Optional[str] = None, 
                        user: Optional[str] = None, success: bool = True, 
                        error: Optional[str] = None, details: Optional[Dict] = None):
    """Log component-related action"""
    logger = get_action_logger()
    logger.log_action(action, 'component', component_id, user, details, success, error)


def log_api_request(method: str, endpoint: str, status_code: int, 
                   user: Optional[str] = None, ip_address: Optional[str] = None,
                   request_data: Optional[Dict] = None, response_time: Optional[float] = None):
    """Log API request"""
    logger = get_action_logger()
    logger.log_request(method, endpoint, status_code, user, ip_address, request_data, response_time)