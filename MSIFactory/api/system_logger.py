"""
System Logger Module
Dual logging system that writes to both database and file system (.git/logs/)
Complete audit trail for all MSI Factory operations
"""

import logging
import os
import json
import sys
from datetime import datetime
from typing import Dict, Any, Optional, List
from functools import wraps
import traceback
import threading
import queue
import time
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class DualSystemLogger:
    """
    Comprehensive dual logging system that writes to:
    1. Database (SQL Server)
    2. File system (.git/logs/ directory)
    """
    
    def __init__(self, project_root: str = None):
        """
        Initialize DualSystemLogger
        
        Args:
            project_root: Root directory of the project (to find .git folder)
        """
        self.project_root = project_root or self._find_project_root()
        self.git_logs_dir = os.path.join(self.project_root, '.git', 'logs', 'msi_factory')
        self.ensure_directories()
        self.setup_loggers()
        self.setup_database_connection()
        
        # Queue for asynchronous database logging
        self.db_queue = queue.Queue()
        self.db_worker = threading.Thread(target=self._db_worker_thread, daemon=True)
        self.db_worker.start()
    
    def _find_project_root(self) -> str:
        """Find project root by looking for .git directory"""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        while current_dir != os.path.dirname(current_dir):
            if os.path.exists(os.path.join(current_dir, '.git')):
                return current_dir
            current_dir = os.path.dirname(current_dir)
        # Fallback to current directory
        return os.path.dirname(os.path.abspath(__file__))
    
    def ensure_directories(self):
        """Create necessary directories if they don't exist"""
        # Create .git/logs/msi_factory directory structure
        os.makedirs(self.git_logs_dir, exist_ok=True)
        
        # Create subdirectories for different log types
        subdirs = ['actions', 'requests', 'errors', 'audit', 'system', 'daily']
        for subdir in subdirs:
            os.makedirs(os.path.join(self.git_logs_dir, subdir), exist_ok=True)
    
    def setup_loggers(self):
        """Setup file-based loggers"""
        self.loggers = {}
        
        # Define logger configurations
        logger_configs = {
            'action': {
                'name': 'msi_factory.system.action',
                'file': 'actions/action.log',
                'level': logging.INFO
            },
            'request': {
                'name': 'msi_factory.system.request',
                'file': 'requests/request.log',
                'level': logging.INFO
            },
            'error': {
                'name': 'msi_factory.system.error',
                'file': 'errors/error.log',
                'level': logging.ERROR
            },
            'audit': {
                'name': 'msi_factory.system.audit',
                'file': 'audit/audit.log',
                'level': logging.INFO
            },
            'system': {
                'name': 'msi_factory.system.events',
                'file': 'system/system.log',
                'level': logging.INFO
            }
        }
        
        # Create formatters
        detailed_formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S.%f'
        )
        
        # Setup each logger
        for key, config in logger_configs.items():
            logger = logging.getLogger(config['name'])
            logger.setLevel(config['level'])
            logger.handlers.clear()
            
            # File handler for main log
            file_path = os.path.join(self.git_logs_dir, config['file'])
            file_handler = logging.FileHandler(file_path, encoding='utf-8')
            file_handler.setFormatter(detailed_formatter)
            logger.addHandler(file_handler)
            
            # Daily rotating file handler
            daily_file = os.path.join(
                self.git_logs_dir, 
                'daily', 
                f"{key}_{datetime.now().strftime('%Y%m%d')}.log"
            )
            daily_handler = logging.FileHandler(daily_file, encoding='utf-8')
            daily_handler.setFormatter(detailed_formatter)
            logger.addHandler(daily_handler)
            
            self.loggers[key] = logger
    
    def setup_database_connection(self):
        """Setup database connection for logging"""
        try:
            from database.db_manager_sqlserver import SQLServerDatabaseManager
            self.db = SQLServerDatabaseManager()
            self.db_available = True
        except Exception as e:
            print(f"Database logging not available: {e}")
            self.db = None
            self.db_available = False
    
    def _db_worker_thread(self):
        """Worker thread for asynchronous database logging"""
        while True:
            try:
                log_entry = self.db_queue.get(timeout=1)
                if log_entry is None:
                    break
                self._write_to_database(log_entry)
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Database logging error: {e}")
    
    def _write_to_database(self, log_entry: Dict):
        """Write log entry to database"""
        if not self.db_available or not self.db:
            return
        
        try:
            log_type = log_entry.get('log_type')
            
            if log_type == 'action':
                self._write_action_to_db(log_entry)
            elif log_type == 'request':
                self._write_request_to_db(log_entry)
            elif log_type == 'error':
                self._write_error_to_db(log_entry)
            elif log_type == 'audit':
                self._write_audit_to_db(log_entry)
            elif log_type == 'system':
                self._write_system_event_to_db(log_entry)
        except Exception as e:
            # Log to file if database write fails
            self.loggers['error'].error(f"Database write failed: {e}")
    
    def _write_action_to_db(self, entry: Dict):
        """Write action log to database"""
        query = """
        INSERT INTO ActionLogs (
            timestamp, action_type, entity_type, entity_id, entity_name,
            user_id, user_name, ip_address, session_id, success,
            error_message, details, duration_ms, affected_rows,
            old_values, new_values
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            entry.get('timestamp'),
            entry.get('action_type'),
            entry.get('entity_type'),
            entry.get('entity_id'),
            entry.get('entity_name'),
            entry.get('user_id'),
            entry.get('user_name'),
            entry.get('ip_address'),
            entry.get('session_id'),
            entry.get('success', True),
            entry.get('error_message'),
            json.dumps(entry.get('details', {})),
            entry.get('duration_ms'),
            entry.get('affected_rows'),
            json.dumps(entry.get('old_values', {})) if entry.get('old_values') else None,
            json.dumps(entry.get('new_values', {})) if entry.get('new_values') else None
        )
        self.db.execute_non_query(query, params)
    
    def _write_request_to_db(self, entry: Dict):
        """Write request log to database"""
        query = """
        INSERT INTO RequestLogs (
            timestamp, method, endpoint, full_url, status_code,
            user_id, user_agent, ip_address, referrer, session_id,
            request_headers, request_body, response_body,
            response_time_ms, bytes_sent, bytes_received
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            entry.get('timestamp'),
            entry.get('method'),
            entry.get('endpoint'),
            entry.get('full_url'),
            entry.get('status_code'),
            entry.get('user_id'),
            entry.get('user_agent'),
            entry.get('ip_address'),
            entry.get('referrer'),
            entry.get('session_id'),
            json.dumps(entry.get('request_headers', {})),
            json.dumps(entry.get('request_body', {})),
            json.dumps(entry.get('response_body', {}))[:4000],  # Truncate if needed
            entry.get('response_time_ms'),
            entry.get('bytes_sent'),
            entry.get('bytes_received')
        )
        self.db.execute_non_query(query, params)
    
    def _write_error_to_db(self, entry: Dict):
        """Write error log to database"""
        query = """
        INSERT INTO ErrorLogs (
            timestamp, error_level, error_type, error_message, error_code,
            stack_trace, user_id, session_id, request_id, action_id,
            module_name, function_name, line_number, context_data
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            entry.get('timestamp'),
            entry.get('error_level'),
            entry.get('error_type'),
            entry.get('error_message'),
            entry.get('error_code'),
            entry.get('stack_trace'),
            entry.get('user_id'),
            entry.get('session_id'),
            entry.get('request_id'),
            entry.get('action_id'),
            entry.get('module_name'),
            entry.get('function_name'),
            entry.get('line_number'),
            json.dumps(entry.get('context_data', {}))
        )
        self.db.execute_non_query(query, params)
    
    def _write_audit_to_db(self, entry: Dict):
        """Write audit log to database"""
        query = """
        INSERT INTO AuditLogs (
            timestamp, event_type, event_category, severity,
            user_id, user_name, user_role, ip_address, machine_name,
            resource_type, resource_id, resource_name,
            action_performed, action_result, reason,
            compliance_flags, data_classification, additional_metadata
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            entry.get('timestamp'),
            entry.get('event_type'),
            entry.get('event_category'),
            entry.get('severity'),
            entry.get('user_id'),
            entry.get('user_name'),
            entry.get('user_role'),
            entry.get('ip_address'),
            entry.get('machine_name'),
            entry.get('resource_type'),
            entry.get('resource_id'),
            entry.get('resource_name'),
            entry.get('action_performed'),
            entry.get('action_result'),
            entry.get('reason'),
            entry.get('compliance_flags'),
            entry.get('data_classification'),
            json.dumps(entry.get('additional_metadata', {}))
        )
        self.db.execute_non_query(query, params)
    
    def _write_system_event_to_db(self, entry: Dict):
        """Write system event to database"""
        query = """
        INSERT INTO SystemEvents (
            timestamp, event_name, event_source, event_level,
            host_name, process_id, thread_id,
            memory_usage_mb, cpu_usage_percent, disk_usage_mb,
            network_bytes_sent, network_bytes_received,
            message, details
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            entry.get('timestamp'),
            entry.get('event_name'),
            entry.get('event_source'),
            entry.get('event_level'),
            entry.get('host_name'),
            entry.get('process_id'),
            entry.get('thread_id'),
            entry.get('memory_usage_mb'),
            entry.get('cpu_usage_percent'),
            entry.get('disk_usage_mb'),
            entry.get('network_bytes_sent'),
            entry.get('network_bytes_received'),
            entry.get('message'),
            json.dumps(entry.get('details', {}))
        )
        self.db.execute_non_query(query, params)
    
    # Public logging methods
    
    def log_action(self, action_type: str, entity_type: str, entity_id: str = None,
                   entity_name: str = None, user_id: str = None, user_name: str = None,
                   success: bool = True, error_message: str = None, details: Dict = None,
                   duration_ms: int = None, old_values: Dict = None, new_values: Dict = None,
                   ip_address: str = None, session_id: str = None):
        """Log an action to both file and database"""
        
        timestamp = datetime.now()
        log_entry = {
            'log_type': 'action',
            'timestamp': timestamp,
            'action_type': action_type,
            'entity_type': entity_type,
            'entity_id': entity_id,
            'entity_name': entity_name,
            'user_id': user_id,
            'user_name': user_name,
            'ip_address': ip_address,
            'session_id': session_id,
            'success': success,
            'error_message': error_message,
            'details': details,
            'duration_ms': duration_ms,
            'old_values': old_values,
            'new_values': new_values
        }
        
        # Log to file
        log_message = f"ACTION: {action_type} on {entity_type}"
        if entity_id:
            log_message += f" [{entity_id}]"
        if entity_name:
            log_message += f" ({entity_name})"
        log_message += f" by {user_name or user_id or 'unknown'}"
        log_message += f" - {'SUCCESS' if success else 'FAILED'}"
        if error_message:
            log_message += f" - {error_message}"
        if duration_ms:
            log_message += f" - {duration_ms}ms"
        
        self.loggers['action'].info(log_message)
        
        # Also write detailed JSON to file
        json_file = os.path.join(
            self.git_logs_dir, 
            'actions', 
            f"action_{timestamp.strftime('%Y%m%d_%H%M%S')}_{action_type}_{entity_type}.json"
        )
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(log_entry, f, indent=2, default=str)
        
        # Queue for database write
        if self.db_available:
            self.db_queue.put(log_entry)
    
    def log_request(self, method: str, endpoint: str, status_code: int,
                   user_id: str = None, ip_address: str = None,
                   user_agent: str = None, request_body: Dict = None,
                   response_body: Dict = None, response_time_ms: int = None,
                   session_id: str = None):
        """Log API request to both file and database"""
        
        timestamp = datetime.now()
        log_entry = {
            'log_type': 'request',
            'timestamp': timestamp,
            'method': method,
            'endpoint': endpoint,
            'status_code': status_code,
            'user_id': user_id,
            'ip_address': ip_address,
            'user_agent': user_agent,
            'session_id': session_id,
            'request_body': self._sanitize_data(request_body),
            'response_body': response_body,
            'response_time_ms': response_time_ms
        }
        
        # Log to file
        log_message = f"REQUEST: {method} {endpoint} - {status_code}"
        if user_id:
            log_message += f" - User: {user_id}"
        if response_time_ms:
            log_message += f" - {response_time_ms}ms"
        
        self.loggers['request'].info(log_message)
        
        # Queue for database write
        if self.db_available:
            self.db_queue.put(log_entry)
    
    def log_error(self, error: Exception, error_level: str = 'ERROR',
                 user_id: str = None, context_data: Dict = None,
                 module_name: str = None, function_name: str = None):
        """Log error to both file and database"""
        
        timestamp = datetime.now()
        tb = traceback.extract_tb(error.__traceback__)
        last_trace = tb[-1] if tb else None
        
        log_entry = {
            'log_type': 'error',
            'timestamp': timestamp,
            'error_level': error_level,
            'error_type': type(error).__name__,
            'error_message': str(error),
            'stack_trace': traceback.format_exc(),
            'user_id': user_id,
            'module_name': module_name or (last_trace.filename if last_trace else None),
            'function_name': function_name or (last_trace.name if last_trace else None),
            'line_number': last_trace.lineno if last_trace else None,
            'context_data': context_data
        }
        
        # Log to file
        self.loggers['error'].error(
            f"{error_level}: {type(error).__name__}: {str(error)}\n"
            f"Module: {log_entry['module_name']}, Function: {log_entry['function_name']}, "
            f"Line: {log_entry['line_number']}\n"
            f"{traceback.format_exc()}"
        )
        
        # Queue for database write
        if self.db_available:
            self.db_queue.put(log_entry)
    
    def log_audit(self, event_type: str, event_category: str, severity: str,
                 resource_type: str = None, resource_id: str = None,
                 action_performed: str = None, action_result: str = None,
                 user_id: str = None, user_name: str = None, user_role: str = None,
                 compliance_flags: str = None, reason: str = None):
        """Log audit event to both file and database"""
        
        timestamp = datetime.now()
        log_entry = {
            'log_type': 'audit',
            'timestamp': timestamp,
            'event_type': event_type,
            'event_category': event_category,
            'severity': severity,
            'resource_type': resource_type,
            'resource_id': resource_id,
            'action_performed': action_performed,
            'action_result': action_result,
            'user_id': user_id,
            'user_name': user_name,
            'user_role': user_role,
            'compliance_flags': compliance_flags,
            'reason': reason,
            'machine_name': os.environ.get('COMPUTERNAME', 'unknown'),
            'ip_address': self._get_local_ip()
        }
        
        # Log to file
        log_message = (
            f"AUDIT: {event_type} - {event_category} - {severity} | "
            f"User: {user_name or user_id or 'unknown'} | "
            f"Action: {action_performed} | Result: {action_result}"
        )
        self.loggers['audit'].info(log_message)
        
        # Queue for database write
        if self.db_available:
            self.db_queue.put(log_entry)
    
    def log_system_event(self, event_name: str, event_source: str,
                        event_level: str = 'INFO', message: str = None,
                        details: Dict = None):
        """Log system event to both file and database"""
        
        timestamp = datetime.now()
        log_entry = {
            'log_type': 'system',
            'timestamp': timestamp,
            'event_name': event_name,
            'event_source': event_source,
            'event_level': event_level,
            'host_name': os.environ.get('COMPUTERNAME', 'unknown'),
            'process_id': os.getpid(),
            'thread_id': threading.get_ident(),
            'message': message,
            'details': details
        }
        
        # Log to file
        log_message = f"SYSTEM: {event_name} from {event_source} - {event_level}"
        if message:
            log_message += f" - {message}"
        
        self.loggers['system'].info(log_message)
        
        # Queue for database write
        if self.db_available:
            self.db_queue.put(log_entry)
    
    def _sanitize_data(self, data: Any) -> Any:
        """Sanitize sensitive data before logging"""
        if not data:
            return data
        
        sensitive_keywords = [
            'password', 'secret', 'token', 'key', 'auth',
            'credential', 'private', 'api_key', 'access_token'
        ]
        
        if isinstance(data, dict):
            sanitized = {}
            for key, value in data.items():
                if any(keyword in key.lower() for keyword in sensitive_keywords):
                    sanitized[key] = '***REDACTED***'
                elif isinstance(value, dict):
                    sanitized[key] = self._sanitize_data(value)
                else:
                    sanitized[key] = value
            return sanitized
        return data
    
    def _get_local_ip(self) -> str:
        """Get local IP address"""
        import socket
        try:
            hostname = socket.gethostname()
            return socket.gethostbyname(hostname)
        except:
            return 'unknown'
    
    def close(self):
        """Close logger and database connections"""
        self.db_queue.put(None)
        if self.db:
            self.db.close()


# Global logger instance
_system_logger = None

def get_system_logger() -> DualSystemLogger:
    """Get or create global system logger instance"""
    global _system_logger
    if _system_logger is None:
        _system_logger = DualSystemLogger()
    return _system_logger

# Decorator for automatic logging
def log_action(action_type: str, entity_type: str):
    """Decorator to automatically log actions"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            logger = get_system_logger()
            start_time = time.time()
            entity_id = None
            
            # Try to extract entity_id from arguments
            if len(args) > 1 and hasattr(args[0], '__class__'):
                # Assume first arg is self, second is entity_id
                entity_id = str(args[1]) if args[1] is not None else None
            
            try:
                result = func(*args, **kwargs)
                duration_ms = int((time.time() - start_time) * 1000)
                
                # Log success
                logger.log_action(
                    action_type=action_type,
                    entity_type=entity_type,
                    entity_id=entity_id,
                    success=True,
                    duration_ms=duration_ms,
                    details={'function': func.__name__}
                )
                
                return result
                
            except Exception as e:
                duration_ms = int((time.time() - start_time) * 1000)
                
                # Log failure
                logger.log_action(
                    action_type=action_type,
                    entity_type=entity_type,
                    entity_id=entity_id,
                    success=False,
                    error_message=str(e),
                    duration_ms=duration_ms,
                    details={'function': func.__name__}
                )
                
                # Also log the error
                logger.log_error(
                    error=e,
                    module_name=func.__module__,
                    function_name=func.__name__
                )
                
                raise
        
        return wrapper
    return decorator