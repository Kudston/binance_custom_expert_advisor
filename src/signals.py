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
    def __init__(self, pair, botconfig:BotConfigClass) -> None:
        self.data_mgt:DataManagement = DataManagement(pair, botconfig)
        self.configData:BotConfigClass = botconfig
        self.order_mgt: ordersManager = ordersManager(pair, botconfig)
        self.pair   = pair
        
        self.start_hour = self.configData.trade_start_time
        todays_date = datetime.datetime.now(tz=datetime.timezone.utc)

        self.trade_start_time = None
        
        self.trade_end_time = None
        
        ##set in milliseconds the trade start time
        self.trade_start_milsecs = 0
        self.trade_end_milsecs = 0
        self.SetTradingTime()

        print(f"trade start time: {self.trade_start_time}\ntrade endtime: {self.trade_end_time}")

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

    traded_last_bar = False

    
    
    def ConfirmSignals(self):
        #send positions using the symbol in pairsINformation dictionary
        try:
            self.CheckLastCandleSignal()
            if not self.traded_last_bar:
                if ((self.last_candle_data['buy_signal']==1) and 
                    (self.best_ask>=self.last_candle_data['lower_band']) and
                    (self.order_mgt.positiondatabase.buyAmount==0) and
                    (self.best_ask-self.best_bid<=self.configData.max_spread_values[self.pair])
                    ):
                    logging.info('placing buy order')
                    print('placing buy order')
                    self.traded_last_bar = True
                    self.order_mgt.BuyOrder(self.configData.pairsInformation[self.pair]['id'],self.pair, self.best_bid, 
                                            self.last_price_time, self.last_candle_data)

                elif ((self.last_candle_data['sell_signal']==1) and 
                      (self.best_bid<=self.last_candle_data['upper_band']) and
                      (self.order_mgt.positiondatabase.sellAmount==0)and
                      (self.best_ask-self.best_bid<=self.configData.max_spread_values[self.pair])
                      ):
                    logging.info('placing sell order')
                    print('placing sell order')
                    self.traded_last_bar = True
                    self.order_mgt.SellOrder(self.configData.pairsInformation[self.pair]['id'], self.pair, self.best_ask, 
                                             self.last_price_time, self.last_candle_data)

            if  self.order_mgt.positiondatabase.buyAmount!=0 and self.best_bid>=self.last_candle_data['ema']:
                logging.info('closing buy order')
                print('closing buy order')
                self.order_mgt.CloseBuyOrder(self.configData.pairsInformation[self.pair]['id'], 0, 
                                             self.best_bid, self.last_price_time, self.last_candle_data)

            if self.order_mgt.positiondatabase.sellAmount!=0 and self.best_ask<=self.last_candle_data['ema']:
                logging.info('closing sell order')
                print('closing sell order')
                self.order_mgt.CloseSellOrder(self.configData.pairsInformation[self.pair]['id'], 0,
                                              self.best_bid, self.last_price_time, self.last_candle_data)
                
            ##check if we past trading time and set a new trading time for the current day
            if (self.last_price_time) > self.trade_end_milsecs:
                self.SetTradingTime()

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

                #get position at the time of current bar start
                #put here to reduce the number of api calls
                self.order_mgt.positiondatabase.GetPositions(self.configData.pairsInformation[self.pair]['id'])

                print(f"information for pair: {self.pair}")
                print("buy positions amount current open:",self.order_mgt.positiondatabase.buyAmount)
                print("sell positions amount current open: ",self.order_mgt.positiondatabase.sellAmount)
                print('last bar ema: ',self.last_candle_data['ema'])
                print('last bar upBand: ',self.last_candle_data['upper_band'])
                print('last bar lowerBand: ', self.last_candle_data['lower_band'])
                print('last close: ', self.last_candle_data['close'])
                
            #check for positions open
            order_book = self.configData.exchange.fetch_order_book(self.pair, 5)
            self.best_bid = order_book['bids'][0][0]
            self.best_ask = order_book['asks'][0][0]
            self.last_price_time = int(order_book['timestamp'])

        except Exception as raised_exception:
            print(str(raised_exception))

    def PopulateIndicators(self):
        self.df = self.data_mgt.df.copy()
        
        self.df['midprice'] = round((self.df['high']+self.df['low'])/2, self.configData.digits[self.pair])
        
        boll = BollingerBands(self.df['close'], self.configData.bollinger_period, 
                              self.configData.bollinger_deviation)

        self.df['upper_band'] = round(boll.bollinger_hband(), self.configData.digits[self.pair])
        self.df['lower_band'] = round(boll.bollinger_lband(), self.configData.digits[self.pair])

        ema = EMAIndicator(self.df['close'], self.configData.ema_period)
        self.df['ema'] = round(ema.ema_indicator(), self.configData.digits[self.pair])
        
        self.df['atr'] = round(AverageTrueRange(self.df['high'], self.df['low'], self.df['close'], 
                                           self.configData.atr_period).average_true_range(), 
                                           self.configData.digits[self.pair])

    def PopulateSignals(self, dataframe: pd.DataFrame):
        dataframe.loc[(
            (dataframe.close<dataframe.lower_band)
            &(dataframe.close<dataframe.ema)
            &(dataframe.datetime>=self.trade_start_milsecs)
            &(dataframe.datetime<=self.trade_end_milsecs)
            &(dataframe.atr<=self.configData.atr_purchase_value[self.pair])
            &(dataframe.volume>0)),
        'buy_signal'] = 1

        dataframe.loc[(
            (dataframe.close>dataframe.upper_band)
            &(dataframe.close>dataframe.ema)
            &(dataframe.datetime>=self.trade_start_milsecs)
            &(dataframe.datetime<=self.trade_end_milsecs)
            &(dataframe.atr<=self.configData.atr_purchase_value[self.pair])
            &(dataframe.volume>0)),
        'sell_signal'] = 1
        
        self.last_candle_data = dataframe.iloc[-1].squeeze()
        
    def SetTradingTime(self):
        todays_date = datetime.datetime.now(tz=datetime.timezone.utc)
        self.trade_start_time = (datetime.datetime(todays_date.year, todays_date.month,
                                            todays_date.day, self.start_hour))

        self.trade_end_time = (self.trade_start_time +
                        datetime.timedelta(hours=self.configData.trading_hour))

        ##set in milliseconds the trade start time
        self.trade_start_milsecs = self.trade_start_time.timestamp()*1000
        self.trade_end_milsecs = self.trade_end_time.timestamp()*1000