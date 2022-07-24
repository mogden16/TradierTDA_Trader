from datetime import datetime
import pandas as pd
import pandas_ta as ta
import pytz
from pyti.hull_moving_average import hull_moving_average as hma

import config
import tech_config

TIMEZONE = config.TIMEZONE
TRADETYPE = tech_config.TRADETYPE.lower()
STAMINA = tech_config.STAMINA.lower()
LOOKAHEAD = tech_config.LOOKAHEAD.lower()
EXITTYPE = tech_config.EXITTYPE.lower()
ORDERPRICE = tech_config.ORDERPRICE.lower()
OFFSET = int(tech_config.OFFSET)
LUNCHSTART_TIME = tech_config.LUNCHSTART_TIME
LUNCHSTOP_TIME = tech_config.LUNCHSTOP_TIME
RSIPAINTTYPE = tech_config.RSIPAINTTYPE.lower()
RSILENGTH = tech_config.RSILENGTH
RSIAVERAGETYPE = tech_config.RSIAVERAGETYPE.lower()
SMALLEST_AGGREGATION = tech_config.SMALLEST_AGGREGATION

RSISUPEROVERSOLD = tech_config.RSISUPEROVERSOLD
RSIOVERSOLD = tech_config.RSIOVERSOLD
RSILOWNEUTRAL = tech_config.RSILOWNEUTRAL
RSIHIGHNEUTRAL = tech_config.RSIHIGHNEUTRAL
RSIOVERBOUGHT = tech_config.RSIOVERBOUGHT
RSISUPEROVERBOUGHT = tech_config.RSISUPEROVERBOUGHT

SMI_FAST = tech_config.SMI_FAST
SMI_SLOW = tech_config.SMI_SLOW

def checkActive():
    current_time = datetime.now(pytz.timezone(TIMEZONE)).strftime('%H:%M:%S')

    if STAMINA == "lunchbreak":
        if "09:30:00" <= current_time <= LUNCHSTART_TIME or LUNCHSTOP_TIME <= current_time <= "16:00:00":
            active = True
        else:
            active = False

    elif STAMINA == "markethours":
        if "09:30:00" <= current_time <= "16:00:00":
            active = True
        else:
            active = False

    else:
        active = True

    return active


def scanRsi():
    pass


def set_aggregations():
    if SMALLEST_AGGREGATION == 1:
        aggs = {
            "lowestAggregation": 1,
            "middleAggregation": 5,
            "highestAggregation": 10,
            "extraHighAggregation": 15,
            "xxlAggregation": 30
        }
        return aggs

    elif SMALLEST_AGGREGATION == 5:
        aggs = {
            "lowestAggregation": 5,
            "middleAggregation": 10,
            "highestAggregation": 15,
            "extraHighAggregation": 30,
            "xxlAggregation": None
        }
        return aggs

    elif SMALLEST_AGGREGATION == 10:
        aggs = {
            "lowestAggregation": 10,
            "middleAggregation": 15,
            "highestAggregation": 30,
            "extraHighAggregation": None,
            "xxlAggregation": None
        }
        return aggs

    elif SMALLEST_AGGREGATION == 15:
        aggs = {
            "lowestAggregation": 15,
            "middleAggregation": 30,
            "highestAggregation": None,
            "extraHighAggregation": None,
            "xxlAggregation": None
        }
        return aggs

    elif SMALLEST_AGGREGATION == 30:
        aggs = {
            "lowestAggregation": 30,
            "middleAggregation": None,
            "highestAggregation": None,
            "extraHighAggregation": None,
            "xxlAggregation": None
        }
        return aggs

    else:
        print(f'SMALLEST_AGGREGATION IS {SMALLEST_AGGREGATION}: Cannot be larger than 30m')


def get_pricehistory():
    pass


def calculate_averageDailyRange(value, trader):
    symbol = value['Symbol']
    endDate = int(datetime.now().timestamp()) * 1000
    url = f"https://api.tdameritrade.com/v1/marketdata/{symbol}/pricehistory?periodType=month&period=1&frequencyType=daily&frequency=1&endDate={endDate}"
    resp = trader.tdameritrade.sendRequest(url)
    df = pd.DataFrame(resp['candles'], columns=['open', 'high', 'low', 'close', 'volume', 'datetime'])
    df['datetime'] = pd.to_datetime(df['datetime'], unit='ms')
    df = df.set_index('datetime')

    df['dayrange'] = df['high'] - df['low']
    df['ADR_10'] = df['dayrange'].rolling(window=10).mean()
    df['ADR_5'] = df['dayrange'].rolling(window=5).mean()

    df['hl1'] = df['open'] + (df['ADR_10'] / 2)
    df['ll1'] = df['open'] - (df['ADR_10'] / 2)
    df['hl2'] = df['open'] + (df['ADR_5'] / 2)
    df['ll2'] = df['open'] - (df['ADR_5'] / 2)

    return df


