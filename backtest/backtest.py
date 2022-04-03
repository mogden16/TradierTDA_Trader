# imports
import time
import os
from datetime import datetime, timedelta, timezone
from tqdm import tqdm
import certifi
import json
import traceback
import pytz
import polygon
import pandas as pd
import shutil
import glob
import config
import constants as c
import numpy as np

from discord import discord_scanner, discord_helpers
from backtest import optimizestrats

pd.options.mode.chained_assignment = None

ca = certifi.where()

MONGO_URI = config.MONGO_URI
CHANNELID = config.CHANNELID
DISCORD_AUTH = config.DISCORD_AUTH
DISCORD_USER = config.DISCORD_USER
POLYGON_URI = config.POLYGON_URI
EXT_DIR = config.EXT_DIR
LOOKBACK_DAYS = config.LOOKBACK_DAYS
TEST_DISCORD = config.TEST_DISCORD
TEST_CLOSED_POSITIONS = config.TEST_CLOSED_POSITIONS
POSITION_SIZE = config.POSITION_SIZE
TIMEZONE = config.TIMEZONE

BACKTESTLIST = []
EXISTINGDFLIST = []
TAKE_PROFIT_PERCENTAGE_LIST = [.1, .15, .2, .25, .3, .5, 1]
STOP_LOSS_PERCENTAGE_LIST = [.1, .15, .2, .25, .3, .5, 1]
TRAIL_STOP_PERCENTAGE_LIST = [.1, .15, .2, .25, .3, .5, 1]

def try_parsing_date(text):

    for fmt in ('%Y-%m-%dT%H:%M:%S.%f%z','%Y-%m-%dT%H:%M:%S%z'):
        try:
            return datetime.strptime(text,fmt)
        except ValueError:
            pass
    raise ValueError('no valid date format found')


def findexistingDFs():
    existingdfs = []

    current_time = datetime.now(pytz.timezone(TIMEZONE)).strftime('%Y:%m:%d')
    current_time = current_time.replace(":", "_")
    directory = str(current_time)

    for file in glob.glob(f'{EXT_DIR}/*.xlsx'):

        file_name = file.split('_')

        file_name = file_name[1]

        existingdfs.append(file_name)

    for file in glob.glob(f'{EXT_DIR}/backtest/dataframes/{directory}/*.xlsx'):

        file_name = file.split('_')

        file_name = file_name[1]

        existingdfs.append(file_name)

    return existingdfs

def find_closed_positions(trader, starttime):
    orders = []

    closed_positions = trader.mongo.closed_positions.find({})

    for position in closed_positions:

        entry_date = position['Entry_Date']

        if entry_date >= (starttime-timedelta(days=LOOKBACK_DAYS)):

            orders.append(position)

    return orders

