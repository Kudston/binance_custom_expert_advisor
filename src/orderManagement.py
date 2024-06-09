from src.initialize_bot import BotConfigClass
import pandas as pd
import ccxt
import os
import datetime

database_folder = os.path.abspath("trades_data")

class ordersManager:
    def __init__(self, config_data:BotConfigClass) -> None:
        self.config_data:BotConfigClass = config_data
        self.client: ccxt.Exchange = config_data.exchange
        self.positiondatabase = OrdersDatabaseMgt(config_data)
        self.pairQuantityPrecision = self.config_data.pairsInformation['precision']['amount'] #this doesnt work with some exchange, use at own risk
        self.openBuyPositionsIds = []
        self.openSellPositionsIds = []
        self.closedtrades = []

    def BuyOrder(self, pair: str, curr_Ask: float, last_bid_time, last_candle_structure):

        takeProfitPrice = curr_Ask + self.config_data.takeProfit
        stopLossPrice = curr_Ask - self.config_data.stopLoss
        
        print(f'tp: {takeProfitPrice},  sl: {stopLossPrice}')
        try:
            trade_result = self.client.create_order(
                    symbol=pair,
                    type='market',
                    side='buy',
                    amount=float(self.config_data.stakeAmount)
                )
            
            stoploss_order_params = {
                'stopLossPrice':stopLossPrice,
                'triggerDirection':'below'
            }
            sl_trade_result = self.client.create_order(
                    symbol=pair,
                    type='limit',
                    side='sell',
                    amount=float(self.config_data.stakeAmount),
                    params=stoploss_order_params
                )

            takeprofit_order_params = {
                'takeProfitPrice':takeProfitPrice,
                'triggerDirection':'above'
            }
            tp_trade_result = self.client.create_order(
                    symbol=pair,
                    type='limit',
                    side='sell',
                    amount=float(self.config_data.stakeAmount),
                    params=stoploss_order_params
                )
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
        # amount = self.GetQuantityPrecised(curr_Ask, self.config_data.stakeAmount)
        takeProfitPrice = curr_Bid - self.config_data.takeProfit
        stopLossPrice = curr_Bid + self.config_data.stopLoss
        try:
            print(f'tp: {takeProfitPrice},  sl: {stopLossPrice}')
            trade_result = self.client.create_order(
                    symbol=pair,
                    type='market',
                    side='sell',
                    amount=float(self.config_data.stakeAmount),
                )
            
            stoploss_order_params = {
                'stopLossPrice':stopLossPrice,
                'triggerDirection':'above'
            }
            sl_trade_result = self.client.create_order(
                    symbol=pair,
                    type='limit',
                    side='buy',
                    amount=float(self.config_data.stakeAmount),
                    params=stoploss_order_params
                )

            takeprofit_order_params = {
                'takeProfitPrice':takeProfitPrice,
                'triggerDirection':'below'
            }
            tp_trade_result = self.client.create_order(
                    symbol=pair,
                    type='limit',
                    side='buy',
                    amount=float(self.config_data.stakeAmount),
                    params=stoploss_order_params
                )
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
            print("close amount: ",quantity)
            
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
            print("close amount: ",quantity)
            result = self.client.create_order(
                symbol=pair,
                type='market',
                side='buy',
                amount=quantity,
                params={
                    'positionSide':'SHORT',
                    'reduceOnly':True,
                }
            )
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
            last_record_time = self.tradesDf.iloc[-1].squeeze()['orderBarTime']
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
                # print('found buy')
                self.buyAmount = self.config.stakeAmount
            elif positions['side']=='sell':
                # print('found sell')
                self.sellAmount = -self.config.stakeAmount
        else:
            self.buyAmount = 0
            self.sellAmount = 0

    def GetPositionsCount(self, type:str, is_open=True):
        pass