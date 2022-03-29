
# imports
import time
import config
import pytz
import requests
from tradier import tradier_constants
from datetime import datetime, timedelta

from assets.exception_handler import exception_handler
from assets.helper_functions import getDatetime, selectSleep, modifiedAccountID
from discord import discord_helpers
from tradier import TradierTrader

TAKE_PROFIT_PERCENTAGE = config.TAKE_PROFIT_PERCENTAGE
STOP_LOSS_PERCENTAGE = config.STOP_LOSS_PERCENTAGE
RUN_TRADIER = config.RUN_TRADIER
MAX_QUEUE_LENGTH = config.MAX_QUEUE_LENGTH
RUN_LIVE_TRADER = config.RUN_LIVE_TRADER

class Tasks:

    # THE TASKS CLASS IS USED FOR HANDLING ADDITIONAL TASKS OUTSIDE OF THE LIVE TRADER.
    # YOU CAN ADD METHODS THAT STORE PROFIT LOSS DATA TO MONGO, SELL OUT POSITIONS AT END OF DAY, ECT.
    # YOU CAN CREATE WHATEVER TASKS YOU WANT FOR THE BOT.
    # YOU CAN USE THE DISCORD CHANNEL NAMED TASKS IF YOU ANY HELP.

    def __init__(self):

        self.isAlive = True

        self.endpoint = tradier_constants.API_ENDPOINT['brokerage'] if RUN_LIVE_TRADER \
            else tradier_constants.API_ENDPOINT['brokerage_sandbox']

        self.account_id = config.LIVE_ACCOUNT_NUMBER if RUN_LIVE_TRADER else config.SANDBOX_ACCOUNT_NUMBER

        self.tradier_token = config.LIVE_ACCESS_TOKEN if RUN_LIVE_TRADER else config.SANDBOX_ACCESS_TOKEN

        self.headers = {'Authorization': f'Bearer {self.tradier_token}',
                        'Accept': 'application/json'
                        }


    @exception_handler
    def checkOCOpapertriggers(self):

        for position in self.mongo.open_positions.find({"Trader": self.user["Name"]}):

            symbol = position["Symbol"]

            asset_type = position["Asset_Type"]

            resp = self.tdameritrade.getQuote(
                symbol if asset_type == "EQUITY" else position["Pre_Symbol"])

            price = float(resp[symbol  if asset_type == "EQUITY" else position["Pre_Symbol"]]["askPrice"])

            if price <= (position["Entry_Price"] * STOP_LOSS_PERCENTAGE) or price >= (position["Entry_Price"] * TAKE_PROFIT_PERCENTAGE):
                # CLOSE POSITION
                pass

    def getTradierorder(self, id):

        api_path = tradier_constants.API_PATH['account_order_status']
        path = f'{self.endpoint}{api_path.replace("{account_id}",str(self.account_id)).replace("{id}",str(id))}'

        response = requests.get(path,
                                params={'includeTags': 'false'},
                                headers=self.headers
                                )
        json_response = response.json()

        return json_response

    @exception_handler
    def checkOCOtriggers(self):
        """ Checks OCO triggers (stop loss/ take profit) to see if either one has filled. If so, then close position in mongo like normal.

        """

        open_positions = self.open_positions.find(
            {"Trader": self.user["Name"], "Order_Type": "OCO"})

        for position in open_positions:

            childOrderStrategies = position["childOrderStrategies"]

            x = 0
            for order in childOrderStrategies:

                spec_order = self.tdameritrade.getSpecificOrder(order['Order_ID'])

                if 'error' in spec_order.keys():
                    spec_order = self.getTradierorder(order['Order_ID'])

                new_status = spec_order['order']["status"]

                if new_status == "FILLED":

                    TradierTrader.pushOrder(position, spec_order)

                elif new_status == "CANCELED" or new_status == "REJECTED":

                    other = {
                        "Symbol": position["Symbol"],
                        "Order_Type": position["Order_Type"],
                        "Order_Status": new_status,
                        "Strategy": position["Strategy"],
                        "Trader": self.user["Name"],
                        "Date": getDatetime(),
                        "Account_ID": self.account_id
                    }

                    self.rejected.insert_one(
                        other) if new_status == "REJECTED" else self.canceled.insert_one(other)

                    self.logger.info(
                        f"{new_status.upper()} ORDER For {position['Symbol']} - TRADER: {self.user['Name']} - ACCOUNT ID: {modifiedAccountID(self.account_id)}")

                else:

                    self.open_positions.update_one({"Trader": self.user["Name"], "Symbol": position["Symbol"], "Strategy": position["Strategy"]},
                        {"$set": {f"childOrderStrategies.{x}.status": new_status}})

                x += 1

    @exception_handler
    def extractOCOchildren(self, spec_order):
        """This method extracts oco children order ids and then sends it to be stored in mongo open positions. 
        Data will be used by checkOCOtriggers with order ids to see if stop loss or take profit has been triggered.

        """

        oco_children = {
            "childOrderStrategies": {}
        }

        childOrderStrategies = spec_order["childOrderStrategies"][0]["childOrderStrategies"]

        for child in childOrderStrategies:

            oco_children["childOrderStrategies"][child["orderId"]] = {
                "Side": child["orderLegCollection"][0]["instruction"],
                "Exit_Price": child["stopPrice"] if "stopPrice" in child else child["price"],
                "Exit_Type": "STOP LOSS" if "stopPrice" in child else "TAKE PROFIT",
                "Order_Status": child["status"]
            }

        return oco_children

    @exception_handler
    def addNewStrategy(self, strategy, asset_type):
        """ METHOD UPDATES STRATEGIES OBJECT IN MONGODB WITH NEW STRATEGIES.

        Args:
            strategy ([str]): STRATEGY NAME
        """

        obj = {"Active": True,
               "Order_Type": "STANDARD",
               "Asset_Type": asset_type,
               "Position_Size": 500,
               "Position_Type": "LONG",
               "Account_ID": self.account_id,
               "Strategy": strategy,
               }

        # IF STRATEGY NOT IN STRATEGIES COLLECTION IN MONGO, THEN ADD IT

        self.strategies.update(
            {"Strategy": strategy},
            {"$setOnInsert": obj},
            upsert=True
        )

    @exception_handler
    def killQueueOrder(self):
        """ METHOD QUERIES ORDERS IN QUEUE AND LOOKS AT INSERTION TIME.
            IF QUEUE ORDER INSERTION TIME GREATER THAN TWO HOURS, THEN THE ORDER IS CANCELLED.
        """
        # CHECK ALL QUEUE ORDERS AND CANCEL ORDER IF GREATER THAN TWO MINUTES OLD
        queue_orders = self.mongo.queue.find(
            {"Trader": self.user["Name"], "Account_ID": self.account_id})

        dt = datetime.now(tz=pytz.UTC).replace(microsecond=0)

        dt_tz = dt.astimezone(pytz.timezone(config.TIMEZONE))

        x_mins_ago = datetime.strptime(datetime.strftime(
            dt_tz - timedelta(minutes=MAX_QUEUE_LENGTH), "%Y-%m-%d %H:%M:%S"), "%Y-%m-%d %H:%M:%S")

        for order in queue_orders:

            order_date = order["Entry_Date"]

            side = order["Side"]

            id = order["Order_ID"]

            forbidden = ["REJECTED", "CANCELED", "FILLED", "rejected", "canceled", 'filled', 'expired']

            pre_symbol = order["Pre_Symbol"]

            if x_mins_ago > order_date and (side == "BUY" or side == "BUY_TO_OPEN") and id != None and order["Order_Status"] not in forbidden:

                # FIRST CANCEL ORDER
                if RUN_TRADIER:
                    resp = self.cancel_order(id)
                else:
                    resp = self.tdameritrade.cancelOrder(id)

                if resp.status_code == 200 or resp.status_code == 201:

                    other = {
                        "Symbol": order["Symbol"],
                        "Pre_Symbol": order["Pre_Symbol"],
                        "Order_Type": order["Order_Type"],
                        "Order_Status": "CANCELED",
                        "Strategy": order["Strategy"],
                        "Account_ID": self.account_id,
                        "Trader": self.user["Name"],
                        "Date": getDatetime()
                    }

                    self.other.insert_one(other)

                    self.queue.delete_one(
                        {"Trader": self.user["Name"], "Symbol": order["Symbol"], "Strategy": order["Strategy"]})

                    self.logger.INFO(
                        f"CANCELED ORDER FOR {order['Symbol']} - TRADER: {self.user['Name']}", True)

                    discord_alert = f"TradingBOT just cancelled order for: {pre_symbol}"
                    discord_helpers.send_discord_alert(discord_alert)

    def runTasks(self):
        """ METHOD RUNS TASKS ON WHILE LOOP EVERY 5 - 60 SECONDS DEPENDING.
        """

        self.logger.info(
            f"STARTING TASKS FOR {self.user['Name']} ({modifiedAccountID(self.account_id)})", extra={'log': False})

        while self.isAlive:

            try:

                # RUN TASKS ####################################################
                self.checkOCOtriggers()
                self.killQueueOrder()

                ##############################################################

            except KeyError:

                self.isAlive = False

            except Exception as e:

                self.logger.error(
                    f"ACCOUNT ID: {modifiedAccountID(self.account_id)} - TRADER: {self.user['Name']} - {e}")

            finally:

                time.sleep(selectSleep())

        self.logger.warning(
            f"TASK STOPPED FOR ACCOUNT ID {modifiedAccountID(self.account_id)}")
