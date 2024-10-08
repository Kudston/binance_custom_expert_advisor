from src.initialize_bot import BotConfigClass
import pandas as pd
import ccxt
import os
import datetime

database_folder = os.path.abspath("trades_data")
if not os.path.exists(database_folder):
    os.makedirs(database_folder)

class ordersManager:
    def __init__(self, pair, config_data:BotConfigClass) -> None:
        self.config_data:BotConfigClass = config_data
        self.client: ccxt.Exchange = config_data.exchange
        self.pair = pair
        self.positiondatabase = OrdersDatabaseMgt(config_data, pair)
        self.pairQuantityPrecision = self.config_data.pairsInformation[pair]['limits']['amount']['min']
        self.openBuyPositionsIds = []
        self.openSellPositionsIds = []
        self.closedtrades = []


    def BuyOrder(self, pair: str, pairFutureName: str, curr_Ask: float, last_bid_time, last_candle_structure):

        takeProfitPrice = round(curr_Ask + self.config_data.takeProfit[pairFutureName], 
                                self.config_data.digits[pairFutureName])
        stopLossPrice = round(curr_Ask - self.config_data.stopLoss[pairFutureName],
                              self.config_data.digits[pairFutureName])
        #save trade informations if successful
        trade_result = None
        sl_trade_result = None
        tp_trade_result = None

        print(f'takeprofit: {takeProfitPrice},  stoploss: {stopLossPrice}')
        try:
            stoploss_order_params = {
                'type':'Market',
                'triggerPrice':stopLossPrice,
            }
            takeprofit_order_params = {
                'type':'Market',
                'triggerPrice':takeProfitPrice,
            }

            trade_result = self.client.create_order(
                    symbol=pair,
                    type='market',
                    side='buy',
                    amount=float(self.config_data.stakeAmount[pairFutureName]),
                    price=curr_Ask,
                    params={
                        'precision':self.pairQuantityPrecision,
                        'takeProfit':takeprofit_order_params,
                        'stopLoss':stoploss_order_params
                    }
                )

            print('positionResponse: ',trade_result)

        except Exception as raised_exception:
            raise raised_exception
        finally:
            order_info = {
                'pair':pair,
                'time':last_bid_time,
                'lastCandleTime':last_candle_structure['datetime'],
                'price':curr_Ask,
                'side':'buy',
                'type':'open'
            }
            self.positiondatabase.AddPosition(orders_info=order_info)

    def SellOrder(self, pair: str, pairFutureName: str, curr_Bid: float, last_ask_time, last_candle_structure):
        takeProfitPrice = round(curr_Bid - self.config_data.takeProfit[pairFutureName], 
                                self.config_data.digits[pairFutureName])
        stopLossPrice = round(curr_Bid + self.config_data.stopLoss[pairFutureName],
                              self.config_data.digits[pairFutureName])
        
        print(f'takeprofit: {takeProfitPrice},  stoploss: {stopLossPrice}')
        try:
            stoploss_order_params = {
                'type':'Market',
                'triggerPrice':stopLossPrice,
            }
            takeprofit_order_params = {
                'type':'Market',
                'triggerPrice':takeProfitPrice,
            }

            trade_result = self.client.create_order(
                    symbol=pair,
                    type='market',
                    side='sell',
                    amount=float(self.config_data.stakeAmount[pairFutureName]),
                    price=curr_Bid,
                    params={
                        'precision':self.pairQuantityPrecision,
                        'takeProfit':takeprofit_order_params,
                        'stopLoss':stoploss_order_params
                    }
                )
            print('positionResponse: ',trade_result)
        except Exception as raised_exception:
            raise raised_exception
        finally:
            order_info = {
                'pair':pair,
                'time':last_ask_time,
                'lastCandleTime':last_candle_structure['datetime'],
                'price':curr_Bid,
                'side':'sell',
                'type':'open'
            }
            self.positiondatabase.AddPosition(orders_info=order_info)

    def CloseBuyOrder(self, pair, quantity: float, price, last_price_time, last_candle_data):
        try:
            takeprofit_order_params = {
                'takeProfitPrice':price,
                'triggerDirection':'above',
                'precision':self.pairQuantityPrecision,
                'reduceOnly':True,
                'reason':'close'
            }
            close_buy_result = self.client.create_order(
                    symbol=pair,
                    type='market',
                    side='sell',
                    price=price,
                    amount=quantity,
                    params=takeprofit_order_params
                )
            print(close_buy_result)
        except Exception as raised_exception:
            raise raised_exception
        finally:
            order_info = {
                'pair':pair,
                'time':last_price_time,
                'lastCandleTime':last_candle_data['datetime'],
                'price':price,
                'side':'sell',
                'type':'close'
            }
            self.positiondatabase.AddPosition(orders_info=order_info)

    def CloseSellOrder(self, pair, quantity: float, price, last_price_time, last_candle_data):
        try:
            takeprofit_order_params = {
                'takeProfitPrice':price,
                'triggerDirection':'above',
                'precision':self.pairQuantityPrecision,
                'reduceOnly':True,
                'reason':'close'
            }
            close_sell_result = self.client.create_order(
                    symbol=pair,
                    type='market',
                    side='buy',
                    price=price,
                    amount=quantity,
                    params=takeprofit_order_params
                )
            print(close_sell_result)
            #close any open order
        except Exception as raised_exception:
            raise raised_exception
        finally:
            order_info = {
                'pair':pair,
                'time':last_price_time,
                'lastCandleTime':last_candle_data['datetime'],
                'price':price,
                'side':'buy',
                'type':'close'
            }
            self.positiondatabase.AddPosition(orders_info=order_info)

