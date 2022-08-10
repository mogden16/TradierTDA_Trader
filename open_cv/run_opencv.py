import time

import config
from discord import discord_helpers

SCAN_TIMES = config.SCAN_TIMES
SLEEP_AFTER_SCAN = config.SLEEP_AFTER_EACH_SCAN
ITM_OR_OTM = config.ITM_OR_OTM
RUN_OPENCV = config.RUN_OPENCV


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


def main(SHUT_DOWN, alertScanner, initiation, self, techanalysis, current_trend, TRADE_SYMBOL):
    if RUN_OPENCV and not SHUT_DOWN:
        switcher = {
            "BUY": "CALL",
            "SELL": "PUT",
            "CLOSE": 0,
            "Not Available": 99999
        }

        trade_signal = alertScanner.scanVisualAlerts()
        if config.GIVE_CONTINUOUS_UPDATES:
            print(f'current_trend: {trade_signal}')
        new_trend = switcher.get(trade_signal)

        if trade_signal == "Not Available":
            current_trend = new_trend

        elif trade_signal is not None and new_trend != current_trend:
            message = f'TradingBOT just saw a possible trade: {trade_signal}'
            discord_helpers.send_discord_alert(message)
            print(message)

            tos_signal = run(alertScanner, new_trend)
            if tos_signal:
                value = {
                    "Symbol": TRADE_SYMBOL,
                    "Strategy": "OpenCV",
                    "Option_Type": trade_signal
                }
                for api_trader in self.traders.values():
                    df = techanalysis.get_TA(value, api_trader)
                    signal = techanalysis.openCV_criteria(df, value, api_trader)
                    if signal:
                        self.set_trader(value, trade_signal=trade_signal, trade_type="LIMIT")
                        current_trend = new_trend

        return current_trend
