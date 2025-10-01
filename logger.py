"""Preconfigured logger for the project"""
import logging
import os
from typing import Optional

class Logger:
    """Logger used throughout the project"""
    def __init__(self, name: str = "unnamed", log_level: str = "INFO",
                 log_file: Optional[str] = None):
        """
        Initialize the logger.
        
        Args:
            name: Logger name
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            log_file: Optional log file path. If None, creates logs/squishy.log
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, log_level.upper()))

        # Clear existing handlers
        if self.logger.handlers:
            self.logger.handlers.clear()

        # Create logs directory if it doesn't exist
        if log_file is None:
            log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
            os.makedirs(log_dir, exist_ok=True)
            log_file = os.path.join(log_dir, f"{name}.log")
        else:
            # Ensure directory for the log file exists
            os.makedirs(os.path.dirname(os.path.abspath(log_file)), exist_ok=True)

        # Create formatters
        file_formatter = logging.Formatter(
            '[%(asctime)s - %(name)s %(levelname)s] %(message)s'
        )

        class ColorFormatter(logging.Formatter):
            """Custom formatter to add colors to log levels in console"""
            COLORS = {
                'DEBUG': '\033[0;36mDEBUG\033[0m',
                'INFO': '\033[0;34mINFO\033[0m',
                'WARNING': '\033[0;31mWARNING\033[0m',
                'ERROR': '\033[0;31mERROR\033[0m',
                'CRITICAL': '\033[0;31mCRITICAL\033[0m',
            }
            def format(self, record):
                levelname = record.levelname
                if levelname in self.COLORS:
                    record.levelname = self.COLORS[levelname]
                return super().format(record)

        console_format = ('\033[1;30m[\033[0m%(asctime)s \033[0;35m- \033[0m'
                          '\033[3m%(name)s \033[0m%(levelname)s\033[1;30m]\033[0m %(message)s')
        console_formatter = ColorFormatter(
            console_format,
            datefmt='%H:%M:%S'
        )

        # File handler
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(file_formatter)
        self.logger.addHandler(file_handler)

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(getattr(logging, log_level.upper()))
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)

        self.log_file = log_file

    def debug(self, message: str):
        """Log a debug message"""
        self.logger.debug(message)

    def info(self, message: str):
        """Log an info message"""
        self.logger.info(message)

    def warning(self, message: str):
        """Log a warning message"""
        self.logger.warning(message)

    def error(self, message: str):
        """Log an error message"""
        self.logger.error(message)

    def critical(self, message: str):
        """Log a critical message"""
        self.logger.critical(message)

    def exception(self, message: str):
        """Log an exception message"""
        self.logger.exception(message)

    def set_level(self, level: str):
        """Set the logging level"""
        self.logger.setLevel(getattr(logging, level.upper()))
        for handler in self.logger.handlers:
            is_stream_handler = isinstance(handler, logging.StreamHandler)
            is_not_file_handler = not isinstance(handler, logging.FileHandler)
            if is_stream_handler and is_not_file_handler:
                handler.setLevel(getattr(logging, level.upper()))

    def get_log_file_path(self) -> str:
        """Get the path to the log file"""
        return self.log_file
