"""
Logging utility for the Binance Futures Trading Bot
Provides structured logging with timestamps, levels, and file rotation
"""

import logging
import os
from datetime import datetime
from pathlib import Path
from logging.handlers import RotatingFileHandler
from colorama import Fore, Style, init

# Initialize colorama
init(autoreset=True)

class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors for console output"""
    
    COLORS = {
        'DEBUG': Fore.CYAN,
        'INFO': Fore.GREEN,
        'WARNING': Fore.YELLOW,
        'ERROR': Fore.RED,
        'CRITICAL': Fore.RED + Style.BRIGHT,
    }
    
    def format(self, record):
        levelname = record.levelname
        if levelname in self.COLORS:
            record.levelname = f"{self.COLORS[levelname]}{levelname}{Style.RESET_ALL}"
        return super().format(record)


def setup_logger(name: str = "BinanceBot", log_level: str = "INFO") -> logging.Logger:
    """
    Setup and configure logger with file and console handlers
    
    Args:
        name: Logger name
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    
    Returns:
        Configured logger instance
    """
    # Create logs directory if it doesn't exist
    log_dir = Path(__file__).parent.parent.parent / "logs"
    log_dir.mkdir(exist_ok=True)
    
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Prevent duplicate handlers
    if logger.handlers:
        return logger
    
    # File handler with rotation (10MB max, keep 5 backups)
    log_file = log_dir / "bot.log"
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_formatter)
    
    # Console handler with colors
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, log_level.upper()))
    console_formatter = ColoredFormatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    console_handler.setFormatter(console_formatter)
    
    # Add handlers
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger


def log_trade(logger: logging.Logger, order_type: str, symbol: str, side: str, 
              quantity: float, price: float = None, **kwargs):
    """
    Log trade execution with structured format
    
    Args:
        logger: Logger instance
        order_type: Type of order (MARKET, LIMIT, etc.)
        symbol: Trading pair
        side: BUY or SELL
        quantity: Order quantity
        price: Order price (optional for market orders)
        **kwargs: Additional order parameters
    """
    trade_info = {
        'type': order_type,
        'symbol': symbol,
        'side': side,
        'quantity': quantity,
    }
    
    if price:
        trade_info['price'] = price
    
    trade_info.update(kwargs)
    
    log_msg = " | ".join([f"{k.upper()}: {v}" for k, v in trade_info.items()])
    logger.info(f"TRADE EXECUTED - {log_msg}")


def log_error(logger: logging.Logger, error: Exception, context: str = ""):
    """
    Log errors with full traceback
    
    Args:
        logger: Logger instance
        error: Exception object
        context: Additional context about where error occurred
    """
    import traceback
    
    error_msg = f"{context + ' - ' if context else ''}{type(error).__name__}: {str(error)}"
    logger.error(error_msg)
    logger.debug(f"Traceback:\n{traceback.format_exc()}")


# Create default logger instance
default_logger = setup_logger()
