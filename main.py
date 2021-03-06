# imports
import time
import logging
import os
import traceback
import math

import config
from datetime import datetime
import pytz
import constants as c
import vectorbt as vbt

from api_trader import ApiTrader
from td_websocket.stream import TDWebsocket
from tdameritrade import TDAmeritrade
from gmail import Gmail
from mongo import MongoDB, mongo_helpers
from tradier import TradierTrader
from threading import Thread
from tqdm import tqdm
from open_cv import AlertScanner, run_opencv

from assets import pushsafer, helper_functions, techanalysis, streamprice
from assets.exception_handler import exception_handler
from assets.timeformatter import Formatter
from assets.multifilehandler import MultiFileHandler
from assets.tasks import Tasks
from discord import discord_helpers, discord_scanner
from backtest import backtest

DAY_TRADE = config.DAY_TRADE
RUN_TRADIER = config.RUN_TRADIER
RUN_DISCORD = config.RUN_DISCORD
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
OPTION_PRICE_INCREMENT = config.OPTION_PRICE_INCREMENT
TRADE_SYMBOL = config.TRADE_SYMBOL.upper()


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
            if gmail_alerts != None:
                for alert in gmail_alerts:
                    position = mongo_helpers.find_mongo_analysisPosition(self, alert['Pre_Symbol'], alert['Entry_Date'])
                    if position != True:
                        trade_alerts.append(alert)

        return trade_alerts

    def OPTIONLIST_find_one(self, alert):
        symbol = alert['Symbol']

        position = next((x for x in c.OPTIONLIST if x["Symbol"] == symbol), None)

        if position is None:
            return False
        else:
            return True

    def set_alerts(self, alerts):

        for alert in alerts:

            if not IS_TESTING:

                try:
                    url = f"https://api.tdameritrade.com/v1/marketdata/chains?symbol={alert['Symbol']}&" \
                          f"contractType={alert['Option_Type']}&" \
                          f"includeQuotes=FALSE&" \
                          f"strike={alert['Strike_Price']}&" \
                          f"fromDate={alert['Exp_Date']}&" \
                          f"toDate={alert['Exp_Date']}"
                    resp = list(self.traders.values())[0].tdameritrade.sendRequest(url)
                    expdatemapkey = alert['Option_Type'].lower() + "ExpDateMap"

                    if list(resp.keys())[0] == "error" or resp['status'] == "FAILED":
                        print(f'error scanning for {alert["Pre_Symbol"]}')
                        # print(resp)
                        self.error += 1
                        c.DONTTRADELIST.append(alert)
                        continue

                    else:
                        for dt in resp[expdatemapkey]:
                            for strikePrice in resp[expdatemapkey][dt]:
                                option_symbol = resp[expdatemapkey][dt][strikePrice][0]["symbol"]
                                ask = float(resp[expdatemapkey][dt][strikePrice][0]["ask"])
                                bid = float(resp[expdatemapkey][dt][strikePrice][0]["bid"])
                                last = float(resp[expdatemapkey][dt][strikePrice][0]["last"])
                                volume = float(resp[expdatemapkey][dt][strikePrice][0]["totalVolume"])
                                delta = float(resp[expdatemapkey][dt][strikePrice][0]["delta"])
                                oi = float(resp[expdatemapkey][dt][strikePrice][0]["openInterest"])
                                # print(f"\n FOUND --> {option_symbol} --> \n"
                                #       f"last={last} delta={delta} volume={volume} OI={oi} \n")

                        if not TRADE_HEDGES and alert['HedgeAlert'] == "TRUE":
                            print(f'Not trading {alert["Pre_Symbol"]}   hedge is True')

                        else:
                            if ask > config.MAX_OPTIONPRICE or ask < config.MIN_OPTIONPRICE or volume < config.MIN_VOLUME \
                                    or abs(delta) < config.MIN_DELTA:
                                message = f'Not trading {alert["Pre_Symbol"]}   ask is: {ask}   volume is: {volume}   delta is: {delta} '
                                print(message)

                            else:
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
                                            if position == True:
                                                c.DONTTRADELIST(alert)
                                            else:
                                                c.OPTIONLIST.append(alert)

                                else:
                                    buy_signal = True
                                    c.OPTIONLIST.append(alert)
                                    self.set_trader(alert, trade_signal="BUY", trade_type="LIMIT")
                                    c.DONTTRADELIST.append(alert)

                        alert['Open_Interest'] = oi
                        alert['Volume'] = volume
                        alert['Entry_Price'] = bid
                        mongo_helpers.set_mongo_analysisPosition(self, alert)

                except Exception as e:

                    logging.error(e)

            else:

                if alert['HedgeAlert'] == "TRUE":

                    print(f'Not trading {alert["Pre_Symbol"]}   hedge is True')
                    alert['Open_Interest'] = oi
                    alert['Volume'] = volume
                    alert['Entry_Price'] = bid
                    print(f'testing: would have sent to mongo Analysis')

                else:

                    print(f'testing: would have sent to mongo Analysis')
                    c.OPTIONLIST.append(alert)

    @exception_handler
    def get_tradeFormat(self, live_trader, value, signal_type, trade_type, isRunner):

        trade_data = []

        if signal_type is None:
            return trade_data

        position = live_trader.open_positions.find_one(
            {"Trader": live_trader.user["Name"], "Symbol": value['Symbol'], "Strategy": value['Strategy']})

        if value['Strategy'] != "OpenCV":

            if signal_type == "CLOSE" and position is not None:

                obj = {
                    "Symbol": value['Symbol'],
                    "Side": "SELL_TO_CLOSE",
                    "Pre_Symbol": value['Pre_Symbol'],
                    "Exp_Date": value['Exp_Date'],
                    "Strike_Price": value['Strike_Price'],
                    "Option_Type": value['Option_Type'],
                    "Strategy": "STANDARD",
                    "Asset_Type": "OPTION",
                    "Trade_Type": trade_type,
                    "isRunner": isRunner
                }
                trade_data.append(obj)

            elif signal_type == "BUY":
                if not IS_TESTING:
                    url = f"https://api.tdameritrade.com/v1/marketdata/chains?symbol={value['Symbol']}&" \
                          f"contractType={value['Option_Type']}&" \
                          f"includeQuotes=FALSE&" \
                          f"strike={value['Strike_Price']}&" \
                          f"fromDate={value['Exp_Date']}&" \
                          f"toDate={value['Exp_Date']}"
                    resp = live_trader.tdameritrade.sendRequest(url)
                    expdatemapkey = value['Option_Type'].lower() + "ExpDateMap"
                    if list(resp.keys())[0] == "error" or list(resp.values())[1] == "FAILED":
                        print(f"Received an error for {value['Symbol']}")
                        self.error += 1
                        return
                    else:
                        for dt in resp[expdatemapkey]:
                            for strikePrice in resp[expdatemapkey][dt]:
                                last = resp[expdatemapkey][dt][strikePrice][0]["last"]
                                volume = resp[expdatemapkey][dt][strikePrice][0]["totalVolume"]
                                delta = resp[expdatemapkey][dt][strikePrice][0]["delta"]
                                oi = resp[expdatemapkey][dt][strikePrice][0]["openInterest"]

                obj = {
                    "Symbol": value['Symbol'],
                    "Side": "BUY_TO_OPEN",
                    "Pre_Symbol": value['Pre_Symbol'],
                    "Exp_Date": value['Exp_Date'],
                    "Strike_Price": value['Strike_Price'],
                    "Option_Type": value['Option_Type'],
                    "Strategy": value['Strategy'],
                    "Asset_Type": "OPTION",
                    "Trade_Type": trade_type,
                    "isRunner": isRunner
                }

                if not IS_TESTING:
                    obj['Volume'] = volume
                    obj['Open_Interest'] = oi
                    obj['Entry_Price'] = last
                    obj['Delta'] = delta

                trade_data.append(obj)

        else:

            if signal_type == "CLOSE":
                if position is not None:
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

            else:
                option_type = "CALL" if signal_type == "BUY" else "PUT"

                option_exp_date = helper_functions.find_option_expDate(live_trader, TRADE_SYMBOL)
                resp = run_opencv.get_optioncontract(live_trader, TRADE_SYMBOL, option_exp_date, option_type)
                expdatemapkey = option_type.lower() + "ExpDateMap"

                for dt in resp[expdatemapkey]:
                    for strikePrice in resp[expdatemapkey][dt]:
                        option_symbol = resp[expdatemapkey][dt][strikePrice][0]["symbol"]
                        last = resp[expdatemapkey][dt][strikePrice][0]["last"]
                        volume = resp[expdatemapkey][dt][strikePrice][0]["totalVolume"]
                        delta = resp[expdatemapkey][dt][strikePrice][0]["delta"]
                        print(option_symbol + " --> mark=" + str(last) + " delta=" + str(delta) + " volume=" + str(
                            volume))

                obj = {
                    "Symbol": TRADE_SYMBOL,
                    "Side": "BUY_TO_OPEN",
                    "Pre_Symbol": option_symbol,
                    "Exp_Date": option_exp_date,
                    "Strike_Price": strikePrice,
                    "Option_Type": option_type,
                    "Strategy": "OpenCV",
                    "Asset_Type": "OPTION",
                    "Trade_Type": trade_type,
                    "isRunner": isRunner
                }
                trade_data.append(obj)

        return trade_data

    @exception_handler
    def set_trader(self, value, trade_signal, trade_type="LIMIT", **kwargs):
        """ METHOD RUNS THE TWO METHODS ABOVE AND THEN RUNS LIVE TRADER METHOD RUNTRADER FOR EACH INSTANCE.
        """
        isRunner = kwargs.get('isRunner', False)

        if not RUN_TRADIER:

            self.setupTraders()

            for api_trader in self.traders.values():
                api_trader.updateStatus()
                temp_trade_data = self.get_tradeFormat(api_trader, value, trade_signal, trade_type,
                                                       "TRUE" if isRunner else "FALSE")
                for trade_data in temp_trade_data:
                    api_trader.runTrader(trade_data)

        else:

            # UPDATE STATUS
            for mongo_trader in self.traders.values():
                temp_trade_data = self.get_tradeFormat(mongo_trader, value, trade_signal, trade_type,
                                                       "TRUE" if isRunner else "FALSE")
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

        alertScanner = AlertScanner.AlertScanner()
        initiation = False
        SHUT_DOWN = False
        current_trend = None

        while connected:

            """  THIS RUNS THE TD INSTANCE  """
            self.setupTraders()

            """  CHECK THE TIME  """
            current_time = datetime.now(pytz.timezone(TIMEZONE)).strftime('%H:%M:%S')

            """  SELL OUT OF ALL POSITIONS AT SELL_ALL_POSITION TIME  """
            if DAY_TRADE:
                if SHUTDOWN_TIME > current_time > SELL_ALL_POSITIONS and not SHUT_DOWN:
                    print("Shutdown time has passed, all positions now CLOSING")
                    if RUN_TRADIER:
                        self.tradier.cancelALLorders()
                    open_positions = mongo_helpers.get_mongo_openPositions(self)
                    for open_position in open_positions:
                        self.set_trader(open_position, trade_signal="CLOSE", trade_type="MARKET")
                    SHUT_DOWN = True

            """  ONCE MARKET IS CLOSED CLOSED, CLOSE ALL CONNECTIONS TO MONGO  """
            if current_time >= SHUTDOWN_TIME:
                self.isAlive = False
                time.sleep(2)
                disconnect = mongo_helpers.disconnect(self)
                if disconnect:
                    connected = False
                    message = f'Bot is shutting down, its currently: {self.start_time}'
                    discord_helpers.send_discord_alert(message)
                    print(message)
                    break

            elif current_time > TURN_OFF_TRADES:
                print(f'It is {TURN_OFF_TRADES}, closing all queued trades')
                c.OPTIONLIST.clear()

            """  THIS WILL COMPILE THE ALERTS FROM DISCORD & GMAIL  """
            trade_alerts = self.get_alerts(self.start_time)

            """  THIS WILL PUT ALL ALERTS INTO C.OPTIONLIST TO BE TRADED & DO AN INITIAL BUY SCAN """
            self.set_alerts(trade_alerts)

            """  CLEAN UP OUR OLD ORDERS  """
            for order in c.DONTTRADELIST:
                if order in c.OPTIONLIST:
                    c.OPTIONLIST.remove(order)

            if config.RUN_TA and (RUN_GMAIL or RUN_DISCORD):
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
                                                for childorder in open_position['childOrderStrategies']:
                                                    self.tradier.cancel_order(childorder['Order_ID'])
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
                print(f'current_trend: {trade_signal}')
                new_trend = switcher.get(trade_signal)
                if initiation is False:
                    current_trend = new_trend
                    initiation = True

                if trade_signal is not None and new_trend != current_trend:
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
            print('\n')

    def run(self):

        runBacktest = True

        while True:

            current_time = datetime.now(pytz.timezone(TIMEZONE)).strftime('%H:%M:%S')
            if current_time[-2:] == '00':

                try:

                    current_time = datetime.now(pytz.timezone(TIMEZONE)).strftime('%H:%M:%S')
                    day = datetime.now(pytz.timezone(TIMEZONE)).strftime('%a')
                    weekends = ["Sat", "Sun"]

                    if current_time < RUN_BACKTEST_TIME:
                        runBacktest = False

                    # if SHUTDOWN_TIME > current_time >= TURN_ON_TIME:
                    if SHUTDOWN_TIME > current_time >= TURN_ON_TIME and day not in weekends:
                        self.runTradingPlatform()

                    elif not runBacktest:
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
