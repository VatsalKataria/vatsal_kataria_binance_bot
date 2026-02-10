"""
Grid Trading Strategy Module (Advanced)
Automated buy-low/sell-high within a price range
"""

import sys
import time
from typing import Optional, List, Dict, Tuple
from datetime import datetime

from src.utils.client import get_client
from src.utils.logger import setup_logger, log_trade, log_error
from src.utils.validators import (
    validate_symbol, validate_quantity, validate_price_range,
    validate_positive_integer
)

logger = setup_logger("GridTrading")


class GridTradingBot:
    """Automated grid trading bot"""
    
    def __init__(self, testnet: bool = None):
        """
        Initialize grid trading bot
        
        Args:
            testnet: Use testnet if True
        """
        self.client = get_client(testnet)
        self.active_grids = []
        self.grid_orders = []
        logger.info("Grid Trading Bot initialized")
    
    def create_grid(
        self,
        symbol: str,
        lower_price: float,
        upper_price: float,
        num_grids: int,
        quantity_per_grid: float,
        initial_investment: float = None,
        auto_rebalance: bool = True
    ) -> Optional[Dict]:
        """
        Create a grid trading setup
        
        Args:
            symbol: Trading pair (e.g., BTCUSDT)
            lower_price: Lower bound of grid
            upper_price: Upper bound of grid
            num_grids: Number of grid levels
            quantity_per_grid: Quantity for each grid order
            initial_investment: Initial capital (auto-calculated if None)
            auto_rebalance: Automatically place opposite orders when filled
        
        Returns:
            Grid configuration dictionary or None
        """
        try:
            # Validate inputs
            symbol = validate_symbol(symbol)
            current_price = self.client.get_current_price(symbol)
            
            if not current_price:
                logger.error("Failed to get current price")
                return None
            
            lower_price, upper_price = validate_price_range(
                lower_price, upper_price, current_price
            )
            
            num_grids = validate_positive_integer(num_grids, "num_grids")
            quantity_per_grid = validate_quantity(quantity_per_grid, symbol)
            
            if num_grids < 2:
                raise ValueError("Number of grids must be at least 2")
            if num_grids > 50:
                raise ValueError("Number of grids limited to 50")
            
            logger.info("="*60)
            logger.info("📊 GRID TRADING SETUP")
            logger.info("="*60)
            logger.info(f"Symbol: {symbol}")
            logger.info(f"Current Price: {current_price}")
            logger.info(f"Price Range: {lower_price} - {upper_price}")
            logger.info(f"Number of Grids: {num_grids}")
            logger.info(f"Quantity per Grid: {quantity_per_grid}")
            logger.info("="*60 + "\n")
            
            # Calculate grid levels
            grid_levels = self._calculate_grid_levels(
                lower_price, upper_price, num_grids
            )
            
            logger.info(f"Grid levels: {[f'{p:.2f}' for p in grid_levels]}")
            
            # Calculate required capital
            if initial_investment is None:
                initial_investment = self._calculate_required_capital(
                    grid_levels, quantity_per_grid, current_price
                )
                logger.info(f"Estimated capital required: {initial_investment:.2f} USDT")
            
            # Place initial grid orders
            logger.info("\nPlacing initial grid orders...")
            buy_orders, sell_orders = self._place_initial_orders(
                symbol, grid_levels, quantity_per_grid, current_price
            )
            
            # Create grid configuration
            grid_config = {
                'symbol': symbol,
                'lower_price': lower_price,
                'upper_price': upper_price,
                'num_grids': num_grids,
                'quantity_per_grid': quantity_per_grid,
                'grid_levels': grid_levels,
                'current_price': current_price,
                'buy_orders': buy_orders,
                'sell_orders': sell_orders,
                'auto_rebalance': auto_rebalance,
                'created_at': datetime.now(),
                'total_profit': 0.0,
                'trades_executed': 0
            }
            
            self.active_grids.append(grid_config)
            
            # Display grid summary
            self._display_grid_summary(grid_config)
            
            logger.info("✓ Grid trading setup completed")
            
            return grid_config
            
        except Exception as e:
            log_error(logger, e, "Grid creation failed")
            return None
    
    def _calculate_grid_levels(
        self, 
        lower_price: float, 
        upper_price: float, 
        num_grids: int
    ) -> List[float]:
        """Calculate grid price levels"""
        step = (upper_price - lower_price) / (num_grids - 1)
        levels = [lower_price + (step * i) for i in range(num_grids)]
        return levels
    
    def _calculate_required_capital(
        self,
        grid_levels: List[float],
        quantity_per_grid: float,
        current_price: float
    ) -> float:
        """Estimate required capital for grid"""
        # Calculate capital needed for buy orders below current price
        buy_levels = [p for p in grid_levels if p < current_price]
        buy_capital = sum(p * quantity_per_grid for p in buy_levels)
        
        # Calculate capital needed to hold inventory for sell orders
        sell_levels = [p for p in grid_levels if p >= current_price]
        sell_capital = len(sell_levels) * quantity_per_grid * current_price
        
        total_capital = buy_capital + sell_capital
        
        # Add 20% buffer
        return total_capital * 1.2
    
    def _place_initial_orders(
        self,
        symbol: str,
        grid_levels: List[float],
        quantity: float,
        current_price: float
    ) -> Tuple[List[Dict], List[Dict]]:
        """Place initial buy and sell orders"""
        from src.core.limit_orders import LimitOrderExecutor
        
        executor = LimitOrderExecutor(testnet=self.client.testnet)
        buy_orders = []
        sell_orders = []
        
        for level in grid_levels:
            try:
                if level < current_price:
                    # Place buy order
                    logger.info(f"Placing BUY order at {level}")
                    order = executor.execute_limit_order(
                        symbol=symbol,
                        side='BUY',
                        quantity=quantity,
                        price=level,
                        post_only=True  # Ensure maker order
                    )
                    if order:
                        buy_orders.append(order)
                        time.sleep(0.2)  # Rate limiting
                
                elif level > current_price:
                    # Place sell order
                    logger.info(f"Placing SELL order at {level}")
                    order = executor.execute_limit_order(
                        symbol=symbol,
                        side='SELL',
                        quantity=quantity,
                        price=level,
                        post_only=True
                    )
                    if order:
                        sell_orders.append(order)
                        time.sleep(0.2)
                
            except Exception as e:
                log_error(logger, e, f"Failed to place order at {level}")
        
        logger.info(f"\n✓ Placed {len(buy_orders)} BUY orders")
        logger.info(f"✓ Placed {len(sell_orders)} SELL orders")
        
        return buy_orders, sell_orders
    
    def monitor_grid(
        self, 
        symbol: str, 
        check_interval: int = 10,
        max_runtime_hours: float = None
    ):
        """
        Monitor and maintain grid trading
        
        Args:
            symbol: Trading pair to monitor
            check_interval: Check interval in seconds
            max_runtime_hours: Maximum runtime in hours (None for infinite)
        """
        try:
            symbol = validate_symbol(symbol)
            
            # Find active grid for this symbol
            grid_config = None
            for grid in self.active_grids:
                if grid['symbol'] == symbol:
                    grid_config = grid
                    break
            
            if not grid_config:
                logger.error(f"No active grid found for {symbol}")
                return
            
            logger.info("="*60)
            logger.info("🤖 GRID MONITORING STARTED")
            logger.info("="*60)
            logger.info(f"Symbol: {symbol}")
            logger.info(f"Check Interval: {check_interval}s")
            if max_runtime_hours:
                logger.info(f"Max Runtime: {max_runtime_hours} hours")
            logger.info("Press Ctrl+C to stop")
            logger.info("="*60 + "\n")
            
            start_time = datetime.now()
            iteration = 0
            
            while True:
                iteration += 1
                logger.info(f"[Iteration {iteration}] Checking grid status...")
                
                # Check if max runtime exceeded
                if max_runtime_hours:
                    elapsed_hours = (datetime.now() - start_time).total_seconds() / 3600
                    if elapsed_hours >= max_runtime_hours:
                        logger.info(f"Max runtime of {max_runtime_hours} hours reached")
                        break
                
                # Get current open orders
                open_orders = self.client.get_open_orders(symbol)
                open_order_ids = {o['orderId'] for o in open_orders}
                
                # Check for filled orders and rebalance
                self._check_and_rebalance(grid_config, open_order_ids)
                
                # Display status
                self._display_grid_status(grid_config)
                
                # Wait before next check
                time.sleep(check_interval)
            
            logger.info("Grid monitoring stopped")
            
        except KeyboardInterrupt:
            logger.info("\n⚠️  Grid monitoring stopped by user")
            self._display_final_stats(grid_config)
            
        except Exception as e:
            log_error(logger, e, "Grid monitoring failed")
    
    def _check_and_rebalance(self, grid_config: Dict, open_order_ids: set):
        """Check for filled orders and place new opposite orders"""
        from src.core.limit_orders import LimitOrderExecutor
        
        if not grid_config.get('auto_rebalance'):
            return
        
        executor = LimitOrderExecutor(testnet=self.client.testnet)
        symbol = grid_config['symbol']
        quantity = grid_config['quantity_per_grid']
        grid_levels = grid_config['grid_levels']
        
        # Check buy orders
        for order in grid_config['buy_orders'][:]:
            order_id = order['orderId']
            
            if order_id not in open_order_ids:
                # Order was filled
                filled_price = float(order['price'])
                logger.info(f"✓ BUY order filled at {filled_price}")
                
                # Find next higher grid level for sell order
                next_sell_level = None
                for level in grid_levels:
                    if level > filled_price:
                        next_sell_level = level
                        break
                
                if next_sell_level:
                    logger.info(f"Placing SELL order at {next_sell_level}")
                    new_order = executor.execute_limit_order(
                        symbol=symbol,
                        side='SELL',
                        quantity=quantity,
                        price=next_sell_level,
                        post_only=True
                    )
                    
                    if new_order:
                        grid_config['sell_orders'].append(new_order)
                        
                        # Calculate profit
                        profit = (next_sell_level - filled_price) * quantity
                        grid_config['total_profit'] += profit
                        grid_config['trades_executed'] += 1
                        
                        logger.info(f"💰 Estimated profit: {profit:.2f} USDT")
                
                # Remove filled order from tracking
                grid_config['buy_orders'].remove(order)
        
        # Check sell orders
        for order in grid_config['sell_orders'][:]:
            order_id = order['orderId']
            
            if order_id not in open_order_ids:
                # Order was filled
                filled_price = float(order['price'])
                logger.info(f"✓ SELL order filled at {filled_price}")
                
                # Find next lower grid level for buy order
                next_buy_level = None
                for level in reversed(grid_levels):
                    if level < filled_price:
                        next_buy_level = level
                        break
                
                if next_buy_level:
                    logger.info(f"Placing BUY order at {next_buy_level}")
                    new_order = executor.execute_limit_order(
                        symbol=symbol,
                        side='BUY',
                        quantity=quantity,
                        price=next_buy_level,
                        post_only=True
                    )
                    
                    if new_order:
                        grid_config['buy_orders'].append(new_order)
                        grid_config['trades_executed'] += 1
                
                # Remove filled order from tracking
                grid_config['sell_orders'].remove(order)
    
    def _display_grid_summary(self, grid_config: Dict):
        """Display grid configuration summary"""
        from tabulate import tabulate
        
        print("\n" + "="*60)
        print("📊 GRID CONFIGURATION")
        print("="*60)
        
        config_data = [
            ["Symbol", grid_config['symbol']],
            ["Price Range", f"{grid_config['lower_price']} - {grid_config['upper_price']}"],
            ["Current Price", grid_config['current_price']],
            ["Grid Levels", grid_config['num_grids']],
            ["Quantity/Grid", grid_config['quantity_per_grid']],
            ["Buy Orders Placed", len(grid_config['buy_orders'])],
            ["Sell Orders Placed", len(grid_config['sell_orders'])],
            ["Auto-Rebalance", "Enabled" if grid_config['auto_rebalance'] else "Disabled"],
        ]
        
        print(tabulate(config_data, tablefmt="simple"))
        print("="*60 + "\n")
    
    def _display_grid_status(self, grid_config: Dict):
        """Display current grid status"""
        print(f"\n--- Grid Status ({datetime.now().strftime('%H:%M:%S')}) ---")
        print(f"Active BUY orders: {len(grid_config['buy_orders'])}")
        print(f"Active SELL orders: {len(grid_config['sell_orders'])}")
        print(f"Total trades: {grid_config['trades_executed']}")
        print(f"Estimated profit: {grid_config['total_profit']:.2f} USDT")
        print("-" * 40)
    
    def _display_final_stats(self, grid_config: Dict):
        """Display final statistics"""
        from tabulate import tabulate
        
        runtime = datetime.now() - grid_config['created_at']
        
        print("\n" + "="*60)
        print("📈 GRID TRADING FINAL STATISTICS")
        print("="*60)
        
        stats = [
            ["Total Runtime", str(runtime).split('.')[0]],
            ["Total Trades", grid_config['trades_executed']],
            ["Estimated Profit", f"{grid_config['total_profit']:.2f} USDT"],
            ["Active BUY Orders", len(grid_config['buy_orders'])],
            ["Active SELL Orders", len(grid_config['sell_orders'])],
        ]
        
        print(tabulate(stats, tablefmt="simple"))
        print("="*60 + "\n")
    
    def stop_grid(self, symbol: str) -> bool:
        """
        Stop grid trading and cancel all orders
        
        Args:
            symbol: Trading pair
        
        Returns:
            True if successful
        """
        try:
            symbol = validate_symbol(symbol)
            
            logger.info(f"Stopping grid for {symbol}...")
            
            # Cancel all open orders
            result = self.client.cancel_all_orders(symbol)
            
            # Remove from active grids
            self.active_grids = [g for g in self.active_grids if g['symbol'] != symbol]
            
            logger.info("✓ Grid stopped and all orders cancelled")
            return True
            
        except Exception as e:
            log_error(logger, e, "Failed to stop grid")
            return False


