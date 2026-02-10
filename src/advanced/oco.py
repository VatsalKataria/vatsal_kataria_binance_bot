"""
OCO (One-Cancels-the-Other) Orders Module (Advanced)
Place take-profit and stop-loss orders simultaneously
"""

import sys
from typing import Optional, Dict, List
from binance.exceptions import BinanceAPIException
import time

from src.utils.client import get_client
from src.utils.logger import setup_logger, log_trade, log_error
from src.utils.validators import (
    validate_symbol, validate_side, validate_quantity, validate_price
)

logger = setup_logger("OCOOrders")


class OCOOrderExecutor:
    """Execute OCO (One-Cancels-the-Other) orders"""
    
    def __init__(self, testnet: bool = None):
        """
        Initialize OCO order executor
        
        Args:
            testnet: Use testnet if True
        """
        self.client = get_client(testnet)
        self.active_oco_groups = []  # Track OCO groups
        logger.info("OCO Order Executor initialized")
    
    def execute_oco_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        take_profit_price: float,
        stop_loss_price: float,
        stop_limit_price: float = None,
        reduce_only: bool = True,
        position_side: str = "BOTH"
    ) -> Optional[Dict]:
        """
        Execute OCO order with take-profit and stop-loss
        
        Note: Binance Futures doesn't support native OCO, so we simulate it
        by placing both orders and monitoring them.
        
        Args:
            symbol: Trading pair (e.g., BTCUSDT)
            side: BUY or SELL (exit direction)
            quantity: Order quantity
            take_profit_price: Take profit limit price
            stop_loss_price: Stop loss trigger price
            stop_limit_price: Stop limit price (defaults to stop_loss_price if None)
            reduce_only: If True, orders will only reduce position
            position_side: BOTH, LONG, or SHORT
        
        Returns:
            Dictionary with take_profit and stop_loss order responses
        """
        try:
            # Validate inputs
            symbol = validate_symbol(symbol)
            side = validate_side(side)
            quantity = validate_quantity(quantity, symbol)
            take_profit_price = validate_price(take_profit_price, symbol)
            stop_loss_price = validate_price(stop_loss_price, symbol)
            
            if stop_limit_price is None:
                stop_limit_price = stop_loss_price
            else:
                stop_limit_price = validate_price(stop_limit_price, symbol)
            
            logger.info(f"Placing OCO orders: {side} {quantity} {symbol}")
            logger.info(f"Take Profit: {take_profit_price} | Stop Loss: {stop_loss_price}")
            
            # Get current price for validation
            current_price = self.client.get_current_price(symbol)
            if current_price:
                logger.info(f"Current price: {current_price}")
                
                # Validate OCO logic
                if side == "SELL":
                    # For closing long position
                    if take_profit_price <= current_price:
                        logger.warning("⚠️  Take profit should be above current price for SELL")
                    if stop_loss_price >= current_price:
                        logger.warning("⚠️  Stop loss should be below current price for SELL")
                else:  # BUY
                    # For closing short position
                    if take_profit_price >= current_price:
                        logger.warning("⚠️  Take profit should be below current price for BUY")
                    if stop_loss_price <= current_price:
                        logger.warning("⚠️  Stop loss should be above current price for BUY")
            
            # Place take profit order (limit order)
            logger.info("Placing take profit order...")
            tp_params = {
                'symbol': symbol,
                'side': side,
                'type': 'LIMIT',
                'quantity': quantity,
                'price': take_profit_price,
                'timeInForce': 'GTC',
                'positionSide': position_side,
            }
            
            if reduce_only:
                tp_params['reduceOnly'] = 'true'
            
            tp_order = self.client.client.futures_create_order(**tp_params)
            logger.info(f"✓ Take profit order placed: {tp_order['orderId']}")
            
            # Small delay to ensure orders don't conflict
            time.sleep(0.2)
            
            # Place stop loss order (stop market)
            logger.info("Placing stop loss order...")
            sl_params = {
                'symbol': symbol,
                'side': side,
                'type': 'STOP_MARKET',
                'quantity': quantity,
                'stopPrice': stop_loss_price,
                'positionSide': position_side,
            }
            
            if reduce_only:
                sl_params['reduceOnly'] = 'true'
            
            sl_order = self.client.client.futures_create_order(**sl_params)
            logger.info(f"✓ Stop loss order placed: {sl_order['orderId']}")
            
            # Track OCO group
            oco_group = {
                'symbol': symbol,
                'tp_order_id': tp_order['orderId'],
                'sl_order_id': sl_order['orderId'],
                'timestamp': time.time()
            }
            self.active_oco_groups.append(oco_group)
            
            # Log successful trades
            log_trade(
                logger,
                order_type='OCO_TAKE_PROFIT',
                symbol=symbol,
                side=side,
                quantity=quantity,
                price=take_profit_price,
                order_id=tp_order['orderId']
            )
            
            log_trade(
                logger,
                order_type='OCO_STOP_LOSS',
                symbol=symbol,
                side=side,
                quantity=quantity,
                stop_price=stop_loss_price,
                order_id=sl_order['orderId']
            )
            
            # Display summary
            self._display_oco_summary(tp_order, sl_order)
            
            result = {
                'take_profit': tp_order,
                'stop_loss': sl_order,
                'oco_group_id': len(self.active_oco_groups) - 1
            }
            
            logger.info("✓ OCO orders placed successfully")
            logger.warning("⚠️  Note: Monitor orders to cancel the other when one executes")
            
            return result
            
        except BinanceAPIException as e:
            logger.error(f"Binance API Error: {e.message} (Code: {e.code})")
            
            # If take profit was placed but stop loss failed, cancel take profit
            if 'tp_order' in locals():
                logger.warning("Cancelling take profit order due to stop loss failure...")
                self.client.cancel_order(symbol, tp_order['orderId'])
            
            return None
            
        except Exception as e:
            log_error(logger, e, "OCO order execution failed")
            return None
    
    def monitor_and_cancel_oco(self, symbol: str, check_interval: int = 5):
        """
        Monitor OCO orders and cancel the opposite order when one fills
        
        Args:
            symbol: Trading pair to monitor
            check_interval: Check interval in seconds
        """
        try:
            symbol = validate_symbol(symbol)
            
            logger.info(f"Monitoring OCO orders for {symbol}...")
            logger.info(f"Press Ctrl+C to stop monitoring")
            
            while self.active_oco_groups:
                for oco_group in self.active_oco_groups[:]:  # Copy to iterate safely
                    if oco_group['symbol'] != symbol:
                        continue
                    
                    # Check order status
                    orders = self.client.get_open_orders(symbol)
                    tp_exists = any(o['orderId'] == oco_group['tp_order_id'] for o in orders)
                    sl_exists = any(o['orderId'] == oco_group['sl_order_id'] for o in orders)
                    
                    # If take profit filled, cancel stop loss
                    if not tp_exists and sl_exists:
                        logger.info(f"✓ Take profit executed! Cancelling stop loss...")
                        self.client.cancel_order(symbol, oco_group['sl_order_id'])
                        self.active_oco_groups.remove(oco_group)
                        logger.info("OCO group resolved")
                    
                    # If stop loss filled, cancel take profit
                    elif not sl_exists and tp_exists:
                        logger.info(f"🛑 Stop loss executed! Cancelling take profit...")
                        self.client.cancel_order(symbol, oco_group['tp_order_id'])
                        self.active_oco_groups.remove(oco_group)
                        logger.info("OCO group resolved")
                    
                    # If both gone, remove from tracking
                    elif not tp_exists and not sl_exists:
                        self.active_oco_groups.remove(oco_group)
                        logger.info("OCO group completed")
                
                time.sleep(check_interval)
            
            logger.info("No more active OCO groups to monitor")
            
        except KeyboardInterrupt:
            logger.info("\n⚠️  Monitoring stopped by user")
        except Exception as e:
            log_error(logger, e, "OCO monitoring failed")
    
    def _display_oco_summary(self, tp_order: Dict, sl_order: Dict):
        """Display formatted OCO order summary"""
        from tabulate import tabulate
        
        summary_data = [
            ["Type", "Order ID", "Price", "Status"],
            [
                "Take Profit",
                tp_order['orderId'],
                tp_order.get('price', 'N/A'),
                tp_order['status']
            ],
            [
                "Stop Loss",
                sl_order['orderId'],
                sl_order.get('stopPrice', 'N/A'),
                sl_order['status']
            ]
        ]
        
        print("\n" + "="*60)
        print("⚖️  OCO ORDER SUMMARY")
        print("="*60)
        print(tabulate(summary_data, headers="firstrow", tablefmt="simple"))
        print("="*60)
        print("💡 Tip: When one order fills, manually cancel the other")
        print("    or use the monitor function to automate this.")
        print("="*60 + "\n")
    
    def execute_oco_for_position(
        self,
        symbol: str,
        take_profit_percentage: float,
        stop_loss_percentage: float,
        position_side: str = "BOTH"
    ) -> Optional[Dict]:
        """
        Execute OCO for an existing position based on percentages
        
        Args:
            symbol: Trading pair
            take_profit_percentage: Take profit % from entry (e.g., 5.0 for 5%)
            stop_loss_percentage: Stop loss % from entry (e.g., 2.0 for 2%)
            position_side: BOTH, LONG, or SHORT
        
        Returns:
            OCO order result or None
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
                logger.error(f"No open position found for {symbol}")
                return None
            
            position_amt = float(position['positionAmt'])
            if position_amt == 0:
                logger.error("Position size is zero")
                return None
            
            entry_price = float(position['entryPrice'])
            quantity = abs(position_amt)
            
            # Determine position direction and exit side
            is_long = position_amt > 0
            exit_side = 'SELL' if is_long else 'BUY'
            
            # Calculate prices
            if is_long:
                tp_price = entry_price * (1 + take_profit_percentage / 100)
                sl_price = entry_price * (1 - stop_loss_percentage / 100)
            else:
                tp_price = entry_price * (1 - take_profit_percentage / 100)
                sl_price = entry_price * (1 + stop_loss_percentage / 100)
            
            logger.info(f"Position: {position_amt} @ {entry_price}")
            logger.info(f"Setting TP: {tp_price} (+{take_profit_percentage}%)")
            logger.info(f"Setting SL: {sl_price} (-{stop_loss_percentage}%)")
            
            return self.execute_oco_order(
                symbol=symbol,
                side=exit_side,
                quantity=quantity,
                take_profit_price=tp_price,
                stop_loss_price=sl_price,
                reduce_only=True,
                position_side=position_side
            )
            
        except Exception as e:
            log_error(logger, e, "Failed to set OCO for position")
            return None


def main():
    """CLI entry point for OCO orders"""
    if len(sys.argv) < 2:
        print("\n📖 OCO Orders Usage")
        print("\n1. Place OCO for exit:")
        print("   python src/advanced/oco.py <SYMBOL> <SIDE> <QTY> <TP_PRICE> <SL_PRICE>")
        print("   Example: python src/advanced/oco.py BTCUSDT SELL 0.01 98000 93000")
        print("\n2. Place OCO for existing position (percentage-based):")
        print("   python src/advanced/oco.py --position <SYMBOL> <TP_%> <SL_%>")
        print("   Example: python src/advanced/oco.py --position BTCUSDT 5.0 2.0")
        print("\n3. Monitor OCO orders:")
        print("   python src/advanced/oco.py --monitor <SYMBOL>")
        print("   Example: python src/advanced/oco.py --monitor BTCUSDT")
        print("\n")
        sys.exit(1)
    
    try:
        executor = OCOOrderExecutor()
        
        if '--position' in sys.argv:
            # OCO based on existing position
            idx = sys.argv.index('--position')
            symbol = sys.argv[idx + 1]
            tp_pct = float(sys.argv[idx + 2])
            sl_pct = float(sys.argv[idx + 3])
            
            result = executor.execute_oco_for_position(
                symbol=symbol,
                take_profit_percentage=tp_pct,
                stop_loss_percentage=sl_pct
            )
            
        elif '--monitor' in sys.argv:
            # Monitor OCO orders
            idx = sys.argv.index('--monitor')
            symbol = sys.argv[idx + 1]
            
            executor.monitor_and_cancel_oco(symbol)
            sys.exit(0)
            
        else:
            # Regular OCO order
            symbol = sys.argv[1]
            side = sys.argv[2]
            quantity = float(sys.argv[3])
            tp_price = float(sys.argv[4])
            sl_price = float(sys.argv[5])
            
            result = executor.execute_oco_order(
                symbol=symbol,
                side=side,
                quantity=quantity,
                take_profit_price=tp_price,
                stop_loss_price=sl_price,
                reduce_only='--reduce-only' in sys.argv
            )
        
        if result:
            logger.info("✓ OCO orders placed successfully")
            sys.exit(0)
        else:
            logger.error("✗ OCO order placement failed")
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
