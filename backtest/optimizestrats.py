# imports
import certifi
import pandas as pd
import config

ca = certifi.where()

MONGO_URI = config.MONGO_URI
CHANNELID = config.CHANNELID
DISCORD_AUTH = config.DISCORD_AUTH
DISCORD_USER = config.DISCORD_USER
POLYGON_URI = config.POLYGON_URI


def startDF(file, position_size):

    df = pd.read_excel(file, engine='openpyxl')
    pre_symbol = file.split("_")
    pre_symbol = pre_symbol[1]
    if df.empty:
        return
    else:
        entry = df.loc[0]
    entry_date = entry['t']
    entry_price = entry['c']
    max_price = entry['c']

    position_size = int(position_size)
    quantity = int((position_size / 100) / entry_price)
    commission_per = 0.65
    fees = quantity * commission_per

    win = 0
    loss = 0
    highest_profit = 0
    greatest_loss = 0
    max_drawdown = 0
    max_profit = 0
    avg_len_of_trade = 0
    avg_len_of_win = 0
    avg_len_of_loss = 0
    avg_pl_of_win = 0
    avg_pl_of_loss = 0
    avg_pl_per_trade = 0
    profit_minus_fees = 0

    obj = {
        "Pre_Symbol": pre_symbol,
        "Win": win,
        "Loss": loss,
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
        "Profit_minus_Fees": profit_minus_fees

    }

    return df, obj


def evalOCOorder(df, obj, take_profit_pct_factor, stop_loss_pct_factor, position_size):

    open_order = True
    for index, row in df.iterrows():
        entry = df.loc[0]
        entry_date = entry['t']
        entry_price = entry['c']
        max_price = entry['c']
        position_size = int(position_size)
        quantity = int((position_size / 100) / entry_price)
        if quantity == 0:
            return
        commission_per = 0.65
        fees = quantity * commission_per

        take_profit_price = round(entry_price*(1+take_profit_pct_factor),2)
        stoploss_price = round(entry_price*(1-stop_loss_pct_factor),2)

        if row['h'] >= take_profit_price and open_order:
            profit = round(((take_profit_price - entry_price) * quantity * 100), 2)
            exit_price = take_profit_price
            exit_time = row['t']
            open_order = False

            obj['Win'] = 1
            obj['Highest_Profit'] = profit
            obj['Max_Profit'] = profit
            obj['Avg_Len_of_Trade'] = pd.Timedelta(exit_time - entry_date).seconds/60
            obj['Avg_Len_of_Win'] = pd.Timedelta(exit_time - entry_date).seconds/60
            obj['Avg_PL_of_Win'] = profit
            obj['Avg_PL_of_Trade'] = profit
            obj['Fees'] = fees
            obj['Profit_minus_Fees'] = profit - fees

            return obj

        elif row['l'] <= stoploss_price and open_order:
            profit = round(((stoploss_price - entry_price) * quantity * 100), 2)
            exit_price = stoploss_price
            exit_time = row['t']
            open_order = False

            obj['Loss'] = 1
            obj['Greatest_Loss'] = profit
            obj['Max_Drawdown'] = profit
            obj['Avg_Len_of_Trade'] = pd.Timedelta(exit_time - entry_date).seconds/60
            obj['Avg_Len_of_Loss'] = pd.Timedelta(exit_time - entry_date).seconds/60
            obj['Avg_PL_of_Loss'] = profit
            obj['Avg_PL_of_Trade'] = profit
            obj['Fees'] = fees
            obj['Profit_minus_Fees'] = profit - fees

            return obj

        elif index == (len(df.index)-1) and open_order:
            # print('did not hit take_profit')
            exit = df.iloc[-1]
            exit_price = exit['c']
            exit_time = exit['t']
            profit = round(((exit_price - entry_price) * quantity * 100), 2)
            open_order = False
            if profit > 0:
                obj['Win'] = 1
                obj['Highest_Profit'] = profit
                obj['Max_Profit'] = profit
                obj['Avg_Len_of_Trade'] = pd.Timedelta(exit_time - entry_date).seconds / 60
                obj['Avg_Len_of_Win'] = pd.Timedelta(exit_time - entry_date).seconds / 60
                obj['Avg_PL_of_Win'] = profit
                obj['Avg_PL_of_Trade'] = profit
                obj['Fees'] = fees
                obj['Profit_minus_Fees'] = profit - fees

            else:
                obj['Loss'] = 1
                obj['Greatest_Loss'] = profit
                obj['Max_Drawdown'] = profit
                obj['Avg_Len_of_Trade'] = pd.Timedelta(exit_time - entry_date).seconds / 60
                obj['Avg_Len_of_Loss'] = pd.Timedelta(exit_time - entry_date).seconds / 60
                obj['Avg_PL_of_Loss'] = profit
                obj['Avg_PL_of_Trade'] = profit
                obj['Fees'] = fees
                obj['Profit_minus_Fees'] = profit - fees

            return obj


