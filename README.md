# Python Trading Bot w/ Thinkorswim

## Description

- This automated trading bot utilitizes, TDameritrade API, TD Websocket API, Tradier API, Gmail API, Discord integration and MongoDB.
- It's intended to be a "plug & play" type of bot for newbies to get invovled with Algo trading.
- You, the user, will have to create the alert system so the bot can trade these signals.


## <a name="how-it-works"></a> How it works (in its simplest terms)

- There are many ways to run this bot:
  - BROKER
    - You can specify your broker (TD or Tradier and can be changed via config.py)
    - TD has a better paper trading set up, but Tradier is $10/mo subscription with free options trading
  - ALERTS
    - You can run it using Trey Thomas's way of using TD API to scan alerts (gmail alerts)
    - You can run it scanning discord notifications
  - TECHNICAL ANLYSIS
    - You can filter these alerts (discord & gmail) to run a technical analysis before you trade it (can be turned off in config.py)
    - Right now, this is just configured using Hull Moving Average & QQE (trending up/down while not being overbought/oversold)
  - WEBSOCKET
    - Open positions in Mongo will be picked up by the TD Websocket API (if turned on) and will continuously give you an update on pricing. Depending on the strategy, it might sell out of the position
* To assist in getting your websocket set up, I recommend watching this video: (Part Time Larry - TD Websocket) https://www.youtube.com/watch?v=P5YanfJFlNs
### **Thinkorswim**

Thinkorswim can be used as a broker for LiveTrading or Papertrading OR it can just be used to send your bot buy signals.  The Papertrading
feature of this bot WILL NOT show up in your papertrading account in ToS, but MongoDB can be set up to visually show your paper trading.
ToS is better than Traider with papertrading because Tradier data is DELAYED for 15m when not live trading.

1. IN ORDER TO TRADE THINKORSWIM, IN CONFIG.PY  --> RUN_TRADIER = False
2. IN ORDER TO TRADE PAPERTRADER, IN CONFIG.PY --> RUN_LIVE_TRADER = FALSE
3. If you want alerts coming from ThinkorSwim, you can set up an OptionHacker alert to send emails to an email you created.
4. Create a scanner for your strategy. (Scanner name will have specific format needed)
5. Set your scanner to send alerts to your non-personal gmail.
6. When a symbol is populated into the scanner with "buy" or "buy_to_open", an alert is triggered and sent to gmail.
7. If you're unfamilar with Trey's repo, please check this out.  This is what the repo this code has been modeled after:
https://github.com/TreyThomas93/python-trading-bot-with-thinkorswim

### **Discord**

1. I personally use https://www.teklutrades.com/FlowAnalysis, I couldn't recommend his work enough.
2. It's $40/month but the alerts are formatted well.
3. If you have your own discord that you'd like to track alerts with, you'll have to format your own discord scanner and throw it in the discord folder.
You can replace discord_scanner.py with your own.  If you don't have a discord_scanner, you can set RUN_DISCORD = False

### **Trading Bot (Python)**

1. Continuously scrapes email inbox/discord looking for alerts.
2. Once found, bot will extract needed information and will run TA (if you have RUN_TA set to True in your config.py).


