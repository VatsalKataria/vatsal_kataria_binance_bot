"""
Stop-Limit Orders Module (Advanced)
Execute orders when price reaches a trigger point
"""

import sys
from typing import Optional, Dict
from binance.exceptions import BinanceAPIException

from src.utils.client import get_client
from src.utils.logger import setup_logger, log_trade, log_error
from src.utils.validators import (
    validate_symbol, validate_side, validate_quantity, validate_price
)

logger = setup_logger("StopLimitOrders")


class StopLimitOrderExecutor:
    """Execute stop-limit and stop-market orders"""
    
    def __init__(self, testnet: bool = None):
        """
        Initialize stop-limit order executor
        
        Args:
            testnet: Use testnet if True
        """
        self.client = get_client(testnet)
        logger.info("Stop-Limit Order Executor initialized")
    
    def execute_stop_limit_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        stop_price: float,
        limit_price: float,
        reduce_only: bool = False,
        position_side: str = "BOTH",
        working_type: str = "CONTRACT_PRICE"
    ) -> Optional[Dict]:
        """
        Execute a stop-limit order
        
        Args:
            symbol: Trading pair (e.g., BTCUSDT)
            side: BUY or SELL
            quantity: Order quantity
            stop_price: Price that triggers the order
            limit_price: Limit price after trigger
            reduce_only: If True, order will only reduce position
            position_side: BOTH, LONG, or SHORT
            working_type: CONTRACT_PRICE or MARK_PRICE
        
        Returns:
            Order response dictionary or None if failed
        """
        try:
            # Validate inputs
            symbol = validate_symbol(symbol)
            side = validate_side(side)
            quantity = validate_quantity(quantity, symbol)
            stop_price = validate_price(stop_price, symbol)
            limit_price = validate_price(limit_price, symbol)
            
            logger.info(f"Placing stop-limit order: {side} {quantity} {symbol}")
            logger.info(f"Stop: {stop_price} | Limit: {limit_price}")
            
            # Get current price for reference
            current_price = self.client.get_current_price(symbol)
            if current_price:
                stop_diff = ((stop_price - current_price) / current_price) * 100
                logger.info(f"Current price: {current_price} (Stop {stop_diff:+.2f}% from market)")
                
                # Validate stop price logic
                if side == "BUY" and stop_price <= current_price:
                    logger.warning("⚠️  BUY stop should typically be above current price")
                elif side == "SELL" and stop_price >= current_price:
                    logger.warning("⚠️  SELL stop should typically be below current price")
            
            # Prepare order parameters
            order_params = {
                'symbol': symbol,
                'side': side,
                'type': 'STOP',
                'quantity': quantity,
                'price': limit_price,
                'stopPrice': stop_price,
                'timeInForce': 'GTC',
                'positionSide': position_side,
                'workingType': working_type,
            }
            
            if reduce_only:
                order_params['reduceOnly'] = 'true'
            
            # Execute order
            logger.debug(f"Order parameters: {order_params}")
            order_response = self.client.client.futures_create_order(**order_params)
            
            # Log successful trade
            log_trade(
                logger,
                order_type='STOP_LIMIT',
                symbol=symbol,
                side=side,
                quantity=quantity,
                stop_price=stop_price,
                limit_price=limit_price,
                order_id=order_response.get('orderId'),
                status=order_response.get('status')
            )
            
            # Display order summary
            self._display_order_summary(order_response)
            
            return order_response
            
        except BinanceAPIException as e:
            logger.error(f"Binance API Error: {e.message} (Code: {e.code})")
            return None
        except Exception as e:
            log_error(logger, e, "Stop-limit order execution failed")
            return None
    
    def execute_stop_market_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        stop_price: float,
        reduce_only: bool = False,
        position_side: str = "BOTH",
        working_type: str = "CONTRACT_PRICE"
    ) -> Optional[Dict]:
        """
        Execute a stop-market order (executes at market when stop is hit)
        
        Args:
            symbol: Trading pair
            side: BUY or SELL
            quantity: Order quantity
            stop_price: Price that triggers the order
            reduce_only: If True, order will only reduce position
            position_side: BOTH, LONG, or SHORT
            working_type: CONTRACT_PRICE or MARK_PRICE
        
        Returns:
            Order response dictionary or None if failed
        """
        try:
            # Validate inputs
            symbol = validate_symbol(symbol)
            side = validate_side(side)
            quantity = validate_quantity(quantity, symbol)
            stop_price = validate_price(stop_price, symbol)
            
            logger.info(f"Placing stop-market order: {side} {quantity} {symbol} @ {stop_price}")
            
            # Prepare order parameters
            order_params = {
                'symbol': symbol,
                'side': side,
                'type': 'STOP_MARKET',
                'quantity': quantity,
                'stopPrice': stop_price,
                'positionSide': position_side,
                'workingType': working_type,
            }
            
            if reduce_only:
                order_params['reduceOnly'] = 'true'
            
            # Execute order
            logger.debug(f"Order parameters: {order_params}")
            order_response = self.client.client.futures_create_order(**order_params)
            
            # Log successful trade
            log_trade(
                logger,
                order_type='STOP_MARKET',
                symbol=symbol,
                side=side,
                quantity=quantity,
                stop_price=stop_price,
                order_id=order_response.get('orderId'),
                status=order_response.get('status')
            )
            
            # Display order summary
            self._display_order_summary(order_response)
            
            return order_response
            
        except BinanceAPIException as e:
            logger.error(f"Binance API Error: {e.message} (Code: {e.code})")
            return None
        except Exception as e:
            log_error(logger, e, "Stop-market order execution failed")
            return None
    
    def execute_trailing_stop(
        self,
        symbol: str,
        side: str,
        quantity: float,
        callback_rate: float,
        activation_price: float = None,
        reduce_only: bool = True,
        position_side: str = "BOTH"
    ) -> Optional[Dict]:
        """
        Execute a trailing stop order
        
        Args:
            symbol: Trading pair
            side: BUY or SELL
            quantity: Order quantity
            callback_rate: Callback rate (0.1 = 0.1%)
            activation_price: Price to activate trailing (optional)
            reduce_only: If True, order will only reduce position
            position_side: BOTH, LONG, or SHORT
        
        Returns:
            Order response dictionary or None if failed
        """
        try:
            # Validate inputs
            symbol = validate_symbol(symbol)
            side = validate_side(side)
            quantity = validate_quantity(quantity, symbol)
            
            if not (0.1 <= callback_rate <= 5.0):
                raise ValueError("Callback rate must be between 0.1 and 5.0")
            
            logger.info(f"Placing trailing stop: {side} {quantity} {symbol}")
            logger.info(f"Callback rate: {callback_rate}%")
            
            # Prepare order parameters
            order_params = {
                'symbol': symbol,
                'side': side,
                'type': 'TRAILING_STOP_MARKET',
                'quantity': quantity,
                'callbackRate': callback_rate,
                'positionSide': position_side,
            }
            
            if activation_price:
                order_params['activationPrice'] = validate_price(activation_price, symbol)
                logger.info(f"Activation price: {activation_price}")
            
            if reduce_only:
                order_params['reduceOnly'] = 'true'
            
            # Execute order
            logger.debug(f"Order parameters: {order_params}")
            order_response = self.client.client.futures_create_order(**order_params)
            
            # Log successful trade
            log_trade(
                logger,
                order_type='TRAILING_STOP',
                symbol=symbol,
                side=side,
                quantity=quantity,
                callback_rate=callback_rate,
                order_id=order_response.get('orderId'),
                status=order_response.get('status')
            )
            
            # Display order summary
            self._display_order_summary(order_response)
            
            return order_response
            
        except BinanceAPIException as e:
            logger.error(f"Binance API Error: {e.message} (Code: {e.code})")
            return None
        except Exception as e:
            log_error(logger, e, "Trailing stop order execution failed")
            return None
    
    def _display_order_summary(self, order: Dict):
        """Display formatted order summary"""
        from tabulate import tabulate
        
        summary_data = [
            ["Order ID", order.get('orderId', 'N/A')],
            ["Symbol", order.get('symbol', 'N/A')],
            ["Side", order.get('side', 'N/A')],
            ["Type", order.get('type', 'N/A')],
            ["Quantity", order.get('origQty', 'N/A')],
            ["Stop Price", order.get('stopPrice', 'N/A')],
            ["Price", order.get('price', 'N/A')],
            ["Status", order.get('status', 'N/A')],
        ]
        
        print("\n" + "="*50)
        print("🛑 STOP ORDER SUMMARY")
        print("="*50)
        print(tabulate(summary_data, tablefmt="simple"))
        print("="*50 + "\n")


