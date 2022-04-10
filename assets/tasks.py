
# imports
import time
import config
import pytz
import requests
import traceback
from random import randrange
from tradier import tradier_constants
from datetime import datetime, timedelta
from pymongo.errors import WriteError, WriteConcernError

from assets.exception_handler import exception_handler
from assets.helper_functions import getDatetime, selectSleep, modifiedAccountID
from discord import discord_helpers

TAKE_PROFIT_PERCENTAGE = config.TAKE_PROFIT_PERCENTAGE
STOP_LOSS_PERCENTAGE = config.STOP_LOSS_PERCENTAGE
TRAILSTOP_PERCENTAGE = config.TRAIL_STOP_PERCENTAGE
RUN_TRADIER = config.RUN_TRADIER
MAX_QUEUE_LENGTH = config.MAX_QUEUE_LENGTH
RUN_LIVE_TRADER = config.RUN_LIVE_TRADER
SELL_PRICE = config.SELL_PRICE




class Tasks:

    # THE TASKS CLASS IS USED FOR HANDLING ADDITIONAL TASKS OUTSIDE OF THE LIVE TRADER.
    # YOU CAN ADD METHODS THAT STORE PROFIT LOSS DATA TO MONGO, SELL OUT POSITIONS AT END OF DAY, ECT.
    # YOU CAN CREATE WHATEVER TASKS YOU WANT FOR THE BOT.
    # YOU CAN USE THE DISCORD CHANNEL NAMED TASKS IF YOU ANY HELP.

    def __init__(self):

        self.isAlive = True

        self.endpoint = tradier_constants.API_ENDPOINT['brokerage'] if RUN_LIVE_TRADER \
            else tradier_constants.API_ENDPOINT['brokerage_sandbox']

        # if RUN_TRADIER:
        #     self.tradier_account_id = config.LIVE_ACCOUNT_NUMBER if RUN_LIVE_TRADER else config.SANDBOX_ACCOUNT_NUMBER

        self.tradier_token = config.LIVE_ACCESS_TOKEN if RUN_LIVE_TRADER else config.SANDBOX_ACCESS_TOKEN

        self.headers = {'Authorization': f'Bearer {self.tradier_token}',
                        'Accept': 'application/json'
                        }

    def getTradierorder(self, order_id):

        api_path = tradier_constants.API_PATH['account_order_status']
        path = f'{self.endpoint}{api_path.replace("{account_id}",str(self.tradier.account_id)).replace("{id}",str(order_id))}'

        response = requests.get(path,
                                params={'includeTags': 'false'},
                                headers=self.headers
                                )
        json_response = response.json()

        return json_response

    def cancelTradierorder(self, order_id):

        api_path = tradier_constants.API_PATH['account_order_status']
        path = f'{self.endpoint}{api_path.replace("{account_id}", str(self.tradier.account_id)).replace("{id}", str(order_id))}'

        response = requests.delete(path,
                                data={},
                                headers=self.headers
                                )
        json_response = response.json()

        return json_response

    def set_closeOrder(self, queue_order, spec_order, data_integrity="Reliable"):
        """ METHOD PUSHES ORDER TO EITHER OPEN POSITIONS OR CLOSED POSITIONS COLLECTION IN MONGODB.
            IF BUY ORDER, THEN PUSHES TO OPEN POSITIONS.
            IF SELL ORDER, THEN PUSHES TO CLOSED POSITIONS.

        Args:
            queue_order ([dict]): [QUEUE ORDER DATA FROM QUEUE]
            spec_order ([dict(json)]): [ORDER DATA FROM TDAMERITRADE]
        """

        symbol = queue_order["Symbol"]

        if 'stop_price' in spec_order.keys():

            price = spec_order['stop_price']

        else:

            price = spec_order["price"]

        shares = int(queue_order["Qty"])

        strategy = queue_order["Strategy"]

        side = spec_order["side"]

        account_id = queue_order["Account_ID"]

        position_size = queue_order["Position_Size"]

        asset_type = queue_order["Asset_Type"]

        if asset_type == "OPTION":

            price = round(price, 2)

        else:
            price = round(price, 2) if price >= 1 else round(price, 4)

        position_type = queue_order["Position_Type"]

        direction = "CLOSE POSITION"

        account_position = queue_order["Account_Position"]

        order_type = queue_order["Order_Type"]

        obj = {
            "Symbol": symbol,
            "Strategy": strategy,
            "Position_Size": position_size,
            "Position_Type": position_type,
            "Data_Integrity": data_integrity,
            "Trader": self.user["Name"],
            "Account_ID": account_id,
            "Asset_Type": asset_type,
            "Account_Position": account_position,
            "Order_Type": order_type
        }

        if asset_type == "OPTION":
            obj["Pre_Symbol"] = queue_order["Pre_Symbol"]

            pre_symbol = queue_order["Pre_Symbol"]

            obj["Exp_Date"] = queue_order["Exp_Date"]

            obj["Option_Type"] = queue_order["Option_Type"]

            obj["Strike_Price"] = queue_order["Strike_Price"]

            obj['isRunner'] = queue_order["isRunner"]

            obj['Bid_Price'] = price

            obj['Ask_Price'] = price

            obj['Last_Price'] = price

        collection_insert = None

        message_to_push = None

        if direction == "CLOSE POSITION":

            position = self.mongo.open_positions.find_one(
                {"Trader": self.user["Name"], "Symbol": symbol, "Strategy": strategy})

            obj["Qty"] = position["Qty"]

            obj["Entry_Price"] = position["Entry_Price"]

            obj["Entry_Date"] = position["Entry_Date"]

            if RUN_TRADIER:
                obj["Exit_Price"] = spec_order['avg_fill_price']
            else:
                obj["Exit_Price"] = price

            obj["Exit_Date"] = getDatetime()

            # exit_price = round(price * position["Qty"], 2)
            #
            # entry_price = round(position["Price"] * position["Qty"], 2)

            collection_insert = self.mongo.closed_positions.insert_one

            discord_message_to_push = f":closed_book: TradingBOT just closed \n Side: {side} \n Symbol: {pre_symbol} \n Qty: {position['Qty']} \n Entry Price: ${position['Entry_Price']} \n Entry Date: {position['Entry_Date']} \n Exit Price: ${price} \n Exit Date: {getDatetime()} \n Strategy: {strategy} \n Asset Type: {asset_type} \n :closed_book: Account Position: {'Live Trade' if RUN_LIVE_TRADER else 'Paper Trade'}"

            # REMOVE FROM OPEN POSITIONS
            is_removed = self.mongo.open_positions.delete_one(
                {"Trader": self.user["Name"], "Symbol": symbol, "Strategy": strategy})

            try:

                if int(is_removed.deleted_count) == 0:
                    if RUN_TRADIER:
                        self.logger.error(
                            f"INITIAL FAIL OF DELETING OPEN POSITION FOR SYMBOL {symbol} - {self.user['Name']} ({modifiedAccountID(self.tradier.account_id)})")
                    else:
                        self.logger.error(
                            f"INITIAL FAIL OF DELETING OPEN POSITION FOR SYMBOL {symbol} - {self.user['Name']} ({modifiedAccountID(self.account_id)})")

                    self.mongo.open_positions.delete_one(
                        {"Trader": self.user["Name"], "Symbol": symbol, "Strategy": strategy})

            except Exception:

                msg = f"{self.user['Name']} - {modifiedAccountID(self.tradier.account_id if RUN_TRADIER else self.account_id)} - {traceback.format_exc()}"

                self.logger.error(msg)

        # PUSH OBJECT TO MONGO. IF WRITE ERROR THEN ONE RETRY WILL OCCUR. IF YOU SEE THIS ERROR, THEN YOU MUST CONFIRM THE PUSH OCCURED.
        try:

            collection_insert(obj)

        except WriteConcernError as e:

            self.logger.error(
                f"INITIAL FAIL OF INSERTING OPEN POSITION FOR SYMBOL {symbol} - DATE/TIME: {getDatetime()} - DATA: {obj} - {e}")

            collection_insert(obj)

        except WriteError as e:

            self.logger.error(
                f"INITIAL FAIL OF INSERTING OPEN POSITION FOR SYMBOL {symbol} - DATE/TIME: {getDatetime()} - DATA: {obj} - {e}")

            collection_insert(obj)

        except Exception:

            msg = f"{self.user['Name']} - {modifiedAccountID(self.tradier.account_id if RUN_TRADIER else self.account_id)} - {traceback.format_exc()}"

            self.logger.error(msg)

        self.logger.info(
            f"Pushing {side} Order For {symbol} To {'Open Positions' if direction == 'OPEN POSITION' else 'Closed Positions'} ({modifiedAccountID(self.account_id)})")

        # REMOVE FROM QUEUE

        self.mongo.queue.delete_one({"Trader": self.user["Name"], "Symbol": symbol,
                                     "Strategy": strategy})

        discord_helpers.send_discord_alert(discord_message_to_push)

    @exception_handler
    def checkOCOtriggers(self):
        """ Checks OCO triggers (stop loss/ take profit) to see if either one has filled. If so, then close position in mongo like normal.

        """
        open_positions = self.mongo.open_positions.find(
            {"Trader": self.user["Name"]})

        for position in open_positions:
            try:

                childOrderStrategies = position["childOrderStrategies"]

            except:

                continue
            x = 0
            trulycanceled = 0
            for order in childOrderStrategies:

                if position['Account_ID'] == self.tradier.account_id:

                    spec_order = self.getTradierorder(order['Order_ID'])

                    new_status = spec_order['order']["status"]

                elif RUN_LIVE_TRADER and position['Account_ID'] == self.account_id:
                    for td_trader in self.traders.values():
                        spec_order = td_trader.tdameritrade.getSpecificOrder(order['Order_ID'])

                    new_status = spec_order['order']["status"]

                else:

                    new_status = position['childOrderStrategies'][order]["Order_Status"]

                if new_status.upper() == "FILLED" or new_status.upper() == "EXPIRED":

                    if position['Account_ID'] == self.tradier.account_id:

                        self.set_closeOrder(position, spec_order['order'])

                    elif RUN_LIVE_TRADER and position['Account_ID'] == self.account_id:

                        self.set_closeOrder(position, spec_order)

                    else:

                        if position['childOrderStrategies'][order]['Exit_Type'] == "STOP LOSS":
                            for td_trader in self.traders.values():
                                price = td_trader.tdameritrade.getQuote(position['Pre_Symbol'])[position['Pre_Symbol']]['bidPrice']

                        else:
                            for td_trader in self.traders.values():
                                price = td_trader.tdameritrade.getQuote(position['Pre_Symbol'])[position['Pre_Symbol']][SELL_PRICE]

                        spec_order = {
                            'price': price,
                            'side': "SELL_TO_CLOSE",
                            'direction': "CLOSE POSITION"
                        }

                        self.set_closeOrder(position, spec_order)

                elif new_status.upper() == "CANCELED" or new_status.upper() == "REJECTED":

                    trulycanceled += 1

                    if trulycanceled == 2:

                        other = {
                            "Symbol": position["Symbol"],
                            "Order_Type": position["Order_Type"],
                            "Order_Status": new_status,
                            "Strategy": position["Strategy"],
                            "Trader": self.user["Name"],
                            "Date": getDatetime(),
                            "Account_ID": self.tradier.account_id if RUN_TRADIER else self.account_id
                        }
                        self.mongo.rejected.insert_one(
                            other) if new_status == "REJECTED" else self.canceled.insert_one(other)

                        self.logger.info(
                            f"{new_status.upper()} ORDER For {position['Symbol']} - TRADER: {self.user['Name']} - ACCOUNT ID: {modifiedAccountID(self.account_id)}")

                    else:

                        continue

                else:

                    if RUN_TRADIER:
                        self.mongo.open_positions.update_one({"Trader": self.user["Name"], "Symbol": position["Symbol"], "Strategy": position["Strategy"]},
                            {"$set": {f"childOrderStrategies.{x}.Order_Status": new_status}})

                    else:
                        self.mongo.open_positions.update_one({"Trader": self.user["Name"], "Symbol": position["Symbol"],
                                                        "Strategy": position["Strategy"]},
                                                       {"$set": {f"childOrderStrategies.{order}.Order_Status": new_status}})
                x += 1

    @exception_handler
    def extractOCOchildren(self, spec_order):
        """This method extracts oco children order ids and then sends it to be stored in mongo open positions. 
        Data will be used by checkOCOtriggers with order ids to see if stop loss or take profit has been triggered.

        """

        oco_children = {
            "childOrderStrategies": {}
        }

        if RUN_LIVE_TRADER:

            childOrderStrategies = spec_order["childOrderStrategies"][0]["childOrderStrategies"]

            for child in childOrderStrategies:

                oco_children["childOrderStrategies"][child["orderId"]] = {
                    "Side": child["orderLegCollection"][0]["instruction"],
                    "Exit_Price": child["stopPrice"] if "stopPrice" in child else child["price"],
                    "Exit_Type": "STOP LOSS" if "stopPrice" in child else "TAKE PROFIT",
                    "Order_Status": child["status"]
                }

        else:

            for i in range(0, 2):

                oco_children['childOrderStrategies'][str(i)] = {
                    "Side": "sell_to_close",
                    "Order_Status": "open",
                    "Exit_Type": "TAKE PROFIT" if i == 0 else "STOP LOSS",
                    "Order_ID": randrange(10000,99999)
                }

                if i == 0:
                    oco_children['childOrderStrategies'][str(i)]['Takeprofit_Price'] = \
                        round(spec_order["price"] * (1+TAKE_PROFIT_PERCENTAGE), 2)

                else:
                    oco_children['childOrderStrategies'][str(i)]['Stop_Price'] = \
                        round(spec_order["price"] * (1-STOP_LOSS_PERCENTAGE), 2)

        return oco_children

    @exception_handler
    def killQueueOrder(self):
        """ METHOD QUERIES ORDERS IN QUEUE AND LOOKS AT INSERTION TIME.
            IF QUEUE ORDER INSERTION TIME GREATER THAN TWO HOURS, THEN THE ORDER IS CANCELLED.
        """
        # CHECK ALL QUEUE ORDERS AND CANCEL ORDER IF GREATER THAN TWO MINUTES OLD
        if RUN_TRADIER:
            queue_orders = self.mongo.queue.find(
                {"Trader": self.user["Name"], "Account_ID": self.tradier.account_id})
        else:
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
                    resp = self.cancelTradierorder(id)

                    if 'ok' in resp['order']['status']:
                        other = {
                            "Symbol": order["Symbol"],
                            "Pre_Symbol": order["Pre_Symbol"],
                            "Order_Type": order["Order_Type"],
                            "Order_Status": "CANCELED",
                            "Strategy": order["Strategy"],
                            "Account_ID": self.tradier.account_id,
                            "Trader": self.user["Name"],
                            "Date": getDatetime()
                        }

                        self.mongo.canceled.insert_one(other)

                        self.mongo.queue.delete_one(
                            {"Trader": self.user["Name"], "Symbol": order["Symbol"], "Strategy": order["Strategy"]})

                        self.logger.info(
                            f"CANCELED ORDER FOR {order['Symbol']} - TRADER: {self.user['Name']}", extra={'log': True})

                        discord_alert = f"TradingBOT just cancelled order for: {pre_symbol}"
                        discord_helpers.send_discord_alert(discord_alert)

                else:
                    for td_trader in self.traders.values():
                        resp = td_trader.tdameritrade.cancelOrder(id)

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

                        self.mongo.canceled.insert_one(other)

                        self.mongo.queue.delete_one(
                            {"Trader": self.user["Name"], "Symbol": order["Symbol"], "Strategy": order["Strategy"]})

                        self.logger.info(
                            f"CANCELED ORDER FOR {order['Symbol']} - TRADER: {self.user['Name']}", extra={'log': True})

                        discord_alert = f"TradingBOT just cancelled order for: {pre_symbol}"
                        discord_helpers.send_discord_alert(discord_alert)

    def runTasks(self):
        """ METHOD RUNS TASKS ON WHILE LOOP EVERY 5 - 60 SECONDS DEPENDING.
        """
        if RUN_TRADIER:
            acct_id = self.tradier.account_id
        else:
            acct_id = self.account_id

        self.logger.info(
            f"STARTING TASKS FOR {self.user['Name']} ({modifiedAccountID(acct_id)})", extra={'log': False})

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
                    f"ACCOUNT ID: {modifiedAccountID(acct_id)} - TRADER: {self.user['Name']} - {e}")

            finally:

                time.sleep(selectSleep())

        self.logger.warning(
            f"TASK STOPPED FOR ACCOUNT ID {modifiedAccountID(acct_id)}")
