from pymongo import MongoClient
import os
import certifi
import config

ca = certifi.where()

THIS_FOLDER = os.path.dirname(os.path.abspath(__file__))

MONGO_URI = config.MONGO_URI
RUN_LIVE_TRADER = config.RUN_LIVE_TRADER


class MongoDB:

    def __init__(self, logger):

        self.logger = logger

    def connect(self):

        try:

            self.logger.info("CONNECTING TO MONGO...", extra={'log': False})

            if MONGO_URI != None:

                self.client = MongoClient(
                    MONGO_URI, authSource="admin", tlsCAFile=ca)

                # SIMPLE TEST OF CONNECTION BEFORE CONTINUING
                self.client.server_info()

                self.db = self.client["Api_Trader"]

                self.users = self.db["users"]

                self.strategies = self.db["strategies"]

                self.open_positions = self.db["open_positions"]

                self.closed_positions = self.db["closed_positions"]

                self.rejected = self.db["rejected"]

                self.canceled = self.db["canceled"]

                self.queue = self.db["queue"]

                self.analysis = self.db["analysis"]

                self.alert_history = self.db["alert_history"]

                self.logger.info("CONNECTED TO MONGO!\n", extra={'log': False})

                return True

            else:

                raise Exception("MISSING MONGO URI")

        except Exception as e:

            self.logger.error(f"FAILED TO CONNECT TO MONGO! - {e}")

            return False

    # def disconnect(self):
    #
    #     try:
    #
    #         self.logger.info("DISCONNECTING FROM MONGO...", extra={'log': False})
    #
    #         if MONGO_URI != None:
    #
    #             self.client = MongoClient(
    #                 MONGO_URI, authSource="admin", tlsCAFile=ca)
    #
    #             self.client.close()
    #
    #             return False
    #
    #         else:
    #
    #             raise Exception("MISSING MONGO URI")
    #
    #     except Exception as e:
    #
    #         self.logger.error(f"FAILED TO CONNECT TO MONGO! - {e}")
    #
    #         return False
