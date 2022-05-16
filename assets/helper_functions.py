from datetime import datetime, timedelta
import os
import pytz
import config
import pandas_market_calendars as mcal
import math


THIS_FOLDER = os.path.dirname(os.path.abspath(__file__))

TIMEZONE = config.TIMEZONE
TURN_ON_TIME = config.TURN_ON_TIME
SELL_ALL_POSITIONS = config.SELL_ALL_POSITIONS
TURN_OFF_TRADES = config.TURN_OFF_TRADES
SHUTDOWN_TIME = config.SHUTDOWN_TIME
MIN_DTE = config.MIN_DTE


def getDatetime():
    """ function obtains the datetime based on timezone using the pytz library.

    Returns:
        [Datetime Object]: [formated datetime object]
    """

    dt = datetime.now(tz=pytz.UTC).replace(microsecond=0)

    dt = dt.astimezone(pytz.timezone(TIMEZONE))

    return datetime.strptime(dt.strftime(
        "%Y-%m-%d %H:%M:%S"), "%Y-%m-%d %H:%M:%S")


def getUTCDatetime():
    """ function obtains the utc datetime. will use this for all timestamps with the bot. GET FEEDBACK FROM DISCORD GROUP ON THIS BEFORE PUBLISH.

    Returns:
        [Datetime Object]: [formated datetime object]
    """

    dt = datetime.utcnow().replace(microsecond=0)

    return dt.isoformat()


def selectSleep():
    """
    PRE-MARKET(0400 - 0930 ET): 1 SECOND
    MARKET OPEN(0930 - 1600 ET): 1 SECOND
    AFTER MARKET(1600 - 2000 ET): 1 SECOND

    WEEKENDS: 60 SECONDS
    WEEKDAYS(2000 - 0400 ET): 60 SECONDS

    EVERYTHING WILL BE BASED OFF CENTRAL TIME

    OBJECTIVE IS TO FREE UP UNNECESSARY SERVER USAGE
    """

    dt = getDatetime()

    day = dt.strftime("%a")

    tm = dt.strftime("%H:%M:%S")

    weekends = ["Sat", "Sun"]

    # IF CURRENT TIME GREATER THAN 8PM AND LESS THAN 4AM, OR DAY IS WEEKEND, THEN RETURN 60 SECONDS
    if tm > "20:00" or tm < "04:00" or day in weekends:

        return 5

    # ELSE RETURN 1 SECOND
    return 1


def modifiedAccountID(account_id):

    return '*' * (len(str(account_id)) - 4) + str(account_id)[-4:]


def formatGmailAlerts(trade_data):

    trade_data_list = []

    for data in trade_data:

        hedge = False
        symbol = data['Symbol']
        pre_symbol = data['Pre_Symbol']
        datetime_object = data['Exp_Date']
        exp_month = '%02d' % datetime_object.month
        exp_day = '%02d' % datetime_object.day
        option_type = data['Option_Type']
        strategy = data['Strategy']
        side = data['Side']

        if side == "SELL_TO_CLOSE":
            continue

        if option_type == "CALL":
            strike_price = pre_symbol.split('C')
            strike_price = strike_price[-1]
        else:
            strike_price = pre_symbol.split('P')
            strike_price = strike_price[-1]

        obj = {
            "Symbol": symbol,
            "Side": "BUY_TO_OPEN",
            "Pre_Symbol": pre_symbol,
            "Exp_Date": f'2022-{exp_month}-{exp_day}',
            "Strike_Price": strike_price,
            "Option_Type": option_type,
            "Strategy": strategy,
            "Asset_Type": "OPTION",
            "HedgeAlert": "TRUE" if hedge else "FALSE",
            "Entry_Date": getDatetime()
        }

        trade_data_list.append(obj)

    return trade_data_list


def addNewStrategy(trader, strategy, asset_type):
    """ METHOD UPDATES STRATEGIES OBJECT IN MONGODB WITH NEW STRATEGIES.

    Args:
        strategy ([str]): STRATEGY NAME
    """

    obj = {"Active": True,
           "Order_Type": "STANDARD",
           "Asset_Type": asset_type,
           "Position_Size": 300,
           "Position_Type": "LONG",
           "Account_ID": trader.account_id,
           "Strategy": strategy,
           }

    # IF STRATEGY NOT IN STRATEGIES COLLECTION IN MONGO, THEN ADD IT

    trader.mongo.strategies.update_one({"Strategy": strategy}, {"$set": obj}, upsert=True)


def find_option_expDate(trader, symbol):

    test_option_type = "CALL"
    nyse = mcal.get_calendar('NYSE')
    cal = nyse.valid_days(start_date=datetime.now(), end_date=datetime.now() + timedelta(days=MIN_DTE + 14))

    resp = trader.tdameritrade.getQuote(symbol)
    test_price = float(resp[symbol]["lastPrice"])
    test_strike_price = int(math.floor(test_price))

    option_exp_date = datetime.now() + timedelta(days=MIN_DTE)
    option_exp_date = option_exp_date.strftime('%Y-%m-%d')
    url = f"https://api.tdameritrade.com/v1/marketdata/chains?symbol={symbol}&contractType={test_option_type}&includeQuotes=FALSE&strike={test_strike_price}&fromDate={option_exp_date}&toDate={option_exp_date}"
    resp = trader.tdameritrade.sendRequest(url)

    new_dte = MIN_DTE
    while resp['status'] == 'FAILED':
        option_exp_date = cal[new_dte].strftime('%Y-%m-%d')
        for i in range(5):
            url = f"https://api.tdameritrade.com/v1/marketdata/chains?symbol={symbol}&contractType={test_option_type}&includeQuotes=FALSE&strike={test_strike_price}&fromDate={option_exp_date}&toDate={option_exp_date}"
            resp = trader.tdameritrade.sendRequest(url)

            if resp['status'] != 'FAILED':
                option_exp_date = cal[new_dte].strftime('%Y-%m-%d')
                break

            else:
                test_strike_price += 1
        new_dte += 1

    return option_exp_date