def grabDataframes():
    x=0
    client = polygon.StocksClient(POLYGON_URI)
    lookback = timedelta(days=LOOKBACK_DAYS)
    end_date = datetime.now()
    start_date = end_date - lookback

    for alert in tqdm(BACKTESTLIST):
        timestamp = alert['Entry_Date']

        try:
            symbol = alert['Symbol']
            option_type = alert['Option_Type'].lower()
            strike_price = float(alert['Strike_Price'])
            exp_date = datetime.strptime(alert['Exp_Date'], '%Y-%m-%d')
            timestamp = timestamp.replace(microsecond=0)
            timestamp = pd.to_datetime(timestamp).tz_localize(None)
            end_of_day = timestamp.replace(hour=21)
            pre_symbol = polygon.build_option_symbol(symbol, exp_date, option_type, strike_price, prefix_o=True)
            symbol_no = polygon.build_option_symbol(symbol, exp_date, option_type, strike_price, prefix_o=False)

            if symbol_no in EXISTINGDFLIST:
                # print(f'found existing df for {pre_symbol}')
                continue

            agg_bars = client.get_aggregate_bars(pre_symbol, start_date, end_date, multiplier='1', timespan='minute')

            if agg_bars['resultsCount'] == 0:
                print(f'Had an issue with resultsCount == 0 for {pre_symbol}')
                continue

            df = pd.DataFrame(agg_bars['results'])
            df['t'] = pd.to_datetime(df['t'], unit='ms')
            # df['hedge'] = hedge
            # print(df)

            mask = (df['t'] >= timestamp) & (df['t'] <= end_of_day)
            df2 = df.loc[mask]

            df3 = df2[df2['h'] == df2['h'].max()]

            if df3.empty:
                print(f'{symbol_no} has an empty dataframe')
                continue

            df4 = df2[df2['l'] == df2['l'].min()]

            entry_price = df2['c'].iloc[0]
            max_price = df3['h'].iloc[0]
            max_time = df3['t'].iloc[0]
            min_price = df4['l'].iloc[0]
            min_time = df4['t'].iloc[0]

            print(f'\n Pre_Symbol {symbol_no}  \n Entry_Time: {timestamp}  @ {entry_price}  \n '
                  f'Max_Time: {max_time}  @ {max_price}  \n '
                  f'Min_Time {min_time}  @ {min_price}')

            file_name = f'dataframe_{symbol_no}_{x}.xlsx'
            df2.to_excel(file_name)
            x += 1

            time.sleep(14)

        except Exception:

            msg = f"error: {traceback.format_exc()}"
            print(msg)

def createFolder():
    current_time = datetime.now(pytz.timezone(TIMEZONE)).strftime('%Y:%m:%d')
    current_time = current_time.replace(":","_")
    directory = str(current_time)
    parent_dir = f"{EXT_DIR}/backtest/dataframes/"

    path = os.path.join(parent_dir, directory)
    os.mkdir(path)

    return path

def movexlsx():

    # ABSOLUTE PATH TO XLSX_FILES DIRECTORY
    path = createFolder()
    print(f"Starting to move files to: {path}")

    for file in tqdm(glob.glob(EXT_DIR + '/' + '*.xlsx')):

        try:

            # MOVES MOST RECENT STRATEGY REPORT FILE FROM DOCUMENTS FOLDER TO XLSX_FILES FOLDER
            shutil.move(file, path)

        except shutil.Error as e:

            print(f'error: {e}')

    return path

    print(f"Done moving dataframes")

def evaluateDF(dataframe):

    df = pd.DataFrame(dataframe)
    # pre_symbol = df['Pre_Symbol']
    win = df['Win'].sum()
    loss = df['Loss'].sum()
    highest_profit = df['Highest_Profit'].max()
    greatest_loss = df['Greatest_Loss'].min()
    max_drawdown = df['Greatest_Loss'].sum()
    max_profit = df['Max_Profit'].sum()
    fees = df['Fees'].sum()
    profit_minus_fees = df['Profit_minus_Fees'].sum()
    df = df.replace(0, np.NaN)
    avg_len_of_trade = df['Avg_Len_of_Trade'].mean()
    avg_len_of_win = df['Avg_Len_of_Win'].mean()
    avg_len_of_loss = df['Avg_Len_of_Loss'].mean()
    avg_pl_of_win = df['Avg_PL_of_Win'].mean()
    avg_pl_of_loss = df['Avg_PL_of_Loss'].mean()
    avg_pl_per_trade = (avg_pl_of_win + avg_pl_of_loss)/2
    win_pct = win/(win+loss)*100
    take_profit_pct = df['Take_Profit_Pct']
    stop_loss_pct = df['Stop_Loss_Pct']

    obj = {
        # "Pre_Symbol": pre_symbol,
        "Win": win,
        "Loss": loss,
        "Win Percentage": win_pct,
        "Highest_Profit": highest_profit,
        "Greatest_Loss": greatest_loss,
        "Max_Drawdown": max_drawdown,
        "Max_Profit": max_profit,
        "Avg_Len_of_Trade": avg_len_of_trade,
        "Avg_Len_of_Win": avg_len_of_win,
        "Avg_Len_of_Loss": avg_len_of_loss,
        "Avg_PL_of_Win": avg_pl_of_win,
        "Avg_PL_of_Loss": avg_pl_of_loss,
        "Avg_PL_per_Trade": avg_pl_per_trade,
        "Fees": fees,
        "Profit_minus_Fees": profit_minus_fees,
        "Take_Profit_Pct": take_profit_pct,
        "Stop_Loss_Pct": stop_loss_pct
    }

    return obj

