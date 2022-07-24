import certifi

import config

ca = certifi.where()

MONGO_URI = config.MONGO_URI


def get_mongo_openPositions(trader):
    col = trader.mongo.open_positions
    llist = list(col.find({}))
    return llist


def get_mongo_closedPositions(trader):
    col = trader.mongo.closed_positions
    llist = list(col.find({}))
    return llist


def get_mongo_analysisPositions(trader):
    col = trader.mongo.analysis
    llist = list(col.find({}))
    return llist


def get_mongo_users(trader):
    col = trader.mongo.users
    llist = list(col.find({}))
    return llist


def get_mongo_queue(trader):
    col = trader.mongo.queue
    llist = list(col.find({}))
    return llist


def set_mongo_openPositions(trader, obj):
    col = trader.mongo.open_positions
    inst = col.insert_one(obj)
    return


def set_mongo_closedPosition(trader, obj):
    col = trader.mongo.closed_positions
    inst = col.insert_one(obj)
    return


def set_mongo_analysisPosition(trader, obj):
    col = trader.mongo.analysis
    inst = col.insert_one(obj)
    return


def set_mongo_user(trader, obj):
    col = trader.mongo.users
    inst = col.insert_one(obj)
    return


def set_mongo_queue(trader, obj):
    col = trader.mongo.queue
    inst = col.insert_one(obj)
    return


def find_mongo_openPosition(trader, trade_symbol, timestamp):
    col = trader.mongo.open_positions
    position = col.find_one({"Pre_Symbol": trade_symbol, "Entry_Date": timestamp})
    if position != None:
        return True
    else:
        return False


def find_mongo_closedPosition(trader, trade_symbol, timestamp):
    col = trader.mongo.closed_positions
    position = col.find_one({"Pre_Symbol": trade_symbol, "Entry_Date": timestamp})
    if position != None:
        return True
    else:
        return False


def find_mongo_analysisPosition(trader, trade_symbol, timestamp):
    col = trader.mongo.analysis
    position = col.find_one({"Pre_Symbol": trade_symbol, "Entry_Date": timestamp})
    if position != None:
        return True
    else:
        return False


def find_mongo_queue(trader, trade_symbol, timestamp):
    col = trader.mongo.queue
    position = col.find_one({"Pre_Symbol": trade_symbol, "Entry_Date": timestamp})
    if position != None:
        return True
    else:
        return False

def close_mongo_position(trader, id):
    trader.mongo.open_positions.update_one({"_id": id},
                                           {"$set": {'childOrderStrategies.1.Order_Status': 'FILLED'}},
                                           upsert=True)
    return


def disconnect(trader):
    try:
        trader.logger.info("DISCONNECTING FROM MONGO...", extra={'log': False})
        trader.mongo.client.close()
        trader.logger.info("DISCONNECTED FROM MONGO", extra={'log': False})
        return True

    except Exception as e:
        trader.logger.error(f"FAILED TO DISCONNECT FROM MONGO! - {e}")
        return False
