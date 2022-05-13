import config
import time
import math
from open_cv import AlertScanner
from discord import discord_helpers
import pandas as pd

SCAN_TIMES = config.SCAN_TIMES
SLEEP_AFTER_SCAN = config.SLEEP_AFTER_EACH_SCAN
ITM_OR_OTM = config.ITM_OR_OTM
OPTION_PRICE_INCREMENT = config.OPTION_PRICE_INCREMENT


def run(alertScanner, current_trend):
    switcher = {
        "BUY": 1,
        "SELL": -1,
        "CLOSE": 0,
        "Not Available": 99999
    }

    for i in range(1, SCAN_TIMES+1):
        print(f'scan#: {i}/{SCAN_TIMES}')
        prev_trade_signal = current_trend

        print(f'Sleeping for {SLEEP_AFTER_SCAN}s')
        time.sleep(SLEEP_AFTER_SCAN)

        trade_signal = alertScanner.scanVisualAlerts()
        new_trend = switcher.get(trade_signal)

        if new_trend == current_trend:
            if i != SCAN_TIMES:
                continue

            else:
                return True

        else:
            message = f'TradingBOT just saw a repaint - signal stopped'
            discord_helpers.send_discord_alert(message)
            print(message)

            return False

def get_optioncontract(trader, trade_symbol, exp_date, option_type):

    resp = trader.tdameritrade.getQuote(trade_symbol)
    price = float(resp[trade_symbol]["lastPrice"])

    if ITM_OR_OTM == "OTM":
        if option_type == "CALL":
            strike_price = int(math.floor(price) + OPTION_PRICE_INCREMENT)
        else:
            strike_price = int(math.ceil(price) - OPTION_PRICE_INCREMENT)

    elif ITM_OR_OTM == "ITM":
        if option_type == "CALL":
            strike_price = int(math.ceil(price) - OPTION_PRICE_INCREMENT)
        else:
            strike_price = int(math.floor(price) + OPTION_PRICE_INCREMENT)

    url = f"https://api.tdameritrade.com/v1/marketdata/chains?symbol={trade_symbol}&contractType={option_type}&includeQuotes=False&strike={strike_price}&fromDate={exp_date}&toDate={exp_date}"
    resp = trader.tdameritrade.sendRequest(url)

    option_symbol = None
    expdatemapkey = option_type.lower() + "ExpDateMap"

    for dt in resp[expdatemapkey]:
        for strikePrice in resp[expdatemapkey][dt]:
            last = resp[expdatemapkey][dt][strikePrice][0]["last"]
            delta = resp[expdatemapkey][dt][strikePrice][0]["delta"]

            while last < config.MIN_OPTIONPRICE or last > config.MAX_OPTIONPRICE or abs(delta) < config.MIN_DELTA:
                if ITM_OR_OTM == "OTM":
                    if option_type == "CALL":
                        strike_price += 1
                    else:
                        strike_price -= 1

                elif ITM_OR_OTM == "ITM":
                    if option_type == "CALL":
                        strike_price -= 1
                    else:
                        strike_price += 1

                url = f"https://api.tdameritrade.com/v1/marketdata/chains?symbol={trade_symbol}&contractType={option_type}&includeQuotes=FALSE&strike={strike_price}&fromDate={exp_date}&toDate={exp_date}"
                resp = trader.tdameritrade.sendRequest(url)

                for dt in resp[expdatemapkey]:
                    for strikePrice in resp[expdatemapkey][dt]:
                        last = resp[expdatemapkey][dt][strikePrice][0]["last"]
                        delta = resp[expdatemapkey][dt][strikePrice][0]["delta"]

    return resp
