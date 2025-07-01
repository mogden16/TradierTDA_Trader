# Python Trading Bot Codebase Explanation

## Overview

This is a sophisticated **automated options trading bot** that integrates multiple broker APIs, alert systems, and technical analysis to execute trades based on various signal sources. The bot is designed as a "plug & play" solution for algorithmic trading with options.

## High-Level Architecture

The system follows a modular, event-driven architecture:

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Alert Sources │    │  Main Bot Core  │    │   Brokers       │
│                 │    │                 │    │                 │
│ • Discord       │───▶│ • main.py       │───▶│ • TD Ameritrade │
│ • Gmail         │    │ • Alert Processing│   │ • Tradier       │
│ • OpenCV        │    │ • Technical Analysis│  │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │   MongoDB       │
                       │                 │
                       │ • Positions     │
                       │ • Orders        │
                       │ • Strategies    │
                       └─────────────────┘
```

## Core Components

### 1. **Main Bot Engine (`main.py`)**
- **Purpose**: Central orchestrator of the entire trading system
- **Key Features**:
  - Manages multiple trading accounts and brokers
  - Coordinates alert scanning from various sources
  - Applies technical analysis filters before trading
  - Handles position management and risk controls
  - Manages time-based trading rules (market hours, stop times, etc.)

**Key Classes:**
- `Main(Tasks, TDWebsocket)`: Primary bot class that inherits from background tasks and websocket functionality

**Core Methods:**
- `connectALL()`: Initializes all connections (MongoDB, Gmail, logging)
- `setupTraders()`: Creates trader instances for each account
- `get_alerts()`: Scans Discord and Gmail for new trading signals
- `set_alerts()`: Processes alerts and decides whether to trade
- `runTradingPlatform()`: Main execution loop

### 2. **API Trader (`api_trader/`)**
- **Purpose**: Handles order execution and position management
- **Key Features**:
  - Order building for different types (Standard, OCO, Trail)
  - Order queue management
  - Position tracking (open/closed)
  - Account management (live/paper trading)

**Key Classes:**
- `ApiTrader(OrderBuilder)`: Main trading execution engine

**Trading Flow:**
1. `sendOrder()`: Creates and validates orders
2. `queueOrder()`: Places order in queue for tracking
3. `updateStatus()`: Monitors order status with broker
4. `pushOrder()`: Moves filled orders to position collections

### 3. **Alert Sources**

#### **Discord Scanner (`discord/discord_scanner.py`)**
- Monitors Discord channels for options flow alerts
- Parses messages in specific format: `SYMBOL MONTH DAY STRIKE-RANGE OPTION_TYPE`
- Example: `SPY Nov 15 $450-$455 CALLS`
- Extracts: symbol, expiration date, strike prices, option type
- Handles hedge alerts (can be filtered out)

#### **Gmail Scanner (`gmail/`)**
- Connects to Gmail API to scan for ThinkorSwim scanner alerts
- Processes email alerts from TOS strategy scanners
- Looks for "buy" or "sell" signals in scanner results

#### **OpenCV Scanner (`open_cv/`)**
- **Visual chart pattern recognition**
- Monitors live trading charts for visual signals
- Uses template matching to identify buy/sell patterns
- Automatically trades based on chart patterns

### 4. **Broker Integrations**

#### **TD Ameritrade (`tdameritrade/`)**
- Full API integration for live and paper trading
- Options chain data retrieval
- Order placement and management
- Websocket streaming for real-time position updates
- Account authentication and token management

#### **Tradier (`tradier/`)**
- Alternative broker with $10/month subscription
- Simple API for order execution
- Lower cost options trading
- 15-minute delayed data for paper trading

### 5. **Database Layer (`mongo/`)**
- **MongoDB** for all data persistence
- **Collections**:
  - `open_positions`: Currently held positions
  - `closed_positions`: Historical completed trades
  - `queue`: Orders waiting to be filled
  - `analysis`: Processed alerts to prevent duplicates
  - `rejected`/`canceled`: Failed orders
  - `strategies`: Trading strategy configurations
  - `users`: Account and user information

### 6. **Technical Analysis (`assets/techanalysis.py`)**
- **Indicators**: Hull Moving Average, QQE (Quantitative Qualitative Estimation)
- **Timeframes**: 10-minute and 30-minute analysis
- **Purpose**: Filters alerts before trading to improve signal quality
- **Logic**: Only trades when both indicators align with the signal direction

### 7. **Background Tasks (`assets/tasks.py`)**
- **Queue Management**: Cancels old queued orders
- **Position Monitoring**: Tracks open positions
- **Profit/Loss Calculations**: Real-time P&L updates
- **Automated Selling**: Time-based position closure
- **Heartbeat Monitoring**: System health checks

### 8. **WebSocket Streaming (`td_websocket/`)**
- **Real-time price updates** for open positions
- **Automatic position management** based on price movements
- **Trail stop execution** and profit-taking
- **Live market data** streaming

## Trading Strategies & Order Types

### **Order Types:**
1. **STANDARD**: Simple buy/sell orders
2. **OCO** (One-Cancels-Other): Take profit + stop loss
3. **TRAIL**: Trailing stop loss orders
4. **CUSTOM**: Advanced multi-leg strategies

### **Position Management:**
- **Take Profit**: Configurable percentage gains
- **Stop Loss**: Risk management with percentage stops
- **Trail Stops**: Dynamic stop loss that follows price
- **Day Trading**: Automatic position closure before market close
- **Runner Strategy**: Partial profit taking with position scaling

## Configuration System (`config.py`)

The bot is highly configurable with 40+ settings:

### **Core Settings:**
- `RUN_LIVE_TRADER`: Switch between live and paper trading
- `RUN_TRADIER`: Choose between TD Ameritrade and Tradier
- `RUN_DISCORD`/`RUN_GMAIL`: Enable/disable alert sources
- `RUN_TA`: Enable technical analysis filtering

### **Trading Criteria:**
- `MIN_OPTIONPRICE`/`MAX_OPTIONPRICE`: Price filters
- `MIN_VOLUME`: Liquidity requirements  
- `MIN_DELTA`: Options Greeks filtering
- `TAKE_PROFIT_PERCENTAGE`: Profit target
- `STOP_LOSS_PERCENTAGE`: Risk management

### **Time Controls:**
- `TURN_ON_TIME`: Bot start time
- `TURN_OFF_TRADES`: Stop accepting new trades
- `SELL_ALL_POSITIONS`: Force close all positions
- `SHUTDOWN_TIME`: Bot shutdown time

## Key Features

### **Multi-Broker Support**
- Seamlessly switch between TD Ameritrade and Tradier
- Different APIs for different use cases
- Live and paper trading modes

### **Advanced Risk Management**
- Position sizing based on strategy rules
- Technical analysis filters to improve signal quality
- Time-based controls for market hours
- Automatic position closure systems

### **Alert Processing Pipeline**
1. **Scan** multiple sources (Discord, Gmail, Charts)
2. **Filter** duplicate alerts using MongoDB
3. **Validate** option contracts (price, volume, delta)
4. **Analyze** with technical indicators (if enabled)
5. **Execute** trades through chosen broker
6. **Monitor** positions with real-time updates

### **Comprehensive Logging & Monitoring**
- Multi-file logging system
- Discord webhook notifications for trades
- Real-time position tracking
- Order status monitoring
- Error handling and recovery

### **Backtesting System (`backtest/`)**
- Test strategies on historical data
- Polygon.io integration for options price history
- Performance analysis and optimization
- Risk/reward calculations

## Dependencies & Infrastructure

### **Key Python Libraries:**
- `pymongo`: MongoDB integration
- `requests`: HTTP API calls
- `pandas`/`pandas_ta`: Data analysis and technical indicators
- `selenium`: Web automation for some features
- `opencv-python`: Chart pattern recognition
- `pytz`: Timezone handling
- `google-api-python-client`: Gmail integration

### **External Services:**
- **MongoDB Atlas**: Cloud database (~$25/month)
- **TekluTrades Discord**: Premium options flow alerts ($49/month)
- **Polygon.io**: Historical options data for backtesting
- **PushSafer**: Mobile notifications (~$5/month)

## Security & Best Practices

### **API Security:**
- Token-based authentication for all broker APIs
- Refresh token management for TD Ameritrade
- Secure credential storage in config files
- Environment variable support

### **Error Handling:**
- Comprehensive exception handling throughout
- Automatic retry logic for failed requests
- Graceful degradation when services are unavailable
- Detailed logging for debugging

### **Risk Controls:**
- Position size limits per strategy
- Maximum concurrent positions
- Time-based trading restrictions
- Automatic day-trading closure
- Real-time balance monitoring

## Usage Scenarios

### **1. Discord Flow Trading**
- Monitor premium Discord channels for large options flow
- Filter signals with technical analysis
- Auto-execute trades on high-conviction signals

### **2. ThinkorSwim Scanner Integration**
- Create custom scanners in TOS
- Receive email alerts for scanner hits
- Auto-trade based on scanner criteria

### **3. Chart Pattern Trading**
- Use OpenCV to monitor live charts
- Recognize visual patterns automatically
- Execute trades based on chart signals

### **4. Hybrid Approach**
- Combine multiple signal sources
- Cross-validate signals for higher accuracy
- Diversify across different strategies

## Getting Started Summary

1. **Set up MongoDB** cluster and collections
2. **Configure broker APIs** (TD Ameritrade or Tradier)
3. **Set up alert sources** (Discord, Gmail, or OpenCV)
4. **Copy and customize** `config.py.example` to `config.py`
5. **Test with paper trading** before going live
6. **Monitor and optimize** strategy performance

This trading bot represents a comprehensive solution for automated options trading, with multiple redundant systems for reliability and extensive configuration options for customization to different trading styles and risk tolerances.