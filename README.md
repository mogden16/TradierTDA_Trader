# Python Trading Bot w/ Thinkorswim

## Description

- This automated trading bot utilitizes, TDameritrade API, TD Websocket API, Tradier API, Gmail API, Discord integration and MongoDB API.

## Table Of Contents

- [How it works](#how-it-works)

- [Getting Started](#getting-started)

  - [Dependencies](#dependencies)
  - [Thinkorswim](#thinkorswim)
  - [TDA API Tokens](#tda-tokens)
  - [Gmail](#gmail)
  - [MongoDB](#mongo)
  - [Pushsafer](#pushsafer)

- [Discrepencies](#discrepencies)

- [What I Use and Costs](#what-i-use-and-costs)

- [Code Counter](#code-counter)

- [Final Thoughts and Support](#final-thoughts-and-support)

## <a name="how-it-works"></a> How it works (in a nutshell)

There are many ways to run this bot:
- You can run it using Trey Thomas's way of using TD API to scan alerts (gmail alerts)
- You can run it scanning discord notifications
- You can filter these alerts (discord & gmail) to run a technical analysis before you trade it
- right now this is just configured using Hull Moving Average & QQE (trending up/down while not being overbought/oversold)
- The open positions will then be continuously scanned and updating in pricing. Depending on the strategy, it will sell out of the position.

### **Thinkorswim**

1. Develop strategies in Thinkorswim.
2. Create a scanner for your strategy. (Scanner name will have specific format needed)
3. Set your scanner to send alerts to your non-personal gmail.
4. When a symbol is populated into the scanner, an alert is triggered and sent to gmail.

### **Discord**

1. I personally use https://www.teklutrades.com/FlowAnalysis, I think he's very knowledgeable and a great programmer.
2. It's $40/month but the alerts are formatted well.

### **Trading Bot (Python)**

1. Continuously scrapes email inbox/discord looking for alerts.
2. Once found, bot will extract needed information and will run TA (if you have RUN_TA set to True in your config.py).

---

- You can only buy a symbol once per strategy, but you can buy the same symbol on multiple strategies.

- For Example:

  1. You place a buy order for AAPL with the strategy name MyRSIStrategy. Once the order is placed and filled, it is pushed to mongo.
  2. If another alert is triggered for AAPL with the strategy name of MyRSIStrategy, the bot will reject it because it's already an open position.
  3. Once the position is removed via a sell order, then AAPL with the strategy name of MyRSIStrategy can be bought again.

- This bot is setup for both Standard orders and OCO orders.

  1. Standard Orders - basic buy and sell order flow.
  2. OCO orders - single entry price with two exit prices (Stop Loss/Take Profit)

- For the OCO orders, the bot uses a task to check your TDA account to see if any OCO exits have triggered.

- **ATTENTION** - The bot is designed to either paper trade or live trade, but not at the same time. You can do one or the other. This can be changed by the value set for the "Account_Position" field located in your account object stored in the users collection in mongo. The options for this field are "Paper" and "Live". These are case sensitive. By default when the account is created, it is set to "Paper" as a safety precaution for the user.

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

> [venv]

- pipenv

> [requires]

- python_version = "3.8"

### <a name="thinkorswim"></a> **THINKORSWIM**

---

1. Create a strategy that you want to use in the bot.
2. Create a scanner and name it using the format below:

   - STRATEGY, SIDE

   - Example: ![Scanner Name Format](https://tos-python-trading-bot.s3.us-east-2.amazonaws.com/img/Scanner_Name_Format.PNG)

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

   - ![Chart Strategy Example](https://tos-python-trading-bot.s3.us-east-2.amazonaws.com/img/Chart_Strategy.PNG)

   ***

   - This is how the scanner should look for the exact same entry strategy.

   - ![Scanner Strategy Example](https://tos-python-trading-bot.s3.us-east-2.amazonaws.com/img/Scanner_Strategy.PNG)

   - The only thing that changed was that [1] was added to offset the scanner by one and to look at the previous candle.

---

4. Set up the alert for the scanner. View images below:

   - ![Create Alert Screen 1](https://tos-python-trading-bot.s3.us-east-2.amazonaws.com/img/Create_Alert_Screen.PNG)
   - Set Event dropdown to "A symbol is added"

   - ![Create Alert Screen 1](https://tos-python-trading-bot.s3.us-east-2.amazonaws.com/img/Create_Alert_Screen2.PNG)
   - Check the box that says "Send an e-mail to all specified e-mail addresses"

   - ![Create Alert Screen 1](https://tos-python-trading-bot.s3.us-east-2.amazonaws.com/img/Create_Alert_Screen3.PNG)
   - Check the radio button thats says "A message for every change"

---

5. You should now start to receive alerts to your specified gmail account.

---

### <a name="tda-tokens"></a> **TDAMERITRADE API TOKENS**

- You will need an access token and refresh token for each account you wish to use.
- This will allow you to connect to your TDA account through the API.
- Here is my [repo](https://github.com/TreyThomas93/TDA-Token) to help you to get these tokens and save them to your mongo database, in your users collection.

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

  1. users
  2. queue
  3. open_positions
  4. closed_positions
  5. rejected
  6. canceled
  7. strategies

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

- Pushsafer allows you to send and receive push notifications to your phone from the program.

- This is handy for knowing in real time when trades are placed.

- The first thing you will need to do is register:
  https://www.pushsafer.com/

- Once registered, read the docs on how to register and connect to devices. There is an Android and IOS app for this.

- You will also need to pay for API calls, which is about $1 for 1,000 calls.

- You will also need to store your api key in your code in a config.env file.

### <a name="discrepencies"></a> **DISCREPENCIES**

---

- This program is not perfect. I am not liable for any profits or losses.
- There are several factors that could play into the program not working correctly. Some examples below:

  1. TDAmeritrades API is buggy at times, and you may lose connection, or not get correct responses after making requests.
  2. Thinkorswim scanners update every 3-5 minutes, and sometimes symbols wont populate at a timely rate. I've seen some to where it took 20-30 minutes to finally send an alert.
  3. Gmail servers could go down aswell. That has happened in the past, but not very common.
  4. And depending on who you have hosting your server for the program, that is also subject to go down sometimes, either for maintenance or for other reasons.
  5. As for refreshing the refresh token, I have been running into issues when renewing it. The TDA API site says the refresh token will expire after 90 days, but for some reason It won't allow you to always renew it and may give you an "invalid grant" error, so you may have to play around with it or even recreate everything using this [repo](https://github.com/TreyThomas93/TDA-Token). Just make sure you set it to existing user in the script so it can update your account.

- The program is very indirect, and lots of factors play into how well it performs. For the most part, it does a great job.

### <a name="what-i-use-and-costs"></a> **WHAT I USED AND COSTS**

> SERVER FOR HOSTING PROGRAM

- PythonAnywhere -- $7 / month

> DATABASE

- MongoDB Atlas -- Approx. $25 / month.
- I currently use the M5 tier. You may be able to do the M2 tier. If you wont be using the web app then you don't need a higher level tier.

![Mongo Tiers](https://tos-python-trading-bot.s3.us-east-2.amazonaws.com/img/cluster-tier.png)

> NOTIFICATION SYSTEM

- PushSafer -- Less than $5 / month

### <a name="code-counter"></a> **CODE COUNTER**

---

- Total : 15 files, 1768 codes, 271 comments, 849 blanks, all 2888 lines

## Languages

| language | files | code | comment | blank | total |
| :------- | ----: | ---: | ------: | ----: | ----: |
| Python   |    12 |  982 |     271 |   719 | 1,972 |
| JSON     |     1 |  576 |       0 |     1 |   577 |
| Markdown |     1 |  190 |       0 |   125 |   315 |
| toml     |     1 |   20 |       0 |     4 |    24 |

## Directories

| path         | files |  code | comment | blank | total |
| :----------- | ----: | ----: | ------: | ----: | ----: |
| .            |    15 | 1,768 |     271 |   849 | 2,888 |
| api_trader   |     3 |   492 |     102 |   306 |   900 |
| assets       |     5 |   114 |      34 |   100 |   248 |
| gmail        |     1 |   122 |      34 |   107 |   263 |
| mongo        |     1 |    36 |       1 |    30 |    67 |
| tdameritrade |     1 |   138 |      85 |   113 |   336 |

### <a name="final-thoughts-and-support"></a> **FINAL THOUGHTS**

---

- This is in continous development, with hopes to make this program as good as it can possibly get. I know this README might not do it justice with giving you all the information you may need, and you most likely will have questions. Therefore, don't hesitate to contact me either via Github or email. As for you all, I would like your input on how to improve this, and I also heavily encourage you to fork the code and send me your improvements. I appreciate all the support! Thanks, Trey.

- > _DISCORD GROUP_ - I have created a Discord group to allow for a more interactive enviroment that will allow for all of us to answer questions and talk about the program. <a href="https://discord.gg/yxrgUbp2A5">Discord Group</a>

- If you like backtesting with Thinkorswim, here's a [repo](https://github.com/TreyThomas93/TOS-Auto-Export) of mine that may help you export strategy reports alot faster.

- Also, If you like what I have to offer, please support me here!

<a href="https://www.buymeacoffee.com/TreyThomas"><img src="https://img.buymeacoffee.com/button-api/?text=Buy me a coffee?&emoji=&slug=TreyThomas&button_colour=604343&font_colour=ffffff&font_family=Inter&outline_colour=ffffff&coffee_colour=FFDD00"></a>
