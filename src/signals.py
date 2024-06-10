import sys
sys.path.append("..")
from src.data_mgt import DataManagement
from src.initialize_bot import BotConfigClass, logging
from src.orderManagement import ordersManager
import pandas as pd
import datetime
import time
from ta.volatility import BollingerBands, AverageTrueRange
from ta.trend import EMAIndicator

import warnings 

warnings.filterwarnings('ignore')

class Signals:
    def __init__(self, datamgt: DataManagement) -> None:
        self.data_mgt:DataManagement = datamgt
        self.configData:BotConfigClass = datamgt.configData
        self.order_mgt: ordersManager = ordersManager(self.configData)
        
        self.start_hour = self.configData.trade_start_time
        self.end_hour = self.configData.trade_end_time

        #initialize dataframe
        self.data_mgt.InitializeDataFrame(self.configData.download_new_data)
        
        self.last_candle_data = None
        self.df = None
        self.best_bid = 0
        self.best_ask = 0
        self.last_price_time = 0
        self.engineUpdateCount = 0
        while self.engineUpdateCount<20:
            if not self.data_mgt.UpdateData():
                break
            self.engineUpdateCount +=1

        self.CheckLastCandleSignal(True)

    period = 20
    deviation = 2
    
    traded_last_bar = False

    
    def ConfirmSignals(self):
        #send positions using the symbol in pairsINformation dictionary
        try:
            self.CheckLastCandleSignal()
            if not self.traded_last_bar:
                if ((self.last_candle_data['buy_signal']==1) and 
                    (self.best_ask>=self.last_candle_data['lower_band']) and
                    (self.order_mgt.positiondatabase.buyAmount==0)
                    ):
                    logging.info('placing buy order')
                    print('placing buy order')
                    self.traded_last_bar = True
                    self.order_mgt.BuyOrder(self.configData.pairsInformation['id'], self.best_bid, 
                                            self.last_price_time, self.last_candle_data)

                elif ((self.last_candle_data['sell_signal']==1) and 
                      (self.best_bid<=self.last_candle_data['upper_band']) and
                      (self.order_mgt.positiondatabase.sellAmount==0)
                      ):
                    logging.info('placing sell order')
                    print('placing sell order')
                    self.traded_last_bar = True
                    self.order_mgt.SellOrder(self.configData.pairsInformation['id'], self.best_ask, 
                                             self.last_price_time, self.last_candle_data)

            if  self.order_mgt.positiondatabase.buyAmount>0 and self.best_bid>=self.last_candle_data['ema']:
                logging.info('closing buy order')
                print('closing buy order')
                self.order_mgt.CloseBuyOrder(self.configData.pairsInformation['id'], 0, 
                                             self.best_bid, self.last_price_time, self.last_candle_data)

            if self.order_mgt.positiondatabase.sellAmount<0 and self.best_ask<=self.last_candle_data['ema']:
                logging.info('closing sell order')
                print('closing sell order')
                self.order_mgt.CloseSellOrder(self.configData.pairsInformation['id'], 0,
                                              self.best_bid, self.last_price_time, self.last_candle_data)
        except Exception as raised_exception:
            print(str(raised_exception))

    def CheckLastCandleSignal(self, forceUpdate=False):
        
        try:
            if self.data_mgt.UpdateData() or forceUpdate:
                self.traded_last_bar = False
                #populate indicators copies raw data into self.df
                self.PopulateIndicators()

                #populate signals modifies self.df and adds signals to it
                self.PopulateSignals(self.df)
                print("buy positions amount: ",self.order_mgt.positiondatabase.buyAmount)
                print("sell positions amount: ",self.order_mgt.positiondatabase.sellAmount)
                print('last bar ema: ',self.last_candle_data['ema'])
                print('last bar upBand: ',self.last_candle_data['upper_band'])
                print('last bar lowerBand: ', self.last_candle_data['lower_band'])
                print('last close: ', self.last_candle_data['close'])
                
            #check for positions open
            self.order_mgt.positiondatabase.GetPositions(self.configData.pairsInformation['id'])
            order_book = self.configData.exchange.fetch_order_book(self.configData.pair, 5)
            self.best_bid = order_book['bids'][0][0]
            self.best_ask = order_book['asks'][0][0]
            self.last_price_time = int(order_book['timestamp'])

        except Exception as raised_exception:
            print(str(raised_exception))

    def PopulateIndicators(self):
        self.df = self.data_mgt.df.copy()
        
        self.df['midprice'] = round((self.df.high+self.df.low)/2, self.configData.digits)
        boll = BollingerBands(self.df['close'], self.period, self.deviation)
        self.df['upper_band'] = boll.bollinger_hband()
        self.df['lower_band'] = boll.bollinger_lband()
        ema = EMAIndicator(self.df['close'], self.period)
        self.df['ema'] = ema.ema_indicator()
        self.df['atr'] = (AverageTrueRange(self.df['high'], self.df['low'], self.df['close'], self.period).
                          average_true_range())
        self.df['hour'] = self.df['datetime'].apply(lambda x: datetime.datetime.fromtimestamp(x / 1000).hour)
        

    def PopulateSignals(self, dataframe: pd.DataFrame):
        dataframe.loc[(
            (dataframe.close<dataframe.lower_band)
            &(dataframe.close<dataframe.ema)
            &(dataframe.hour>=self.start_hour)
            &(dataframe.hour<=self.end_hour)
            &(dataframe.volume>0)),
        'buy_signal'] = 1

        dataframe.loc[(
            (dataframe.close>dataframe.upper_band)
            &(dataframe.close>dataframe.ema)
            &(dataframe.hour>=self.start_hour)
            &(dataframe.hour<=self.end_hour)
            &(dataframe.volume>0)),
        'sell_signal'] = 1

        self.last_candle_data = dataframe.iloc[-1].squeeze()