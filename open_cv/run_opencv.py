import time

import config
from discord import discord_helpers

SCAN_TIMES = config.SCAN_TIMES
SLEEP_AFTER_SCAN = config.SLEEP_AFTER_EACH_SCAN
ITM_OR_OTM = config.ITM_OR_OTM


def run(alertScanner, current_trend):
    switcher = {
        "BUY": "CALL",
        "SELL": "PUT",
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

        if new_trend == 99999:
            return False

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
