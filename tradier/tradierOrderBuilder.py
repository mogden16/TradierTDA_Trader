import config
import polygon

RUNNER_FACTOR = config.RUNNER_FACTOR
IS_TESTING = config.IS_TESTING

class tradierOrderBuilder:

    def __init__(self):

        self.order = {
            'class': None,
            'symbol': None,
            'option_symbol': None,
            'side': None,
            'quantity': None,
            'type': None,
            'duration': None
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

        self.obj['Strategy'] = strategy

        asset_type = "OPTION" if "Pre_Symbol" in trade_data else "EQUITY"

        self.order['duration'] = 'day'

        self.order['class'] = asset_type.lower()

        self.order['symbol'] = symbol

        self.obj['Symbol'] = symbol

        self.order['side'] = side.lower()

        self.obj['Side'] = side

        self.obj['Account_ID'] = self.account_id

        self.obj['Asset_Type'] = asset_type

        self.order['type'] = trade_type.lower()

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

            self.obj['Price'] = str(price)

        position_size = int((strategy_object["Position_Size"]) * runnerFactor)

        self.obj['Position_Size'] = position_size

        qty = int(position_size/price) if asset_type == "EQUITY" else int((position_size / 100)/price)

        if qty > 0:

            self.order['quantity'] = str(qty)
            self.obj['Qty'] = qty

        else:

            self.logger.warning(f"{side} ORDER STOPPED: STRATEGY STATUS - {strategy_object['Active']} SHARES - {qty}")

            return None, None

        self.obj['Trader'] = self.user['Name']

        self.obj["Position_Type"] = strategy_object["Position_Type"]

        self.obj['isRunner'] = trade_data['isRunner']

        self.obj["Direction"] = direction

        return self.order, self.obj
