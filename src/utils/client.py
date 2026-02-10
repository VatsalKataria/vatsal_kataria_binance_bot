"""
Binance Futures API Client Wrapper
Handles connection, authentication, and common API operations
"""

import os
from typing import Dict, Optional, List
from binance.client import Client
from binance.exceptions import BinanceAPIException, BinanceRequestException
from dotenv import load_dotenv

from src.utils.logger import setup_logger, log_error
from src.utils.validators import validate_symbol, validate_leverage

# Load environment variables
load_dotenv()

logger = setup_logger("BinanceClient")


class BinanceFuturesClient:
    """Wrapper for Binance Futures API client with error handling"""
    
    def __init__(self, testnet: bool = True):
        """
        Initialize Binance Futures client
        
        Args:
            testnet: Use testnet if True, live trading if False
        """
        self.testnet = testnet
        self.client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize Binance client with API credentials"""
        try:
            if self.testnet:
                api_key = os.getenv('TESTNET_API_KEY')
                api_secret = os.getenv('TESTNET_API_SECRET')
                base_url = 'https://testnet.binancefuture.com'
                
                if not api_key or not api_secret:
                    raise ValueError(
                        "Testnet API credentials not found. "
                        "Please set TESTNET_API_KEY and TESTNET_API_SECRET in .env file"
                    )
                
                logger.info("Initializing Binance TESTNET Futures client")
                logger.warning("⚠️  TESTNET MODE - No real funds will be used")
                
            else:
                api_key = os.getenv('BINANCE_API_KEY')
                api_secret = os.getenv('BINANCE_API_SECRET')
                base_url = None  # Use default
                
                if not api_key or not api_secret:
                    raise ValueError(
                        "Binance API credentials not found. "
                        "Please set BINANCE_API_KEY and BINANCE_API_SECRET in .env file"
                    )
                
                logger.warning("🚨 LIVE TRADING MODE - REAL FUNDS AT RISK 🚨")
            
            self.client = Client(api_key, api_secret, testnet=self.testnet)
            
            if self.testnet and base_url:
                self.client.API_URL = base_url
            
            # Test connection
            self._test_connection()
            
            logger.info("✓ Binance Futures client initialized successfully")
            
        except Exception as e:
            log_error(logger, e, "Failed to initialize Binance client")
            raise
    
    def _test_connection(self):
        """Test API connection and permissions"""
        try:
            # Test connectivity
            self.client.futures_ping()
            
            # Get account info to verify API key permissions
            account = self.client.futures_account()
            
            logger.info(f"Account Balance: {account.get('totalWalletBalance', 'N/A')} USDT")
            logger.debug(f"Account permissions verified")
            
        except BinanceAPIException as e:
            logger.error(f"Binance API Error: {e.message} (Code: {e.code})")
            raise
        except Exception as e:
            log_error(logger, e, "Connection test failed")
            raise
    
    def get_symbol_info(self, symbol: str) -> Optional[Dict]:
        """
        Get symbol trading info and filters
        
        Args:
            symbol: Trading pair symbol
        
        Returns:
            Symbol information dictionary or None
        """
        try:
            symbol = validate_symbol(symbol)
            exchange_info = self.client.futures_exchange_info()
            
            for s in exchange_info['symbols']:
                if s['symbol'] == symbol:
                    logger.debug(f"Symbol info retrieved for {symbol}")
                    return s
            
            logger.warning(f"Symbol {symbol} not found")
            return None
            
        except Exception as e:
            log_error(logger, e, f"Failed to get symbol info for {symbol}")
            return None
    
    def get_current_price(self, symbol: str) -> Optional[float]:
        """
        Get current market price for symbol
        
        Args:
            symbol: Trading pair symbol
        
        Returns:
            Current price or None
        """
        try:
            symbol = validate_symbol(symbol)
            ticker = self.client.futures_symbol_ticker(symbol=symbol)
            price = float(ticker['price'])
            
            logger.debug(f"Current price for {symbol}: {price}")
            return price
            
        except Exception as e:
            log_error(logger, e, f"Failed to get price for {symbol}")
            return None
    
    def get_account_balance(self) -> Optional[Dict]:
        """
        Get futures account balance
        
        Returns:
            Account balance information or None
        """
        try:
            account = self.client.futures_account()
            balance_info = {
                'totalWalletBalance': float(account['totalWalletBalance']),
                'availableBalance': float(account['availableBalance']),
                'totalUnrealizedProfit': float(account['totalUnrealizedProfit']),
            }
            
            logger.debug(f"Account balance: {balance_info}")
            return balance_info
            
        except Exception as e:
            log_error(logger, e, "Failed to get account balance")
            return None
    
    def set_leverage(self, symbol: str, leverage: int) -> bool:
        """
        Set leverage for a symbol
        
        Args:
            symbol: Trading pair symbol
            leverage: Leverage multiplier (1-125)
        
        Returns:
            True if successful, False otherwise
        """
        try:
            symbol = validate_symbol(symbol)
            leverage = validate_leverage(leverage)
            
            result = self.client.futures_change_leverage(
                symbol=symbol,
                leverage=leverage
            )
            
            logger.info(f"Leverage set to {leverage}x for {symbol}")
            logger.debug(f"Leverage response: {result}")
            return True
            
        except BinanceAPIException as e:
            logger.error(f"Failed to set leverage: {e.message} (Code: {e.code})")
            return False
        except Exception as e:
            log_error(logger, e, f"Failed to set leverage for {symbol}")
            return False
    
    def get_open_positions(self) -> List[Dict]:
        """
        Get all open positions
        
        Returns:
            List of open positions
        """
        try:
            positions = self.client.futures_position_information()
            
            # Filter only positions with non-zero quantity
            open_positions = [
                pos for pos in positions 
                if float(pos.get('positionAmt', 0)) != 0
            ]
            
            logger.debug(f"Found {len(open_positions)} open positions")
            return open_positions
            
        except Exception as e:
            log_error(logger, e, "Failed to get open positions")
            return []
    
    def get_open_orders(self, symbol: str = None) -> List[Dict]:
        """
        Get all open orders
        
        Args:
            symbol: Filter by symbol (optional)
        
        Returns:
            List of open orders
        """
        try:
            params = {}
            if symbol:
                params['symbol'] = validate_symbol(symbol)
            
            orders = self.client.futures_get_open_orders(**params)
            
            logger.debug(f"Found {len(orders)} open orders")
            return orders
            
        except Exception as e:
            log_error(logger, e, "Failed to get open orders")
            return []
    
    def cancel_order(self, symbol: str, order_id: int) -> bool:
        """
        Cancel an open order
        
        Args:
            symbol: Trading pair symbol
            order_id: Order ID to cancel
        
        Returns:
            True if successful, False otherwise
        """
        try:
            symbol = validate_symbol(symbol)
            
            result = self.client.futures_cancel_order(
                symbol=symbol,
                orderId=order_id
            )
            
            logger.info(f"Order {order_id} cancelled for {symbol}")
            logger.debug(f"Cancel response: {result}")
            return True
            
        except BinanceAPIException as e:
            logger.error(f"Failed to cancel order: {e.message} (Code: {e.code})")
            return False
        except Exception as e:
            log_error(logger, e, f"Failed to cancel order {order_id}")
            return False
    
    def cancel_all_orders(self, symbol: str) -> bool:
        """
        Cancel all open orders for a symbol
        
        Args:
            symbol: Trading pair symbol
        
        Returns:
            True if successful, False otherwise
        """
        try:
            symbol = validate_symbol(symbol)
            
            result = self.client.futures_cancel_all_open_orders(symbol=symbol)
            
            logger.info(f"All orders cancelled for {symbol}")
            logger.debug(f"Cancel all response: {result}")
            return True
            
        except BinanceAPIException as e:
            logger.error(f"Failed to cancel all orders: {e.message} (Code: {e.code})")
            return False
        except Exception as e:
            log_error(logger, e, f"Failed to cancel all orders for {symbol}")
            return False


# Singleton instance
_client_instance = None

def get_client(testnet: bool = None) -> BinanceFuturesClient:
    """
    Get Binance Futures client instance (singleton)
    
    Args:
        testnet: Use testnet if True, live if False, or read from env if None
    
    Returns:
        BinanceFuturesClient instance
    """
    global _client_instance
    
    if testnet is None:
        testnet = os.getenv('USE_TESTNET', 'True').lower() == 'true'
    
    if _client_instance is None:
        _client_instance = BinanceFuturesClient(testnet=testnet)
    
    return _client_instance
