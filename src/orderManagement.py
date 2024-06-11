from src.initialize_bot import BotConfigClass
import pandas as pd
import ccxt
import os
import datetime

database_folder = os.path.abspath("trades_data")
if not os.path.exists(database_folder):
    os.makedirs(database_folder)

class ordersManager:
    def __init__(self, config_data:BotConfigClass) -> None:
        self.config_data:BotConfigClass = config_data
        self.client: ccxt.Exchange = config_data.exchange
        self.positiondatabase = OrdersDatabaseMgt(config_data)
        self.pairQuantityPrecision = self.config_data.pairsInformation['limits']['amount']['min'] #this doesnt work with some exchange, use at own risk
        pairdotindex = str(self.pairQuantityPrecision).index('.')
        self.pairQuantityPrecision = len(str(self.pairQuantityPrecision)[pairdotindex+1:])
        self.openBuyPositionsIds = []
        self.openSellPositionsIds = []
        self.closedtrades = []


    def BuyOrder(self, pair: str, curr_Ask: float, last_bid_time, last_candle_structure):

        takeProfitPrice = curr_Ask + self.config_data.takeProfit
        stopLossPrice = curr_Ask - self.config_data.stopLoss
        #save trade informations if successful
        trade_result = None
        sl_trade_result = None
        tp_trade_result = None

        print(f'takeprofit: {takeProfitPrice},  stoploss: {stopLossPrice}')
        try:
            trade_result = self.client.create_order(
                    symbol=pair,
                    type='market',
                    side='buy',
                    amount=float(self.config_data.stakeAmount),
                    price=curr_Ask,
                    params={
                        'precision':self.pairQuantityPrecision
                    }
                )

            print('positionResponse: ',trade_result)
            stoploss_order_params = {
                'stopLossPrice':stopLossPrice,
                'triggerDirection':'below',
                'precision':self.pairQuantityPrecision,
                'reduceOnly':True,
                'reason':'stopLoss'
            }
            sl_trade_result = self.client.create_order(
                    symbol=pair,
                    type='limit',
                    side='sell',
                    amount=float(self.config_data.stakeAmount),
                    price = stopLossPrice,
                    params=stoploss_order_params
                )
            print('stoplossResponse: ',sl_trade_result)
            takeprofit_order_params = {
                'takeProfitPrice':takeProfitPrice,
                'triggerDirection':'above',
                'precision':self.pairQuantityPrecision,
                'reduceOnly':True,
                'reason':'takeProfit'
            }
            tp_trade_result = self.client.create_order(
                    symbol=pair,
                    type='limit',
                    side='sell',
                    price=takeProfitPrice,
                    amount=float(self.config_data.stakeAmount),
                    params=takeprofit_order_params
                )
            print('takeProfitResponse: ',tp_trade_result)
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

    def SellOrder(self, pair: str, curr_Bid: float, last_ask_time, last_candle_structure):
        takeProfitPrice = curr_Bid - self.config_data.takeProfit
        stopLossPrice = curr_Bid + self.config_data.stopLoss
        
        print(f'takeprofit: {takeProfitPrice},  stoploss: {stopLossPrice}')
        try:
            trade_result = self.client.create_order(
                    symbol=pair,
                    type='market',
                    side='sell',
                    amount=float(self.config_data.stakeAmount),
                    price=curr_Bid,
                    params={
                        'precision':self.pairQuantityPrecision
                    }
                )
            print('positionResponse: ',trade_result)
            ##place stoploss
            stoploss_order_params = {
                'stopLossPrice':stopLossPrice,
                'triggerDirection':'below',
                'precision':self.pairQuantityPrecision,
                'reduceOnly':True,
                'reason':'stopLoss'
            }
            sl_trade_result = self.client.create_order(
                    symbol=pair,
                    type='limit',
                    side='buy',
                    amount=float(self.config_data.stakeAmount),
                    price = stopLossPrice,
                    params=stoploss_order_params
                )
            print('stoplossResponse: ',sl_trade_result)
            takeprofit_order_params = {
                'takeProfitPrice':takeProfitPrice,
                'triggerDirection':'above',
                'precision':self.pairQuantityPrecision,
                'reduceOnly':True,
                'reason':'takeProfit'
            }
            tp_trade_result = self.client.create_order(
                    symbol=pair,
                    type='limit',
                    side='buy',
                    price=takeProfitPrice,
                    amount=float(self.config_data.stakeAmount),
                    params=takeprofit_order_params
                )
            print('takeProfitResponse: ',tp_trade_result)
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
            #close any open orders
            result = self.client.cancel_all_orders(symbol=pair)
            print('order cancel result: ',result)
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
            result = self.client.cancel_all_orders(symbol=pair)
            print("order cancel result: ",result)
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

    def GetQuantityPrecised(self, price, stakeAmount):
        quantity = round(stakeAmount/price,self.pairQuantityPrecision)
        return quantity


class OrdersDatabaseMgt:
    def __init__(self, config:BotConfigClass):
        self.trades_dataframe_path = os.path.join(database_folder,"positions.csv")
        self.config     = config
        self.client:ccxt.Exchange = self.config.exchange
        self.currentSessionFile = os.path.join(database_folder, f"trades_data_{self.config.pairsInformation['id']}.csv")
        self.columns = None
        self.tradesDf = None
        self.buyPosition = {}
        self.sellPosition = {}
        self.buyAmount = 0
        self.sellAmount = 0
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
        
        positions = self.tradesDf.iloc[0].squeeze()
        
        if positions['type']=='open':
            if positions['side']=='buy':
                self.buyAmount = positions['orderOpenPrice']
            elif positions['side']=='sell':
                self.sellAmount = -positions['orderOpenPrice']
        else:
            self.buyAmount = 0
            self.sellAmount = 0

    def GetPositionsCount(self, type:str, is_open=True):
        pass