class OrdersDatabaseMgt:
    def __init__(self, config:BotConfigClass, pair: str):
        self.config     = config
        self.client:ccxt.Exchange = self.config.exchange
        self.currentSessionFile = os.path.join(database_folder, f"trades_data_{self.config.pairsInformation[pair]['id']}_{self.config.timeframe}.csv")
        self.columns = None
        self.tradesDf = None
        self.buyPosition = {}
        self.sellPosition = {}
        self.buyAmount = 0
        self.sellAmount = 0
        self.last_trade_recorded = None
        self.close_remnant_orders = False
        self.remnant_order_type = 'None'
        self.InitiateOrderTable()
    
    def InitiateOrderTable(self):
        self.columns = ['orderBarTime','realOrderTime','orderOpenPrice','pair', 'side','type']
        file_already_exist = os.path.exists(self.currentSessionFile)
        self.tradesDf:pd.DataFrame = (pd.DataFrame(columns=self.columns) if not 
                                      file_already_exist else pd.read_csv(self.currentSessionFile))

    def AddPosition(self, orders_info: dict):
        oCandleTime = datetime.datetime.fromtimestamp(orders_info['lastCandleTime']/1000)

        ##check if last record is on same candle
        last_record_time = -1
        try:
            last_record_time = self.tradesDf.iloc[0].squeeze()['orderBarTime']
        except:
            pass

        if oCandleTime==last_record_time:
            return
        
        oRealTime = datetime.datetime.fromtimestamp(orders_info['time']/1000)
        oOpenPrice = orders_info['price']
        oPair   = orders_info['pair']
        oSide   = orders_info['side']
        oType   = orders_info['type']

        list = [[oCandleTime, oRealTime, oOpenPrice, oPair, oSide, oType]]
        newOrder = pd.DataFrame(list, columns=self.columns)
        self.tradesDf = pd.concat([newOrder,self.tradesDf], axis=0).reset_index(drop=True)
        self.tradesDf.to_csv(self.currentSessionFile,index=False)

    def GetPositions(self, pair:str):
        if len(self.tradesDf)<=0:
            return
        
        trades = self.config.exchange.fetch_my_trades(pair)

        for trade in trades['info']:
            if trade['positionIdx']==1:
                self.buyAmount =  float(trade['size'])

            elif trade['positionIdx']==2:
                self.sellAmount = float(trade['size'])