def evalTRAILorder(df, obj, trail_stop_pct_factor, position_size):

    open_order = True
    max_price = 0
    for index, row in df.iterrows():
        entry = df.loc[0]
        entry_date = entry['t']
        entry_price = entry['c']

        position_size = int(position_size)
        quantity = int((position_size / 100) / entry_price)
        if quantity == 0:
            return
        commission_per = 0.65
        fees = quantity * commission_per

        trail_stop_value = entry_price * trail_stop_pct_factor
        current_price = row['c']
        trailstop_price = round(max_price - trail_stop_value, 2)
        # print(f'entryprice: {entry_price}   \n'
        #       f'trailstopprice: {trailstop_price}  \n'
        #       f'trailstoppct: {pct_factor}')
        if current_price > max_price and open_order == True:
            max_price = current_price

        elif row['l'] <= trailstop_price and open_order == True:
            exit_price = row['l']
            exit_time = row['t']
            profit = round(((exit_price - entry_price) * quantity * 100), 2)
            # print(f'closing order entry_date {entry_date}  entry_price {entry_price}'
            #       f'  exit_date {exit_time}  exit_price {exit_price}   total P/L {exit_pl} ')
            open_order = False
            if profit >= 0:
                obj['Win'] = 1
                obj['Highest_Profit'] = profit
                obj['Max_Profit'] = profit
                obj['Avg_Len_of_Trade'] = pd.Timedelta(exit_time - entry_date).seconds / 60
                obj['Avg_Len_of_Win'] = pd.Timedelta(exit_time - entry_date).seconds / 60
                obj['Avg_PL_of_Win'] = profit
                obj['Avg_PL_of_Trade'] = profit
                obj['Fees'] = fees
                obj['Profit_minus_Fees'] = profit - fees

            else:
                obj['Loss'] = 1
                obj['Greatest_Loss'] = profit
                obj['Max_Drawdown'] = profit
                obj['Avg_Len_of_Trade'] = pd.Timedelta(exit_time - entry_date).seconds / 60
                obj['Avg_Len_of_Loss'] = pd.Timedelta(exit_time - entry_date).seconds / 60
                obj['Avg_PL_of_Loss'] = profit
                obj['Avg_PL_of_Trade'] = profit
                obj['Fees'] = fees
                obj['Profit_minus_Fees'] = profit - fees

            return obj

        elif index == (len(df.index) - 1) and open_order == True:
            exit_time = row['t']
            exit_price = row['c']
            profit = round(((exit_price - entry_price) * quantity * 100), 2)
            # print(f'closing order entry_date {entry_date}  entry_price {entry_price}'
            #       f'  exit_date {exit_time}  exit_price {exit_price}   total P/L {exit_pl} ')
            open_order = False
            if profit >= 0:
                obj['Win'] = 1
                obj['Highest_Profit'] = profit
                obj['Max_Profit'] = profit
                obj['Avg_Len_of_Trade'] = pd.Timedelta(exit_time - entry_date).seconds / 60
                obj['Avg_Len_of_Win'] = pd.Timedelta(exit_time - entry_date).seconds / 60
                obj['Avg_PL_of_Win'] = profit
                obj['Avg_PL_of_Trade'] = profit
                obj['Fees'] = fees
                obj['Profit_minus_Fees'] = profit - fees

            else:
                obj['Loss'] = 1
                obj['Greatest_Loss'] = profit
                obj['Max_Drawdown'] = profit
                obj['Avg_Len_of_Trade'] = pd.Timedelta(exit_time - entry_date).seconds / 60
                obj['Avg_Len_of_Loss'] = pd.Timedelta(exit_time - entry_date).seconds / 60
                obj['Avg_PL_of_Loss'] = profit
                obj['Avg_PL_of_Trade'] = profit
                obj['Fees'] = fees
                obj['Profit_minus_Fees'] = profit - fees

            return obj


# def evalCUSTOMorder(df, obj, take_profit_pct_factor, stop_loss_pct_factor, trail_stop_pct_factor, position_size):
#
#     first_order = evalOCOorder(df, obj, take_profit_pct_factor, stop_loss_pct_factor, position_size=position_size)
#
#     if first_order == None:
#         # print(f'first order = {first_order}')
#         return first_order
#
#     elif first_order['Win'] != 0:
#
#         position_size = position_size * .5
#         second_order = evalTRAILorder(df, obj, trail_stop_pct_factor, position_size)
#
#         if second_order == None:
#             # print(f'first_order: {first_order}')
#             return first_order
#
#         else:
#             final_orders = [first_order, second_order]
#             # print(f'final_orders: {final_orders}')
#             return final_orders
#     else:
#         # print(f'first_order: {first_order}')
#         return first_order

