"""
utils.py
=========

Utility module providing helper functions for logging configuration
and verifying that imports are working correctly.

Functions
---------
configure_logging():
    Configure colorized logging output using the `colorlog` library for clearer log visibility.

test_import():
    Print a simple confirmation message to verify that the module imports successfully.

Example
-------
>>> from utils import configure_logging
>>> logger = configure_logging()
>>> logger.info("Logger initialized successfully.")
2025-10-07 10:00:00 - INFO - Logger initialized successfully.

>>> from utils import test_import
>>> test_import()
importing working
"""
import colorlog


def configure_logging():
    """
    Configure color logging for better visibility in logs.

    Returns
    -------
    logger : logging.Logger
        A configured logger instance that outputs colorized log messages.

    Notes
    -----
    The following colors are applied by log level:
        - DEBUG: cyan
        - INFO: green
        - WARNING: yellow
        - ERROR: red
        - CRITICAL: bold red
    """
    handler = colorlog.StreamHandler()
    handler.setFormatter(
        colorlog.ColoredFormatter(
            '%(log_color)s%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S',
            log_colors={
                'DEBUG': 'cyan',
                'INFO': 'green',
                'WARNING': 'yellow',
                'ERROR': 'red',
                'CRITICAL': 'bold_red',
            },
        )
    )
    logger = colorlog.getLogger()
    logger.addHandler(handler)
    logger.setLevel('INFO')
    return logger


def test_import():
    """Print a simple confirmation that the module import worked."""
    print('importing working')