def get_TA(value, trader):

    symbol = value['Symbol']

    active = checkActive()

    if active:
        """ GET AGGREGATIONS"""
        aggs = set_aggregations()
        if aggs == None:
            print(f'ERROR: Check your SMALLEST_AGGREGATION')

        master_df = pd.DataFrame()

        for agg in aggs.values():

            if agg == None:
                continue

            else:
                """ GET PRICE HISTORY """
                endDate = int(datetime.now().timestamp()) * 1000
                if agg == 1:
                    url = f"https://api.tdameritrade.com/v1/marketdata/{symbol}/pricehistory?periodType=day&period=2&frequencyType=minute&frequency={agg}&endDate={endDate}"
                elif agg == 5:
                    url = f"https://api.tdameritrade.com/v1/marketdata/{symbol}/pricehistory?periodType=day&period=3&frequencyType=minute&frequency={agg}&endDate={endDate}"
                else:
                    url = f"https://api.tdameritrade.com/v1/marketdata/{symbol}/pricehistory?periodType=day&period=10&frequencyType=minute&frequency={agg}&endDate={endDate}"
                resp = trader.tdameritrade.sendRequest(url)
                df = pd.DataFrame(resp['candles'], columns=['open', 'high', 'low', 'close', 'volume', 'datetime'])
                df['datetime'] = pd.to_datetime(df['datetime'], unit='ms')
                df = df.set_index('datetime')

                """ HULL EMA """
                df['hma_fast'] = hma(df['close'], tech_config.HULL_FAST)
                df['hma_slow'] = hma(df['close'], tech_config.HULL_SLOW)

                """ QQE """
                df_qqe = ta.qqe(df['close'], length=tech_config.QQE_RSI_PERIOD,
                                smooth=tech_config.QQE_SLOW_FACTOR, factor=tech_config.QQE_SETTING, append=True)

                """ CREATE DATAFRAME """
                # df = pd.concat([df, df_qqe], axis=1)
                df['agg'] = agg
                master_df = pd.concat([master_df, df], axis=0, ignore_index=False)

        return master_df


