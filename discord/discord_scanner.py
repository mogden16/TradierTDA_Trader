import requests
import config
from datetime import datetime, timedelta, timezone
import json

CHANNELID = config.CHANNELID
DISCORD_AUTH = config.DISCORD_AUTH
DISCORD_USER = config.DISCORD_USER
STRATEGY = config.STRATEGY


def try_parsing_date(text):

    for fmt in ('%Y-%m-%dT%H:%M:%S.%f%z', '%Y-%m-%dT%H:%M:%S%z'):

        try:

            return datetime.strptime(text, fmt)

        except ValueError:

            pass

    raise ValueError('no valid date format found')

def discord_messages(start_time):

        discord_alerts = []

        headers = {
            'authorization': DISCORD_AUTH
        }
        r = requests.get(
            f'https://discord.com/api/v9/channels/{CHANNELID}/messages', headers=headers)

        jsonn = json.loads(r.text)
        # for i in jsonn:
        #     print(i['timestamp'])
        x=0
        for value in jsonn:
            hedge = False
            value['timestamp'] = try_parsing_date(value['timestamp'])
            if value['timestamp'] >= start_time - timedelta(minutes=1):
                if value['author']['username'] == DISCORD_USER:
                    if len(value['embeds']) == 0:
                        continue
                    statement = value['embeds'][0]['description'].split(' ')
                    # print(statement)
                    # if statement[1] == 'Hedge':
                    #     continue
                    if statement[1] == 'Hedge':
                        hedge = True
                        statement.remove('Hedge')
                    if statement[1] == "flow,":
                        statement.remove("flow,")
                    if statement[1] == "flow":
                        statement.remove('flow')
                    if statement[1] == " ":
                        statement.remove(" ")
                    if statement[1] == "":
                        statement.remove("")
                    if statement[1] == ",":
                        statement.remove(",")
                    symbol = statement[0]
                    str_month = statement[1]
                    datetime_month_object = datetime.strptime(str_month, '%b')
                    exp_month = '%02d' % datetime_month_object.month
                    float_day = float(statement[2])
                    if float_day < 10:
                        exp_day = str(0)+statement[2]
                    else:
                        exp_day = statement[2]
                    if statement[3] == "":
                        statement.remove("")
                    min_strike = statement[3].split('-')[0].lstrip('$')
                    max_strike = statement[3].split('-')[1].lstrip('$')
                    option_type = statement[4].upper()
                    if option_type[-1] == "S":
                        option_type = option_type.rstrip(option_type[-1])
                    option_type_short = option_type[0]
                    timestamp = value['timestamp']
                    trade_symbol = f'{symbol}_{exp_month}{exp_day}22{option_type_short}{min_strike}'
                    list_pre_symbol = {'symbol': symbol, 'exp_month': exp_month, 'exp_day': exp_day,
                                       'option_type': option_type, 'min_strike': min_strike, 'max_strike': max_strike}

                    obj = {
                        "Symbol": symbol,
                        "Side": "BUY_TO_OPEN",
                        "Pre_Symbol": trade_symbol,
                        "Exp_Date": f'2022-{exp_month}-{exp_day}',
                        "Strike_Price": min_strike,
                        "Option_Type": option_type,
                        "Strategy": STRATEGY,
                        "Asset_Type": "OPTION",
                        "HedgeAlert": "TRUE" if hedge else "FALSE",
                        "Entry_Date": timestamp
                    }

                    discord_alerts.append(obj)

        if len(discord_alerts) != 0:

            return discord_alerts

        else:

            return
