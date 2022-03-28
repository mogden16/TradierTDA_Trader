# imports
import time
import logging
import os

import config
from datetime import datetime
import pytz
import constants as c

from api_trader import ApiTrader
from tdameritrade import TDAmeritrade
from gmail import Gmail
from mongo import MongoDB
from tradier import TradierTrader, tradier_helpers

from assets import pushsafer, helper_functions, techanalysis
from assets.exception_handler import exception_handler
from assets.timeformatter import Formatter
from assets.multifilehandler import MultiFileHandler
from discord import discord_helpers, discord_scanner

RUN_TRADIER = config.RUN_TRADIER
RUN_DISCORD = config.RUN_DISCORD
RUN_GMAIL = config.RUN_GMAIL
IS_TESTING = config.IS_TESTING
TRADE_HEDGES = config.TRADE_HEDGES
RUN_LIVE_TRADER = config.RUN_LIVE_TRADER
RUN_WEBSOCKET = config.RUN_WEBSOCKET

class Main:

    def __init__(self):

        self.error = 0

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

                            time.sleep(0.1)

                        else:

                            self.not_connected.append(account_id)

                    self.accounts.append(account_id)

            except Exception as e:

                logging.error(e)

    def get_mongo_openPositions(self):
        col = self.mongo.open_positions
        llist = list(col.find({}))
        return llist
    def get_mongo_closedPositions(self):
        col = self.mongo.closed_positions
        llist = list(col.find({}))
        return llist
    def get_mongo_analysisPositions(self):
        col = self.mongo.analysis
        llist = list(col.find({}))
        return llist
    def get_mongo_users(self):
        col = self.mongo.users
        llist = list(col.find({}))
        return llist
    def get_mongo_queue(self):
        col = self.mongo.queue
        llist = list(col.find({}))
        return llist

    def set_mongo_openPositions(self, obj):
        col = self.mongo.open_positions
        inst = col.insert_one(obj)
        return
    def set_mongo_closedPosition(self, obj):
        col = self.mongo.closed_positions
        inst = col.insert_one(obj)
        return
    def set_mongo_analysisPosition(self, obj):
        col = self.mongo.analysis
        inst = col.insert_one(obj)
        return
    def set_mongo_user(self, obj):
        col = self.mongo.users
        inst = col.insert_one(obj)
        return
    def set_mongo_queue(self, obj):
        col = self.mongo.queue
        inst = col.insert_one(obj)
        return

    def find_mongo_openPosition(self, trade_symbol, timestamp):
        col = self.mongo.open_positions
        position = col.find_one({"Pre_Symbol": trade_symbol, "Entry_Date": timestamp})
        if position != None:
            return True
        else:
            return False
    def find_mongo_closedPosition(self, trade_symbol, timestamp):
        col = self.mongo.closed_positions
        position = col.find_one({"Pre_Symbol": trade_symbol, "Entry_Date": timestamp})
        if position != None:
            return True
        else:
            return False
    def find_mongo_analysisPosition(self, trade_symbol, timestamp):
        col = self.mongo.analysis
        position = col.find_one({"Pre_Symbol": trade_symbol, "Entry_Date": timestamp})
        if position != None:
            return True
        else:
            return False
    def find_mongo_queue(self, trade_symbol, timestamp):
        col = self.mongo.queue
        position = col.find_one({"Pre_Symbol": trade_symbol, "Entry_Date": timestamp})
        if position != None:
            return True
        else:
            return False

    def get_alerts(self, start_time):
        """ METHOD RUNS THE DISCORD ALERT AND/OR GMAIL ALERT AT EACH INSTANCE.
            newAlerts WILL FILTER OUT THE ALERTS & POPULATE c.OPTIONLIST.
        """

        trade_alerts = []
        if RUN_DISCORD:
            discord_alerts = discord_scanner.discord_messages(start_time)
            if discord_alerts != None:
                for alert in discord_alerts:
                    position = self.find_mongo_analysisPosition(alert['Pre_Symbol'], alert['Entry_Date'])
                    if position != True:
                        trade_alerts.append(alert)

        if RUN_GMAIL:
            gmail_alerts = self.gmail.getEmails()
            gmail_alerts = helper_functions.formatGmailAlerts(gmail_alerts)
            if gmail_alerts != None:
                for alert in gmail_alerts:
                    position = self.find_mongo_analysisPosition(alert['Pre_Symbol'], alert['Entry_Date'])
                    if position != True:
                        trade_alerts.append(alert)

        return trade_alerts

    def set_alerts(self, alerts):

        for alert in alerts:

            if not IS_TESTING:

                url = f"https://api.tdameritrade.com/v1/marketdata/chains?symbol={alert['Symbol']}&contractType={alert['Option_Type']}&includeQuotes=FALSE&strike={alert['Strike_Price']}&fromDate={alert['Exp_Date']}&toDate={alert['Exp_Date']}"
                resp = list(self.traders.values())[0].tdameritrade.sendRequest(url)
                expdatemapkey = alert['Option_Type'].lower() + "ExpDateMap"

                if list(resp.keys())[0] == "error":
                    print(f'error scanning for {alert["Pre_Symbol"]}')
                    print(resp)
                    self.error += 1
                    return

                else:
                    for dt in resp[expdatemapkey]:
                        for strikePrice in resp[expdatemapkey][dt]:
                            option_symbol = resp[expdatemapkey][dt][strikePrice][0]["symbol"]
                            ask = resp[expdatemapkey][dt][strikePrice][0]["ask"]
                            bid = resp[expdatemapkey][dt][strikePrice][0]["bid"]
                            last = resp[expdatemapkey][dt][strikePrice][0]["last"]
                            volume = resp[expdatemapkey][dt][strikePrice][0]["totalVolume"]
                            delta = resp[expdatemapkey][dt][strikePrice][0]["delta"]
                            oi = resp[expdatemapkey][dt][strikePrice][0]["openInterest"]
                            print(f"\n FOUND --> {option_symbol} --> \n"
                                  f"last={last} delta={delta} volume={volume} OI={oi} \n")

                    if not TRADE_HEDGES and alert['HedgeAlert'] == "TRUE":
                        print(f'Not trading {alert["Pre_Symbol"]}   hedge is True')

                    else:
                        if ask > config.MAX_OPTIONPRICE or ask < config.MIN_OPTIONPRICE or volume < config.MIN_VOLUME or abs(delta) < config.MIN_DELTA:
                            message = f'Not trading {alert["Pre_Symbol"]}   ask is: {ask}   volume is: {volume}   delta is: {delta} '
                            print(message)

                        else:
                            message = f'Bot just Queued {alert["Pre_Symbol"]}   ask is: {ask}   volume is: {volume}   delta is: {delta} '
                            print(message)
                            discord_helpers.send_discord_alert(message)
                            c.OPTIONLIST.append(alert)

                    alert['Open_Interest'] = oi
                    alert['Volume'] = volume
                    alert['Entry_Price'] = bid
                    self.set_mongo_analysisPosition(alert)

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

        if signal_type == None:
            return trade_data

        position = live_trader.open_positions.find_one(
            {"Trader": live_trader.user["Name"], "Symbol": value['Symbol'], "Strategy": value['Strategy']})

        if signal_type == "CLOSE" and position is not None:
                obj = {
                    "Symbol": value['Symbol'],
                    "Side": "SELL_TO_CLOSE",
                    "Pre_Symbol": value['Pre_Symbol'],
                    "Exp_Date": value['Exp_Date'],
                    "Strike_Price": value['Strike_Price'],
                    "Option_Type": value['Option_Type'],
                    "Strategy": value['Strategy'],
                    "Asset_Type": "OPTION",
                    "Trade_Type": trade_type
                }
                trade_data.append(obj)

        elif signal_type == "BUY":
            if not IS_TESTING:
                url = f"https://api.tdameritrade.com/v1/marketdata/chains?symbol={value['Symbol']}&contractType={value['Option_Type']}&includeQuotes=FALSE&strike={value['Strike_Price']}&fromDate={value['Exp_Date']}&toDate={value['Exp_Date']}"
                resp = live_trader.tdameritrade.sendRequest(url)
                expdatemapkey = value['Option_Type'].lower() + "ExpDateMap"
                if list(resp.keys())[0]=="error" or list(resp.values())[1]=="FAILED":
                    print(f"Received an error for {value['Symbol']}")
                    self.error+=1
                    return
                else:
                    for dt in resp[expdatemapkey]:
                        for strikePrice in resp[expdatemapkey][dt]:
                            last=resp[expdatemapkey][dt][strikePrice][0]["last"]
                            volume=resp[expdatemapkey][dt][strikePrice][0]["totalVolume"]
                            delta=resp[expdatemapkey][dt][strikePrice][0]["delta"]
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

        return trade_data


    @exception_handler
    def buy_order(self, value, trade_signal, trade_type="LIMIT", **kwargs):
        """ METHOD RUNS THE TWO METHODS ABOVE AND THEN RUNS LIVE TRADER METHOD RUNTRADER FOR EACH INSTANCE.
        """
        isRunner = kwargs.get('isRunner', False)

        if not RUN_TRADIER:

            self.setupTraders()

            for api_trader in self.traders.values():
                api_trader.updateStatus()
                temp_trade_data=self.get_tradeFormat(api_trader, value, trade_signal, trade_type, "TRUE" if isRunner else "FALSE")
                for trade_data_row in temp_trade_data:
                    trade_data=[]
                    trade_data.append(trade_data_row)
                    api_trader.runTrader(trade_data)
                    if not RUN_LIVE_TRADER:
                        api_trader.runTrader(trade_data=None)

        else:

            #UPDATE STATUS
            for mongo_trader in self.traders.values():
                temp_trade_data = self.get_tradeFormat(mongo_trader, value, trade_signal, trade_type, "TRUE" if isRunner else "FALSE")
                for trade_data in temp_trade_data:
                    self.tradier.runTrader(trade_data)

    def run(self):
        """ METHOD RUNS THE TWO METHODS ABOVE AND THEN RUNS LIVE TRADER METHOD RUNTRADER FOR EACH INSTANCE.
        """

        start_time = datetime.now(pytz.timezone(config.TIMEZONE))

        connected = self.connectALL()

        while connected:

            """THIS RUNS THE TD INSTANCE"""
            self.setupTraders()

            """THIS WILL COMPILE THE ALERTS FROM DISCORD & GMAIL"""
            trade_alerts = self.get_alerts(start_time)

            """THIS WILL PUT ALL ALERTS INTO C.OPTIONLIST TO BE TRADED"""
            self.set_alerts(trade_alerts)

            if config.RUN_TA:

                """ALL ALERTS HAVE TO BE SCANNED UNTIL THEY MEET THE TA CRITERIA"""
                for api_trader in self.traders.values():

                    for value in c.OPTIONLIST:

                        signals = techanalysis.get_TA(value, api_trader)
                        buy_signal = techanalysis.buy_criteria(signals)

                        """IF BUY SIGNAL == TRUE THEN BUY!"""
                        if buy_signal:
                            self.buy_order(value, trade_signal="BUY", trade_type="LIMIT")
                            c.DONTTRADELIST.append(value)

            else:
                buy_signal = True
                for value in c.OPTIONLIST:
                    self.buy_order(value, trade_signal="BUY", trade_type="LIMIT")
                    c.DONTTRADELIST.append(value)

            """  CLEAN UP OUR OLD ORDERS  """
            for order in c.DONTTRADELIST:
                if order in c.OPTIONLIST:
                    c.OPTIONLIST.remove(order)

            """  CHECK ON ALL ORDER STATUSES  """
            if RUN_TRADIER:
                self.tradier.updateStatus()
            else:
                for api_trader in main.traders.values():
                    api_trader.updateStatus()

            if RUN_WEBSOCKET:
                tradier_helpers.streamPrice(self)

            if main.error > 0:
                print('errors', main.error)


            """ QUICK SEARCH TO MAKE SURE THERE THE SAME ## OF 
            QUEUED ORDERS ON TRADIER & MONGO """
            tradier_queued_list = []
            tradier_queued = self.tradier.get_queuedPositions()
            if len(tradier_queued) == 0 or tradier_queued == 'null':
                traider_queued = []
            else:
                for queued in tradier_queued:
                    tradier_queued_list.append(queued['id'])

            mongo_queued_list = []
            mongo_queued = list(self.mongo.queue.find({}))
            for queued in mongo_queued:
                mongo_queued_list.append(queued['Order_ID'])

            tradier_queued_list.sort()
            mongo_queued_list.sort()

            if tradier_queued_list == mongo_queued_list:
                pass
            else:
                print(f'something went wrong, tradier queued={tradier_queued} and mongo queued={mongo_queued}')

            """ QUICK SEARCH TO MAKE SURE THERE THE SAME ## OF 
            OPEN ORDERS ON TRADIER & MONGO """
            tradier_open_list = []
            tradier_open = self.tradier.get_openPositions()
            if len(tradier_open) == 0 or tradier_open['positions'] == 'null':
                pass
            elif len(tradier_open) == 1:
                tradier_open_list.append(tradier_open['positions']['position']['id'])
            else:
                tradier_open = tradier_open['positions']['position']
                for openn in tradier_open:
                    tradier_open_list.append(openn['id'])

            mongo_open_list = []
            mongo_open = list(self.mongo.open_positions.find({}))
            for openn in mongo_open:
                mongo_open_list.append(openn['Order_ID'])

            tradier_open_list.sort()
            mongo_open_list.sort()
            if tradier_open_list == mongo_open_list:
                pass
            else:
                print(f'something went wrong, tradier openOrders={tradier_open} and mongo openOrders={mongo_open}')

            time.sleep(helper_functions.selectSleep())


if __name__ == "__main__":
    """ START OF SCRIPT.
        INITIALIZES MAIN CLASS AND STARTS RUN METHOD ON WHILE LOOP WITH A DYNAMIC SLEEP TIME.
    """

    main = Main()

    main.run()
    # main.connectALL()
    # main.setupTraders()
    # positions = main.tradier.get_openPositions()
    # print(positions)