def buy_criteria(df, value, trader):
    symbol = value['Symbol']
    pre_symbol = value['Pre_Symbol']

    agg_group = df.groupby('agg')

    if SMALLEST_AGGREGATION == 1:
        df_1m = agg_group.get_group(1)
        df_5m = agg_group.get_group(5)
        df_10m = agg_group.get_group(10)
        df_15m = agg_group.get_group(15)
        df_30m = agg_group.get_group(30)

    elif SMALLEST_AGGREGATION == 5:
        df_5m = agg_group.get_group(5)
        df_10m = agg_group.get_group(10)
        # df_15m = agg_group.get_group(15)
        df_30m = agg_group.get_group(30)

    elif SMALLEST_AGGREGATION == 10:
        df_10m = agg_group.get_group(10)
        df_15m = agg_group.get_group(15)
        df_30m = agg_group.get_group(30)

    elif SMALLEST_AGGREGATION == 15:
        df_15m = agg_group.get_group(15)
        df_30m = agg_group.get_group(30)

    elif SMALLEST_AGGREGATION == 30:
        df_30m = agg_group.get_group(30)

    adr = calculate_averageDailyRange(value, trader)

    # df_5m['hl1'] = adr['hl1']
    # df_5m['hl2'] = adr['hl2']
    # df_5m['ll1'] = adr['ll1']
    # df_5m['ll2'] = adr['hl2']

    # df_5m['hl1'] = adr['hl1'].reindex(df_5m.index, method='nearest')
    # df_5m['hl2'] = adr['hl2'].reindex(df_5m.index, method='nearest')
    # df_5m['ll1'] = adr['ll1'].reindex(df_5m.index, method='nearest')
    # df_5m['ll2'] = adr['ll2'].reindex(df_5m.index, method='nearest')
    # df_10m['hl1'] = adr['hl1'].reindex(df_10m.index, method='nearest')
    # df_10m['hl2'] = adr['hl2'].reindex(df_10m.index, method='nearest')
    # df_10m['ll1'] = adr['ll1'].reindex(df_10m.index, method='nearest')
    # df_10m['ll2'] = adr['ll2'].reindex(df_10m.index, method='nearest')
    # df_30m['hl1'] = adr['hl1'].reindex(df_30m.index, method='nearest')
    # df_30m['hl2'] = adr['hl2'].reindex(df_30m.index, method='nearest')
    # df_30m['ll1'] = adr['ll1'].reindex(df_30m.index, method='nearest')
    # df_30m['ll2'] = adr['ll2'].reindex(df_30m.index, method='nearest')

    current_adr = adr.iloc[-1]

    pRsiMa = df.columns[-4]
    pFastAtrRsiTL = df.columns[-5]

    """ SHOW CHART """
    df_5m = df_5m.iloc[-150:]
    df_10m = df_10m.iloc[-150:]
    df_30m = df_30m.iloc[-150:]


    # apd = [
    #     mpf.make_addplot(df_5m[f'{pRsiMa}'],
    #                      type='line', color='green', panel=1),
    #     mpf.make_addplot(df_5m[f'{pFastAtrRsiTL}'],
    #                      type='line', color='grey', panel=1),
    #     mpf.make_addplot(df_5m[f'hma_fast'],
    #                      type='line', color='green', panel=0),
    #     mpf.make_addplot(df_5m[f'hma_slow'],
    #                      type='line', color='grey', panel=0),
    #     mpf.make_addplot(df_5m[f'hl1'],
    #                      type='line', color='green', panel=0),
    #     mpf.make_addplot(df_5m[f'hl2'],
    #                      type='line', color='green', panel=0),
    #     mpf.make_addplot(df_5m[f'll1'],
    #                      type='line', color='red', panel=0),
    #     mpf.make_addplot(df_5m[f'll2'],
    #                      type='line', color='red', panel=0),
    #     ]
    # ape = [
    #     mpf.make_addplot(df_10m[f'{pRsiMa}'],
    #                      type='line', color='green', panel=1),
    #     mpf.make_addplot(df_10m[f'{pFastAtrRsiTL}'],
    #                      type='line', color='grey', panel=1),
    #     mpf.make_addplot(df_10m[f'hma_fast'],
    #                      type='line', color='green', panel=0),
    #     mpf.make_addplot(df_10m[f'hma_slow'],
    #                      type='line', color='grey', panel=0),
    #     mpf.make_addplot(df_10m[f'hl1'],
    #                      type='line', color='green', panel=0),
    #     mpf.make_addplot(df_10m[f'hl2'],
    #                      type='line', color='green', panel=0),
    #     mpf.make_addplot(df_10m[f'll1'],
    #                      type='line', color='red', panel=0),
    #     mpf.make_addplot(df_10m[f'll2'],
    #                      type='line', color='red', panel=0)
    # ]
    # apf = [
    #     mpf.make_addplot(df_30m[f'{pRsiMa}'],
    #                      type='line', color='green', panel=1),
    #     mpf.make_addplot(df_30m[f'{pFastAtrRsiTL}'],
    #                      type='line', color='grey', panel=1),
    #     mpf.make_addplot(df_30m[f'hma_fast'],
    #                      type='line', color='green', panel=0),
    #     mpf.make_addplot(df_30m[f'hma_slow'],
    #                      type='line', color='grey', panel=0),
    #     mpf.make_addplot(df_30m[f'hl1'],
    #                      type='line', color='green', panel=0),
    #     mpf.make_addplot(df_30m[f'hl2'],
    #                      type='line', color='green', panel=0),
    #     mpf.make_addplot(df_30m[f'll1'],
    #                      type='line', color='red', panel=0),
    #     mpf.make_addplot(df_30m[f'll2'],
    #                      type='line', color='red', panel=0)
    # ]
    #
    # mpf.plot(
    #     df_5m, type='candle', volume=True, title=f'{symbol}_5', addplot=apd, main_panel=0, volume_panel=2, block=False
    # )
    # mpf.plot(
    #     df_10m,type='candle', volume=True, title=f'{symbol}_10', addplot=ape, main_panel=0, volume_panel=2, block=False
    # )
    # mpf.plot(
    #     df_30m, type='candle', volume=True, title=f'{symbol}_30', addplot=apf, main_panel=0, volume_panel=2, block=False
    # )

    """ RUN STRATEGY """

    twolast_5m_bar = df_5m.iloc[-3]
    last_5m_bar = df_5m.iloc[-2]
    current_10m_bar = df_10m.iloc[-1]
    last_10m_bar = df_10m.iloc[-2]
    twolast_10m_bar = df_10m.iloc[-3]
    current_30m_bar = df_30m.iloc[-1]
    current_adr = adr.iloc[-1]

    if value['Option_Type'].upper() == "CALL":

        if (current_10m_bar['high'] > (current_adr['hl2'] or current_adr['hl1'])) and \
                (current_10m_bar['close'] <= (current_adr['hl1'] or current_adr['hl2'])):
            print(f'called for CALL for {pre_symbol} but in HIGH resistance zone')

        elif (last_5m_bar[pRsiMa] > last_5m_bar[pFastAtrRsiTL]) and \
                (twolast_5m_bar[pRsiMa] < twolast_5m_bar[pFastAtrRsiTL]) and \
                (current_30m_bar[pRsiMa] > RSILOWNEUTRAL) and \
                (last_10m_bar['hma_fast'] >= last_10m_bar['hma_slow']) and \
                (current_30m_bar[pRsiMa] < RSISUPEROVERBOUGHT):
            message = f"Buying CALL for {pre_symbol} because QQE Cross UP & Current 30m QQE is above 45"
            # discord_helpers.send_discord_alert(message)
            print(message)
            return True

        else:
            if (current_adr['ll1'] <= current_10m_bar['close'] <= current_adr['ll2']) and (current_30m_bar[pRsiMa] > RSIHIGHNEUTRAL):
                message = f"Buying because CALL is at bottom of ADR & 30m QQE is over 55"
                # discord_helpers.send_discord_alert(message)
                print(message)
                return True

    elif value['Option_Type'].upper() == "PUT":

        if (current_10m_bar['low'] < (current_adr['ll2'] or current_adr['ll1'])) and \
                (current_10m_bar['close'] >= (current_adr['ll1'] or current_adr['ll2'])):
            print(f'called for PUT for {pre_symbol} but in LOW resistance zone')

        elif (last_5m_bar[pRsiMa] < last_5m_bar[pFastAtrRsiTL]) and \
                (twolast_5m_bar[pRsiMa] > twolast_5m_bar[pFastAtrRsiTL]) and \
                (current_30m_bar[pRsiMa] < RSIHIGHNEUTRAL) and \
                (last_10m_bar['hma_fast'] <= last_10m_bar['hma_slow']) and \
                (current_30m_bar[pRsiMa] > RSISUPEROVERSOLD):
            message = f"Buying PUT for {pre_symbol} because QQE Cross DOWN & Current 30m QQE is below 55"
            # discord_helpers.send_discord_alert(message)
            print(message)
            return True

        else:
            if (current_adr['hl1'] <= current_10m_bar['close'] <= current_adr['hl2']) and (current_30m_bar[pRsiMa] < RSILOWNEUTRAL):
                message = f"Buying because PUT is at top of ADR & 30m QQE is below 45"
                # discord_helpers.send_discord_alert(message)
                print(message)
                return True


