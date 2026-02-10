"""
Market Orders Module
Executes immediate buy/sell orders at current market price
"""

import sys
from typing import Optional, Dict
from binance.exceptions import BinanceAPIException

from src.utils.client import get_client
from src.utils.logger import setup_logger, log_trade, log_error
from src.utils.validators import validate_symbol, validate_side, validate_quantity

logger = setup_logger("MarketOrders")


class MarketOrderExecutor:
    """Execute market orders on Binance Futures"""
    
    def __init__(self, testnet: bool = None):
        """
        Initialize market order executor
        
        Args:
            testnet: Use testnet if True
        """
        self.client = get_client(testnet)
        logger.info("Market Order Executor initialized")
    
    def execute_market_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        reduce_only: bool = False,
        position_side: str = "BOTH"
    ) -> Optional[Dict]:
        """
        Execute a market order
        
        Args:
            symbol: Trading pair (e.g., BTCUSDT)
            side: BUY or SELL
            quantity: Order quantity
            reduce_only: If True, order will only reduce position
            position_side: BOTH, LONG, or SHORT (for hedge mode)
        
        Returns:
            Order response dictionary or None if failed
        """
        try:
            # Validate inputs
            symbol = validate_symbol(symbol)
            side = validate_side(side)
            quantity = validate_quantity(quantity, symbol)
            
            logger.info(f"Executing market order: {side} {quantity} {symbol}")
            
            # Get current price for reference
            current_price = self.client.get_current_price(symbol)
            if current_price:
                logger.info(f"Current market price: {current_price}")
            
            # Prepare order parameters
            order_params = {
                'symbol': symbol,
                'side': side,
                'type': 'MARKET',
                'quantity': quantity,
                'positionSide': position_side,
            }
            
            if reduce_only:
                order_params['reduceOnly'] = 'true'
            
            # Execute order
            logger.debug(f"Order parameters: {order_params}")
            order_response = self.client.client.futures_create_order(**order_params)
            
            # Log successful trade
            log_trade(
                logger,
                order_type='MARKET',
                symbol=symbol,
                side=side,
                quantity=quantity,
                order_id=order_response.get('orderId'),
                status=order_response.get('status'),
                reduce_only=reduce_only
            )
            
            # Display order summary
            self._display_order_summary(order_response)
            
            return order_response
            
        except BinanceAPIException as e:
            logger.error(f"Binance API Error: {e.message} (Code: {e.code})")
            if e.code == -2019:
                logger.error("Insufficient margin. Please add funds or reduce position size.")
            elif e.code == -1111:
                logger.error("Invalid quantity precision. Check symbol filters.")
            return None
            
        except Exception as e:
            log_error(logger, e, "Market order execution failed")
            return None
    
    def _display_order_summary(self, order: Dict):
        """Display formatted order summary"""
        from tabulate import tabulate
        
        # Extract key information
        summary_data = [
            ["Order ID", order.get('orderId', 'N/A')],
            ["Symbol", order.get('symbol', 'N/A')],
            ["Side", order.get('side', 'N/A')],
            ["Type", order.get('type', 'N/A')],
            ["Quantity", order.get('origQty', 'N/A')],
            ["Status", order.get('status', 'N/A')],
            ["Avg Price", order.get('avgPrice', 'N/A')],
            ["Update Time", order.get('updateTime', 'N/A')],
        ]
        
        print("\n" + "="*50)
        print("📊 ORDER SUMMARY")
        print("="*50)
        print(tabulate(summary_data, tablefmt="simple"))
        print("="*50 + "\n")
    
    def close_position(self, symbol: str, position_side: str = "BOTH") -> Optional[Dict]:
        """
        Close an existing position using market order
        
        Args:
            symbol: Trading pair
            position_side: BOTH, LONG, or SHORT
        
        Returns:
            Order response or None
        """
        try:
            symbol = validate_symbol(symbol)
            
            # Get current position
            positions = self.client.get_open_positions()
            position = None
            
            for pos in positions:
                if pos['symbol'] == symbol and pos['positionSide'] == position_side:
                    position = pos
                    break
            
            if not position:
                logger.warning(f"No open position found for {symbol} ({position_side})")
                return None
            
            position_amt = float(position['positionAmt'])
            
            if position_amt == 0:
                logger.info(f"Position already closed for {symbol}")
                return None
            
            # Determine close side (opposite of position)
            close_side = 'SELL' if position_amt > 0 else 'BUY'
            close_quantity = abs(position_amt)
            
            logger.info(f"Closing position: {close_quantity} {symbol} (Side: {close_side})")
            
            return self.execute_market_order(
                symbol=symbol,
                side=close_side,
                quantity=close_quantity,
                reduce_only=True,
                position_side=position_side
            )
            
        except Exception as e:
            log_error(logger, e, "Failed to close position")
            return None


def main():
    """CLI entry point for market orders"""
    if len(sys.argv) < 4:
        print("\n📖 Usage: python src/core/market_orders.py <SYMBOL> <SIDE> <QUANTITY> [OPTIONS]")
        print("\nExamples:")
        print("  python src/core/market_orders.py BTCUSDT BUY 0.01")
        print("  python src/core/market_orders.py ETHUSDT SELL 0.1")
        print("\nArguments:")
        print("  SYMBOL    - Trading pair (e.g., BTCUSDT, ETHUSDT)")
        print("  SIDE      - BUY or SELL")
        print("  QUANTITY  - Order quantity (must be > 0)")
        print("\nOptions:")
        print("  --reduce-only    - Only reduce existing position")
        print("  --close          - Close existing position")
        print("\n")
        sys.exit(1)
    
    symbol = sys.argv[1]
    side = sys.argv[2]
    quantity = float(sys.argv[3])
    
    # Parse options
    reduce_only = '--reduce-only' in sys.argv
    close_position = '--close' in sys.argv
    
    try:
        executor = MarketOrderExecutor()
        
        if close_position:
            logger.info("Closing position...")
            result = executor.close_position(symbol)
        else:
            result = executor.execute_market_order(
                symbol=symbol,
                side=side,
                quantity=quantity,
                reduce_only=reduce_only
            )
        
        if result:
            logger.info("✓ Order executed successfully")
            sys.exit(0)
        else:
            logger.error("✗ Order execution failed")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.warning("\n⚠️  Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        log_error(logger, e, "Unexpected error")
        sys.exit(1)


if __name__ == "__main__":
    main()
