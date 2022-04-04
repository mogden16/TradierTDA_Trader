import config
import traceback

RUN_LIVE_TRADER = config.RUN_LIVE_TRADER
RUN_TRADIER = config.RUN_TRADIER
IS_TESTING = config.IS_TESTING
STREAMPRICE_LINK = config.STREAMPRICE_LINK.upper()
TAKEPROFIT_PERCENTAGE = config.TAKE_PROFIT_PERCENTAGE
STOPLOSS_PERCENTAGE = config.STOP_LOSS_PERCENTAGE
TRAILSTOP_PERCENTAGE = config.TRAIL_STOP_PERCENTAGE


def streamPrice(trader):
    """  THIS WILL FIND YOUR EXIT STRATEGIES  """

    open_positions = list(trader.mongo.open_positions.find({}))
    queue = list(trader.mongo.queue.find({}))

    if len(queue) == 0 and len(open_positions) == 0:
        print("zero open positions")
        return

    elif len(queue) != 0:
        for order in queue:
            pre_symbol = order['Pre_Symbol']
            price = order['Entry_Price']
            if RUN_TRADIER:
                current_price = trader.tradier.get_quote(order)['lastPrice']
            else:
                current_price = list(trader.traders.values())[0].tdameritrade.getQuote(pre_symbol)[str(pre_symbol)]['lastPrice']
            print(f'Queued Position: {pre_symbol}  order_price: {price}  last_price: {current_price} \n')

    for open_position in open_positions:
        id = open_position['_id']
        symbol = open_position['Symbol']
        asset_type = open_position['Asset_Type']
        entry_price = open_position['Entry_Price']
        order_type = open_position['Order_Type']
        pre_symbol = open_position["Pre_Symbol"]
        isRunner = open_position["isRunner"]
        trail_stop_value = open_position['Trail_Stop_Value']

        try:
            if IS_TESTING:
                current_price = float(input(f'what is current price for {pre_symbol}    '
                                            f'take profit {takeprofit_price}: '))
                print(f'self.isTesting is set to {IS_TESTING} - running fake numbers')

            else:
                if STREAMPRICE_LINK == "BID":
                    if 'Bid_Price' in open_position.keys():
                        bid = open_position['Bid_Price']
                        current_price = bid
                    else:
                        continue

                elif STREAMPRICE_LINK == "ASK":
                    if 'Ask_Price' in open_position.keys():
                        ask = open_position['Ask_Price']
                        current_price = ask
                    else:
                        continue

                elif STREAMPRICE_LINK == "LAST":
                    if 'Last_Price' in open_position.keys():
                        last = open_position['Last_Price']
                        current_price = last
                    else:
                        continue

                else:
                    print('error with STREAMPRICE_LINK in env')

                trader.mongo.open_positions.update_one({"_id": id}, {"$set": {'Current_Price': current_price}}, upsert=True)

        except Exception:

            msg = f"error: {traceback.format_exc()}"
            trader.logger.error(msg)

        takeprofit_price = round(entry_price * (1 + TAKEPROFIT_PERCENTAGE), 2)
        stoploss_price = round(entry_price * (1 - STOPLOSS_PERCENTAGE), 2)

        if asset_type == "EQUITY":
            continue

        else:
            if order_type == "STANDARD":
                pass

            elif order_type == "OCO":

                if RUN_TRADIER:
                    for position in open_position['childOrderStrategies']:
                        if "Takeprofit_Price" in position:
                            takeprofit_price = position['Takeprofit_Price']
                        else:
                            stoploss_price = position['Stop_Price']

                    if current_price >= takeprofit_price:
                        print('max_price exceeds TakeProfit price, closing position')

                    elif current_price <= stoploss_price:
                        print('current_price exceeds StopLoss price, closing position')

                else:
                    takeprofit_price = open_position['childOrderStrategies'][str(0)]['Takeprofit_Price']
                    stoploss_price = open_position['childOrderStrategies'][str(1)]['Stop_Price']

                    if current_price >= takeprofit_price:
                        print('max_price exceeds TakeProfit price, closing position')
                        trader.mongo.open_positions.update_one({"_id": id},
                                                           {"$set": {'childOrderStrategies.0.Order_Status': 'FILLED'}},
                                                           upsert=True)

                    elif current_price <= stoploss_price:
                        print('current_price exceeds StopLoss price, closing position')
                        trader.mongo.open_positions.update_one({"_id": id},
                                                               {"$set": {'childOrderStrategies.1.Order_Status': 'FILLED'}},
                                                               upsert=True)

            elif order_type == "CUSTOM":

                if RUN_TRADIER:
                    for i in range(0, 2):
                        order = open_position['childOrderStrategies'][i]

                        if 'Stop_Price' not in order:
                            continue

                        else:

                            stop_order_id = order['Order_ID']

                            max_price = open_position['Max_Price']

                            limits = {
                                'target1': round(entry_price * (1 + .05), 2),
                                'target2': round(entry_price * (1 + .10), 2),
                                'target3': round(entry_price * (1 + .20), 2),
                                'target4': round(entry_price * (1 + .30), 2),
                                'target5': round(entry_price * (1 + .50), 2),
                                'target6': round(entry_price * (1 + .70), 2),
                                'stop1': round(entry_price * (1 - .10), 2),
                                'stop2': round(entry_price * (1 + 0), 2),
                                'stop3': round(entry_price * (1 + .10), 2),
                                'stop4': round(entry_price * (1 + .20), 2),
                                'stop5': round(entry_price * (1 + .30), 2),
                                'stop6': round(entry_price * (1 + .50), 2)
                            }

                            if current_price > max_price:
                                trader.mongo.open_positions.update_one({"_id": id}, {"$set": {'Max_Price': current_price}},
                                                               upsert=False)

                            if max_price < limits['target1']:
                                target_price = limits['target1']
                                stoploss_price = limits['stop1']
                                trader.mongo.open_positions.update_one({"_id": id}, {"$set": {'Target_Price': target_price}},
                                                               upsert=True)
                                trader.mongo.open_positions.update_one({"_id": id}, {"$set": {'StopLoss_Price': stoploss_price}},
                                                               upsert=True)
                                trader.tradier.modify_stopprice(stop_order_id, stoploss_price)

                            elif limits['target1'] <= max_price < limits['target2']:
                                target_price = limits['target2']
                                stoploss_price = limits['stop2']
                                trader.mongo.open_positions.update_one({"_id": id}, {"$set": {'Target_Price': target_price}},
                                                               upsert=True)
                                trader.mongo.open_positions.update_one({"_id": id}, {"$set": {'StopLoss_Price': stoploss_price}},
                                                               upsert=True)
                                trader.tradier.modify_stopprice(stop_order_id, stoploss_price)

                            elif limits['target2'] <= max_price < limits['target3']:
                                target_price = limits['target3']
                                stoploss_price = limits['stop3']
                                trader.mongo.open_positions.update_one({"_id": id}, {"$set": {'Target_Price': target_price}},
                                                               upsert=True)
                                trader.mongo.open_positions.update_one({"_id": id}, {"$set": {'StopLoss_Price': stoploss_price}},
                                                               upsert=True)
                                trader.tradier.modify_stopprice(stop_order_id, stoploss_price)

                            elif limits['target3'] <= max_price < limits['target4']:
                                target_price = limits['target4']
                                stoploss_price = limits['stop4']
                                trader.mongo.open_positions.update_one({"_id": id}, {"$set": {'Target_Price': target_price}},
                                                               upsert=True)
                                trader.mongo.open_positions.update_one({"_id": id}, {"$set": {'StopLoss_Price': stoploss_price}},
                                                               upsert=True)
                                trader.tradier.modify_stopprice(stop_order_id, stoploss_price)

                            elif limits['target4'] <= max_price < limits['target5']:
                                target_price = limits['target5']
                                stoploss_price = limits['stop5']
                                trader.mongo.open_positions.update_one({"_id": id}, {"$set": {'Target_Price': target_price}},
                                                               upsert=True)
                                trader.mongo.open_positions.update_one({"_id": id}, {"$set": {'StopLoss_Price': stoploss_price}},
                                                               upsert=True)
                                trader.tradier.modify_stopprice(stop_order_id, stoploss_price)

                            elif limits['target5'] <= max_price < limits['target6']:
                                target_price = limits['target6']
                                stoploss_price = limits['stop6']
                                trader.mongo.open_positions.update_one({"_id": id}, {"$set": {'Target_Price': target_price}},
                                                               upsert=True)
                                trader.mongo.open_positions.update_one({"_id": id}, {"$set": {'StopLoss_Price': stoploss_price}},
                                                               upsert=True)
                                trader.tradier.modify_stopprice(stop_order_id, stoploss_price)

                            elif max_price >= limits['target6']:
                                trailstop_price = round(max_price - trail_stop_value, 2)

                                if current_price < trailstop_price:
                                    print('current_price is lower than trailstop price, closing position')

                            else:
                                print('error with streaming positions')

                            print(
                                f'{pre_symbol}   TargetPrice {target_price}   currentPrice {current_price}   '
                                f'entryPrice {entry_price}   stoplossPrice{stoploss_price} \n')

                else:

                    for i in range(0, 2):
                        order = open_position['childOrderStrategies'][str(i)]

                        if 'Stop_Price' not in order:
                            continue

                        else:

                            stop_order_id = order['Order_ID']
                            max_price = open_position['Max_Price']

                            limits = {
                                'target1': round(entry_price * (1 + .05), 2),
                                'target2': round(entry_price * (1 + .10), 2),
                                'target3': round(entry_price * (1 + .20), 2),
                                'target4': round(entry_price * (1 + .30), 2),
                                'target5': round(entry_price * (1 + .50), 2),
                                'target6': round(entry_price * (1 + .70), 2),
                                'stop1': round(entry_price * (1 - .10), 2),
                                'stop2': round(entry_price * (1 + 0), 2),
                                'stop3': round(entry_price * (1 + .10), 2),
                                'stop4': round(entry_price * (1 + .20), 2),
                                'stop5': round(entry_price * (1 + .30), 2),
                                'stop6': round(entry_price * (1 + .50), 2)
                            }

                            if current_price > max_price:
                                trader.open_positions.update_one({"_id": id}, {"$set": {'Max_Price': current_price}},
                                                                 upsert=False)

                            if max_price < limits['target1']:
                                target_price = limits['target1']
                                stoploss_price = limits['stop1']
                                trader.mongo.open_positions.update_one({"_id": id},
                                                                       {"$set": {'Target_Price': target_price}},
                                                                       upsert=True)
                                trader.mongo.open_positions.update_one({"_id": id},
                                                                       {"$set": {'StopLoss_Price': stoploss_price}},
                                                                       upsert=True)

                            elif limits['target1'] <= max_price < limits['target2']:
                                target_price = limits['target2']
                                stoploss_price = limits['stop2']
                                trader.mongo.open_positions.update_one({"_id": id},
                                                                       {"$set": {'Target_Price': target_price}},
                                                                       upsert=True)
                                trader.mongo.open_positions.update_one({"_id": id},
                                                                       {"$set": {'StopLoss_Price': stoploss_price}},
                                                                       upsert=True)

                            elif limits['target2'] <= max_price < limits['target3']:
                                target_price = limits['target3']
                                stoploss_price = limits['stop3']
                                trader.mongo.open_positions.update_one({"_id": id},
                                                                       {"$set": {'Target_Price': target_price}},
                                                                       upsert=True)
                                trader.mongo.open_positions.update_one({"_id": id},
                                                                       {"$set": {'StopLoss_Price': stoploss_price}},
                                                                       upsert=True)

                            elif limits['target3'] <= max_price < limits['target4']:
                                target_price = limits['target4']
                                stoploss_price = limits['stop4']
                                trader.mongo.open_positions.update_one({"_id": id},
                                                                       {"$set": {'Target_Price': target_price}},
                                                                       upsert=True)
                                trader.mongo.open_positions.update_one({"_id": id},
                                                                       {"$set": {'StopLoss_Price': stoploss_price}},
                                                                       upsert=True)

                            elif limits['target4'] <= max_price < limits['target5']:
                                target_price = limits['target5']
                                stoploss_price = limits['stop5']
                                trader.mongo.open_positions.update_one({"_id": id},
                                                                       {"$set": {'Target_Price': target_price}},
                                                                       upsert=True)
                                trader.mongo.open_positions.update_one({"_id": id},
                                                                       {"$set": {'StopLoss_Price': stoploss_price}},
                                                                       upsert=True)

                            elif limits['target5'] <= max_price < limits['target6']:
                                target_price = limits['target6']
                                stoploss_price = limits['stop6']
                                trader.mongo.open_positions.update_one({"_id": id},
                                                                       {"$set": {'Target_Price': target_price}},
                                                                       upsert=True)
                                trader.mongo.open_positions.update_one({"_id": id},
                                                                       {"$set": {'StopLoss_Price': stoploss_price}},
                                                                       upsert=True)

                            elif max_price >= limits['target6']:
                                trailstop_price = round(max_price - trail_stop_value, 2)

                                if current_price < trailstop_price:
                                    print('current_price is lower than trailstop price, closing position')

                            else:
                                print('error with streaming positions')

                            if current_price < stoploss_price:
                                trader.set_trader(open_position, trade_signal="SELL", trade_type="MARKET")

                            print(
                                f'{pre_symbol}   TargetPrice {target_price}   currentPrice {current_price}   '
                                f'entryPrice {entry_price}   stoplossPrice{stoploss_price} \n')


            #
            # elif order_type == "TRAIL":
            #     max_price = open_position['Max_Price']
            #     trailstop_price = round(max_price - trail_stop_value, 2)
            #
            #     if current_price > max_price:
            #         open_position['Max_Price'] = current_price
            #         trailstop_price = round(current_price - trail_stop_value, 2)
            #
            #         print(f'Updated Trailstop_Price for {symbol}')
            #
            #         trader.mongo.open_positions.update_one({"_id": id}, {"$set": {'Trail_Stop_Price': trailstop_price}},
            #                                        upsert=True)
            #         trader.mongo.open_positions.update_one({"_id": id}, {"$set": {'Max_Price': current_price}},
            #                                        upsert=False)
            #
            #     elif current_price < trailstop_price:
            #         print('current_price is lower than trailstop price, closing position')
            #         trader.set_trader(open_position, trade_signal="CLOSE", trade_type="MARKET")
            #         if not RUN_LIVE_TRADER:
            #             trader.set_trader(open_position, trade_signal=None)
            #
            # elif order_type == "CUSTOM":
            #
            #     trader.mongo.open_positions.update_one({"_id": id}, {"$set": {'Current_Price': current_price}}, upsert=True)
            #     max_price = open_position['Max_Price']
            #     trailstop_price = round(max_price - trail_stop_value, 2)
            #
            #     if isRunner == "FALSE":
            #
            #         open_position['Takeprofit_Price'] = takeprofit_price
            #         open_position['Stoploss_Price'] = stoploss_price
            #
            #         if current_price >= takeprofit_price:
            #             print('max_price exceeds TakeProfit price, closing position')
            #             leaverunner(trader, open_position)
            #
            #     elif isRunner == "TRUE":
            #
            #         if current_price > max_price:
            #             open_position['Max_Price'] = current_price
            #             trailstop_price = round(current_price - trail_stop_value, 2)
            #
            #             print(f'Updated Trailstop_Price for {symbol}')
            #
            #             trader.open_positions.update_one({"_id": id}, {"$set": {'Trail_Stop_Price': trailstop_price}},
            #                                            upsert=True)
            #             trader.open_positions.update_one({"_id": id}, {"$set": {'Max_Price': current_price}},
            #                                            upsert=False)
            #
            #         elif current_price < trailstop_price:
            #             print('current_price is lower than trailstop price, closing position')
            #             trader.set_trader(open_position, trade_signal="CLOSE", trade_type="MARKET")
            #             if not RUN_LIVE_TRADER:
            #                 trader.set_trader(open_position, trade_signal=None)
            #
            # elif order_type == "CUSTOM2":
            #
            #     trader.mongo.open_positions.update_one({"_id": id}, {"$set": {'Current_Price': current_price}}, upsert=True)
            #     max_price = open_position['Max_Price']
            #     trailstop_price = round(max_price - trail_stop_value, 2)
            #
            #     if isRunner == "FALSE":
            #
            #         open_position['Takeprofit_Price'] = takeprofit_price
            #         open_position['Stoploss_Price'] = stoploss_price
            #
            #         if current_price >= takeprofit_price:
            #             print('max_price exceeds TakeProfit price, closing position')
            #             trader.set_trader(open_position, trade_signal="CLOSE")
            #             if not RUN_LIVE_TRADER:
            #                 trader.set_trader(open_position, trade_signal=None)
            #             leaverunner(trader, open_position)
            #
            #         elif current_price <= stoploss_price:
            #             print('current_price exceeds StopLoss price, closing position')
            #             trader.set_trader(open_position, trade_signal="CLOSE", trade_type="MARKET")
            #             if not RUN_LIVE_TRADER:
            #                 trader.set_trader(open_position, trade_signal=None)
            #
            #     elif isRunner == "TRUE":
            #         target_price = None
            #         limits = {
            #             'target1': round(entry_price * (1 + .05), 2),
            #             'target2': round(entry_price * (1 + .10), 2),
            #             'target3': round(entry_price * (1 + .20), 2),
            #             'target4': round(entry_price * (1 + .30), 2),
            #             'target5': round(entry_price * (1 + .50), 2),
            #             'target6': round(entry_price * (1 + .70), 2),
            #             'stop1': round(entry_price * (1 - .10), 2),
            #             'stop2': round(entry_price * (1 + 0), 2),
            #             'stop3': round(entry_price * (1 + .10), 2),
            #             'stop4': round(entry_price * (1 + .20), 2),
            #             'stop5': round(entry_price * (1 + .30), 2),
            #             'stop6': round(entry_price * (1 + .50), 2)
            #         }
            #
            #         if current_price > max_price:
            #             open_position['Max_Price'] = current_price
            #             trader.open_positions.update_one({"_id": id}, {"$set": {'Max_Price': current_price}},
            #                                            upsert=False)
            #
            #         if max_price < limits['target1']:
            #             target_price = limits['target1']
            #             stoploss_price = limits['stop1']
            #             trader.open_positions.update_one({"_id": id}, {"$set": {'Target_Price': target_price}},
            #                                            upsert=True)
            #             trader.open_positions.update_one({"_id": id}, {"$set": {'StopLoss_Price': stoploss_price}},
            #                                            upsert=True)
            #
            #         elif max_price >= limits['target1'] and max_price < limits['target2']:
            #             target_price = limits['target2']
            #             stoploss_price = limits['stop2']
            #             trader.open_positions.update_one({"_id": id}, {"$set": {'Target_Price': target_price}},
            #                                            upsert=True)
            #             trader.open_positions.update_one({"_id": id}, {"$set": {'StopLoss_Price': stoploss_price}},
            #                                            upsert=True)
            #
            #         elif max_price >= limits['target2'] and max_price < limits['target3']:
            #             target_price = limits['target3']
            #             stoploss_price = limits['stop3']
            #             trader.open_positions.update_one({"_id": id}, {"$set": {'Target_Price': target_price}},
            #                                            upsert=True)
            #             trader.open_positions.update_one({"_id": id}, {"$set": {'StopLoss_Price': stoploss_price}},
            #                                            upsert=True)
            #
            #         elif max_price >= limits['target3'] and max_price < limits['target4']:
            #             target_price = limits['target4']
            #             stoploss_price = limits['stop4']
            #             trader.open_positions.update_one({"_id": id}, {"$set": {'Target_Price': target_price}},
            #                                            upsert=True)
            #             trader.open_positions.update_one({"_id": id}, {"$set": {'StopLoss_Price': stoploss_price}},
            #                                            upsert=True)
            #
            #         elif max_price >= limits['target4'] and max_price < limits['target5']:
            #             target_price = limits['target5']
            #             stoploss_price = limits['stop5']
            #             trader.open_positions.update_one({"_id": id}, {"$set": {'Target_Price': target_price}},
            #                                            upsert=True)
            #             trader.open_positions.update_one({"_id": id}, {"$set": {'StopLoss_Price': stoploss_price}},
            #                                            upsert=True)
            #
            #         elif max_price >= limits['target5'] and max_price < limits['target6']:
            #             target_price = limits['target6']
            #             stoploss_price = limits['stop6']
            #             trader.open_positions.update_one({"_id": id}, {"$set": {'Target_Price': target_price}},
            #                                            upsert=True)
            #             trader.open_positions.update_one({"_id": id}, {"$set": {'StopLoss_Price': stoploss_price}},
            #                                            upsert=True)
            #
            #         elif max_price >= limits['target6']:
            #             trailstop_price = round(max_price - trail_stop_value, 2)
            #
            #             if current_price < trailstop_price:
            #                 print('current_price is lower than trailstop price, closing position')
            #                 trader.set_trader(open_position, trade_signal="CLOSE", trade_type="MARKET")
            #                 if not RUN_LIVE_TRADER:
            #                     trader.set_trader(open_position, trade_signal=None)
            #
            #         else:
            #             print('error with streaming positions')
            #
            #         if current_price < stoploss_price:
            #             trader.set_trader(open_position, trade_signal="CLOSE", trade_type="MARKET")
            #             if not RUN_LIVE_TRADER:
            #                 trader.set_trader(open_position, trade_signal=None)
            #
            #         print(
            #             f'{pre_symbol}   TARGETPrice {target_price}   currentPrice {current_price}   '
            #             f'entryPrice {entry_price}   stoplossPrice{stoploss_price}   '
            #             f'trailPrice {trailstop_price} \n')
        #
        # if order_type == "OCO" or order_type == "CUSTOM":
        #     if current_price > entry_price:
        #         print(f'{pre_symbol}   takeprofit_price {round(takeprofit_price, 2)}     '
        #               f'currentPrice {current_price}   entryPrice {entry_price}    '
        #               f'stoplossPrice {stoploss_price} \n')
        #
        #     else:
        #         print(f'{pre_symbol}   takeprofit_price {round(takeprofit_price, 2)}     '
        #               f'entryPrice {entry_price}   currentPrice {current_price}    '
        #               f'stoplossPrice {stoploss_price} \n')
        #
        # elif order_type == "TRAIL":
        #     if current_price > entry_price:
        #         print(
        #             f'{pre_symbol}   takeprofit_price {round(takeprofit_price, 2)}     '
        #             f'currentPrice {current_price}   entryPrice {entry_price}    '
        #             f'trailstopPrice {trailstop_price}' '\n')
        #     else:
        #         print(
        #             f'{pre_symbol}   takeprofit_price {round(takeprofit_price, 2)}     '
        #             f'entryPrice {entry_price}   currentPrice {current_price}    '
        #             f'trailstopPrice {trailstop_price}' '\n')
        #
        # elif order_type == "CUSTOM2" and isRunner == "TRUE":
        #     pass

        # else:
        #     if current_price > entry_price:
        #         print(
        #             f'{pre_symbol}   takeprofit_price {round(takeprofit_price, 2)}     '
        #             f'currentPrice {current_price}   entryPrice {entry_price}    '
        #             f'trailstopPrice {trailstop_price}    stoplossPrice {stoploss_price}' '\n')
        #
        #     else:
        #         print(
        #             f'{pre_symbol}   takeprofit_price {round(takeprofit_price, 2)}     '
        #             f'entryPrice {entry_price}   currentPrice {current_price}    '
        #             f'trailstopPrice {trailstop_price}    stoplossPrice {stoploss_price}' '\n')
