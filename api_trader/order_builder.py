# imports
from assets.helper_functions import getDatetime
from discord import discord_helpers
import os
import config
import traceback

THIS_FOLDER = os.path.dirname(os.path.abspath(__file__))

IS_TESTING = config.IS_TESTING
BUY_PRICE = config.BUY_PRICE
SELL_PRICE = config.SELL_PRICE
TAKE_PROFIT_PERCENTAGE = config.TAKE_PROFIT_PERCENTAGE
STOP_LOSS_PERCENTAGE = config.STOP_LOSS_PERCENTAGE
TRAIL_STOP_PERCENTAGE = config.TRAIL_STOP_PERCENTAGE
RUNNER_FACTOR = config.RUNNER_FACTOR
RUN_WEBSOCKET = config.RUN_WEBSOCKET


class OrderBuilder:

    def __init__(self):

        self.order = {
            "orderType": None,
            "price": None,
            "session": None,
            "duration": None,
            "orderStrategyType": "SINGLE",
            "orderLegCollection": [
                {
                    "instruction": None,
                    "quantity": None,
                    "instrument": {
                        "symbol": None,
                        "assetType": None,
                    }
                }
            ]
        }

        self.obj = {
            "Symbol": None,
            "Qty": None,
            "Position_Size": None,
            "Strategy": None,
            "Trader": self.user["Name"],
            "Order_ID": None,
            "Order_Status": None,
            "Side": None,
            "Asset_Type": None,
            "Account_ID": self.account_id,
            "Position_Type": None,
            "Direction": None
        }

    def standardOrder(self, trade_data, strategy_object, direction, OCOorder=False):

        isRunner = trade_data['isRunner']

        if isRunner == "TRUE":

            runnerFactor = RUNNER_FACTOR

        else:

            runnerFactor = 1

        symbol = trade_data["Symbol"]

        side = trade_data["Side"]

        strategy = trade_data["Strategy"]

        asset_type = "OPTION" if "Pre_Symbol" in trade_data else "EQUITY"

        trade_type = trade_data["Trade_Type"]

        # TDA ORDER OBJECT
        self.order["session"] = "NORMAL"

        self.order["duration"] = "GOOD_TILL_CANCEL" if asset_type == "EQUITY" else "DAY"

        self.order["orderLegCollection"][0]["instruction"] = side

        self.order["orderLegCollection"][0]["instrument"]["symbol"] = symbol if asset_type == "EQUITY" else trade_data["Pre_Symbol"]

        self.order["orderLegCollection"][0]["instrument"]["assetType"] = asset_type
        ##############################################################

        # MONGO OBJECT
        self.obj["Symbol"] = symbol

        self.obj["Strategy"] = strategy

        self.obj["Side"] = side

        self.obj["Asset_Type"] = asset_type

        self.obj["Position_Type"] = strategy_object["Position_Type"]

        self.obj["Order_Type"] = strategy_object["Order_Type"]

        self.obj["Direction"] = direction
        ##############################################################

        # IF OPTION
        if asset_type == "OPTION":

            self.obj["Pre_Symbol"] = trade_data["Pre_Symbol"]

            self.obj["Exp_Date"] = trade_data["Exp_Date"]

            self.obj["Option_Type"] = trade_data["Option_Type"]

            self.order["orderLegCollection"][0]["instrument"]["putCall"] = trade_data["Option_Type"]

            self.obj["isRunner"] = trade_data["isRunner"]

        # GET QUOTE FOR SYMBOL
        if IS_TESTING:

            price = 1

        # OCO ORDER NEEDS TO USE ASK PRICE FOR ISSUE WITH THE ORDER BEING TERMINATED UPON BEING PLACED
        elif OCOorder:

            resp = self.tdameritrade.getQuote(
                symbol if asset_type == "EQUITY" else trade_data["Pre_Symbol"])

            price = float(resp[symbol if asset_type == "EQUITY" else trade_data["Pre_Symbol"]][SELL_PRICE])

            if price > config.MAX_OPTIONPRICE or price < config.MIN_OPTIONPRICE:
                message = (f'actual price of option: {trade_data["Pre_Symbol"]} is outside of '
                           f'price setting on config.py')
                print(message)
                discord_helpers.send_discord_alert(message)
                return

        else:

            try:
                resp = self.tdameritrade.getQuote(
                    symbol if asset_type == "EQUITY" else trade_data["Pre_Symbol"])

                if trade_type == "MARKET":
                    price = float(resp[symbol if asset_type == "EQUITY" else trade_data["Pre_Symbol"]]['bidPrice'])

                else:
                    if side in ["BUY", "BUY_TO_OPEN", "BUY_TO_CLOSE"]:
                        price = float(resp[symbol if asset_type == "EQUITY" else trade_data["Pre_Symbol"]][BUY_PRICE])

                    else:
                        price = float(resp[symbol if asset_type == "EQUITY" else trade_data["Pre_Symbol"]][SELL_PRICE])

                if list(resp.keys())[0] == "error":
                    print(f'error scanning for {symbol}') if asset_type == "EQUITY" else (
                        f'error scanning for {trade_data["Pre_Symbol"]}')
                    self.error += 1
                    return

                elif price > config.MAX_OPTIONPRICE or price < config.MIN_OPTIONPRICE:
                    message = (f'actual price of option: {trade_data["Pre_Symbol"]} is outside of '
                               f'price setting on config.py')
                    print(message)
                    discord_helpers.send_discord_alert(message)
                    return None, None

            except Exception:

                msg = f"error: {traceback.format_exc()}"

                self.logger.error(msg)

        self.order["price"] = round(price, 2) if price >= 1 else round(price, 4)

        # IF OPENING A POSITION
        if direction == "OPEN POSITION":

            position_size = int(strategy_object["Position_Size"]) * runnerFactor

            shares = int(
                position_size/price) if asset_type == "EQUITY" else int((position_size / 100)/price)

            if shares > 0:

                self.order["orderType"] = "LIMIT"

                self.order["orderLegCollection"][0]["quantity"] = shares

                self.obj["Qty"] = shares

                self.obj["Position_Size"] = position_size

                self.obj["Entry_Price"] = price

                self.obj["Entry_Date"] = getDatetime()

            else:

                self.logger.warning(
                    f"{side} ORDER STOPPED: STRATEGY STATUS - {strategy_object['Active']} SHARES - {shares}")

                return None, None

        # IF CLOSING A POSITION
        elif direction == "CLOSE POSITION":

            if RUN_WEBSOCKET:

                self.order["orderType"] = "MARKET"

            else:

                self.order["orderType"] = "LIMIT"

            self.order["orderLegCollection"][0]["quantity"] = trade_data["Qty"]

            self.obj["Entry_Price"] = trade_data["Entry_Price"]

            self.obj["Entry_Date"] = trade_data["Entry_Date"]

            self.obj["Exit_Price"] = price

            self.obj["Exit_Date"] = getDatetime()

            self.obj["Qty"] = trade_data["Qty"]

            self.obj["Position_Size"] = trade_data["Position_Size"]
        ############################################################################

        return self.order, self.obj

    def OCOorder(self, trade_data, strategy_object, direction):

        order, obj = self.standardOrder(
            trade_data, strategy_object, direction, OCOorder=True)

        asset_type = "OPTION" if "Pre_Symbol" in trade_data else "EQUITY"

        side = trade_data["Side"]

        take_profit_price = round(order["price"] * TAKE_PROFIT_PERCENTAGE, 2) \
            if order["price"] * TAKE_PROFIT_PERCENTAGE >= 1 \
            else round(order["price"] * TAKE_PROFIT_PERCENTAGE, 4)

        stop_price = round(order["price"] * STOP_LOSS_PERCENTAGE, 2) \
            if order["price"] * STOP_LOSS_PERCENTAGE >= 1 \
            else round(order["price"] * STOP_LOSS_PERCENTAGE, 4)

        # GET THE INVERSE OF THE SIDE
        #####################################
        if side == "BUY_TO_OPEN":

            instruction = "SELL_TO_CLOSE"

        elif side == "BUY":

            instruction = "SELL"

        elif side == "SELL":

            instruction = "BUY"

        elif side == "SELL_TO_OPEN":

            instruction = "BUY_TO_CLOSE"
        #####################################

        order["orderStrategyType"] = "TRIGGER"

        order["childOrderStrategies"] = [
            {
                "orderStrategyType": "OCO",
                "childOrderStrategies": [
                    {
                        "orderStrategyType": "SINGLE",
                        "session": "NORMAL",
                        "duration": "GOOD_TILL_CANCEL",
                        "orderType": "LIMIT",
                        "price": take_profit_price,
                        "orderLegCollection": [
                            {
                                "instruction": instruction,
                                "quantity": obj["Qty"],
                                "instrument": {
                                    "assetType": asset_type,
                                    "symbol": trade_data["Symbol"] if asset_type == "EQUITY" else trade_data["Pre_Symbol"]
                                }
                            }
                        ]
                    },
                    {
                        "orderStrategyType": "SINGLE",
                        "session": "NORMAL",
                        "duration": "GOOD_TILL_CANCEL",
                        "orderType": "STOP",
                        "stopPrice": stop_price,
                        "orderLegCollection": [
                            {
                                "instruction": instruction,
                                "quantity": obj["Qty"],
                                "instrument": {
                                    "assetType": asset_type,
                                    "symbol": trade_data["Symbol"] if asset_type == "EQUITY" else trade_data["Pre_Symbol"]
                                }
                            }
                        ]
                    }
                ]
            }
        ]

        return order, obj

    def TRAILorder(self, trade_data, strategy_object, direction):

        order, obj = self.standardOrder(
            trade_data, strategy_object, direction)

        asset_type = "OPTION" if "Pre_Symbol" in trade_data else "EQUITY"

        side = trade_data["Side"]

        stop_price_offset = (round((order["price"] * TRAIL_STOP_PERCENTAGE), 2)
                             if asset_type == "OPTION"
                             else round(order["price"] * TRAIL_STOP_PERCENTAGE, 4))

        #####################################
        if side == "BUY_TO_OPEN":

            instruction = "SELL_TO_CLOSE"

        elif side == "BUY":

            instruction = "SELL"

        elif side == "SELL":

            instruction = "BUY"

        elif side == "SELL_TO_OPEN":

            instruction = "BUY_TO_CLOSE"
        #####################################

        order["orderStrategyType"] = "TRIGGER"

        order["childOrderStrategies"] = [
                    {
                        "orderStrategyType": "SINGLE",
                        "session": "NORMAL",
                        "duration": "GOOD_TILL_CANCEL",
                        "orderType": "TRAILING_STOP",
                        "stopPriceLinkBasis": "ASK",
                        "stopPriceLinkType": "VALUE",
                        "stopPriceOffset": stop_price_offset,
                        "orderLegCollection": [
                            {
                                "instruction": instruction,
                                "quantity": obj["Qty"],
                                "instrument": {
                                    "assetType": asset_type,
                                    "symbol": trade_data["Symbol"] if asset_type == "EQUITY" else trade_data["Pre_Symbol"]
                                }
                            }
                        ]
                    }
            ]

        return order, obj
