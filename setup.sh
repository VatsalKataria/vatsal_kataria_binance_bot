#!/bin/bash

# Binance Futures Bot - Quick Setup Script
# This script helps you get started quickly

echo "=================================================="
echo "  Binance Futures Trading Bot - Quick Setup"
echo "=================================================="
echo ""

# Check Python version
echo "Checking Python version..."
python3 --version

if [ $? -ne 0 ]; then
    echo "❌ Python 3 is not installed. Please install Python 3.8 or higher."
    exit 1
fi

echo "✅ Python is installed"
echo ""

# Create virtual environment (optional but recommended)
echo "Creating virtual environment..."
python3 -m venv venv

if [ $? -eq 0 ]; then
    echo "✅ Virtual environment created"
    echo ""
    echo "To activate it, run:"
    echo "  source venv/bin/activate  # On Linux/Mac"
    echo "  venv\\Scripts\\activate     # On Windows"
    echo ""
else
    echo "⚠️  Could not create virtual environment. Proceeding without it."
    echo ""
fi

# Install dependencies
echo "Installing dependencies..."
pip3 install -r requirements.txt

if [ $? -eq 0 ]; then
    echo "✅ Dependencies installed successfully"
else
    echo "❌ Failed to install dependencies"
    exit 1
fi

echo ""

# Setup .env file
if [ ! -f .env ]; then
    echo "Setting up environment file..."
    cp .env.example .env
    echo "✅ Created .env file from template"
    echo ""
    echo "⚠️  IMPORTANT: Edit .env file and add your API keys!"
    echo ""
else
    echo "✅ .env file already exists"
    echo ""
fi

# Create logs directory
mkdir -p logs
echo "✅ Logs directory created"
echo ""

# Display next steps
echo "=================================================="
echo "  Setup Complete! 🎉"
echo "=================================================="
echo ""
echo "Next steps:"
echo ""
echo "1. Edit .env file with your API keys:"
echo "   nano .env  # or use your favorite editor"
echo ""
echo "2. Get Testnet API keys (RECOMMENDED for beginners):"
echo "   https://testnet.binancefuture.com/"
echo ""
echo "3. Try your first market order:"
echo "   python src/core/market_orders.py BTCUSDT BUY 0.001"
echo ""
echo "4. Read the full documentation:"
echo "   cat README.md"
echo ""
echo "5. View available commands for each module:"
echo "   python src/core/market_orders.py"
echo "   python src/core/limit_orders.py"
echo "   python src/advanced/twap.py"
echo "   python src/advanced/grid.py"
echo ""
echo "=================================================="
echo "  Happy Trading! 📈"
echo "=================================================="
echo ""
echo "⚠️  Remember: Always test on TESTNET first!"
echo ""
