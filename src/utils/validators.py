"""
Input validation utilities for trading bot
Validates symbols, quantities, prices, and other trading parameters
"""

import re
from typing import Tuple, Optional
from decimal import Decimal, InvalidOperation


class ValidationError(Exception):
    """Custom exception for validation errors"""
    pass


def validate_symbol(symbol: str) -> str:
    """
    Validate trading symbol format
    
    Args:
        symbol: Trading pair symbol (e.g., BTCUSDT)
    
    Returns:
        Uppercase symbol
    
    Raises:
        ValidationError: If symbol format is invalid
    """
    if not symbol:
        raise ValidationError("Symbol cannot be empty")
    
    symbol = symbol.upper().strip()
    
    # Check if symbol ends with USDT (for USDT-M futures)
    if not symbol.endswith('USDT'):
        raise ValidationError(f"Invalid symbol: {symbol}. Must be a USDT-M futures pair (e.g., BTCUSDT)")
    
    # Check if base currency is valid (alphanumeric)
    base = symbol[:-4]  # Remove USDT
    if not base.isalnum() or len(base) < 2:
        raise ValidationError(f"Invalid base currency in symbol: {symbol}")
    
    return symbol


def validate_side(side: str) -> str:
    """
    Validate order side (BUY/SELL)
    
    Args:
        side: Order side
    
    Returns:
        Uppercase side
    
    Raises:
        ValidationError: If side is invalid
    """
    if not side:
        raise ValidationError("Side cannot be empty")
    
    side = side.upper().strip()
    
    if side not in ['BUY', 'SELL']:
        raise ValidationError(f"Invalid side: {side}. Must be BUY or SELL")
    
    return side


def validate_quantity(quantity: float, symbol: str = None) -> float:
    """
    Validate order quantity
    
    Args:
        quantity: Order quantity
        symbol: Trading symbol (optional, for symbol-specific validation)
    
    Returns:
        Validated quantity
    
    Raises:
        ValidationError: If quantity is invalid
    """
    try:
        quantity = float(quantity)
    except (ValueError, TypeError):
        raise ValidationError(f"Invalid quantity: {quantity}. Must be a number")
    
    if quantity <= 0:
        raise ValidationError(f"Invalid quantity: {quantity}. Must be greater than 0")
    
    # Check for reasonable maximum (prevent accidental huge orders)
    if quantity > 1000000:
        raise ValidationError(f"Quantity too large: {quantity}. Maximum is 1,000,000")
    
    return quantity


def validate_price(price: float, symbol: str = None) -> float:
    """
    Validate order price
    
    Args:
        price: Order price
        symbol: Trading symbol (optional)
    
    Returns:
        Validated price
    
    Raises:
        ValidationError: If price is invalid
    """
    try:
        price = float(price)
    except (ValueError, TypeError):
        raise ValidationError(f"Invalid price: {price}. Must be a number")
    
    if price <= 0:
        raise ValidationError(f"Invalid price: {price}. Must be greater than 0")
    
    # Check for reasonable maximum
    if price > 10000000:
        raise ValidationError(f"Price too large: {price}. Maximum is 10,000,000")
    
    return price


def validate_percentage(percentage: float, min_val: float = 0, max_val: float = 100) -> float:
    """
    Validate percentage value
    
    Args:
        percentage: Percentage value
        min_val: Minimum allowed value
        max_val: Maximum allowed value
    
    Returns:
        Validated percentage
    
    Raises:
        ValidationError: If percentage is invalid
    """
    try:
        percentage = float(percentage)
    except (ValueError, TypeError):
        raise ValidationError(f"Invalid percentage: {percentage}. Must be a number")
    
    if not (min_val <= percentage <= max_val):
        raise ValidationError(
            f"Invalid percentage: {percentage}. Must be between {min_val} and {max_val}"
        )
    
    return percentage


def validate_leverage(leverage: int) -> int:
    """
    Validate leverage value for Binance Futures
    
    Args:
        leverage: Leverage multiplier
    
    Returns:
        Validated leverage
    
    Raises:
        ValidationError: If leverage is invalid
    """
    try:
        leverage = int(leverage)
    except (ValueError, TypeError):
        raise ValidationError(f"Invalid leverage: {leverage}. Must be an integer")
    
    if not (1 <= leverage <= 125):
        raise ValidationError(f"Invalid leverage: {leverage}. Must be between 1 and 125")
    
    return leverage


def validate_time_in_force(time_in_force: str) -> str:
    """
    Validate time in force parameter
    
    Args:
        time_in_force: Time in force value
    
    Returns:
        Uppercase time in force
    
    Raises:
        ValidationError: If time in force is invalid
    """
    valid_values = ['GTC', 'IOC', 'FOK', 'GTX']
    
    time_in_force = time_in_force.upper().strip()
    
    if time_in_force not in valid_values:
        raise ValidationError(
            f"Invalid timeInForce: {time_in_force}. Must be one of {valid_values}"
        )
    
    return time_in_force


def validate_order_type(order_type: str) -> str:
    """
    Validate order type
    
    Args:
        order_type: Order type
    
    Returns:
        Uppercase order type
    
    Raises:
        ValidationError: If order type is invalid
    """
    valid_types = ['MARKET', 'LIMIT', 'STOP', 'STOP_MARKET', 'TAKE_PROFIT', 
                   'TAKE_PROFIT_MARKET', 'TRAILING_STOP_MARKET']
    
    order_type = order_type.upper().strip()
    
    if order_type not in valid_types:
        raise ValidationError(
            f"Invalid order type: {order_type}. Must be one of {valid_types}"
        )
    
    return order_type


def validate_positive_integer(value: int, name: str = "value") -> int:
    """
    Validate positive integer
    
    Args:
        value: Integer value
        name: Name of the parameter (for error messages)
    
    Returns:
        Validated integer
    
    Raises:
        ValidationError: If value is invalid
    """
    try:
        value = int(value)
    except (ValueError, TypeError):
        raise ValidationError(f"Invalid {name}: {value}. Must be an integer")
    
    if value <= 0:
        raise ValidationError(f"Invalid {name}: {value}. Must be greater than 0")
    
    return value


def validate_price_range(lower_price: float, upper_price: float, current_price: float = None) -> Tuple[float, float]:
    """
    Validate price range for grid trading
    
    Args:
        lower_price: Lower bound of price range
        upper_price: Upper bound of price range
        current_price: Current market price (optional)
    
    Returns:
        Tuple of (lower_price, upper_price)
    
    Raises:
        ValidationError: If price range is invalid
    """
    lower_price = validate_price(lower_price)
    upper_price = validate_price(upper_price)
    
    if lower_price >= upper_price:
        raise ValidationError(
            f"Invalid price range: lower_price ({lower_price}) must be less than upper_price ({upper_price})"
        )
    
    # Check if range is reasonable (at least 1% difference)
    price_diff_pct = ((upper_price - lower_price) / lower_price) * 100
    if price_diff_pct < 0.5:
        raise ValidationError(
            f"Price range too narrow: {price_diff_pct:.2f}%. Minimum recommended range is 0.5%"
        )
    
    if current_price:
        current_price = validate_price(current_price)
        if not (lower_price <= current_price <= upper_price):
            raise ValidationError(
                f"Current price ({current_price}) is outside the specified range "
                f"({lower_price} - {upper_price})"
            )
    
    return lower_price, upper_price
