import traceback
from datetime import datetime
import pandas as pd
from pyti.hull_moving_average import hull_moving_average as hma
import pandas_ta as ta
import config
import tech_config
import pytz
import mplfinance as mpf
import numpy as np


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
    df['dayrange'] = df['high']-df['low']
    dayrange = []

    for i in range(1,12):
        one_dayrange = df['high'][-i] - df['low'][-i]
        dayrange.append(one_dayrange)

    adr_10 = sum(dayrange[1:11])
    adr_5 = sum(dayrange[1:6])

    obj = {
        "hl1": df['open'] + (adr_10/2),
        "ll1": df['open'] - (adr_10/2),
        "hl2": df['open'] + (adr_5/2),
        "ll2": df['open'] - (adr_5/2)
    }

    return obj


def get_TA(value, trader):

    adr = calculate_averageDailyRange(value, trader)
    symbol = value['Symbol']
    pre_symbol = value['Pre_Symbol']
    option_type = value['Option_Type']

    active = checkActive()

    if active:
        """ GET AGGREGATIONS"""
        aggs = set_aggregations()
        if aggs == None:
            print(f'ERROR: Check your SMALLEST_AGGREGATION')

        master_df = []

        for agg in aggs.values():

            if agg == None:
                continue

            else:
                """ GET PRICE HISTORY """
                endDate = int(datetime.now().timestamp()) * 1000
                url = f"https://api.tdameritrade.com/v1/marketdata/{symbol}/pricehistory?periodType=day&period=10&frequencyType=minute&frequency={agg}&endDate={endDate}"
                resp = trader.tdameritrade.sendRequest(url)
                df = pd.DataFrame(resp['candles'], columns=['open', 'high', 'low', 'close', 'volume', 'datetime'])
                df['datetime'] = pd.to_datetime(df['datetime'], unit='ms')

                # df = pd.read_excel('Price_History.xlsx')
                # df = df.iloc[:,:-6]

                df = df.set_index('datetime')

                """ HULL EMA """
                df['hma_fast'] = hma(df['close'], tech_config.HULL_FAST)
                df['hma_slow'] = hma(df['close'], tech_config.HULL_SLOW)

                """ QQE """
                df_qqe = ta.qqe(df['close'], length=tech_config.QQE_RSI_PERIOD,
                                smooth=tech_config.QQE_SLOW_FACTOR, factor=tech_config.QQE_SETTING)

                """ CREATE DATAFRAME """
                df = pd.concat([df, df_qqe], axis=1)
                pRsiMa = df.columns[-3]
                pFastAtrRsiTL = df.columns[-4]

                """ BUY_CRITERIA """
                " LONG "
                df.loc[(df[pRsiMa] > df[pFastAtrRsiTL]) &
                       (df[pRsiMa] > RSILOWNEUTRAL) &
                       (df[pRsiMa] < RSISUPEROVERBOUGHT),
                       'QQE_Long'] = 1

                df['QQE_Long'] = df['QQE_Long'].replace(np.nan, 0)

                df.loc[(df['QQE_Long'] == 1) &
                       (df['QQE_Long'].shift(1) == 0),
                       'Total_Long'] = 1

                " SHORT "
                df.loc[(df[pRsiMa] < df[pFastAtrRsiTL]) &
                       (df[pRsiMa] < RSIHIGHNEUTRAL) &
                       (df[pRsiMa] < RSISUPEROVERSOLD),
                       'QQE_Short'] = 1

                df['QQE_Short'] = df['QQE_Short'].replace(np.nan, 0)

                df.loc[(df['QQE_Short'] == 1) &
                       (df['QQE_Short'].shift(1) == 0),
                       'Total_Short'] = 1

                """ SHOW CHART """
                df = df.iloc[-150:]

                apd = [
                    mpf.make_addplot(df[f'{pRsiMa}'],
                                     type='line', color='green', panel=1),
                    mpf.make_addplot(df[f'{pFastAtrRsiTL}'],
                                     type='line', color='grey', panel=1),
                    mpf.make_addplot(df[f'hma_slow'],
                                     type='line', color='blue', panel=0),
                    mpf.make_addplot(df[f'hma_fast'],
                                     type='line', color='orange', panel=0),
                    mpf.make_addplot(df['Total_Long'],
                                     type='scatter', color='yellow', panel=1),
                    mpf.make_addplot(df['Total_Short'],
                                     type='scatter', color='orange', panel=1)
                    ]

                mpf.plot(
                    df,
                    type='candle',
                    volume=True,
                    title=f'{symbol}_{agg}',
                    addplot=apd,
                    main_panel=0,
                    volume_panel=2,
                    block=False

                )

                master_df.append(df)

        return master_df, value

def buy_criteria(df, value):
    df = pd.DataFrame.from_dict(df)

    if tech_config.LOOKAHEAD.upper() == "PREVBAR":
        bar = df.iloc[-2]

    elif tech_config.LOOKAHEAD.upper() == "CURRENTBAR":
        bar = df.iloc[-1]

    if value['Option_Type'].upper() == "CALL":
        if bar['Total_Long'] == 1:
            return True

    elif value['Option_Type'].upper() == "PUT":
        if bar['Total_Short'] == 1:
            return True

#
#
#
#
#
#
# runFlashTA()
