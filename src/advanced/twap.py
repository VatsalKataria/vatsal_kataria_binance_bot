"""
TWAP (Time-Weighted Average Price) Module (Advanced)
Split large orders into smaller chunks executed over time
"""

import sys
import time
from typing import Optional, List, Dict
from datetime import datetime, timedelta

from src.utils.client import get_client
from src.utils.logger import setup_logger, log_trade, log_error
from src.utils.validators import (
    validate_symbol, validate_side, validate_quantity, 
    validate_positive_integer
)

logger = setup_logger("TWAP")


class TWAPExecutor:
    """Execute TWAP (Time-Weighted Average Price) orders"""
    
    def __init__(self, testnet: bool = None):
        """
        Initialize TWAP executor
        
        Args:
            testnet: Use testnet if True
        """
        self.client = get_client(testnet)
        self.execution_history = []
        logger.info("TWAP Executor initialized")
    
    def execute_twap(
        self,
        symbol: str,
        side: str,
        total_quantity: float,
        num_orders: int,
        time_interval_seconds: int,
        order_type: str = "MARKET",
        limit_price: float = None,
        randomize_timing: bool = False,
        randomize_quantity: bool = False
    ) -> List[Dict]:
        """
        Execute TWAP strategy
        
        Args:
            symbol: Trading pair (e.g., BTCUSDT)
            side: BUY or SELL
            total_quantity: Total quantity to execute
            num_orders: Number of orders to split into
            time_interval_seconds: Time between orders in seconds
            order_type: MARKET or LIMIT
            limit_price: Limit price (required if order_type is LIMIT)
            randomize_timing: Add random variance to intervals (±20%)
            randomize_quantity: Add random variance to order sizes (±10%)
        
        Returns:
            List of executed order responses
        """
        try:
            # Validate inputs
            symbol = validate_symbol(symbol)
            side = validate_side(side)
            total_quantity = validate_quantity(total_quantity, symbol)
            num_orders = validate_positive_integer(num_orders, "num_orders")
            time_interval_seconds = validate_positive_integer(
                time_interval_seconds, 
                "time_interval_seconds"
            )
            
            if num_orders > 100:
                raise ValueError("Maximum 100 orders allowed for TWAP")
            
            if order_type.upper() not in ['MARKET', 'LIMIT']:
                raise ValueError("order_type must be MARKET or LIMIT")
            
            order_type = order_type.upper()
            
            logger.info("="*60)
            logger.info("🕐 STARTING TWAP EXECUTION")
            logger.info("="*60)
            logger.info(f"Symbol: {symbol}")
            logger.info(f"Side: {side}")
            logger.info(f"Total Quantity: {total_quantity}")
            logger.info(f"Number of Orders: {num_orders}")
            logger.info(f"Time Interval: {time_interval_seconds}s")
            logger.info(f"Order Type: {order_type}")
            if limit_price:
                logger.info(f"Limit Price: {limit_price}")
            logger.info(f"Randomize Timing: {randomize_timing}")
            logger.info(f"Randomize Quantity: {randomize_quantity}")
            
            # Calculate total execution time
            total_time_seconds = (num_orders - 1) * time_interval_seconds
            end_time = datetime.now() + timedelta(seconds=total_time_seconds)
            logger.info(f"Estimated completion: {end_time.strftime('%H:%M:%S')}")
            logger.info("="*60 + "\n")
            
            # Calculate order sizes
            order_sizes = self._calculate_order_sizes(
                total_quantity, 
                num_orders, 
                randomize_quantity
            )
            
            executed_orders = []
            
            # Execute orders
            for i in range(num_orders):
                order_num = i + 1
                order_size = order_sizes[i]
                
                logger.info(f"[{order_num}/{num_orders}] Executing order: {order_size} {symbol}")
                
                try:
                    # Execute order based on type
                    if order_type == "MARKET":
                        order_result = self._execute_market_chunk(
                            symbol, side, order_size
                        )
                    else:  # LIMIT
                        # Update limit price based on current market
                        current_limit_price = self._get_adaptive_limit_price(
                            symbol, side, limit_price
                        )
                        order_result = self._execute_limit_chunk(
                            symbol, side, order_size, current_limit_price
                        )
                    
                    if order_result:
                        executed_orders.append(order_result)
                        self.execution_history.append({
                            'timestamp': datetime.now(),
                            'order_num': order_num,
                            'result': order_result
                        })
                        logger.info(f"✓ Order {order_num} executed successfully")
                    else:
                        logger.error(f"✗ Order {order_num} failed")
                
                except Exception as e:
                    log_error(logger, e, f"Order {order_num} execution error")
                
                # Wait before next order (except for last order)
                if i < num_orders - 1:
                    wait_time = self._calculate_wait_time(
                        time_interval_seconds, 
                        randomize_timing
                    )
                    logger.info(f"Waiting {wait_time}s until next order...\n")
                    time.sleep(wait_time)
            
            # Display execution summary
            self._display_execution_summary(executed_orders, total_quantity)
            
            return executed_orders
            
        except KeyboardInterrupt:
            logger.warning("\n⚠️  TWAP execution interrupted by user")
            logger.info(f"Executed {len(executed_orders)}/{num_orders} orders")
            return executed_orders
            
        except Exception as e:
            log_error(logger, e, "TWAP execution failed")
            return []
    
    def _calculate_order_sizes(
        self, 
        total_quantity: float, 
        num_orders: int, 
        randomize: bool
    ) -> List[float]:
        """Calculate individual order sizes"""
        import random
        
        if not randomize:
            # Equal distribution
            base_size = total_quantity / num_orders
            return [base_size] * num_orders
        
        # Random distribution with constraints
        sizes = []
        remaining = total_quantity
        
        for i in range(num_orders - 1):
            # Random size between 50% and 150% of average
            avg_remaining = remaining / (num_orders - i)
            min_size = avg_remaining * 0.5
            max_size = avg_remaining * 1.5
            
            order_size = random.uniform(min_size, max_size)
            order_size = min(order_size, remaining * 0.8)  # Don't use more than 80% in one order
            
            sizes.append(order_size)
            remaining -= order_size
        
        # Last order gets all remaining
        sizes.append(remaining)
        
        logger.debug(f"Order sizes calculated: {[f'{s:.6f}' for s in sizes]}")
        return sizes
    
    def _calculate_wait_time(self, base_interval: int, randomize: bool) -> int:
        """Calculate wait time with optional randomization"""
        import random
        
        if not randomize:
            return base_interval
        
        # Add ±20% variance
        variance = base_interval * 0.2
        wait_time = base_interval + random.uniform(-variance, variance)
        
        return max(1, int(wait_time))  # Minimum 1 second
    
    def _get_adaptive_limit_price(
        self, 
        symbol: str, 
        side: str, 
        base_limit_price: float
    ) -> float:
        """
        Get adaptive limit price based on current market
        Updates limit price to stay competitive
        """
        current_price = self.client.get_current_price(symbol)
        
        if not current_price:
            return base_limit_price
        
        # Adjust limit price to be slightly better than market
        if side == "BUY":
            # For buy, place slightly above market to increase fill probability
            adaptive_price = current_price * 1.001  # 0.1% above market
            return min(adaptive_price, base_limit_price)
        else:  # SELL
            # For sell, place slightly below market
            adaptive_price = current_price * 0.999  # 0.1% below market
            return max(adaptive_price, base_limit_price)
    
    def _execute_market_chunk(
        self, 
        symbol: str, 
        side: str, 
        quantity: float
    ) -> Optional[Dict]:
        """Execute a single market order chunk"""
        from src.core.market_orders import MarketOrderExecutor
        
        executor = MarketOrderExecutor(testnet=self.client.testnet)
        return executor.execute_market_order(symbol, side, quantity)
    
    def _execute_limit_chunk(
        self, 
        symbol: str, 
        side: str, 
        quantity: float, 
        price: float
    ) -> Optional[Dict]:
        """Execute a single limit order chunk"""
        from src.core.limit_orders import LimitOrderExecutor
        
        executor = LimitOrderExecutor(testnet=self.client.testnet)
        return executor.execute_limit_order(
            symbol, side, quantity, price, time_in_force="IOC"  # Immediate or Cancel
        )
    
    def _display_execution_summary(self, orders: List[Dict], total_quantity: float):
        """Display TWAP execution summary"""
        from tabulate import tabulate
        
        if not orders:
            logger.warning("No orders executed")
            return
        
        executed_qty = sum(float(o.get('executedQty', 0)) for o in orders)
        avg_price = sum(
            float(o.get('avgPrice', 0)) * float(o.get('executedQty', 0)) 
            for o in orders
        ) / executed_qty if executed_qty > 0 else 0
        
        print("\n" + "="*60)
        print("📊 TWAP EXECUTION SUMMARY")
        print("="*60)
        print(f"Total Orders Placed: {len(orders)}")
        print(f"Target Quantity: {total_quantity}")
        print(f"Executed Quantity: {executed_qty}")
        print(f"Fill Rate: {(executed_qty/total_quantity)*100:.2f}%")
        print(f"Average Price: {avg_price}")
        print("="*60)
        
        # Detail table
        detail_data = []
        for i, order in enumerate(orders, 1):
            detail_data.append([
                i,
                order.get('orderId', 'N/A'),
                order.get('executedQty', 'N/A'),
                order.get('avgPrice', 'N/A'),
                order.get('status', 'N/A')
            ])
        
        print("\nOrder Details:")
        print(tabulate(
            detail_data,
            headers=['#', 'Order ID', 'Quantity', 'Avg Price', 'Status'],
            tablefmt='simple'
        ))
        print("="*60 + "\n")


