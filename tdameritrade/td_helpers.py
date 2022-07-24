import os
import sys

import pandas as pd
from tda import auth

import config

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


token_path = config.TOKEN_PATH
api_key = config.API_KEY
redirect_uri = config.REDIRECT_URI
RUNNER_FACTOR = config.RUNNER_FACTOR


def get_token_selenium():
    try:
        c = auth.client_from_token_file(token_path, api_key)

    except FileNotFoundError:
        from selenium import webdriver
        with webdriver.Chrome() as driver:
            c = auth.client_from_login_flow(
                driver, api_key, redirect_uri, token_path)


def getOptionChain(api_trader, symbol, option_type, exp_date):
    """ METHOD GETS AN OPTION CHAIN FOR A PARTICULAR OPTION

    Args:
        symbol ([str]): STOCK SYMBOL
        option_type ([str]): CALL OR PUT
        strike_price ([str]): STRIKE PRICE
        exp_date ([str]): YYYY-MM-DD

    Returns:
        [json]: STOCK QUOTE
    """

    url = f"https://api.tdameritrade.com/v1/marketdata/chains?symbol={symbol}&" \
          f"contractType={option_type}&" \
          f"strikeCount=25&" \
          f"includeQuotes=TRUE&" \
          f"range={config.ITM_OR_OTM}&" \
          f"fromDate={exp_date}&" \
          f"toDate={exp_date}"

    resp = api_trader.tdameritrade.sendRequest(url)
    expdatemapkey = option_type.lower() + "ExpDateMap"

    chain = []
    for dt in resp[expdatemapkey]:
        for strikePrice in resp[expdatemapkey][dt]:
            for i in resp[expdatemapkey][dt][strikePrice]:
                chain.append(i)

    df = pd.DataFrame(chain)
    df = df.rename(columns={"symbol": "pre_symbol"})

    return df

def getSingleOption(df, **kwargs):
    isRunner = kwargs.get('isRunner', False)

    df = df.dropna(subset=['delta', 'ask', 'totalVolume'])
    df = df.astype({"delta": "float", "ask": "float", "totalVolume": "float"})
    df['delta'] = df['delta'].abs()
    inTheMoney = True if config.ITM_OR_OTM == "ITM" else False

    minOptionPrice = (RUNNER_FACTOR * config.MIN_OPTIONPRICE) if isRunner else config.MIN_OPTIONPRICE
    maxOptionPrice = (RUNNER_FACTOR * config.MAX_OPTIONPRICE) if isRunner else config.MAX_OPTIONPRICE
    minVolume = config.RUNNER_MIN_VOLUME if isRunner else config.MIN_VOLUME
    minDelta = (RUNNER_FACTOR * config.MIN_DELTA) if isRunner else config.MIN_DELTA

    filter_criteria = (df['ask'] >= minOptionPrice) & \
                      (df['totalVolume'] >= minVolume) & \
                      (df['delta'] >= minDelta) & \
                      (df['ask'] <= maxOptionPrice) & \
                      (df['inTheMoney'] == inTheMoney)

    df1 = df[filter_criteria]
    if df1.empty:
        return None

    else:
        df1 = df1.sort_values(by='totalVolume', ascending=False)
        df1 = df1.iloc[0]

        return df1

def getPotentialDF(df):
    inTheMoney = True if config.ITM_OR_OTM == "ITM" else False

    df = df[df['inTheMoney'] == inTheMoney]
    df = df.loc[(df['ask'] >= config.MIN_OPTIONPRICE) & (df['ask'] <= config.MAX_OPTIONPRICE)]

    df = df[["pre_symbol", "ask", "totalVolume", "delta"]].copy()

    return df
