"""
Tests for logging system
"""

import pytest
import os
from src.core.logger import GameLogger, get_logger, init_logger

def test_logger_singleton():
    """Test that logger is a singleton."""
    logger1 = get_logger()
    logger2 = get_logger()
    assert logger1 is logger2

def test_logger_methods():
    """Test that all logging methods work."""
    logger = get_logger()
    
    logger.debug("Debug message")
    logger.info("Info message")
    logger.warning("Warning message")
    logger.error("Error message")
    
    assert True

def test_logger_creates_log_file():
    """Test that logger creates log file."""
    logger = get_logger()
    log_dir = logger.log_dir
    
    assert log_dir.exists()
    assert log_dir.is_dir()
    
    log_files = list(log_dir.glob("maze_bourne_*.log"))
    assert len(log_files) > 0