def main():
    """CLI entry point for TWAP execution"""
    if len(sys.argv) < 6:
        print("\n📖 TWAP Usage")
        print("\npython src/advanced/twap.py <SYMBOL> <SIDE> <TOTAL_QTY> <NUM_ORDERS> <INTERVAL_SEC> [OPTIONS]")
        print("\nExamples:")
        print("  # Execute 0.1 BTC over 10 orders, 60s apart")
        print("  python src/advanced/twap.py BTCUSDT BUY 0.1 10 60")
        print("\n  # With randomization for stealth")
        print("  python src/advanced/twap.py BTCUSDT BUY 0.1 10 60 --randomize")
        print("\n  # Using limit orders")
        print("  python src/advanced/twap.py BTCUSDT BUY 0.1 10 60 --limit 95000")
        print("\nArguments:")
        print("  SYMBOL          - Trading pair (e.g., BTCUSDT)")
        print("  SIDE            - BUY or SELL")
        print("  TOTAL_QTY       - Total quantity to execute")
        print("  NUM_ORDERS      - Number of orders to split into")
        print("  INTERVAL_SEC    - Seconds between orders")
        print("\nOptions:")
        print("  --limit <PRICE>     - Use limit orders at specified price")
        print("  --randomize         - Randomize timing and quantities")
        print("  --randomize-time    - Only randomize timing")
        print("  --randomize-qty     - Only randomize quantities")
        print("\n")
        sys.exit(1)
    
    symbol = sys.argv[1]
    side = sys.argv[2]
    total_quantity = float(sys.argv[3])
    num_orders = int(sys.argv[4])
    interval_seconds = int(sys.argv[5])
    
    # Parse options
    order_type = "MARKET"
    limit_price = None
    randomize_timing = False
    randomize_quantity = False
    
    if '--limit' in sys.argv:
        order_type = "LIMIT"
        limit_idx = sys.argv.index('--limit')
        if limit_idx + 1 < len(sys.argv):
            limit_price = float(sys.argv[limit_idx + 1])
    
    if '--randomize' in sys.argv:
        randomize_timing = True
        randomize_quantity = True
    else:
        if '--randomize-time' in sys.argv:
            randomize_timing = True
        if '--randomize-qty' in sys.argv:
            randomize_quantity = True
    
    try:
        executor = TWAPExecutor()
        
        # Confirm execution
        print("\n⚠️  TWAP Execution Plan:")
        print(f"   Symbol: {symbol}")
        print(f"   Side: {side}")
        print(f"   Total Quantity: {total_quantity}")
        print(f"   Number of Orders: {num_orders}")
        print(f"   Time Interval: {interval_seconds}s")
        print(f"   Order Type: {order_type}")
        if limit_price:
            print(f"   Limit Price: {limit_price}")
        print(f"   Total Time: ~{(num_orders-1)*interval_seconds}s ({((num_orders-1)*interval_seconds)/60:.1f} minutes)")
        
        response = input("\nProceed with execution? (yes/no): ")
        if response.lower() not in ['yes', 'y']:
            logger.info("Execution cancelled by user")
            sys.exit(0)
        
        print()  # Blank line
        
        executed_orders = executor.execute_twap(
            symbol=symbol,
            side=side,
            total_quantity=total_quantity,
            num_orders=num_orders,
            time_interval_seconds=interval_seconds,
            order_type=order_type,
            limit_price=limit_price,
            randomize_timing=randomize_timing,
            randomize_quantity=randomize_quantity
        )
        
        if executed_orders:
            logger.info("✓ TWAP execution completed")
            sys.exit(0)
        else:
            logger.error("✗ TWAP execution failed")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.warning("\n⚠️  Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        log_error(logger, e, "Unexpected error")
        sys.exit(1)


if __name__ == "__main__":
    main()