def main():
    """CLI entry point for stop-limit orders"""
    if len(sys.argv) < 2:
        print("\n📖 Stop-Limit Orders Usage")
        print("\n1. Stop-Limit Order:")
        print("   python src/advanced/stop_limit.py <SYMBOL> <SIDE> <QTY> <STOP_PRICE> <LIMIT_PRICE>")
        print("   Example: python src/advanced/stop_limit.py BTCUSDT SELL 0.01 94000 93800")
        print("\n2. Stop-Market Order:")
        print("   python src/advanced/stop_limit.py --stop-market <SYMBOL> <SIDE> <QTY> <STOP_PRICE>")
        print("   Example: python src/advanced/stop_limit.py --stop-market BTCUSDT SELL 0.01 94000")
        print("\n3. Trailing Stop:")
        print("   python src/advanced/stop_limit.py --trailing <SYMBOL> <SIDE> <QTY> <CALLBACK_RATE>")
        print("   Example: python src/advanced/stop_limit.py --trailing BTCUSDT SELL 0.01 1.0")
        print("\n")
        sys.exit(1)
    
    try:
        executor = StopLimitOrderExecutor()
        
        # Check for order type flags
        if '--stop-market' in sys.argv:
            # Stop-market order
            idx = sys.argv.index('--stop-market')
            symbol = sys.argv[idx + 1]
            side = sys.argv[idx + 2]
            quantity = float(sys.argv[idx + 3])
            stop_price = float(sys.argv[idx + 4])
            
            result = executor.execute_stop_market_order(
                symbol=symbol,
                side=side,
                quantity=quantity,
                stop_price=stop_price,
                reduce_only='--reduce-only' in sys.argv
            )
            
        elif '--trailing' in sys.argv:
            # Trailing stop order
            idx = sys.argv.index('--trailing')
            symbol = sys.argv[idx + 1]
            side = sys.argv[idx + 2]
            quantity = float(sys.argv[idx + 3])
            callback_rate = float(sys.argv[idx + 4])
            
            result = executor.execute_trailing_stop(
                symbol=symbol,
                side=side,
                quantity=quantity,
                callback_rate=callback_rate,
                reduce_only='--reduce-only' in sys.argv
            )
            
        else:
            # Regular stop-limit order
            symbol = sys.argv[1]
            side = sys.argv[2]
            quantity = float(sys.argv[3])
            stop_price = float(sys.argv[4])
            limit_price = float(sys.argv[5])
            
            result = executor.execute_stop_limit_order(
                symbol=symbol,
                side=side,
                quantity=quantity,
                stop_price=stop_price,
                limit_price=limit_price,
                reduce_only='--reduce-only' in sys.argv
            )
        
        if result:
            logger.info("✓ Stop order placed successfully")
            sys.exit(0)
        else:
            logger.error("✗ Stop order placement failed")
            sys.exit(1)
            
    except (IndexError, ValueError) as e:
        logger.error(f"Invalid arguments: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.warning("\n⚠️  Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        log_error(logger, e, "Unexpected error")
        sys.exit(1)


if __name__ == "__main__":
    main()
