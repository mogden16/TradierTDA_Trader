from tda.auth import easy_client
from tda.streaming import StreamClient

from assets.helper_functions import selectSleep, modifiedAccountID

import certifi
import asyncio
import json
import config
import pandas as pd
import time
import tracemalloc

tracemalloc.start()
ca = certifi.where()

client = easy_client(
        api_key=config.API_KEY,
        redirect_uri=config.REDIRECT_URI,
        token_path=config.TOKEN_PATH)
stream_client = StreamClient(client, account_id=config.ACCOUNT_ID)

HEARTBEAT_SETTING = config.HEARTBEAT_SETTING

class TDWebsocket:

    def __init__(self):

        self.isAlive = True
        self.open_position_keys = []

    def initiate_open_positions(self):
        open_position_keys = []
        open_positions = list(self.mongo.open_positions.find({}))

        if open_positions == None:
            self.open_position_keys = open_position_keys
        else:
            for open_position in open_positions:
                key = open_position['Pre_Symbol']
                open_position_keys.append(key)

            self.open_position_keys = open_position_keys


    async def monitor(self):
        await asyncio.sleep(3)
        loop = asyncio.get_event_loop()

        while self.isAlive:
            open_position_keys = []
            open_positions = self.mongo.open_positions.find({})

            if open_positions == None:
                await asyncio.sleep(.5)
            else:
                for open_position in open_positions:
                    key = open_position['Pre_Symbol']
                    open_position_keys.append(key)

                self.open_position_keys.sort()
                open_position_keys.sort()
                # print(self.open_position_keys)
                # print(open_position_keys)

                if self.open_position_keys != open_position_keys:
                    # print('stopping')
                    loop.stop()

            await asyncio.sleep(1)


    async def heartbeat(self):
        while self.isAlive:
            await asyncio.sleep(HEARTBEAT_SETTING)
            print(f'\n ========Running stream======== \n')
            await asyncio.sleep(HEARTBEAT_SETTING)

    def print_message(self,message):

        orderflow_dict = json.loads(json.dumps(message, indent=4))
        df = pd.DataFrame(orderflow_dict['content'],columns=['key', 'BID_PRICE', 'ASK_PRICE', 'LAST_PRICE'])
        df = df.set_index('key')
        df = df.fillna(0)
        # print(df)

        for pre_symbol in self.open_position_keys:
            try:
                row = df.loc[pre_symbol]
                bid = row['BID_PRICE']
                ask = row['ASK_PRICE']
                last = row['LAST_PRICE']

                if bid != 0:
                    self.mongo.open_positions.update_one({"Pre_Symbol": pre_symbol}, {"$set": {'Bid_Price': bid}}, upsert=False)
                if ask != 0:
                    self.mongo.open_positions.update_one({"Pre_Symbol": pre_symbol}, {"$set": {'Ask_Price': ask}}, upsert=False)
                if last != 0:
                    self.mongo.open_positions.update_one({"Pre_Symbol": pre_symbol}, {"$set": {'Last_Price': last}}, upsert=False)

            except Exception as e:

                continue


    async def work(self):
        while self.isAlive:
            await stream_client.login()
            await stream_client.quality_of_service(StreamClient.QOSLevel.EXPRESS)
            self.initiate_open_positions()

            # Always add handlers before subscribing because many streams start sending
            # data immediately after success, and messages with no handlers are dropped.


            stream_client.add_level_one_option_handler(self.print_message)
            await stream_client.level_one_option_subs(self.open_position_keys, fields=[stream_client.LevelOneOptionFields.BID_PRICE,
                                                                                  stream_client.LevelOneOptionFields.ASK_PRICE,
                                                                                  stream_client.LevelOneOptionFields.LAST_PRICE
                                                                                  ])

            # stream_client.add_level_one_futures_handler(self.print_message)
            # await stream_client.level_one_futures_subs(self.open_position_keys, fields = [stream_client.LevelOneFuturesFields.BID_PRICE,stream_client.LevelOneFuturesFields.ASK_PRICE])

            while self.isAlive:
                await stream_client.handle_message()
                await asyncio.sleep(.5)


    def main(self):

        loop = asyncio.new_event_loop()
        loop.create_task(self.monitor())
        while self.isAlive:
            workers = []
            workers.append(loop.create_task(self.work()))
            workers.append(loop.create_task(self.heartbeat()))
            loop.run_forever()
            for t in workers:
                t.cancel()


    def runWebsocket(self):
        """ METHOD RUNS TASKS ON WHILE LOOP EVERY 5 - 60 SECONDS DEPENDING.
        """

        self.logger.info(
            f"STARTING WEBSOCKET FOR {self.user['Name']} ({modifiedAccountID(self.account_id)})", extra={'log': False})

        while self.isAlive:

            try:

                # RUN TASKS ####################################################
                self.main()

                ##############################################################

            except KeyError:

                self.isAlive = False

            except Exception as e:

                self.logger.error(
                    f"ACCOUNT ID: {modifiedAccountID(self.account_id)} - TRADER: {self.user['Name']} - {e}")

            finally:

                time.sleep(selectSleep())

        self.logger.warning(
            f"WEBSOCKET STOPPED FOR ACCOUNT ID {modifiedAccountID(self.account_id)}")