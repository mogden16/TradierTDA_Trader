# imports
import logging
import os
import time
import traceback
from datetime import datetime
from threading import Thread

import pytz
from tqdm import tqdm

import config
import constants as c
from api_trader import ApiTrader
from assets import pushsafer, helper_functions, techanalysis, streamprice
from assets.exception_handler import exception_handler
from assets.multifilehandler import MultiFileHandler
from assets.tasks import Tasks
from assets.timeformatter import Formatter
from backtest import backtest
from discord import discord_helpers, discord_scanner
from gmail import Gmail
from mongo import MongoDB, mongo_helpers
from open_cv import AlertScanner, run_opencv
from td_websocket.stream import TDWebsocket
from tdameritrade import TDAmeritrade
from tdameritrade import td_helpers
from tradier import TradierTrader

DAY_TRADE = config.DAY_TRADE
RUN_TRADIER = config.RUN_TRADIER
RUN_DISCORD = config.RUN_DISCORD
RUN_LIST = config.RUN_LIST
RUN_GMAIL = config.RUN_GMAIL
IS_TESTING = config.IS_TESTING
TRADE_HEDGES = config.TRADE_HEDGES
RUN_LIVE_TRADER = config.RUN_LIVE_TRADER
RUN_WEBSOCKET = config.RUN_WEBSOCKET
TIMEZONE = config.TIMEZONE
TURN_ON_TIME = config.TURN_ON_TIME
TURN_OFF_TRADES = config.TURN_OFF_TRADES
SELL_ALL_POSITIONS = config.SELL_ALL_POSITIONS
SHUTDOWN_TIME = config.SHUTDOWN_TIME
RUN_TASKS = config.RUN_TASKS
RUN_BACKTEST_TIME = config.RUN_BACKTEST_TIME
TEST_CLOSED_POSITIONS = config.TEST_CLOSED_POSITIONS
TEST_ANALYSIS_POSITIONS = config.TEST_ANALYSIS_POSITIONS
RUN_OPENCV = config.RUN_OPENCV
ITM_OR_OTM = config.ITM_OR_OTM.upper()
TRADE_SYMBOL = config.TRADE_SYMBOL.upper()
TICKER_LIST = config.TICKER_LIST


