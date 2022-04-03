import config
import traceback

RUN_LIVE_TRADER = config.RUN_LIVE_TRADER
RUN_TRADIER = config.RUN_TRADIER
IS_TESTING = config.IS_TESTING
STREAMPRICE_LINK = config.STREAMPRICE_LINK.upper()
TAKEPROFIT_PERCENTAGE = config.TAKE_PROFIT_PERCENTAGE
STOPLOSS_PERCENTAGE = config.STOP_LOSS_PERCENTAGE
TRAILSTOP_PERCENTAGE = config.TRAIL_STOP_PERCENTAGE


def leaverunner(trader, open_position):
    print('Running leaverunner')

    trader.set_trader(open_position, trade_signal="BUY", isRunner="TRUE")


def tradierExtractOCOChildren(spec_order):
    """This method extracts oco children order ids and then sends it to be stored in mongo open positions.
    Data will be used by checkOCOtriggers with order ids to see if stop loss or take profit has been triggered.

    """
    orders = []
    oco_children = {
        "childOrderStrategies": {}
    }
    childOrderStrategies = spec_order["leg"][1:]

    for child in childOrderStrategies:
        sub_order = {}
        if 'stop_price' in child:
            sub_order["Order_ID"] = child['id']
            sub_order["Side"] = child["side"]
            sub_order["Stop_Price"] = child["stop_price"]
            sub_order["Order_Status"] = child["status"]
            orders.append(sub_order)

        else:
            sub_order["Order_ID"] = child['id']
            sub_order["Side"] = child["side"]
            sub_order["Takeprofit_Price"] = child['price']
            sub_order["Order_Status"] = child['status']
            orders.append(sub_order)

    oco_children['childOrderStrategies'] = orders

    return oco_children
