import config
import polygon

RUNNER_FACTOR = config.RUNNER_FACTOR
IS_TESTING = config.IS_TESTING

TAKE_PROFIT_PERCENTAGE = config.TAKE_PROFIT_PERCENTAGE
STOP_LOSS_PERCENTAGE = config.STOP_LOSS_PERCENTAGE

class tradierOrderBuilder:

    def __init__(self):

        self.order = {
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

    def standardOrder(self, trade_data, strategy_object, direction):

        isRunner = trade_data['isRunner']

        if isRunner == "TRUE":

            runnerFactor = RUNNER_FACTOR

        else:

            runnerFactor = 1

        symbol = trade_data["Symbol"]

        side = trade_data["Side"]

        strategy = trade_data["Strategy"]

        trade_type = trade_data["Trade_Type"]

        asset_type = "OPTION" if "Pre_Symbol" in trade_data else "EQUITY"

        # TRADIER

        self.order['duration'] = 'day'

        self.order['class'] = asset_type.lower()

        self.order['symbol'] = symbol

        self.order['side'] = side.lower()

        self.order['type'] = trade_type.lower()

        self.obj['Strategy'] = strategy

        self.obj['Symbol'] = symbol

        self.obj['Side'] = side

        self.obj['Account_ID'] = self.account_id

        self.obj['Asset_Type'] = asset_type

        self.obj['Trade_Type'] = trade_type

        self.obj["Order_Type"] = strategy_object["Order_Type"]

        if asset_type == "OPTION":

            formatted_exp_date = trade_data['Exp_Date'][2:].replace("-", "")

            trading_symbol = polygon.build_option_symbol(symbol, formatted_exp_date,
                                                         trade_data['Option_Type'], trade_data['Strike_Price'],
                                                         prefix_o=False)

            self.order['option_symbol'] = trading_symbol

            self.obj['Pre_Symbol'] = trade_data['Pre_Symbol']

            self.obj['Exp_Date'] = trade_data['Exp_Date']

            self.obj['Option_Type'] = trade_data['Option_Type']

            self.obj['isRunner'] = trade_data['isRunner']

        if trade_type == "LIMIT":

            if not IS_TESTING:

                symbol_for_quote = trading_symbol if asset_type == "OPTION" else symbol

                resp = self.get_quote(symbol_for_quote)

                if side == "BUY_TO_OPEN" or side == "BUY":

                    price = resp[f'{config.BUY_PRICE}']

                else:

                    price = resp[f'{config.SELL_PRICE}']

            else:

                price = 1

            self.order['price'] = str(price)

            self.obj['Price'] = float(price)

        position_size = int((strategy_object["Position_Size"]) * runnerFactor)

        qty = int(position_size/price) if asset_type == "EQUITY" else int((position_size / 100)/price)

        if qty > 0:

            self.order['quantity'] = str(qty)

            self.obj['Qty'] = qty

        else:

            self.logger.warning(f"{side} ORDER STOPPED: STRATEGY STATUS - {strategy_object['Active']} SHARES - {qty}")

            return None, None

        self.obj['Position_Size'] = position_size

        self.obj['Trader'] = self.user['Name']

        self.obj["Position_Type"] = strategy_object["Position_Type"]

        self.obj['isRunner'] = trade_data['isRunner']

        self.obj["Direction"] = direction

        return self.order, self.obj


    def otoco_order(self, trade_data, strategy_object, direction):

        asset_type = "OPTION" if "Pre_Symbol" in trade_data else "EQUITY"

        symbol = trade_data["Symbol"]

        if asset_type == "OPTION":

            formatted_exp_date = trade_data['Exp_Date'][2:].replace("-", "")

            trading_symbol = polygon.build_option_symbol(symbol, formatted_exp_date,
                                                         trade_data['Option_Type'], trade_data['Strike_Price'],
                                                         prefix_o=False)

        else:
            print(f'otoco trades cannot be done with equtities')
            return

        isRunner = trade_data['isRunner']

        if isRunner == "TRUE":

            runnerFactor = RUNNER_FACTOR

        else:

            runnerFactor = 1

        side = trade_data["Side"]

        strategy = trade_data["Strategy"]

        trade_type = trade_data["Trade_Type"]

        if trade_type == "LIMIT":

            if not IS_TESTING:

                symbol_for_quote = trading_symbol if asset_type == "OPTION" else symbol

                resp = self.get_quote(symbol_for_quote)

                if side == "BUY_TO_OPEN" or side == "BUY":

                    price = resp[f'{config.BUY_PRICE}']

                else:

                    price = resp[f'{config.SELL_PRICE}']

            else:

                price = 1

            tradier_entry_price = str(price)

            entry_price = float(price)

        position_size = int((strategy_object["Position_Size"]) * runnerFactor)

        qty = int(position_size/price) if asset_type == "EQUITY" else int((position_size / 100)/price)

        # base order
        self.order['account_id'] = self.account_id
        self.order['class'] = 'otoco'
        self.order['duration'] = 'day'
        self.order['symbol[0]'] = symbol
        self.order['quantity[0]'] = str(qty)
        self.order['type[0]'] = 'limit'
        self.order['option_symbol[0]'] = trading_symbol
        self.order['side[0]'] = side.lower()
        self.order['price[0]'] = tradier_entry_price

        # takeprofit order
        self.order['symbol[1]'] = symbol
        self.order['quantity[1]'] = str(qty)
        self.order['type[1]'] = 'limit'
        self.order['option_symbol[1]'] = trading_symbol
        self.order['side[1]'] = 'sell_to_close'
        self.order['price[1]'] = str(round(entry_price * (1 + TAKE_PROFIT_PERCENTAGE),2))

        # stoploss order
        self.order['symbol[2]'] = symbol
        self.order['quantity[2]'] = str(qty)
        self.order['type[2]'] = 'stop'
        self.order['option_symbol[2]'] = trading_symbol
        self.order['side[2]'] = 'sell_to_close'
        self.order['stop[2]'] = str(round(entry_price * (1 - STOP_LOSS_PERCENTAGE),2))

        return self.order, self.obj