def evaluateTakeProfit(path):
    MASTER_DF = pd.DataFrame()
    DF = pd.DataFrame()
    # runningPL = []

    for take_profit_pct_factor in TAKE_PROFIT_PERCENTAGE_LIST:
        for stop_loss_pct_factor in tqdm(STOP_LOSS_PERCENTAGE_LIST):
            runningPL= []
            for file in tqdm(glob.glob(path + '/*.xlsx')):
                file_name = file.split('_')
                file_name = file_name[-2]
                # print(file_name)
                try:
                    returnn = optimizestrats.startDF(file, position_size=POSITION_SIZE)
                    # print(returnn)
                    if returnn == None:
                        continue

                    df = returnn[0]
                    obj = returnn[1]

                    PL = optimizestrats.evalOCOorder(df, obj, take_profit_pct_factor,
                                                     stop_loss_pct_factor, position_size=POSITION_SIZE)
                    if PL == None:
                        continue
                    else:
                        PL['Take_Profit_Pct'] = take_profit_pct_factor * 100
                        PL['Stop_Loss_Pct'] = stop_loss_pct_factor * 100
                        runningPL.append(PL)

                except Exception:

                    msg = f"error: {traceback.format_exc()}"
                    print(msg)
                    # print(runningPL)

            df_eval = pd.DataFrame(runningPL)
            DF = evaluateDF(df_eval)
            DF = pd.DataFrame(DF, index=[0])

            MASTER_DF = pd.concat([MASTER_DF, DF], axis=0, ignore_index=False).round(decimals=2)

            # runningPL = []
    # print(runningPL)
    # DF = pd.DataFrame(runningPL)
    # print(DF)
    # MASTER_DF = evaluateDF(DF)
    # df_eval = pd.Series(df_eval).round(decimals=2)
    # profit_minus_fees = df_eval['Profit_minus_Fees']
    # print(f'{df_eval} \n')

    # discord_helpers.send_discord_alert = f'P/L if take profit is {take_profit_pct_factor * 100}% \n'\
    #                                      f'P/L if stop loss is {stop_loss_pct_factor * 100}%: \n'\
    #                                      f'Profit_minus_Fees: {profit_minus_fees}'


    MASTER_DF = MASTER_DF.sort_values(by=["Profit_minus_Fees"], ascending=False)
    print(MASTER_DF.head())
    discord_helpers.send_discord_alert = f'{MASTER_DF.head(1)}'
    MASTER_DF.to_excel('OCO_backtest.xlsx')

def run(trader):

    start_time = datetime.now(pytz.timezone(config.TIMEZONE))

    existing_dfs = findexistingDFs()
    for dataframe in existing_dfs:
        EXISTINGDFLIST.append(dataframe)

    if TEST_DISCORD:
        discord_alerts = discord_scanner.discord_messages(start_time, mins=60*24*LOOKBACK_DAYS)  # Convert to mins
        if not discord_alerts:
            return

        for alert in discord_alerts:
            BACKTESTLIST.append(alert)

    if TEST_CLOSED_POSITIONS:
        closed_alerts = find_closed_positions(trader, start_time)
        if not closed_alerts:
            return

        for alert in closed_alerts:
            BACKTESTLIST.append(alert)

    grabDataframes()

    path = movexlsx()

    evaluateTakeProfit(path)

    movexlsx()

    print('done')
