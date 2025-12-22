"""
Logging System for Maze Bourne
Provides centralized logging with file output and level controls
"""

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

class GameLogger:
    _instance: Optional['GameLogger'] = None
    
    def __init__(self, log_dir: str = "logs", log_level: int = logging.INFO):
        if GameLogger._instance is not None:
            raise RuntimeError("GameLogger is a singleton. Use get_logger() instead.")
        
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = self.log_dir / f"maze_bourne_{timestamp}.log"
        
        self.logger = logging.getLogger("MazeBourne")
        self.logger.setLevel(log_level)
        
        if self.logger.handlers:
            self.logger.handlers.clear()
        
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        
        formatter = logging.Formatter(
            '[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s',
            datefmt='%H:%M:%S'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        
        GameLogger._instance = self
        self.debug("Logger initialized")
    
    def debug(self, message: str):
        self.logger.debug(message)
    
    def info(self, message: str):
        self.logger.info(message)
    
    def warning(self, message: str):
        self.logger.warning(message)
    
    def error(self, message: str, exc_info: bool = False):
        self.logger.error(message, exc_info=exc_info)
    
    def critical(self, message: str, exc_info: bool = False):
        self.logger.critical(message, exc_info=exc_info)
    
    @classmethod
    def get_instance(cls) -> 'GameLogger':
        if cls._instance is None:
            cls._instance = GameLogger()
        return cls._instance
    
    @classmethod
    def shutdown(cls):
        if cls._instance:
            logging.shutdown()
            cls._instance = None

def get_logger() -> GameLogger:
    return GameLogger.get_instance()

def init_logger(log_dir: str = "logs", log_level: int = logging.INFO):
    if GameLogger._instance is None:
        GameLogger(log_dir, log_level)
    return get_logger()
