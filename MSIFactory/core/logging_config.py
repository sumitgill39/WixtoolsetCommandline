#!/usr/bin/env python3
"""
Enhanced Logging Configuration for MSI Factory
Captures all system events, errors, and exceptions
"""

import os
import sys
import logging
import logging.handlers
import traceback
from datetime import datetime
from pathlib import Path

class ComprehensiveLogger:
    """Comprehensive logging system that captures all events"""

    def __init__(self, log_dir="logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)

        # Configure root logger to catch everything
        self.setup_root_logger()

        # Configure Flask logger
        self.setup_flask_logger()

        # Configure Waitress logger
        self.setup_waitress_logger()

        # Setup custom loggers for different components
        self.system_logger = self.setup_logger('system', 'system.log')
        self.error_logger = self.setup_logger('errors', 'error.log')
        self.access_logger = self.setup_logger('access', 'access.log')

    def setup_root_logger(self):
        """Configure the root logger to catch all uncaught exceptions"""
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)

        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)s | %(name)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        # File handler for all logs
        all_handler = logging.handlers.RotatingFileHandler(
            self.log_dir / 'system.log',
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        all_handler.setFormatter(formatter)
        all_handler.setLevel(logging.INFO)
        root_logger.addHandler(all_handler)

        # Error file handler
        error_handler = logging.handlers.RotatingFileHandler(
            self.log_dir / 'error.log',
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        error_handler.setFormatter(formatter)
        error_handler.setLevel(logging.ERROR)
        root_logger.addHandler(error_handler)

        # Console handler (with less verbose output)
        console_handler = logging.StreamHandler(sys.stdout)
        console_formatter = logging.Formatter('%(levelname)s: %(message)s')
        console_handler.setFormatter(console_formatter)
        console_handler.setLevel(logging.WARNING)
        root_logger.addHandler(console_handler)

    def setup_flask_logger(self):
        """Configure Flask application logger"""
        flask_logger = logging.getLogger('flask.app')
        flask_logger.setLevel(logging.INFO)

        # Flask specific formatter
        formatter = logging.Formatter(
            '%(asctime)s | FLASK | %(levelname)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        # Handler for Flask logs
        handler = logging.handlers.RotatingFileHandler(
            self.log_dir / 'system.log',
            maxBytes=10*1024*1024,
            backupCount=5
        )
        handler.setFormatter(formatter)
        flask_logger.addHandler(handler)

    def setup_waitress_logger(self):
        """Configure Waitress server logger"""
        waitress_logger = logging.getLogger('waitress')
        waitress_logger.setLevel(logging.INFO)

        # Waitress specific formatter
        formatter = logging.Formatter(
            '%(asctime)s | WAITRESS | %(levelname)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        # Handler for Waitress logs
        handler = logging.handlers.RotatingFileHandler(
            self.log_dir / 'system.log',
            maxBytes=10*1024*1024,
            backupCount=5
        )
        handler.setFormatter(formatter)
        waitress_logger.addHandler(handler)

        # Also log Waitress errors to error log
        error_handler = logging.handlers.RotatingFileHandler(
            self.log_dir / 'error.log',
            maxBytes=10*1024*1024,
            backupCount=5
        )
        error_handler.setFormatter(formatter)
        error_handler.setLevel(logging.ERROR)
        waitress_logger.addHandler(error_handler)

    def setup_logger(self, name, filename):
        """Setup a custom logger"""
        logger = logging.getLogger(name)
        logger.setLevel(logging.DEBUG)

        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        handler = logging.handlers.RotatingFileHandler(
            self.log_dir / filename,
            maxBytes=10*1024*1024,
            backupCount=5
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        return logger

    def log_exception(self, exc_type, exc_value, exc_traceback):
        """Log uncaught exceptions"""
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return

        error_msg = "Uncaught exception:\n" + "".join(
            traceback.format_exception(exc_type, exc_value, exc_traceback)
        )
        self.error_logger.error(error_msg)
        self.system_logger.error(f"CRITICAL ERROR: {exc_type.__name__}: {exc_value}")

def setup_comprehensive_logging(app=None):
    """Setup comprehensive logging for the application"""
    # Create logger instance
    logger_instance = ComprehensiveLogger()

    # Set up exception hook to catch uncaught exceptions
    sys.excepthook = logger_instance.log_exception

    # If Flask app is provided, configure it
    if app:
        configure_flask_app_logging(app, logger_instance)

    # Log startup
    logger_instance.system_logger.info("=" * 60)
    logger_instance.system_logger.info("MSI Factory System Started")
    logger_instance.system_logger.info(f"Python Version: {sys.version}")
    logger_instance.system_logger.info(f"Working Directory: {os.getcwd()}")
    logger_instance.system_logger.info("=" * 60)

    return logger_instance

def configure_flask_app_logging(app, logger_instance):
    """Configure Flask application with comprehensive logging"""
    import traceback
    from flask import request, g

    # Log all requests
    @app.before_request
    def log_request():
        g.start_time = datetime.now()
        logger_instance.access_logger.info(
            f"REQUEST | {request.method} {request.path} | "
            f"IP: {request.remote_addr} | User-Agent: {request.user_agent.string}"
        )

    # Log all responses
    @app.after_request
    def log_response(response):
        if hasattr(g, 'start_time'):
            elapsed = (datetime.now() - g.start_time).total_seconds()
            logger_instance.access_logger.info(
                f"RESPONSE | {request.method} {request.path} | "
                f"Status: {response.status_code} | Time: {elapsed:.3f}s"
            )
        return response

    # Log all errors
    @app.errorhandler(Exception)
    def log_exception(error):
        error_traceback = traceback.format_exc()
        logger_instance.error_logger.error(
            f"Flask Exception on {request.method} {request.path}:\n{error_traceback}"
        )
        logger_instance.system_logger.error(
            f"ERROR | {error.__class__.__name__} | {request.method} {request.path} | {str(error)}"
        )
        # Re-raise the error so Flask can handle it normally
        raise

    # Override Flask's logger
    app.logger.handlers = []
    app.logger.propagate = True

    return app

# Compatibility functions for existing code
def get_logger():
    """Get logger instance (for compatibility)"""
    return logging.getLogger('system')

def log_info(message):
    """Log info message"""
    logging.getLogger('system').info(message)

def log_error(message):
    """Log error message"""
    logging.getLogger('errors').error(message)
    logging.getLogger('system').error(f"ERROR | {message}")

def log_security(message):
    """Log security message"""
    logging.getLogger('system').warning(f"SECURITY | {message}")
    logging.getLogger('access').warning(f"SECURITY | {message}")