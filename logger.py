"""
logger.py
Centralized logging configuration
"""

import logging
import sys
from datetime import datetime
from config import config

def setup_logger(name: str = "github_auditor") -> logging.Logger:
    """
    Setup and configure logger
    
    Args:
        name: Logger name
        
    Returns:
        Configured logger instance
    """
    
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, config.LOG_LEVEL))
    
    # Remove existing handlers
    logger.handlers = []
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, config.LOG_LEVEL))
    
    # Create formatter
    if config.DEBUG_MODE:
        # Detailed format for development
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    else:
        # Simpler format for production
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Optional: Add file handler
    if not config.DEBUG_MODE:
        file_handler = logging.FileHandler('app.log')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


# Create global logger instance
logger = setup_logger()


# Convenience functions
def log_api_request(endpoint: str, username: str = None, ip: str = None):
    """Log API request"""
    msg = f"API Request: {endpoint}"
    if username:
        msg += f" | User: {username}"
    if ip:
        msg += f" | IP: {ip}"
    logger.info(msg)


def log_analysis_start(username: str, analysis_type: str):
    """Log analysis start"""
    logger.info(f"Starting {analysis_type} analysis for: {username}")


def log_analysis_complete(username: str, analysis_type: str, duration_seconds: float):
    """Log analysis completion"""
    logger.info(f"Completed {analysis_type} analysis for: {username} (took {duration_seconds:.2f}s)")


def log_error(error: Exception, context: str = ""):
    """Log error with context"""
    logger.error(f"Error in {context}: {type(error)._name_}: {str(error)}")


if __name__ == "__main__":
    """Test logger"""
    print("🧪 Testing Logger...")
    
    logger.debug("This is a debug message")
    logger.info("This is an info message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")
    
    # Test convenience functions
    log_api_request("/analyze/torvalds", username="torvalds", ip="192.168.1.1")
    log_analysis_start("torvalds", "profile")
    log_analysis_complete("torvalds", "profile", 2.5)
    
    print("\n✅ Logger test complete!")