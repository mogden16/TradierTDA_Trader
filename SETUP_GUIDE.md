# Trading Bot Setup Guide for Cursor

## ✅ Current Status
Your trading bot is **successfully configured** and ready to run in Cursor! All dependencies are installed and the bot is in safe testing mode.

## 🚀 Quick Start (Testing Mode)

### 1. Current Configuration ✅
- **✅ Safe Testing Mode**: `RUN_LIVE_TRADER = False` (paper trading only)
- **✅ Dependencies**: All Python packages installed
- **✅ Virtual Environment**: `trading_bot_env` created and configured
- **✅ Alert Sources**: Disabled for testing (Discord/Gmail off)

### 2. Run the Bot Test
```bash
# Activate environment and test
source trading_bot_env/bin/activate
python test_bot.py
```

### 3. Try Running the Main Bot
```bash
# Activate environment and run main bot
source trading_bot_env/bin/activate
python main.py
```

**Note**: The main bot will ask for TD Ameritrade tokens, but you can still test the configuration.

## 🔧 Next Steps for Full Setup

### Option A: Use TD Ameritrade (Free Paper Trading)

1. **Get TD Ameritrade Developer Account**:
   - Go to [TD Ameritrade Developer](https://developer.tdameritrade.com/)
   - Create free developer account
   - Create a new app to get your API key

2. **Update config.py**:
   ```python
   API_KEY = 'YOUR_API_KEY_HERE@AMER.OAUTHAP'
   ACCOUNT_ID = 1234567890  # Your account number
   ```

3. **Set up OAuth Token**:
   - The bot will guide you through OAuth setup on first run
   - Tokens are saved in `./tdameritrade/token`

### Option B: Use Tradier (Alternative Broker)

1. **Get Tradier Account**:
   - Sign up at [Tradier](https://tradier.com/)
   - Get sandbox (paper trading) API token

2. **Update config.py**:
   ```python
   RUN_TRADIER = True  # Switch to Tradier
   SANDBOX_ACCESS_TOKEN = 'your_sandbox_token_here'
   SANDBOX_ACCOUNT_NUMBER = 'your_sandbox_account'
   ```

### Option C: Database Setup (Optional but Recommended)

1. **MongoDB Atlas (Free)**:
   - Create account at [MongoDB Atlas](https://cloud.mongodb.com/)
   - Create free cluster
   - Get connection string

2. **Update config.py**:
   ```python
   MONGO_URI = 'mongodb+srv://username:password@cluster.mongodb.net/Api_Trader'
   ```

## 📱 Enable Alert Sources (When Ready)

### Discord Integration
```python
# In config.py
RUN_DISCORD = True
CHANNELID = 'your_discord_channel_id'
DISCORD_AUTH = 'your_discord_token'
```

### Gmail Integration (ThinkorSwim alerts)
```python
# In config.py
RUN_GMAIL = True
# Place credentials.json in gmail/creds/ folder
```

## 🛡️ Safety Features (Already Enabled)

- **Paper Trading Only**: No real money at risk
- **Testing Mode**: All dangerous features disabled
- **Alert Sources Off**: No automatic trades from external signals
- **Conservative Settings**: Safe profit/loss percentages

## 🎯 Test Trading Workflow

1. **Start the bot** in testing mode
2. **Monitor logs** for any issues
3. **Test with fake alerts** (if desired)
4. **Gradually enable features** as you become comfortable

## 📋 Files Overview

- **`config.py`**: Main configuration (✅ already created)
- **`main.py`**: Main bot entry point
- **`test_bot.py`**: Test script to verify setup
- **`requirements.txt`**: Python dependencies (✅ installed)
- **`trading_bot_env/`**: Virtual environment (✅ created)

## ⚡ Commands Quick Reference

```bash
# Activate environment
source trading_bot_env/bin/activate

# Test configuration
python test_bot.py

# Run main bot
python main.py

# Install additional packages (if needed)
pip install package_name

# Deactivate environment
deactivate
```

## 🚨 Important Notes

1. **Always test first**: Keep `RUN_LIVE_TRADER = False` until you're ready
2. **Start simple**: Enable features one at a time
3. **Monitor closely**: Watch logs and behavior
4. **Paper trade first**: Use sandbox/paper accounts before real money
5. **Understand the code**: Make sure you understand what the bot does

## 🆘 Troubleshooting

- **Import errors**: Make sure virtual environment is activated
- **Token errors**: Set up broker API credentials
- **Database errors**: Set up MongoDB connection
- **Permission errors**: Check file permissions and paths

## 📞 Getting Help

- Check logs in the terminal for detailed error messages
- Review the `README.md` for additional documentation
- Test individual components using `test_bot.py`

---

**🎉 Congratulations! Your trading bot is ready to run in Cursor!**