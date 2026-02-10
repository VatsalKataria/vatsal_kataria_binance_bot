# Binance Futures Trading Bot

A professional, production-ready CLI-based trading bot for Binance USDT-M Futures with comprehensive order types, risk management, and detailed logging.

## 🚀 Features

### Core Order Types

- ✅ **Market Orders** - Instant execution at current market price
- ✅ **Limit Orders** - Precise price control with maker/taker options
- ✅ **Bracket Orders** - Entry + Take Profit + Stop Loss in one command

### Advanced Order Types (Bonus Features)

- 🎯 **Stop-Limit Orders** - Conditional orders triggered at specific prices
- ⚖️ **OCO (One-Cancels-the-Other)** - Simultaneous TP/SL management
- 🕐 **TWAP (Time-Weighted Average Price)** - Split large orders over time
- 📊 **Grid Trading** - Automated buy-low/sell-high strategy
- 📉 **Trailing Stop** - Dynamic stop-loss that follows price

### Additional Features

- 🔒 **Testnet Support** - Safe testing with fake money
- 📝 **Comprehensive Logging** - All actions logged with timestamps
- ✔️ **Input Validation** - Prevents invalid orders
- 🎨 **Colored Console Output** - Easy-to-read status updates
- 🔄 **Position Management** - View and close positions easily
- 📊 **Execution Summaries** - Detailed order reports

## 📋 Prerequisites

- Python 3.8 or higher
- Binance account with Futures enabled
- API keys (Testnet for practice, Live for real trading)

## 🛠️ Installation

### 1. Clone/Extract the Repository

```bash
# If using git
git clone <repository-url>
cd binance_futures_bot

# Or extract the .zip file
unzip binance_futures_bot.zip
cd binance_futures_bot
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure API Keys

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env with your favorite editor
nano .env  # or vim, code, etc.
```

**For Testnet (Recommended for Learning):**

```env
USE_TESTNET=True
TESTNET_API_KEY=your_testnet_api_key_here
TESTNET_API_SECRET=your_testnet_api_secret_here
```

**Get Testnet API Keys:**

1. Visit https://testnet.binancefuture.com/
2. Login with your Binance account
3. Go to API Management
4. Create new API key
5. Copy both API Key and Secret Key to .env file

**For Live Trading (⚠️ REAL MONEY):**

```env
USE_TESTNET=False
BINANCE_API_KEY=your_live_api_key_here
BINANCE_API_SECRET=your_live_api_secret_here
```

## 📚 Usage Examples

### Market Orders

Execute immediate buy/sell at current price:

```bash
# Buy 0.01 BTC at market price
python src/core/market_orders.py BTCUSDT BUY 0.01

# Sell 0.1 ETH at market price
python src/core/market_orders.py ETHUSDT SELL 0.1

# Close existing position
python src/core/market_orders.py BTCUSDT BUY 0.01 --close
```

### Limit Orders

Place orders at specific price levels:

```bash
# Buy 0.01 BTC at $95,000
python src/core/limit_orders.py BTCUSDT BUY 0.01 95000

# Sell 0.1 ETH at $3,500 (maker-only)
python src/core/limit_orders.py ETHUSDT SELL 0.1 3500 --post-only

# Limit order with IOC (Immediate or Cancel)
python src/core/limit_orders.py BTCUSDT BUY 0.01 95000 --tif IOC
```

### Stop-Limit Orders (Advanced)

Conditional orders triggered at specific prices:

```bash
# Stop-limit: Sell 0.01 BTC if price hits $94,000, limit at $93,800
python src/advanced/stop_limit.py BTCUSDT SELL 0.01 94000 93800

# Stop-market: Sell immediately when price hits $94,000
python src/advanced/stop_limit.py --stop-market BTCUSDT SELL 0.01 94000

# Trailing stop: 1% callback rate
python src/advanced/stop_limit.py --trailing BTCUSDT SELL 0.01 1.0
```

### OCO Orders (Advanced)

Place take-profit and stop-loss simultaneously:

```bash
# OCO for closing long: TP at $98,000, SL at $93,000
python src/advanced/oco.py BTCUSDT SELL 0.01 98000 93000

# OCO based on existing position (5% TP, 2% SL)
python src/advanced/oco.py --position BTCUSDT 5.0 2.0

# Monitor OCO orders (auto-cancel opposite when one fills)
python src/advanced/oco.py --monitor BTCUSDT
```

### TWAP Orders (Advanced)

Split large orders into smaller chunks over time:

```bash
# Execute 0.1 BTC over 10 orders, 60 seconds apart
python src/advanced/twap.py BTCUSDT BUY 0.1 10 60

# TWAP with randomization (stealth execution)
python src/advanced/twap.py BTCUSDT BUY 0.1 10 60 --randomize

# TWAP with limit orders at $95,000
python src/advanced/twap.py BTCUSDT BUY 0.1 10 60 --limit 95000
```

### Grid Trading (Advanced)

Automated buy-low/sell-high within a price range:

```bash
# Create grid: $90k-$100k range, 10 levels, 0.001 BTC per level
python src/advanced/grid.py create BTCUSDT 90000 100000 10 0.001

# Monitor existing grid
python src/advanced/grid.py monitor BTCUSDT --interval 30

# Stop grid and cancel all orders
python src/advanced/grid.py stop BTCUSDT
```

## 📁 Project Structure

```
binance_futures_bot/
│
├── src/
│   ├── core/                      # Core order types
│   │   ├── market_orders.py       # Market orders
│   │   └── limit_orders.py        # Limit orders
│   │
│   ├── advanced/                  # Advanced strategies
│   │   ├── stop_limit.py          # Stop-limit orders
│   │   ├── oco.py                 # OCO orders
│   │   ├── twap.py                # TWAP execution
│   │   └── grid.py                # Grid trading
│   │
│   └── utils/                     # Utilities
│       ├── client.py              # Binance API client wrapper
│       ├── logger.py              # Logging configuration
│       └── validators.py          # Input validation
│
├── logs/
│   └── bot.log                    # Execution logs
│
├── .env.example                   # Environment template
├── .env                          # Your API keys (create from .env.example)
├── requirements.txt              # Python dependencies
└── README.md                     # This file
```

## 🔐 Security Best Practices

1. **Never commit .env file** - Already in .gitignore
2. **Use testnet first** - Practice with fake money
3. **Enable IP whitelist** - Restrict API key to your IP
4. **Set withdrawal restrictions** - Disable withdrawals for trading API keys
5. **Use separate API keys** - Different keys for bot vs manual trading
6. **Monitor regularly** - Check logs and positions frequently

## 📊 Logging

All activities are logged to `logs/bot.log` with:

- Timestamps
- Order details
- Execution results
- Error traces

View logs:

```bash
# View latest logs
tail -f logs/bot.log

# Search for errors
grep ERROR logs/bot.log

# View today's trades
grep "TRADE EXECUTED" logs/bot.log
```

## 🐛 Troubleshooting

### Common Issues

**1. API Connection Error**

```
Error: Binance API credentials not found
```

Solution: Check your .env file has correct API keys

**2. Insufficient Margin**

```
Error: -2019 Margin is insufficient
```

Solution: Add more USDT to your Futures wallet

**3. Invalid Quantity**

```
Error: -1111 Precision is over the maximum defined
```

Solution: Check symbol filters, adjust quantity precision

**4. Order Outside Price Range**

```
Error: -4061 Order's notional must be no smaller than...
```

Solution: Increase order size or adjust price

### Getting Help

1. Check `logs/bot.log` for detailed error messages
2. Verify API keys are correct
3. Ensure sufficient balance
4. Test with smaller quantities first
5. Use testnet to practice

## 📈 Risk Management Tips

1. **Start Small** - Use minimal quantities when learning
2. **Use Stop Losses** - Always protect your positions
3. **Don't Over-Leverage** - Stick to 1-3x leverage initially
4. **Monitor Positions** - Check regularly, especially with automated strategies
5. **Diversify** - Don't put all capital in one trade
6. **Test Strategies** - Use testnet to validate before live trading

## 🎯 Advanced Features

### Position Management

```python
# Check current positions
from src.utils.client import get_client

client = get_client()
positions = client.get_open_positions()
for pos in positions:
    print(f"{pos['symbol']}: {pos['positionAmt']} @ {pos['entryPrice']}")
```

### Order Monitoring

```python
# Check open orders
orders = client.get_open_orders('BTCUSDT')
print(f"Open orders: {len(orders)}")
```

### Custom Strategies

The modular structure makes it easy to build custom strategies by combining existing components:

```python
from src.core.market_orders import MarketOrderExecutor
from src.advanced.oco import OCOOrderExecutor

# Enter position
market = MarketOrderExecutor()
entry = market.execute_market_order('BTCUSDT', 'BUY', 0.01)

# Set protective OCO
oco = OCOOrderExecutor()
oco.execute_oco_for_position('BTCUSDT', tp_pct=5.0, sl_pct=2.0)
```

## 📝 Important Notes

- This bot is for educational purposes
- Trading involves significant risk
- Past performance doesn't guarantee future results
- Always do your own research (DYOR)
- Only trade with money you can afford to lose

## 🤝 Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Add tests for new features
4. Submit a pull request

## 📄 License

This project is for educational purposes. Use at your own risk.

## 🔗 Resources

- [Binance Futures API Documentation](https://binance-docs.github.io/apidocs/futures/en/)
- [Binance Testnet](https://testnet.binancefuture.com/)
- [Python-Binance Library](https://python-binance.readthedocs.io/)

## ⚠️ Disclaimer

This software is provided "as is", without warranty of any kind. Trading cryptocurrencies carries substantial risk of loss. The authors are not responsible for any financial losses incurred through the use of this software.

---

**Happy Trading! 📈🚀**

Remember: Test on testnet first, start small, use stop losses, and never risk more than you can afford to lose.
