"""
Limit Orders Module
Place orders at specific price levels with control over execution
"""

import sys
from typing import Optional, Dict
from binance.exceptions import BinanceAPIException

from src.utils.client import get_client
from src.utils.logger import setup_logger, log_trade, log_error
from src.utils.validators import (
    validate_symbol, validate_side, validate_quantity, 
    validate_price, validate_time_in_force
)

logger = setup_logger("LimitOrders")


class LimitOrderExecutor:
    """Execute limit orders on Binance Futures"""
    
    def __init__(self, testnet: bool = None):
        """
        Initialize limit order executor
        
        Args:
            testnet: Use testnet if True
        """
        self.client = get_client(testnet)
        logger.info("Limit Order Executor initialized")
    
    def execute_limit_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        price: float,
        time_in_force: str = "GTC",
        reduce_only: bool = False,
        position_side: str = "BOTH",
        post_only: bool = False
    ) -> Optional[Dict]:
        """
        Execute a limit order
        
        Args:
            symbol: Trading pair (e.g., BTCUSDT)
            side: BUY or SELL
            quantity: Order quantity
            price: Limit price
            time_in_force: GTC (Good Till Cancel), IOC (Immediate or Cancel), 
                          FOK (Fill or Kill), GTX (Good Till Crossing - Post Only)
            reduce_only: If True, order will only reduce position
            position_side: BOTH, LONG, or SHORT
            post_only: If True, order will only be maker (GTX)
        
        Returns:
            Order response dictionary or None if failed
        """
        try:
            # Validate inputs
            symbol = validate_symbol(symbol)
            side = validate_side(side)
            quantity = validate_quantity(quantity, symbol)
            price = validate_price(price, symbol)
            
            if post_only:
                time_in_force = "GTX"
            else:
                time_in_force = validate_time_in_force(time_in_force)
            
            logger.info(f"Placing limit order: {side} {quantity} {symbol} @ {price}")
            
            # Get current price for comparison
            current_price = self.client.get_current_price(symbol)
            if current_price:
                price_diff = ((price - current_price) / current_price) * 100
                logger.info(f"Current price: {current_price} (Limit {price_diff:+.2f}% from market)")
                
                # Warn if price is far from market
                if abs(price_diff) > 10:
                    logger.warning(f"⚠️  Limit price is {abs(price_diff):.2f}% from market price")
            
            # Prepare order parameters
            order_params = {
                'symbol': symbol,
                'side': side,
                'type': 'LIMIT',
                'quantity': quantity,
                'price': price,
                'timeInForce': time_in_force,
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
                order_type='LIMIT',
                symbol=symbol,
                side=side,
                quantity=quantity,
                price=price,
                order_id=order_response.get('orderId'),
                status=order_response.get('status'),
                time_in_force=time_in_force,
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
                logger.error("Invalid precision. Check symbol filters for quantity/price.")
            elif e.code == -4061:
                logger.error("Order price is outside allowable range.")
            return None
            
        except Exception as e:
            log_error(logger, e, "Limit order execution failed")
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
            ["Price", order.get('price', 'N/A')],
            ["Status", order.get('status', 'N/A')],
            ["Time in Force", order.get('timeInForce', 'N/A')],
            ["Update Time", order.get('updateTime', 'N/A')],
        ]
        
        print("\n" + "="*50)
        print("📊 LIMIT ORDER SUMMARY")
        print("="*50)
        print(tabulate(summary_data, tablefmt="simple"))
        print("="*50 + "\n")
    
    def modify_limit_order(
        self,
        symbol: str,
        order_id: int,
        new_quantity: float = None,
        new_price: float = None
    ) -> Optional[Dict]:
        """
        Modify an existing limit order
        
        Args:
            symbol: Trading pair
            order_id: Order ID to modify
            new_quantity: New quantity (optional)
            new_price: New price (optional)
        
        Returns:
            New order response or None
        """
        try:
            symbol = validate_symbol(symbol)
            
            # Get existing order details
            orders = self.client.get_open_orders(symbol)
            existing_order = None
            
            for order in orders:
                if order['orderId'] == order_id:
                    existing_order = order
                    break
            
            if not existing_order:
                logger.error(f"Order {order_id} not found or already filled/cancelled")
                return None
            
            # Cancel existing order
            logger.info(f"Cancelling order {order_id} to modify...")
            if not self.client.cancel_order(symbol, order_id):
                return None
            
            # Place new order with modified parameters
            quantity = new_quantity if new_quantity else float(existing_order['origQty'])
            price = new_price if new_price else float(existing_order['price'])
            
            logger.info(f"Placing modified order...")
            return self.execute_limit_order(
                symbol=symbol,
                side=existing_order['side'],
                quantity=quantity,
                price=price,
                time_in_force=existing_order.get('timeInForce', 'GTC'),
                position_side=existing_order.get('positionSide', 'BOTH')
            )
            
        except Exception as e:
            log_error(logger, e, "Failed to modify order")
            return None
    
    def place_bracket_orders(
        self,
        symbol: str,
        entry_side: str,
        quantity: float,
        entry_price: float,
        take_profit_price: float,
        stop_loss_price: float
    ) -> Dict[str, Optional[Dict]]:
        """
        Place entry order with take profit and stop loss
        
        Args:
            symbol: Trading pair
            entry_side: BUY or SELL for entry
            quantity: Order quantity
            entry_price: Entry limit price
            take_profit_price: Take profit target
            stop_loss_price: Stop loss price
        
        Returns:
            Dictionary with entry, take_profit, and stop_loss order responses
        """
        try:
            logger.info(f"Placing bracket orders for {symbol}")
            
            # Place entry order
            entry_order = self.execute_limit_order(
                symbol=symbol,
                side=entry_side,
                quantity=quantity,
                price=entry_price
            )
            
            if not entry_order:
                logger.error("Entry order failed, aborting bracket orders")
                return {'entry': None, 'take_profit': None, 'stop_loss': None}
            
            # Determine exit side (opposite of entry)
            exit_side = 'SELL' if entry_side == 'BUY' else 'BUY'
            
            # Place take profit order
            logger.info("Placing take profit order...")
            take_profit_order = self.execute_limit_order(
                symbol=symbol,
                side=exit_side,
                quantity=quantity,
                price=take_profit_price,
                reduce_only=True
            )
            
            # Import here to avoid circular dependency
            from src.advanced.stop_limit import StopLimitOrderExecutor
            stop_executor = StopLimitOrderExecutor()
            
            # Place stop loss order
            logger.info("Placing stop loss order...")
            stop_loss_order = stop_executor.execute_stop_market_order(
                symbol=symbol,
                side=exit_side,
                quantity=quantity,
                stop_price=stop_loss_price,
                reduce_only=True
            )
            
            logger.info("✓ Bracket orders placed successfully")
            
            return {
                'entry': entry_order,
                'take_profit': take_profit_order,
                'stop_loss': stop_loss_order
            }
            
        except Exception as e:
            log_error(logger, e, "Failed to place bracket orders")
            return {'entry': None, 'take_profit': None, 'stop_loss': None}


