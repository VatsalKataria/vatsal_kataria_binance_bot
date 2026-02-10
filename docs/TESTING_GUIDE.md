# Testing Guide

This guide will help you test all features of the bot before submission.

## Prerequisites

1. Testnet account created at https://testnet.binancefuture.com/
2. Testnet API keys added to .env file
3. Dependencies installed
4. Some testnet USDT in your Futures wallet

## Test Checklist

### 1. Environment Setup ✓

```bash
# Verify API connection
python -c "from src.utils.client import get_client; c = get_client(); print('Connection OK')"
```

Expected: "Connection OK" message with balance info

### 2. Market Orders ✓

```bash
# Test buy market order
python src/core/market_orders.py BTCUSDT BUY 0.001

# Test sell market order  
python src/core/market_orders.py BTCUSDT SELL 0.001
```

Expected:
- Order executed successfully
- Order details displayed
- Log entry created in logs/bot.log

### 3. Limit Orders ✓

```bash
# Get current BTC price first, then place limit orders

# Buy limit below market
python src/core/limit_orders.py BTCUSDT BUY 0.001 90000

# Sell limit above market
python src/core/limit_orders.py BTCUSDT SELL 0.001 100000

# Post-only order
python src/core/limit_orders.py BTCUSDT BUY 0.001 90000 --post-only
```

Expected:
- Orders placed successfully
- Order IDs returned
- Orders visible in Binance testnet interface

### 4. Stop-Limit Orders ✓

```bash
# Stop-limit sell (stop loss)
python src/advanced/stop_limit.py BTCUSDT SELL 0.001 94000 93800

# Stop-market order
python src/advanced/stop_limit.py --stop-market BTCUSDT SELL 0.001 94000

# Trailing stop
python src/advanced/stop_limit.py --trailing BTCUSDT SELL 0.001 1.0
```

Expected:
- Stop orders placed
- Orders in "NEW" status
- Will trigger when price hits stop level

### 5. OCO Orders ✓

```bash
# First open a position
python src/core/market_orders.py BTCUSDT BUY 0.001

# Then set OCO (take profit and stop loss)
python src/advanced/oco.py BTCUSDT SELL 0.001 98000 94000

# Or use percentage-based OCO
python src/advanced/oco.py --position BTCUSDT 5.0 2.0
```

Expected:
- Two orders placed (TP and SL)
- Both orders visible
- When one fills, manually cancel the other (or use monitor mode)

### 6. TWAP Execution ✓

```bash
# Small TWAP test (0.01 BTC over 5 orders, 10s apart)
python src/advanced/twap.py BTCUSDT BUY 0.01 5 10

# TWAP with randomization
python src/advanced/twap.py BTCUSDT BUY 0.01 5 10 --randomize
```

Expected:
- 5 orders executed over ~40 seconds
- Progress displayed
- Summary statistics at the end

### 7. Grid Trading ✓

```bash
# Create a grid (adjust prices based on current market)
python src/advanced/grid.py create BTCUSDT 90000 100000 5 0.001

# Monitor the grid (in separate terminal)
python src/advanced/grid.py monitor BTCUSDT --interval 30

# Stop the grid when done
python src/advanced/grid.py stop BTCUSDT
```

Expected:
- Buy orders placed below market
- Sell orders placed above market
- Orders fill as price moves
- Auto-rebalancing works

### 8. Error Handling ✓

Test these to verify error handling:

```bash
# Invalid symbol
python src/core/market_orders.py INVALID BUY 0.001
# Expected: Error - Invalid symbol format

# Invalid quantity
python src/core/market_orders.py BTCUSDT BUY -1
# Expected: Error - Invalid quantity

# Invalid side
python src/core/market_orders.py BTCUSDT HOLD 0.001
# Expected: Error - Invalid side

# Price too high
python src/core/limit_orders.py BTCUSDT BUY 0.001 99999999
# Expected: Error - Price validation failed
```

### 9. Logging Verification ✓

```bash
# View logs
tail -50 logs/bot.log

# Check for trade logs
grep "TRADE EXECUTED" logs/bot.log

# Check for errors
grep "ERROR" logs/bot.log
```

Expected:
- All operations logged
- Timestamps correct
- Trade details captured
- Errors logged with context

### 10. Documentation ✓

Review all documentation:
- [ ] README.md is complete and accurate
- [ ] All examples work
- [ ] Installation steps are clear
- [ ] Usage examples are correct

## Screenshot Checklist for Report

Take screenshots of:

1. ✅ Successful market order execution (with order details)
2. ✅ Limit order placement (showing order ID and price)
3. ✅ Stop-limit order configuration
4. ✅ OCO order summary (both TP and SL orders)
5. ✅ TWAP execution in progress (showing order count)
6. ✅ Grid trading setup (showing grid levels)
7. ✅ Grid monitoring (showing auto-rebalancing)
8. ✅ Log file sample (showing various operations)
9. ✅ Error handling example (showing validation error)
10. ✅ Binance testnet interface (showing your orders)

## Performance Testing

Test with different parameters:

### TWAP Performance
```bash
# Quick TWAP
python src/advanced/twap.py BTCUSDT BUY 0.01 10 5

# Slower TWAP
python src/advanced/twap.py BTCUSDT BUY 0.01 20 30
```

### Grid Performance
```bash
# Tight grid (more levels)
python src/advanced/grid.py create BTCUSDT 94000 96000 10 0.001

# Wide grid (fewer levels)
python src/advanced/grid.py create BTCUSDT 90000 100000 5 0.001
```

## Common Issues

### Issue: API Connection Failed
**Solution:** Check .env file has correct testnet API keys

### Issue: Insufficient Margin
**Solution:** Add more USDT to testnet Futures wallet (use the faucet)

### Issue: Orders Not Filling
**Solution:** Ensure prices are reasonable relative to market price

### Issue: Import Errors
**Solution:** Ensure all dependencies installed: `pip install -r requirements.txt`

## Final Pre-Submission Checklist

- [ ] All features tested on testnet
- [ ] All tests passed
- [ ] Screenshots captured
- [ ] Logs show successful operations
- [ ] No errors in normal operation
- [ ] README.md is accurate
- [ ] Code is well-commented
- [ ] .env.example is complete
- [ ] GitHub repo is updated
- [ ] .zip file created with correct structure

## Submission Package

Your final .zip should contain:
```
binance_futures_bot/
├── src/
│   ├── core/
│   ├── advanced/
│   └── utils/
├── logs/
│   └── bot.log (with test executions)
├── docs/
│   └── REPORT_TEMPLATE.md
├── .env.example
├── .gitignore
├── README.md
├── requirements.txt
└── setup.sh
```

**Important:** Do NOT include:
- .env file (contains API keys)
- __pycache__ directories
- .venv or venv directories

## Getting Help

If you encounter issues:
1. Check logs/bot.log for detailed errors
2. Review README.md troubleshooting section
3. Verify API keys are correct
4. Ensure testnet has sufficient balance
5. Try with smaller quantities first

---

**Good luck with your submission! 🚀**