def main():
    """CLI entry point for grid trading"""
    if len(sys.argv) < 2:
        print("\n📖 Grid Trading Usage")
        print("\n1. Create Grid:")
        print("   python src/advanced/grid.py create <SYMBOL> <LOWER> <UPPER> <GRIDS> <QTY>")
        print("   Example: python src/advanced/grid.py create BTCUSDT 90000 100000 10 0.001")
        print("\n2. Monitor Grid:")
        print("   python src/advanced/grid.py monitor <SYMBOL> [--interval SECONDS]")
        print("   Example: python src/advanced/grid.py monitor BTCUSDT --interval 30")
        print("\n3. Stop Grid:")
        print("   python src/advanced/grid.py stop <SYMBOL>")
        print("   Example: python src/advanced/grid.py stop BTCUSDT")
        print("\n")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    try:
        bot = GridTradingBot()
        
        if command == "create":
            if len(sys.argv) < 7:
                print("Error: Insufficient arguments for create command")
                sys.exit(1)
            
            symbol = sys.argv[2]
            lower_price = float(sys.argv[3])
            upper_price = float(sys.argv[4])
            num_grids = int(sys.argv[5])
            quantity = float(sys.argv[6])
            
            grid_config = bot.create_grid(
                symbol=symbol,
                lower_price=lower_price,
                upper_price=upper_price,
                num_grids=num_grids,
                quantity_per_grid=quantity
            )
            
            if grid_config:
                # Ask if user wants to start monitoring
                response = input("\nStart monitoring this grid? (yes/no): ")
                if response.lower() in ['yes', 'y']:
                    bot.monitor_grid(symbol)
            
        elif command == "monitor":
            if len(sys.argv) < 3:
                print("Error: Symbol required for monitor command")
                sys.exit(1)
            
            symbol = sys.argv[2]
            interval = 10
            
            if '--interval' in sys.argv:
                idx = sys.argv.index('--interval')
                if idx + 1 < len(sys.argv):
                    interval = int(sys.argv[idx + 1])
            
            bot.monitor_grid(symbol, check_interval=interval)
            
        elif command == "stop":
            if len(sys.argv) < 3:
                print("Error: Symbol required for stop command")
                sys.exit(1)
            
            symbol = sys.argv[2]
            bot.stop_grid(symbol)
            
        else:
            print(f"Unknown command: {command}")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.warning("\n⚠️  Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        log_error(logger, e, "Unexpected error")
        sys.exit(1)


if __name__ == "__main__":
    main()
