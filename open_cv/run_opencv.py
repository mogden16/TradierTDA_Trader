import config
import time
from open_cv import AlertScanner
from discord import discord_helpers

SCAN_TIMES = config.SCAN_TIMES
SLEEP_AFTER_SCAN = config.SLEEP_AFTER_EACH_SCAN


def run(current_trend):
    switcher = {
        "BUY": 1,
        "SELL": -1,
        "CLOSE": 0,
        "Not Available": 99999
    }

    alertScanner = AlertScanner.AlertScanner()

    for i in range(0, SCAN_TIMES+1):
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