def main():
    """CLI entry point for limit orders"""
    if len(sys.argv) < 5:
        print("\n📖 Usage: python src/core/limit_orders.py <SYMBOL> <SIDE> <QUANTITY> <PRICE> [OPTIONS]")
        print("\nExamples:")
        print("  python src/core/limit_orders.py BTCUSDT BUY 0.01 95000")
        print("  python src/core/limit_orders.py ETHUSDT SELL 0.1 3500 --post-only")
        print("\nArguments:")
        print("  SYMBOL    - Trading pair (e.g., BTCUSDT, ETHUSDT)")
        print("  SIDE      - BUY or SELL")
        print("  QUANTITY  - Order quantity (must be > 0)")
        print("  PRICE     - Limit price")
        print("\nOptions:")
        print("  --post-only      - Ensure order is maker (GTX)")
        print("  --reduce-only    - Only reduce existing position")
        print("  --tif <GTC|IOC|FOK> - Time in force (default: GTC)")
        print("\n")
        sys.exit(1)
    
    symbol = sys.argv[1]
    side = sys.argv[2]
    quantity = float(sys.argv[3])
    price = float(sys.argv[4])
    
    # Parse options
    post_only = '--post-only' in sys.argv
    reduce_only = '--reduce-only' in sys.argv
    
    time_in_force = "GTC"
    if '--tif' in sys.argv:
        tif_index = sys.argv.index('--tif')
        if tif_index + 1 < len(sys.argv):
            time_in_force = sys.argv[tif_index + 1]
    
    try:
        executor = LimitOrderExecutor()
        result = executor.execute_limit_order(
            symbol=symbol,
            side=side,
            quantity=quantity,
            price=price,
            time_in_force=time_in_force,
            reduce_only=reduce_only,
            post_only=post_only
        )
        
        if result:
            logger.info("✓ Limit order placed successfully")
            sys.exit(0)
        else:
            logger.error("✗ Limit order placement failed")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.warning("\n⚠️  Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        log_error(logger, e, "Unexpected error")
        sys.exit(1)


if __name__ == "__main__":
    main()
