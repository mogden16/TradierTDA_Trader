import traceback
from datetime import datetime
import pandas as pd
from pyti.hull_moving_average import hull_moving_average as hma
import pandas_ta as ta
import config

RUN_TA = config.RUN_TA
RUN_30M_TA = config.RUN_30M_TA


def get_TA(value, trader):
    obj = {}
    try:
        symbol = value['Symbol']
        pre_symbol = value['Pre_Symbol']
        option_type = value['Option_Type']

        endDate = int(datetime.now().timestamp()) * 1000
        url = f"https://api.tdameritrade.com/v1/marketdata/{symbol}/pricehistory?periodType=day&period=10&frequencyType=minute&frequency=10&endDate={endDate}"
        resp = trader.tdameritrade.sendRequest(url)
        df = pd.DataFrame(resp['candles'], columns=['open', 'high', 'low', 'close', 'volume', 'datetime'])
        # print(resp)
        # print(df)
        fast = 9
        slow = 18

        df['datetime'] = pd.to_datetime(df['datetime'], unit='ms')
        df['hma_fast'] = hma(df['close'], fast)
        df['hma_slow'] = hma(df['close'], slow)

        qqe_length = 6
        qqe_smooth = 3
        qqe_factor = 2.621
        suffix = f'{qqe_length}_{qqe_smooth}_{qqe_factor}'
        df_qqe = ta.qqe(df['close'], length=qqe_length, smooth=qqe_smooth, factor=qqe_factor)
        qqe_column_name = f'QQE_{suffix}_RSIMA'
        df = pd.concat([df, df_qqe], axis=1)

        # df = df.set_index('datetime')

        # apd = mpf.make_addplot(df['hma_fast'],type = 'line')
        # apd = mpf.make_addplot(df['hma_slow], type='line')
        # mpf.plot(df,type='candle',volume=True,tight_layout=True,title=symbol,block=False)
        df['signalUP'] = df['hma_fast'] > df['hma_slow']
        df['signalDN'] = df['hma_fast'] < df['hma_slow']

        df2 = df.iloc[-2]
        qqe_oversold = df2[f'{qqe_column_name}'] < 35
        qqe_overbought = df2[f'{qqe_column_name}'] > 75
        qqe_value = round(df2[f'{qqe_column_name}'], 2)
        hullvalue_up = df2['signalUP']
        hullvalue_dn = df2['signalDN']

        obj = {
            "Pre_Symbol": pre_symbol,
            "Option_Type": option_type,
            "hullvalue_up": hullvalue_up,
            "hullvalue_dn": hullvalue_dn,
            "qqe_value": qqe_value,
            "qqe_overbought": qqe_overbought,
            "qqe_oversold": qqe_oversold
        }

        print(f'{pre_symbol} \n'
              f'HullUP_5m: {hullvalue_up}  '
              f'HullDN_5m: {hullvalue_dn}  '
              f'QQE: {qqe_value}')

        if RUN_30M_TA:
            url2 = f"https://api.tdameritrade.com/v1/marketdata/{symbol}/pricehistory?periodType=day&period=10&frequencyType=minute&frequency=30&endDate={endDate}"
            resp = trader.tdameritrade.sendRequest(url2)
            df_30m = pd.DataFrame(resp['candles'], columns=['open', 'high', 'low', 'close', 'volume', 'datetime'])

            fast = 9
            slow = 18

            df_30m['datetime'] = pd.to_datetime(df_30m['datetime'], unit='ms')
            df_30m['hma_fast'] = hma(df_30m['close'], fast)
            df_30m['hma_slow'] = hma(df_30m['close'], slow)

            df_30m = df_30m.set_index('datetime')
            df_30m['signalUP'] = df_30m['hma_fast'] > df_30m['hma_slow']
            df_30m['signalDN'] = df_30m['hma_fast'] < df_30m['hma_slow']

            df2_30m = df_30m.iloc[-1]
            hullvalue_up_30m = df2_30m['signalUP']
            hullvalue_dn_30m = df2_30m['signalDN']

            obj['hullvalue_up_30m'] = hullvalue_up_30m
            obj['hullvalue_dn_30m'] = hullvalue_dn_30m

            print(f'HullUP_30: {hullvalue_up_30m}  HullDN_30: {hullvalue_dn_30m} \n')




    except Exception:

        msg = f"error: {traceback.format_exc()}"


    return obj


def buy_criteria(signal):
    """THIS METHOD WILL CHECK THE INDICATORS AND INDICATE A BUY (BUY = 1)"""

    hullvalue_up = signal['hullvalue_up']
    hullvalue_dn = signal['hullvalue_dn']
    qqe_overbought = signal['qqe_overbought']
    qqe_oversold = signal['qqe_oversold']
    if config.RUN_30M_TA:
        hullvalue_up_30m = signal['hullvalue_up_30m']
        hullvalue_dn_30m = signal['hullvalue_dn_30m']


    if signal['Option_Type'] == "CALL":

        if config.RUN_30M_TA:

            if hullvalue_up and not qqe_overbought and hullvalue_up_30m:
                return True

        else:
            if hullvalue_up and not qqe_overbought:
                return True

    elif signal['Option_Type'] == "PUT":

        if config.RUN_30M_TA:

            if hullvalue_dn and not qqe_oversold and hullvalue_dn_30m:
                return True

        else:

            if hullvalue_dn and not qqe_oversold:
                return True

    else:
        print('Cant get option type. Running into issue with runTA')

    return False
