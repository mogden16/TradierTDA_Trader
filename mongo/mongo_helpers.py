from pymongo import MongoClient
import certifi
import config

ca = certifi.where()

MONGO_URI = config.MONGO_URI

class MongoFunctions:
    def __init__(self):

        self.client = None

    def connect(self, logger):

        try:

            logger.info("CONNECTING TO MONGO...", extra={'log': False})

            if MONGO_URI != None:

                self.client = MongoClient(
                    MONGO_URI, authSource="admin", tlsCAFile=ca)

                # SIMPLE TEST OF CONNECTION BEFORE CONTINUING
                self.client.server_info()

                db = self.client["Api_Trader"]

                users = db["users"]

                strategies = db["strategies"]

                open_positions = db["open_positions"]

                closed_positions = db["closed_positions"]

                rejected = db["rejected"]

                canceled = db["canceled"]

                queue = db["queue"]

                forbidden = db["forbidden"]

                logger.info("CONNECTED TO MONGO!\n", extra={'log': False})

                return True

            else:

                raise Exception("MISSING MONGO URI")

        except Exception as e:

            logger.error(f"FAILED TO CONNECT TO MONGO! - {e}")

            return False


    def disconnect(self):

        self.client.close()


    def get_collection(self, col="open_positions"):

        db = MongoFunctions.client["Api_Trader"]

        collection = db[f"{col}"]

        cursor = list(collection.find({}))

        return cursor

    def set_collection(self, col="analysis"):

        db = self.client["Api_Trader"]



    def mongo_list(self, collection, mongo):

        mongodb = mongo

        col = mongodb[str(collection)]

        col_list = list(col)

        return col_list


if __name__ == "__main__":

    main = MongoFunctions()

    main.connect()
    col = str(input('whats col? '))
    main.get_collection(col)

    main.disconnect()