def sell_criteria(df, value):

    symbol = value['Symbol']

    agg_group = df.groupby('agg')

    if SMALLEST_AGGREGATION == 5:
        df_5m = agg_group.get_group(5)
        df_10m = agg_group.get_group(10)
        df_30m = agg_group.get_group(30)

    last_5m_bar = df_5m.iloc[-2]
    current_10m_bar = df_10m.iloc[-1]
    last_10m_bar = df_10m.iloc[-2]
    current_30m_bar = df_30m.iloc[-1]

    if value['Option_Type'].upper() == "CALL":

        if last_5m_bar['hma_fast'] < last_5m_bar['hma_slow']:
            return True

    elif value['Option_Type'].upper() == "PUT":

        if last_5m_bar['hma_fast'] > last_5m_bar['hma_slow']:
            return True


def openCV_criteria(df, value, trader):

    adr = calculate_averageDailyRange(value, trader)
    symbol = value['Symbol']

    agg_group = df.groupby('agg')

    if SMALLEST_AGGREGATION == 5:
        df_5m = agg_group.get_group(5)
        df_10m = agg_group.get_group(10)
        df_30m = agg_group.get_group(30)

    last_5m_bar = df_5m.iloc[-2]
    current_5m_bar = df_5m.iloc[-1]
    current_10m_bar = df_10m.iloc[-1]
    last_10m_bar = df_10m.iloc[-2]
    current_30m_bar = df_30m.iloc[-1]
    current_adr = adr.iloc[-1]

    if value['Option_Type'].upper() == "CALL":

        if (current_adr['hl1'] <= current_5m_bar['close'] <= current_adr['hl2']) or \
                (current_adr['hl1'] <= current_5m_bar['high'] <= current_adr['hl2']) or \
                (current_adr['hl1'] <= current_5m_bar['low'] <= current_adr['hl2']) or \
                (current_adr['hl1'] <= current_5m_bar['open'] <= current_adr['hl2']):
            return False

    elif value['Option_Type'].upper() == "PUT":

        if (current_adr['ll1'] <= current_5m_bar['close'] <= current_adr['ll2']) or \
                (current_adr['ll1'] <= current_5m_bar['high'] <= current_adr['ll2']) or \
                (current_adr['ll1'] <= current_5m_bar['low'] <= current_adr['ll2']) or \
                (current_adr['ll1'] <= current_5m_bar['open'] <= current_adr['ll2']):
            return False

    return True
