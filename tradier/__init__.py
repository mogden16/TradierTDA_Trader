# imports
import requests
import traceback
import config
import polygon
from pymongo.errors import WriteError, WriteConcernError
from tradier import tradier_constants
from assets.helper_functions import modifiedAccountID, getDatetime
from assets.exception_handler import exception_handler
from tradier.tradierOrderBuilder import tradierOrderBuilder
from tradier.tradier_helpers import tradierExtractOCOChildren
from api_trader.tasks import Tasks
from discord import discord_helpers

RUN_LIVE_TRADER = config.RUN_LIVE_TRADER
RUN_WEBSOCKET = config.RUN_WEBSOCKET
TRAILSTOP_PERCENTAGE = config.TRAIL_STOP_PERCENTAGE

class TradierTrader(tradierOrderBuilder, Tasks):

    def __init__(self, user, mongo, logger):
        self.endpoint = tradier_constants.API_ENDPOINT['brokerage'] if RUN_LIVE_TRADER \
            else tradier_constants.API_ENDPOINT['brokerage_sandbox']

        self.user = user

        self.mongo = mongo

        self.logger = logger

        self.account_id = config.LIVE_ACCOUNT_NUMBER if RUN_LIVE_TRADER else config.SANDBOX_ACCOUNT_NUMBER

        self.tradier_token = config.LIVE_ACCESS_TOKEN if RUN_LIVE_TRADER else config.SANDBOX_ACCESS_TOKEN

        self.headers = {'Authorization': f'Bearer {self.tradier_token}',
                        'Accept': 'application/json'
                        }

        tradierOrderBuilder.__init__(self)

        Tasks.__init__(self)

    def get_accountbalance(self):
        api_path = tradier_constants.API_PATH['account_balances']
        path = f'{self.endpoint}{api_path.replace("{account_id}",str(self.account_id))}'

        response = requests.get(path,
                                params={},
                                headers=self.headers
                                )
        json_response = response.json()
        # print(response.status_code)
        print(json_response)

    @exception_handler
    def get_quote(self, polygon_symbol):

        if type(polygon_symbol) == dict:
            trade_data = polygon_symbol
            formatted_exp_date = trade_data['Exp_Date'][2:].replace("-", "")

            polygon_symbol = polygon.build_option_symbol(trade_data['Symbol'], formatted_exp_date,
                                                         trade_data['Option_Type'], trade_data['Strike_Price'],
                                                         prefix_o=False)

        api_path = tradier_constants.API_PATH['quotes']
        path = f'{self.endpoint}{api_path}'

        response = requests.get(path,
                                params={'symbols': f'{polygon_symbol}'},
                                headers=self.headers
                                )
        json_response = response.json()
        obj = {
            'bidPrice': float(json_response['quotes']['quote']['bid']),
            'askPrice': float(json_response['quotes']['quote']['ask']),
            'lastPrice': float(json_response['quotes']['quote']['last'])
        }
        return obj

    @exception_handler
    def get_order(self, id):

        api_path = tradier_constants.API_PATH['account_order_status']
        path = f'{self.endpoint}{api_path.replace("{account_id}",str(self.account_id)).replace("{id}",str(id))}'

        response = requests.get(path,
                                params={'includeTags': 'false'},
                                headers=self.headers
                                )
        json_response = response.json()

        return json_response

    @exception_handler
    def get_openPositions(self):

        api_path = tradier_constants.API_PATH['account_positions']
        path = f'{self.endpoint}{api_path.replace("{account_id}",str(self.account_id))}'

        response = requests.get(path,
                                params={},
                                headers=self.headers
                                )
        json_response = response.json()

        return json_response

    @exception_handler
    def get_allPositions(self):
        """ THIS GETS ALL ORDERS FOR THE DAY'S SESSION """

        api_path = tradier_constants.API_PATH['account_orders']
        path = f'{self.endpoint}{api_path.replace("{account_id}", str(self.account_id))}'

        response = requests.get(path,
                                params={'includeTags': 'false'},
                                headers=self.headers
                                )
        json_response = response.json()

        return json_response

    @exception_handler
    def get_queuedPositions(self):

        queued_positions = []
        todays_positions = self.get_allPositions()

        if todays_positions['orders'] == 'null':
            return
        else:
            todays_positions = todays_positions['orders']['order']

        for position in todays_positions:
            if position['status'] == 'pending' or position['status'] == 'open':
                queued_positions.append(position)

        return queued_positions

    @exception_handler
    def place_order(self, order):

        api_path = tradier_constants.API_PATH['orders']
        path = f'{self.endpoint}{api_path.replace("{account_id}",str(self.account_id))}'

        response = requests.post(path,
                                data=order,
                                headers=self.headers
                                )

        json_response = response.json()
        status_code = response.status_code
        return json_response, status_code

    # STEP ONE
    @exception_handler
    def sendOrder(self, trade_data, strategy_object, direction, special_order_type):

        symbol = trade_data["Symbol"]

        strategy = trade_data["Strategy"]

        side = trade_data["Side"]

        order_type = strategy_object["Order_Type"]

        pre_symbol = trade_data["Pre_Symbol"]

        strike_price = trade_data["Strike_Price"]

        isRunner = trade_data["isRunner"]

        # volume = trade_data["Volume"]

        # oi = trade_data["Open_Interest"]

        if order_type == "CUSTOM":

            if special_order_type == "STANDARD":

                order, obj = self.standardOrder(
                    trade_data, strategy_object, direction)

            elif special_order_type == "OCO":

                order, obj = self.otoco_order(
                    trade_data, strategy_object, direction)

            elif special_order_type == "TRAIL":

                pass

            else:
                print('your order_type in Mongo is incorrect')

        else:

            if order_type == "STANDARD":

                order, obj = self.standardOrder(
                    trade_data, strategy_object, direction)

            elif order_type == "OCO":

                order, obj = self.otoco_order(
                    trade_data, strategy_object, direction)

            elif order_type == "TRAIL":

                pass

            else:
                print('your order_type in Mongo is incorrect')

        if order == None and obj == None:

            return

        # PLACE ORDER ################################################

        resp, status_code = self.place_order(order)

        resp = resp['order']

        if status_code not in [200, 201]:

            other = {
                "Symbol": symbol,
                "Order_Type": side,
                "Order_Status": "REJECTED",
                "Strategy": strategy,
                "Trader": self.user["Name"],
                "Date": getDatetime(),
                "Account_ID": self.account_id
            }

            self.logger.info(
                f"{symbol} Rejected For {self.user['Name']} ({modifiedAccountID(self.account_id)}) - Reason: {(resp.json())['error']} ")

            self.mongo.rejected.insert_one(other)

            return

        # GETS ORDER ID FROM RESPONSE HEADERS LOCATION
        obj["Order_ID"] = resp["id"]
        
        if RUN_LIVE_TRADER:
            
            obj["Account_Position"] = "Live"
            
        else:
            
            obj["Account_Position"] = "Paper"

        obj["Order_Status"] = "QUEUED"

        obj['Strike_Price'] = trade_data['Strike_Price']

        obj['isRunner'] = trade_data['isRunner']

        self.queueOrder(obj)

        response_msg = f"{'Live Trade' if RUN_LIVE_TRADER else 'Paper Trade'}: just Queued {side} Order for Symbol {symbol} ({modifiedAccountID(self.account_id)})"

        self.logger.info(response_msg)

        discord_queue_message_to_push = f":eyes: TradingBOT just Queued \n Side: {side} \n Symbol: {pre_symbol} \n :eyes: Account Position: {'Live Trade' if RUN_LIVE_TRADER else 'Paper Trade'}"
        discord_helpers.send_discord_alert(discord_queue_message_to_push)

    # STEP TWO
    @exception_handler
    def queueOrder(self, order):
        """ METHOD FOR QUEUEING ORDER TO QUEUE COLLECTION IN MONGODB

        Args:
            order ([dict]): [ORDER DATA TO BE PLACED IN QUEUE COLLECTION]
        """
        # CHECK TRADIER TO MAKE SURE IT WAS ACTUALLY QUEUED

        # ADD TO QUEUE WITHOUT ORDER ID AND STATUS
        position = self.get_order(order['Order_ID'])

        if position == None:

            print("TradingBOT 'placed' order but no order found in Tradier")
            return

        else:
            current_status = position['order']['status']

            if current_status == 'pending' or current_status == 'open' or current_status == 'filled':

                self.mongo.queue.update_one(
                    {"Trader": self.user["Name"], "Symbol": order["Symbol"], "Strategy": order["Strategy"]},
                    {"$set": order}, upsert=True)

                self.updateStatus()

    # STEP THREE
    @exception_handler
    def updateStatus(self):
        """ METHOD QUERIES THE QUEUED ORDERS AND USES THE ORDER ID TO QUERY TDAMERITRADES ORDERS FOR ACCOUNT TO CHECK THE ORDERS CURRENT STATUS.
            INITIALLY WHEN ORDER IS PLACED, THE ORDER STATUS ON TDAMERITRADES END IS SET TO WORKING OR QUEUED. THREE OUTCOMES THAT I AM LOOKING FOR ARE
            FILLED, CANCELED, REJECTED.

            IF FILLED, THEN QUEUED ORDER IS REMOVED FROM QUEUE AND THE pushOrder METHOD IS CALLED.

            IF REJECTED OR CANCELED, THEN QUEUED ORDER IS REMOVED FROM QUEUE AND SENT TO OTHER COLLECTION IN MONGODB.

            IF ORDER ID NOT FOUND, THEN ASSUME ORDER FILLED AND MARK AS ASSUMED DATA. ELSE MARK AS RELIABLE DATA.
        """

        # SCAN ALL QUEUED ORDERS
        queued_orders = self.mongo.queue.find({"Trader": self.user["Name"], "Order_ID": {
                                        "$ne": None}, "Account_ID": self.account_id})

        for queue_order in queued_orders:

            spec_order = self.get_order(queue_order['Order_ID'])['order']

            new_status = spec_order["status"]

            order_type = queue_order["Order_Type"]

            # CHECK IF QUEUE ORDER ID EQUALS TDA ORDER ID
            if queue_order["Order_ID"] == spec_order["id"]:

                if new_status == "filled":

                    if spec_order["class"] == "otoco":
                        queue_order = {**queue_order, **tradierExtractOCOChildren(spec_order)}

                    # self.pushOrder(queue_order, spec_order)
                    self.pushOrder(queue_order, spec_order)

                elif new_status == "canceled" or new_status == "rejected" or new_status == "expired":

                    # REMOVE FROM QUEUE
                    self.mongo.queue.delete_one({"Trader": self.user["Name"], "Symbol": queue_order["Symbol"],
                                           "Strategy": queue_order["Strategy"], "Account_ID": self.account_id})

                    other = {
                        "Symbol": queue_order["Symbol"],
                        "Order_Type": order_type,
                        "Order_Status": new_status,
                        "Strategy": queue_order["Strategy"],
                        "Trader": self.user["Name"],
                        "Date": getDatetime(),
                        "Account_ID": self.account_id
                    }

                    self.mongo.canceled.insert_one(
                        other) if new_status == "canceled" else self.mongo.rejected.insert_one(other)

                    self.logger.info(
                        f"{new_status.upper()} Order For {queue_order['Symbol']} ({modifiedAccountID(self.account_id)})")

                else:

                    self.mongo.queue.update_one({"Trader": self.user["Name"], "Symbol": queue_order["Symbol"], "Strategy": queue_order["Strategy"]}, {
                        "$set": {"Order_Status": new_status}})

    # STEP FOUR
    @exception_handler
    def pushOrder(self, queue_order, spec_order, data_integrity="Reliable"):
        """ METHOD PUSHES ORDER TO EITHER OPEN POSITIONS OR CLOSED POSITIONS COLLECTION IN MONGODB.
            IF BUY ORDER, THEN PUSHES TO OPEN POSITIONS.
            IF SELL ORDER, THEN PUSHES TO CLOSED POSITIONS.

        Args:
            queue_order ([dict]): [QUEUE ORDER DATA FROM QUEUE]
            spec_order ([dict(json)]): [ORDER DATA FROM TDAMERITRADE]
        """

        symbol = queue_order["Symbol"]

        if spec_order['class'] == 'otoco':

            price = spec_order["leg"][0]["price"]

            shares = int(spec_order["quantity"])

        else:

            price = spec_order["price"]

            shares = int(queue_order["Qty"])

        strategy = queue_order["Strategy"]

        side = queue_order["Side"]

        account_id = queue_order["Account_ID"]

        position_size = queue_order["Position_Size"]

        asset_type = queue_order["Asset_Type"]

        if asset_type == "OPTION":

            price = round(price, 2)

        else:
            price = round(price, 2) if price >= 1 else round (price, 4)

        position_type = queue_order["Position_Type"]

        direction = queue_order["Direction"]

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

        if direction == "OPEN POSITION":

            obj["Qty"] = shares

            obj["Price"] = price

            obj["Entry_Date"] = getDatetime()

            obj["Max_Price"] = price

            obj['Order_ID'] = queue_order['Order_ID']

            obj["Trail_Stop_Value"] = price * TRAILSTOP_PERCENTAGE

            collection_insert = self.mongo.open_positions.insert_one

            discord_message_to_push = f":rocket: TradingBOT just opened \n Side: {side} \n Symbol: {pre_symbol} \n Qty: {shares} \n Price: ${price} \n Strategy: {strategy} \n Asset Type: {asset_type} \n Date: {getDatetime()} \n :rocket: Account Position: {'Live Trade' if RUN_LIVE_TRADER else 'Paper Trade'}"

        elif direction == "CLOSE POSITION":

            position = self.mongo.open_positions.find_one(
                {"Trader": self.user["Name"], "Symbol": symbol, "Strategy": strategy})

            obj["Qty"] = position["Qty"]

            obj["Price"] = position["Price"]

            obj["Entry_Date"] = position["Entry_Date"]

            obj["Exit_Price"] = price

            obj["Exit_Date"] = getDatetime()

            exit_price = round(price * position["Qty"], 2)

            entry_price = round(position["Price"] * position["Qty"], 2)

            collection_insert = self.mongo.closed_positions.insert_one

            discord_message_to_push = f":closed_book: TradingBOT just closed \n Side: {side} \n Symbol: {pre_symbol} \n Qty: {position['Qty']} \n Entry Price: ${position['Price']} \n Entry Date: {position['Entry_Date']} \n Exit Price: ${price} \n Exit Date: {getDatetime()} \n Strategy: {strategy} \n Asset Type: {asset_type} \n :closed_book: Account Position: {'Live Trade' if RUN_LIVE_TRADER else 'Paper Trade'}"

            # REMOVE FROM OPEN POSITIONS
            is_removed = self.mongo.open_positions.delete_one(
                {"Trader": self.user["Name"], "Symbol": symbol, "Strategy": strategy})

            try:

                if int(is_removed.deleted_count) == 0:

                    self.logger.error(
                        f"INITIAL FAIL OF DELETING OPEN POSITION FOR SYMBOL {symbol} - {self.user['Name']} ({modifiedAccountID(self.account_id)})")

                    self.mongo.open_positions.delete_one(
                        {"Trader": self.user["Name"], "Symbol": symbol, "Strategy": strategy})

            except Exception:

                msg = f"{self.user['Name']} - {modifiedAccountID(self.account_id)} - {traceback.format_exc()}"

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

            msg = f"{self.user['Name']} - {modifiedAccountID(self.account_id)} - {traceback.format_exc()}"

            self.logger.error(msg)

        self.logger.info(
            f"Pushing {side} Order For {symbol} To {'Open Positions' if direction == 'OPEN POSITION' else 'Closed Positions'} ({modifiedAccountID(self.account_id)})")

        # REMOVE FROM QUEUE
        self.mongo.queue.delete_one({"Trader": self.user["Name"], "Symbol": symbol,
                               "Strategy": strategy, "Account_ID": self.account_id})

        discord_helpers.send_discord_alert(discord_message_to_push)

    # RUN TRADER
    @exception_handler
    def runTrader(self, trade_data, special_order_type="STANDARD"):
        """ METHOD RUNS ON A FOR LOOP ITERATING OVER THE TRADE DATA AND MAKING DECISIONS ON WHAT NEEDS TO BUY OR SELL.

        Args:
            trade_data ([list]): CONSISTS OF TWO DICTS TOP LEVEL, AND THEIR VALUES AS LISTS CONTAINING ALL THE TRADE DATA FOR EACH STOCK.
        """

        # UPDATE ALL ORDER STATUS'S
        self.updateStatus()

        # UPDATE USER ATTRIBUTE
        self.user = self.mongo.users.find_one({"Name": self.user["Name"]})

        row = trade_data

        strategy = row["Strategy"]

        symbol = row["Symbol"]

        asset_type = row["Asset_Type"]

        side = row["Side"]

        # CHECK OPEN POSITIONS AND QUEUE
        open_position = self.mongo.open_positions.find_one(
            {"Trader": self.user["Name"], "Symbol": symbol, "Strategy": strategy, "Account_ID": self.account_id})

        queued = self.mongo.queue.find_one(
            {"Trader": self.user["Name"], "Symbol": symbol, "Strategy": strategy, "Account_ID": self.account_id})

        strategy_object = self.mongo.strategies.find_one(
            {"Strategy": strategy})

        if not strategy_object:

            print('issue with strategy_object, see tradier --> __init__.py')

            strategy_object = self.strategies.find_one(
                {"Account_ID": self.account_id, "Strategy": strategy})

        position_type = strategy_object["Position_Type"]

        row["Position_Type"] = position_type

        if not queued:

            direction = None

            # IS THERE AN OPEN POSITION ALREADY IN MONGO FOR THIS SYMBOL/STRATEGY COMBO
            if open_position:

                direction = "CLOSE POSITION"

                # NEED TO COVER SHORT
                if side == "BUY" and position_type == "SHORT":

                    pass

                # NEED TO SELL LONG
                elif side == "SELL" and position_type == "LONG":

                    pass

                # NEED TO SELL LONG OPTION
                elif side == "SELL_TO_CLOSE" and position_type == "LONG":

                    pass

                # NEED TO COVER SHORT OPTION
                elif side == "BUY_TO_CLOSE" and position_type == "SHORT":

                    pass

                else:

                    pass

            else:

                direction = "OPEN POSITION"

                # NEED TO GO LONG
                if side == "BUY" and position_type == "LONG":

                    pass

                # NEED TO GO SHORT
                elif side == "SELL" and position_type == "SHORT":

                    pass

                # NEED TO GO SHORT OPTION
                elif side == "SELL_TO_OPEN" and position_type == "SHORT":

                    pass

                # NEED TO GO LONG OPTION
                elif side == "BUY_TO_OPEN" and position_type == "LONG":

                    pass

                else:

                    pass

            if direction != None:
                self.sendOrder(row if not open_position else {
                               **row, **open_position}, strategy_object, direction, special_order_type)