class Main(Tasks, TDWebsocket):

    def __init__(self):

        self.error = 0

        Tasks.__init__(self)

        TDWebsocket.__init__(self)

    def connectALL(self):
        """ METHOD INITIALIZES LOGGER, MONGO, GMAIL, PAPERTRADER.
        """

        # INSTANTIATE LOGGER
        file_handler = MultiFileHandler(
            filename=f'{os.path.abspath(os.path.dirname(__file__))}/logs/error.log', mode='a')

        formatter = Formatter('%(asctime)s [%(levelname)s] %(message)s')

        file_handler.setFormatter(formatter)

        ch = logging.StreamHandler()

        ch.setLevel(level="INFO")

        ch.setFormatter(formatter)

        self.logger = logging.getLogger(__name__)

        self.logger.setLevel(level="INFO")

        self.logger.addHandler(file_handler)

        self.logger.addHandler(ch)

        # CONNECT TO MONGO
        self.mongo = MongoDB(self.logger)

        mongo_connected = self.mongo.connect()

        # CONNECT TO GMAIL API
        if config.RUN_GMAIL:

            self.gmail = Gmail(self.logger)

            gmail_connected = self.gmail.connect()

        else:

            self.gmail = None

        if mongo_connected:
            self.traders = {}

            self.accounts = []

            self.not_connected = []

            return True

        return False

    @exception_handler
    def setupTraders(self):
        """ METHOD GETS ALL USERS ACCOUNTS FROM MONGO AND CREATES LIVE TRADER INSTANCES FOR THOSE ACCOUNTS.
            IF ACCOUNT INSTANCE ALREADY IN SELF.TRADERS DICT, THEN ACCOUNT INSTANCE WILL NOT BE CREATED AGAIN.
        """
        # GET ALL USERS ACCOUNTS
        users = self.mongo.users.find({})

        for user in users:

            try:

                for account_id in user["Accounts"].keys():

                    if account_id not in self.traders and account_id not in self.not_connected:

                        push_notification = pushsafer.PushNotification(
                            user["deviceID"], self.logger)

                        tdameritrade = TDAmeritrade(
                            self.mongo, user, account_id, self.logger, push_notification)

                        connected = tdameritrade.initialConnect()

                        if connected:

                            obj = ApiTrader(user, self.mongo, push_notification, self.logger, int(
                                account_id), tdameritrade)

                            self.traders[account_id] = obj

                            self.tradier = TradierTrader(user, self.mongo, self.logger)

                            self.user = user

                            self.account_id = account_id

                            time.sleep(0.1)

                            if RUN_TASKS:
                                Thread(target=self.runTasks, daemon=False).start()

                            if RUN_WEBSOCKET:
                                Thread(target=self.runWebsocket, daemon=False).start()

                            if not RUN_WEBSOCKET and not RUN_TASKS:
                                self.logger.info(
                                    f"NOT RUNNING TASKS FOR {self.user['Name']} "
                                    f"({helper_functions.modifiedAccountID(self.account_id)})\n",
                                    extra={'log': False})

                        else:

                            self.not_connected.append(account_id)

                    self.accounts.append(account_id)

            except Exception as e:

                logging.error(e)

    def get_list_alerts(self, live_trader):
        alerts = []
        try:
            for symbol in TICKER_LIST:
                for option_type in ['CALL', 'PUT']:
                    alert = {
                        'Symbol': symbol,
                        'Option_Type': option_type,
                        "Strategy": "LIST"
                    }
                    option_exp_date = helper_functions.find_option_expDate(live_trader, symbol)
                    alert['Exp_Date'] = option_exp_date
                    alerts.append(alert)

        except Exception as e:
            print(e)

        return alerts

    def get_alerts(self, start_time):
        """ METHOD RUNS THE DISCORD ALERT AND/OR GMAIL ALERT AT EACH INSTANCE.
            newAlerts WILL FILTER OUT THE ALERTS & POPULATE c.OPTIONLIST.
        """

        trade_alerts = []
        if RUN_DISCORD:
            discord_alerts = discord_scanner.discord_messages(start_time, mins=2)
            if discord_alerts != None:
                for alert in discord_alerts:
                    position = mongo_helpers.find_mongo_analysisPosition(self, alert['Pre_Symbol'], alert['Entry_Date'])
                    if position != True:
                        trade_alerts.append(alert)

        if RUN_GMAIL:
            gmail_alerts = self.gmail.getEmails()
            gmail_alerts = helper_functions.formatGmailAlerts(gmail_alerts)
            if gmail_alerts is not None:
                for alert in gmail_alerts:
                    position = mongo_helpers.find_mongo_analysisPosition(self, alert['Pre_Symbol'], alert['Entry_Date'])
                    if position is not True:
                        trade_alerts.append(alert)

        if RUN_LIST:
            current_time = datetime.now(pytz.timezone(TIMEZONE)).strftime('%H:%M:%S')
            """ SCAN EVERY 5m - ("XX:00:XX" or "XX:05:XX) """
            if current_time[-4] == "0" or current_time[-4] == "5":
                for live_trader in self.traders.values():
                        list_alerts = self.get_list_alerts(live_trader)
                        for alert in list_alerts:
                            trade_alerts.append(alert)

        return trade_alerts

    def OPTIONLIST_find_one(self, alert):
        symbol = alert['Symbol']
        option_type = alert['Option_Type']

        position = next((x for x in c.OPTIONLIST if x["Symbol"] == symbol and x["Option_Type"] == option_type), None)

        if position is None:
            return False
        else:
            return True

    def set_alerts(self, alerts):

        for alert in alerts:

            try:
                for api_trader in self.traders.values():
                    df = td_helpers.getOptionChain(api_trader, alert['Symbol'], alert['Option_Type'], alert['Exp_Date'])
                    df1 = td_helpers.getSingleOption(df)

                if alert['Strategy'] == "LIST":
                    if df1 is None:

                        message = f"No possible contracts for {alert['Symbol']} - {alert['Option_Type']}"
                        print(message)
                        # discord_helpers.send_discord_alert(message)
                        continue

                    alert = {
                        "Symbol": alert['Symbol'],
                        "Pre_Symbol": df1['pre_symbol'],
                        "Side": "BUY_TO_OPEN",
                        "Exp_Date": alert['Exp_Date'],
                        "Option_Type": alert['Option_Type'],
                        "Strike_Price": df1['strikePrice'],
                        "Strategy": alert['Strategy'],
                        "Asset_Type": "OPTION",
                        "HedgeAlert": "FALSE",
                        "Entry_Date": datetime.now()
                    }

                if df1 is None:
                    small_df = td_helpers.getPotentialDF(df)
                    message = f"{small_df} \n" \
                              f"No possible contracts for {alert['Symbol']} - {alert['Option_Type']}"
                    print(message)
                    # discord_helpers.send_discord_alert(message)
                    continue

                else:
                    option_symbol = df1["pre_symbol"]
                    ask = df1["ask"]
                    bid = df1["bid"]
                    last = df1["last"]
                    volume = df1["totalVolume"]
                    delta = df1["delta"]
                    oi = df1["openInterest"]

                    alert['option_symbol'] = option_symbol
                    alert['ask'] = float(ask)
                    alert['bid'] = float(bid)
                    alert['last'] = float(last)
                    alert['volume'] = float(volume)
                    alert['delta'] = float(delta)
                    alert['oi'] = float(oi)

                    if not TRADE_HEDGES and alert['HedgeAlert'] == "TRUE":
                        print(f'Not trading {alert["Pre_Symbol"]}   hedge is True')

                    """ 
                    WE'RE DECIDING WHETHER OR NOT TO BUY IT RIGHT HERE 
                    """

                    message = f"\n FOUND --> {option_symbol} --> \n" \
                              f"last={last} delta={delta} volume={volume} OI={oi} \n"
                    print(message)
                    # discord_helpers.send_discord_alert(message)

                    if config.RUN_TA:

                        """  ALL ALERTS HAVE TO BE SCANNED UNTIL THEY MEET THE TA CRITERIA  """
                        for api_trader in self.traders.values():
                            df = techanalysis.get_TA(alert, api_trader)
                            buy_signal = techanalysis.buy_criteria(df, alert, api_trader)

                            """  IF BUY SIGNAL == TRUE THEN BUY!  """
                            if buy_signal:
                                c.OPTIONLIST.append(alert)
                                self.set_trader(alert, trade_signal="BUY", trade_type="LIMIT")
                                c.DONTTRADELIST.append(alert)

                            else:
                                position = self.OPTIONLIST_find_one(alert)
                                if position is True:
                                    c.DONTTRADELIST.append(alert)
                                else:
                                    c.OPTIONLIST.append(alert)

                    else:
                        buy_signal = True
                        c.OPTIONLIST.append(alert)
                        self.set_trader(alert, trade_signal="BUY", trade_type="LIMIT")
                        c.DONTTRADELIST.append(alert)

                    mongo_helpers.set_mongo_analysisPosition(self, alert)

            except Exception as e:

                logging.error(e)


    @exception_handler
    def get_tradeFormat(self, live_trader, value, signal_type, trade_type, isRunner):

        trade_data = []

        if signal_type is None:
            return trade_data

        if isRunner == "TRUE":
            for api_trader in self.traders.values():
                strategy = value['Strategy']
                exp_date = value['Exp_Date']
                symbol = value["Symbol"]
                df = td_helpers.getOptionChain(api_trader, value['Symbol'], value['Option_Type'],
                                               value['Exp_Date'])
                value = td_helpers.getSingleOption(df, isRunner=True)
                if value is None:
                    small_df = td_helpers.getPotentialDF(df)
                    message = f"{small_df} \n" \
                              f"Didn't find any running contracts for {symbol}"
                    print(message)
                    discord_helpers.send_discord_alert(message)
                    return None

                value = value.rename({"totalVolume": "volume", "openInterest": "oi", "putCall": "Option_Type", "strikePrice": "Strike_Price", "symbol": "Pre_Symbol"})

                value['Strategy'] = strategy
                value['Exp_Date'] = exp_date
                value['Symbol'] = symbol
        position = live_trader.open_positions.find_one(
            {"Trader": live_trader.user["Name"], "Symbol": value['Symbol'], "Strategy": value['Strategy']})

        if signal_type == "CLOSE" and position is not None:

            obj = {
                "Symbol": position['Symbol'],
                "Side": "SELL_TO_CLOSE",
                "Pre_Symbol": position["Pre_Symbol"],
                "Exp_Date": position['Exp_Date'],
                "Strike_Price": position['Strike_Price'],
                "Option_Type": position["Option_Type"],
                "Strategy": "STANDARD",
                "Asset_Type": "OPTION",
                "Trade_Type": trade_type,
                "isRunner": isRunner
            }
            trade_data.append(obj)

        elif signal_type == "BUY" or signal_type == "SELL":

            if value['Strategy'] != "OpenCV":

                obj = {
                    "Symbol": value['Symbol'],
                    "Side": "BUY_TO_OPEN",
                    "Pre_Symbol": value['pre_symbol'] if isRunner == "TRUE" else value['Pre_Symbol'],
                    "Exp_Date": str(value['Exp_Date']),
                    "Strike_Price": str(value['Strike_Price']),
                    "Option_Type": value['Option_Type'],
                    "Strategy": value['Strategy'],
                    "Asset_Type": "OPTION",
                    "Trade_Type": trade_type,
                    "isRunner": isRunner
                }

                if isRunner:
                    obj['Volume'] = value['volume']
                    obj['Open_Interest'] = value['oi']
                    obj['Entry_Price'] = value['last']
                    if value['Option_Type'] == "CALL":
                        obj['Delta'] = value['delta']
                    else:
                        obj['Delta'] = value['delta'] * -1

                trade_data.append(obj)

            else:
                if isRunner != "TRUE":
                    option_type = "CALL" if signal_type == "BUY" else "PUT"

                option_exp_date = helper_functions.find_option_expDate(live_trader, TRADE_SYMBOL)
                df = td_helpers.getOptionChain(live_trader, TRADE_SYMBOL, option_type, option_exp_date)

                if isRunner == "TRUE":
                    value = td_helpers.getSingleOption(df, isRunner=True)
                else:
                    value = td_helpers.getSingleOption(df)

                if value is None:
                    small_df = td_helpers.getPotentialDF(df)
                    message = f'{small_df} \n' \
                              f'No possible {option_type} contracts for {TRADE_SYMBOL}'
                    # discord_helpers.send_discord_alert(message)
                    print(message)
                    return None

                option_symbol = value["pre_symbol"]
                last = value["last"]
                volume = value["totalVolume"]
                delta = value["delta"]
                oi = value["openInterest"]
                print(option_symbol + " --> mark=" + str(last) + " delta=" + str(delta) + " volume=" + str(
                            volume))

                obj = {
                    "Symbol": TRADE_SYMBOL,
                    "Side": "BUY_TO_OPEN",
                    "Pre_Symbol": option_symbol,
                    "Exp_Date": option_exp_date,
                    "Strike_Price": value['strikePrice'],
                    "Option_Type": option_type,
                    "Strategy": "OpenCV",
                    "Asset_Type": "OPTION",
                    "Trade_Type": trade_type,
                    "isRunner": isRunner,
                    "Delta": delta if option_type == "CALL" else delta * -1,
                    "Volume": volume,
                    "OI": oi
                }

                trade_data.append(obj)

        return trade_data

    @exception_handler
    def set_trader(self, alert, trade_signal, trade_type="LIMIT", **kwargs):
        """ METHOD RUNS THE TWO METHODS ABOVE AND THEN RUNS LIVE TRADER METHOD RUNTRADER FOR EACH INSTANCE.
        """
        isRunner = kwargs.get('isRunner', False)

        if not RUN_TRADIER:

            for api_trader in self.traders.values():
                temp_trade_data = self.get_tradeFormat(api_trader, alert, trade_signal, trade_type,
                                                       "TRUE" if isRunner else "FALSE")
                if temp_trade_data is None:
                    return

                for trade_data in temp_trade_data:
                    api_trader.runTrader(trade_data)

        else:

            # UPDATE STATUS
            for mongo_trader in self.traders.values():
                temp_trade_data = self.get_tradeFormat(mongo_trader, alert, trade_signal, trade_type,
                                                       "TRUE" if isRunner else "FALSE")
                if temp_trade_data is None:
                    return

                for trade_data in temp_trade_data:
                    self.tradier.runTrader(mongo_trader, trade_data)

    def runTradingPlatform(self):
        """ METHOD RUNS THE TWO METHODS ABOVE AND THEN RUNS LIVE TRADER METHOD RUNTRADER FOR EACH INSTANCE.
        """

        self.start_time = datetime.now(pytz.timezone(TIMEZONE))

        message = f'Bot is booting up, its currently: {self.start_time}'
        discord_helpers.send_discord_alert(message)
        print(message)

        connected = self.connectALL()

        """  THIS RUNS THE TD INSTANCE  """
        self.setupTraders()

        alertScanner = AlertScanner.AlertScanner()
        initiation = False
        SHUT_DOWN = False
        current_trend = None

        while connected:

            """  CHECK THE TIME  """
            current_time = datetime.now(pytz.timezone(TIMEZONE)).strftime('%H:%M:%S')

            """  SELL OUT OF ALL POSITIONS AT SELL_ALL_POSITION TIME  """
            if DAY_TRADE and not SHUT_DOWN:
                if current_time > SELL_ALL_POSITIONS:
                    print("Shutdown time has passed, all positions now CLOSING")
                    if RUN_TRADIER:
                        self.tradier.cancelALLorders()
                    open_positions = mongo_helpers.get_mongo_openPositions(self)
                    for open_position in open_positions:
                        self.set_trader(open_position, trade_signal="CLOSE", trade_type="MARKET")
                    SHUT_DOWN = True

                    """  ONCE MARKET IS CLOSED CLOSED, CLOSE ALL CONNECTIONS TO MONGO  """
                    self.isAlive = False
                    time.sleep(2)
                    disconnect = mongo_helpers.disconnect(self)
                    if disconnect:
                        connected = False
                        message = f'Bot is shutting down, its currently: {self.start_time}'
                        discord_helpers.send_discord_alert(message)
                        print(message)
                        break

            """  THIS WILL COMPILE THE ALERTS FROM DISCORD & GMAIL  """
            trade_alerts = self.get_alerts(self.start_time)

            """ THIS WILL BLOCK ANY NEW ALERTS YOU MAY GET AT END OF DAY """
            if current_time > TURN_OFF_TRADES:
                print(f'It is {TURN_OFF_TRADES}, closing all queued trades')
                c.OPTIONLIST.clear()

            """  THIS WILL PUT ALL ALERTS INTO C.OPTIONLIST TO BE TRADED & DO AN INITIAL BUY SCAN """
            self.set_alerts(trade_alerts)

            """  CLEAN UP OUR OLD ORDERS  """
            for order in c.DONTTRADELIST:
                if order in c.OPTIONLIST:
                    c.OPTIONLIST.remove(order)

            if config.RUN_TA and (RUN_GMAIL or RUN_DISCORD or RUN_LIST):
                """ SCAN EVERY 5m - ("XX:00:XX" or "XX:05:XX) """
                if current_time[-4] == "0" or current_time[-4] == "5":

                    """  LEFT OVER ALERTS HAVE TO BE SCANNED UNTIL THEY MEET THE TA CRITERIA  """
                    for api_trader in self.traders.values():
                        if len(c.OPTIONLIST) == 0:
                            pass

                        else:
                            for value in tqdm(c.OPTIONLIST, desc="Scanning BUY signals..."):
                                if value['Strategy'] == "OpenCV":
                                    continue
                                df = techanalysis.get_TA(value, api_trader)
                                buy_signal = techanalysis.buy_criteria(df, value, api_trader)

                                """  IF BUY SIGNAL == TRUE THEN BUY!  """
                                if buy_signal:
                                    self.set_trader(value, trade_signal="BUY", trade_type="LIMIT")
                                    c.DONTTRADELIST.append(value)
                        print('\n')

                    """
                    RUN SELL_TA CRITERIA
                    """
                    if config.RUN_SELL_TA:
                        for api_trader in self.traders.values():
                            open_positions = mongo_helpers.get_mongo_openPositions(self)
                            if len(open_positions) == 0:
                                pass
                            else:
                                for open_position in tqdm(open_positions, desc="Scanning SELL signals..."):
                                    if open_position['Strategy'] == "OpenCV":
                                        continue
                                    df = techanalysis.get_TA(open_position, api_trader)
                                    sell_signal = techanalysis.sell_criteria(df, open_position)
                                    if sell_signal:
                                        if RUN_LIVE_TRADER:
                                            if RUN_TRADIER:
                                                for childOrder in open_position['childOrderStrategies']:
                                                    self.tradier.cancel_order(childOrder['Order_ID'])
                                                self.set_trader(open_position, trade_signal="CLOSE", trade_type="MARKET")
                                            else:
                                                print('no exit criteria for TD intraday technical analysis yet')
                                        else:
                                            mongo_helpers.close_mongo_position(self, open_position['_id'])

            else:
                buy_signal = True
                for value in c.OPTIONLIST:
                    self.set_trader(value, trade_signal="BUY", trade_type="LIMIT")
                    c.DONTTRADELIST.append(value)

            """" 
            RUN OPENCV FOR config.TRADE_SYMBOL ONLY 
            """
            if RUN_OPENCV and not SHUT_DOWN:
                switcher = {
                    "BUY": "CALL",
                    "SELL": "PUT",
                    "CLOSE": 0,
                    "Not Available": 99999
                }

                trade_signal = alertScanner.scanVisualAlerts()
                if config.GIVE_CONTINUOUS_UPDATES:
                    print(f'current_trend: {trade_signal}')
                new_trend = switcher.get(trade_signal)
                if initiation is False:
                    current_trend = new_trend
                    initiation = True

                elif trade_signal == "Not Available":
                    current_trend = new_trend

                elif trade_signal is not None and new_trend != current_trend:
                    message = f'TradingBOT just saw a possible trade: {trade_signal}'
                    discord_helpers.send_discord_alert(message)
                    print(message)

                    tos_signal = run_opencv.run(alertScanner, new_trend)
                    if tos_signal:
                        value = {
                            "Symbol": TRADE_SYMBOL,
                            "Strategy": "OpenCV",
                            "Option_Type": trade_signal
                        }
                        for api_trader in self.traders.values():
                            df = techanalysis.get_TA(value, api_trader)
                            signal = techanalysis.openCV_criteria(df, value, api_trader)
                            if signal:
                                self.set_trader(value, trade_signal=trade_signal, trade_type="LIMIT")
                                current_trend = new_trend

            """  
            USE WEBSOCKET TO PRINT CURRENT PRICES - IF STRATEGY USES WEBSOCKET, IT MIGHT SELL OUT USING IT  
            """
            if RUN_WEBSOCKET:
                streamprice.streamPrice(self)


            """  CHECK ON ALL ORDER STATUSES  """
            if RUN_TRADIER:
                self.tradier.updateStatus()
            else:
                for api_trader in self.traders.values():
                    api_trader.updateStatus()

            """  THIS KEEPS TRACK OF ANY TIME THE API GETS AN ERROR. 
            IF ERRORS ARE > 10, YOU MIGHT WANT TO CHECK OUT YOUR REQUESTS  """
            if self.error > 0:
                print(f'errors: {self.error}')
                if self.error >= 60:
                    discord_helpers.send_discord_alert(f'self.errors: {self.error}')
                    c.OPTIONLIST.clear()
                    self.error = 0

            time.sleep(helper_functions.selectSleep())
            if config.GIVE_CONTINUOUS_UPDATES:
                print('\n')

    def run(self):

        runBacktest = True

        while True:

            current_time = datetime.now(pytz.timezone(TIMEZONE)).strftime('%H:%M:%S')

            try:

                current_time = datetime.now(pytz.timezone(TIMEZONE)).strftime('%H:%M:%S')
                day = datetime.now(pytz.timezone(TIMEZONE)).strftime('%a')
                weekends = ["Sat", "Sun"]

                if current_time < RUN_BACKTEST_TIME:
                    runBacktest = False

                if SHUTDOWN_TIME > current_time >= TURN_ON_TIME:
                # if SHUTDOWN_TIME >= current_time >= TURN_ON_TIME and day not in weekends:
                    self.runTradingPlatform()

                if not runBacktest:
                    if TEST_CLOSED_POSITIONS or TEST_ANALYSIS_POSITIONS:
                        self.connectALL()
                    study = backtest.run(self)
                    if study:
                        runBacktest = True
                        disconnect = mongo_helpers.disconnect(self)
                        if disconnect:
                            message = f'Bot is shutting down, its currently: {current_time}'
                            discord_helpers.send_discord_alert(message)
                            print(message)

                else:
                    print(f'sleeping 10m intermittently until {TURN_ON_TIME} or {RUN_BACKTEST_TIME} - '
                          f'current_time: {current_time}')
                    time.sleep(10*60)

            except Exception:
                message = f"Just received an error: {traceback.format_exc()}"
                discord_helpers.send_discord_alert(message)
                print(message)
                break


if __name__ == "__main__":
    """ START OF SCRIPT.
        INITIALIZES MAIN CLASS AND STARTS RUN METHOD ON WHILE LOOP WITH A DYNAMIC SLEEP TIME.
    """

    main = Main()
    main.run()

    """ IF YOU JUST WANT TO RUN BACKTEST, 
    COMMENT OUT "main.run()" AND UNCOMMENT THESE LINES BELOW """
    # main.connectALL()
    # backtest.run(main)