## HOW TO SET UP config.py ##
1. Create a copy of config.py.example and save it as config.py. Place it in the root of this folder (next to config.py.example)
2. RUN_LIVE_TRADER: change to True if you want to trade using real money (True, False)
3. RUN_TRADIER: change to True if you want to trade using Tradier as your broker (True, False) - the websocket is still ToS based,
so you will still need to have ToS set up if you'd like to runWebsocket with Tradier
4. IS_TESTING: this might not work... it's intended to provide prices when the market is closed to make sure everything is still working in Mongo (True, False)
5. TRADE_HEDGES: only changes the alerts from my discord_scanner (True, False).  TekluTrades indicates when it thinks a flow might be a hedge.  If you aren't using this flow, it won't affect your trading.  If you are using this flow and would like to trade when there's a Hedge Alert flow, set to True
6. MONGO_URI: your Mongo_URI (string) - (see Trey's repo if necessary)
7. RUN_GMAIL & RUN_DISCORD: how do you want to get your alerts?  Set to True for the alerts you'd like (True, False)
8. PUSH_API_KEY: I use a free discord webhook to a personal discord channel, but this is possible too (string) [commented out]
9. TIMEZONE: use a pytz timezone (string) https://gist.github.com/heyalexej/8bf688fd67d7199be4a1682b3eec7568
10. RUN_TASKS: this runs on a totally separate python thread.  I suggest having it set to True (True, False).  Functions can be found in assets -> tasks.py
11. RUN_WEBSOCKET: this will actively stream all open_posiitons in mongo with pricing and update it to mongo (True, False) - personal preference, I have it on
12. TURN_ON_TIME, TURN_OFF_TRADES, SELL_ALL_POSITIONS, SHUTDOWN_TIME: ('HH:MM:SS')
- TURN_ON_TIME - not set up currently, when you'd like to start the mongo connection and boot up the bot
- TURN_OFF_TRADES - at what time would you like to stop accepting trades ('15:50:00') (ie. 10mins before close)
- SELL_ALL_POSITIONS - at what time would you like to start selling all positions?
- SHUTDOWN_TIME - at what time would you like to disconnect from Mongo?  *MONGO CHARGES BASED OFF THE HOUR, NOT NUMBER OF CONNECTIONS, SO IT'S BEST TO SHUT THE CONNECTION ONCE MARKET IS CLOSED

---
TRADING CRITERIA

13. MIN_OPTIONPRICE: (Float) as you're scanning discord alerts, what's the minimum option price you'd like to potentially trade?
14. MAX_OPTIONPRICE: (Float) what's the maximum price you'd like to trade?  *NOTE: THE POSITION SIZE MUST BE SET IN MONGO IN STRATEGIES*
15. MIN_VOLUME: (Float) as you get alerts, python will send a request to TD API to get the price & volume of the option.  What's the minimum volume you want to trade?  You want to ensure that the contract is liquid
16. MIN_DELTA: (Float) what's the minimum delta you'd like to trade? It takes absolute value
17. GET_PRICE_FROM_TD: personal preference.  Do you want to get your price quotes from TD or Tradier?  Tradier is delayed for papertrading, so I always get price data from TD (True, False)
18. BUY_PRICE: do you want to buy on the bidPrice, askPrice, lastPrice, mark? (string) I prefer to buy on bid, sell on ask
19. SELL_PRICE: do you want to sell on the bidPrice, askPrice, lastPrice, mark? (string)
20. MAX_QUEUE_LENGTH: (Float) a tasks has a KillQueueOrder function.  If an order is queued for longer than MAX_QUEUE_LENGTH, then it's cancelled
21. TAKE_PROFIT_PERCENTAGE: (Float) If trading OCO or Custom, what would you like your Take_Profit set as?
- Entry_Price * (1+Take_Profit_Percentage) = Take_Profit_Price
22. STOP_LOSS_PERCENTAGE: (Float) If trading OCO or Custom, what would you like your Stop_Loss set as?
- Entry_Price * (1-Stop_Loss_Percentage) = Stop_Loss_Price
23. TRAIL_STOP_PERCENTAGE: (Float) If trading Trail, it will set your trailing stop.
- Entry_Price * TRAIL_STOP_PERCENTAGE = Trail_Stop_Value
- Entry_Price - Trail_Stop_Value = Trail_Stop_Price
- Please note that this trail stop is not 100% developed yet (Traider does NOT have a trailing stop order, so the websocket will constantly update a closing order)
24. RUNNER_FACTOR: (Float) this is currently *not* being used. It used to enter a new order of RUNNER_FACTOR * position_size after an order hits take_profit_price
25. TRADE_MULTI_STRIKES: do you want to trade multiple strikes of the same options?  TD sometimes sends gmails of 3 separate strikes in one email.  If you don't want to trade these, it should be False (True, False)

---
TECHNICAL ANALYSIS
26. RUN_TA: runs QQE & HULL_MOVING_AVG for alerts in the 10m timeframe (True, False)
27. RUN_30M_TA: Runs QQE & HULL_MOVING_AVG for alerts in the 30m timeframe (True, False)
* If both are true, then the 10m and 30m timeframes are in agreement with your indicators (puts & calls have separate criteria)

---
TD STREAMING
28. API_KEY, REDIRECT_URI, TOKEN_PATH: (string) please watch Part Time Larry's video to get a separate API_KEY for your account.  You will need to create a new TD Developer account for this
29. ACCOUNT_ID: (float) This is the TD account you'd like to trade with
30. HEARTBEAT_SETTING: (float) in seconds, how often would you like a "heartbeat signal" from the websocket task incase you don't have any open positions, it will show that your streamer is still working
31. STREAMPRICE_LINK: (string) in streamprice.py, would you like to trade out of a signal based on 'bid', 'ask', 'last'? I prefer ask price

---
DISCORD
32. CHANNELID: (string) channel ID for discord alert channel
33. DISCORD_AUTH: (string) authorization for discord alert channel
34. DISCORD_USER: (string) username of discord alert bot
35. STRATEGY: (string) what do you want to name your strategy coming from discord alerts
36. DISCORD_WEBHOOK: (string) personal discord webhook (this is how I get alerts instead of Pushsafer)
---
TRADIER
* Tradier API is very easy to work with.  It just needs the specific Access Token & Account Number to trade via Paper or Live
37. LIVE_ACCESS_TOKEN: (string) this will be your live trading access-token from Tradier website
38. LIVE_ACCOUNT_NUMBER: (string) this will be your live trading account-number from Tradier
39. SANDBOX_ACCESS_TOKEN: (string) on Tradier website (this is papertrading) - 15m delayed
40. SANDBOX_ACCOUNT_NUMBER: (string) on Tradier website (this is papetrading) - 15m delayed 
___
 BACKTESTER
* This is how to backtest your strategy - it's currently a work in progress
41. POLYGON_URI: (string) - sign up for Polygon to get free PolygonAPI access - we use it for option price history (only 5 API requests per min for a free account, so it sleeps every 14 mins when grabbing a dataframe) 
42. EXT_DIR: (string) this is the root folder of your code (where main.py is located)
43. LOOKBACK_DAYS: (float) amount of day lookback from current UCT time to backtest (max discord alerts is 50 alerts due to json requests)
44. TEST_DISCORD: (True, False) if you'd like to backtest discord alerts, set to True
45. TEST_CLOSED_POSITIONS: (True, False) if you'd like to backtest mongo closed_positions, set to True
46. POSITION_SIZE: (float) what's your assumed position size for each trade?  If option entry_price exceeds position size, it doesn't trade
___

- **ATTENTION** - The bot is designed to either paper trade or live trade, but not at the same time. You can do one or the other. This can be changed by: TD --> the value set for the "Account_Position" field located in your account object stored in the users collection in mongo. The options for this field are "Paper" and "Live". These are case sensitive. By default when the account is created, it is set to "Paper" as a safety precaution for the user.  TRADIER --> switch your RUN_LIVE_TRADER in config.py to True

---

## <a name="getting-started"></a> Getting Started

### <a name="dependencies"></a> **DEPENDENCIES**

---

> [dev-packages]

- pylint
- autopep8

> [packages]

- google-api-python-client = "\*"
- google-auth-httplib2 = "\*"
- google-auth-oauthlib = "\*"
- python-dotenv = "\*"
- pymongo = "\*"
- dnspython = "\*"
- requests = "\*"
- pytz = "\*"
- psutil = "\*"
- certifi = "\*"
- polygon = "\*"
- pyti = "\*"
- pandas = "\*"
- pandas_ta = "\*"

> [venv]

- pipenv

> [requires]

- python_version = "3.8"

### <a name="thinkorswim"></a> **THINKORSWIM**

---

1. Create a strategy that you want to use in the bot.
2. Create a scanner and name it using the format below:

   - STRATEGY, SIDE
   

   1. REVA is the strategy name example.
   2. BUY is the side. Can be BUY, BUY_TO_OPEN, BUY_TO_CLOSE, SELL, SELL_TO_CLOSE, SELL_TO_OPEN

   ***

   - _**ATTENTION**_ - Your scanner names must have the same strategy names for the buy and sell scanners, or the bot will not be able to trade correctly.
   - Example:

     - MyRSIStrategy, BUY
     - MyRSIStrategy, SELL

---

3. You will need to offset the scanner logic to prevent premature alerts from firing. This is due to the fact of the current candle constantly repainting and meeting/not meeting criteria.

   - This is how an entry strategy in the charts may look.

   ***

   - This is how the scanner should look for the exact same entry strategy.

   - The only thing that changed was that [1] was added to offset the scanner by one and to look at the previous candle.

---

4. Set up the alert for the scanner. View images below:

   - Set Event dropdown to "A symbol is added"


   - Check the box that says "Send an e-mail to all specified e-mail addresses"


   - Check the radio button thats says "A message for every change"

---

5. You should now start to receive alerts to your specified gmail account.

---

### <a name="tda-tokens"></a> **TDAMERITRADE API TOKENS**

- You will need an access token and refresh token for each account you wish to use.
- This will allow you to connect to your TDA account through the API.
- Here is Trey Thomas's [repo](https://github.com/TreyThomas93/TDA-Token) to help you to get these tokens and save them to your mongo database, in your users collection.

### <a name="gmail"></a> **GMAIL**

- First off, it is best to create an additional and seperate Gmail account and not your personal account.

- Make sure that you are in the account that will be used to receive alerts from Thinkorswim.
- _Step by Step (Follow this to setup Gmail API):_

1. https://developers.google.com/gmail/api/quickstart/python
2. https://developers.google.com/workspace/guides/create-project
3. https://developers.google.com/workspace/guides/create-credentials
4. After you obtain your credentials file, make sure you rename it to credentials.json and store it in the creds folding within the gmail package in the program.
5. Run the program and you will go through the OAuth process. Once complete, a token.json file will be stored in your creds folder.
6. If you get an access_denied during the OAuth process, try this: https://stackoverflow.com/questions/65184355/error-403-access-denied-from-google-authentication-web-api-despite-google-acc

- _ATTENTION:_ Be advised that while your gmail api app that you create during the above process is in TESTING mode, the tokens will expire after 7 days. https://stackoverflow.com/questions/66058279/token-has-been-expired-or-revoked-google-oauth2-refresh-token-gets-expired-i

- You will need to set this in production mode to avoid this. Simply skip the SCOPES section of the setup process.

### <a name="mongo"></a> **MONGODB**

---

- Create a MongoDB [account](https://www.mongodb.com/), create a cluster, and create one database with the following names:

  1. Api_Trader

- The Api_Trader will contain all live and paper data. Each document contains a field called Account_Position which will tell the bot if its for paper trading or live trading.

- You will need the mongo URI to be able to connect pymongo in the program. Store this URI in a config.env file within your mongo package in your code.

> #### _ApiTrader_

- The collections you will find in the Api_Trader database will be the following:

1. analysis (THIS IS WHERE THE DISCORD ALERTS GO AFTER THEY'RE SCANNED TO AVOID RE-TRADING)
2. users
3. queue
4. open_positions
5. closed_positions
6. rejected
7. canceled
8. strategies

- The analysis collection stores all alerts so that the bot recognizes a duplicate alert (tracks timestamp of alert & symbol)

- The users collection stores all users and their individial data, such as name and accounts.

- The queue collection stores non-filled orders that are working or queued, until either cancelled or filled.

- The open_positions collection stores all open positions and is used to help determine if an order is warranted.

- The closed_positions collection stores all closed positions after a trade has completed.

- The rejected collection stores all rejected orders.

- The canceled collection stores all canceled orders.

- The strategies collection stores all strategies that have been used with the bot. Here is an example of a strategy object stored in mongo: `{"Active": True, "Order_Type": "STANDARD", "Asset_Type": asset_type, "Position_Size": 500, "Position_Type": "LONG", "Trader": self.user["Name"], "Strategy": strategy, }`

- **FYI** - You are able to add more collections for additional tasks that you so wish to use with the bot. Mongo will automatically add a collection if it doesnt exist when the bot needs to use it so you dont need to manually create it.

### <a name="pushsafer"></a> **PUSHSAFER**

---
- Pushsafer IS integrated, but personally, I use a discord webhook to a personal server since it's a free service

- If you choose to use it, Pushsafer allows you to send and receive push notifications to your phone from the program.

- This is handy for knowing in real time when trades are placed.

- The first thing you will need to do is register:
  https://www.pushsafer.com/

- Once registered, read the docs on how to register and connect to devices. There is an Android and IOS app for this.

- You will also need to pay for API calls, which is about $1 for 1,000 calls.

- You will also need to store your api key in your code in a config.py file.

### <a name="discrepencies"></a> **DISCREPENCIES**

---

- This program is not perfect. I am not liable for any profits or losses.
- There are several factors that could play into the program not working correctly. Some examples below:

  1. TDAmeritrades API is buggy at times, and you may lose connection, or not get correct responses after making requests.
  2. Thinkorswim scanners update every 3-5 minutes, and sometimes symbols wont populate at a timely rate. I've seen some to where it took 20-30 minutes to finally send an alert.
  3. Gmail servers could go down aswell. That has happened in the past, but not very common.
  4. MongoDB can go down at times and the bot may do unexpected things.
  5. Discord notifications are often spotty, so the alerts may not come in at times either.
  6. And depending on who you have hosting your server for the program, that is also subject to go down sometimes, either for maintenance or for other reasons.
  7. As for refreshing the refresh token, I have been running into issues when renewing it. The TDA API site says the refresh token will expire after 90 days, but for some reason It won't allow you to always renew it and may give you an "invalid grant" error, so you may have to play around with it or even recreate everything using this [repo](https://github.com/TreyThomas93/TDA-Token). Just make sure you set it to existing user in the script so it can update your account.
  8. Lastly, running the websocket with TD as your broker, will need high supervision.  The websocket executes the close orders, so if there's an error and the bot stops, the position will never be closed.

- The program is very indirect, and lots of factors play into how well it performs. For the most part, it does a great job.

### <a name="what-i-use-and-costs"></a> **WHAT I USED AND COSTS**

> SERVER FOR HOSTING PROGRAM

- PythonAnywhere -- $7 / month

> DATABASE

- MongoDB Atlas -- Approx. $25 / month.
- I currently use the M5 tier. You may be able to do the M2 tier. If you wont be using the web app then you don't need a higher level tier.


> NOTIFICATION SYSTEM

- PushSafer -- Less than $5 / month

> DISCORD NOTIFICATIONS

- TekluTrades -- $49 / month


### <a name="final-thoughts-and-support"></a> **FINAL THOUGHTS**

---

- I honestly cannot thank Trey enough for getting this base code started and his help along the way when I first got this started.  I didn't know much Python when I started this journey in early 2021 so Trey's help was monumental.  This is in continous development, with hopes to make this program as good as it can possibly get. I know this README might not do it justice with giving you all the information you may need, and you most likely will have questions. Therefore, don't hesitate to contact me on Discord below. As for you all, I would like your input on how to improve this. I appreciate all the support! Thanks, Matt.

- > _DISCORD GROUP_ - Trey created a Discord group to allow for a more interactive enviroment that will allow for all of us to answer questions and talk about the program.  I am the mod on there if you have any questions <a href="https://discord.gg/yxrgUbp2A5">Discord Group</a>

- I'm currently working a backtest into this to backtest your entries from your closed positions

- Also, If you like what I have to offer, please support me here!

> Venmo -  **@Matt-Ogden**
