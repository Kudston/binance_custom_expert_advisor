import sys
sys.path.append("..")
from src.data_mgt import DataManagement
from src.initialize_bot import BotConfigClass
from src.orderManagement import ordersManager
import pandas as pd
import datetime
import time
from ta.volatility import BollingerBands, AverageTrueRange
from ta.trend import EMAIndicator


class Signals:
    def __init__(self, datamgt: DataManagement) -> None:
        self.data_mgt:DataManagement = datamgt
        self.configData:BotConfigClass = datamgt.configData
        self.order_mgt: ordersManager = ordersManager(self.configData)
        #initialize dataframe
        self.data_mgt.InitializeDataFrame(self.configData.download_new_data)

        self.last_candle_data = None
        self.df = None
        self.best_bid = 0
        self.best_ask = 0


    period = 20
    deviation = 2
    start_hour = 15
    end_hour = 23
    
    traded_last_bar = False

    def ConfirmSignals(self):
        #send positions using the symbol in pairsINformation dictionary
        self.CheckLastCandleSignal()
        self.order_mgt.BuyOrder(self.configData.pairsInformation['id'], self.best_ask)
        if self.last_candle_data['buy_signal'] and self.best_ask>=self.last_candle_data['ema']:
            self.order_mgt.BuyOrder(self.configData.pairsInformation['id'], self.best_bid)

        elif self.last_candle_data['sell_signal'] and self.best_bid<=self.last_candle_data['ema']:
            self.order_mgt.SellOrder(self.configData.pairsInformation['id'], self.best_ask)

        if len(self.order_mgt.openBuyPositionsIds)>0 and self.best_bid>=self.last_candle_data['ema']:
            self.order_mgt.CloseBuyOrder(self.configData.pairsInformation['id'], 100)

        if len(self.order_mgt.openSellPositionsIds)>0 and self.best_ask<=self.last_candle_data['ema']:
            self.order_mgt.CloseSellOrder(self.configData.pairsInformation['id'], 100)

    def CheckLastCandleSignal(self):
        if self.data_mgt.UpdateData():
            #populate indicators copies raw data into self.df
            self.PopulateIndicators()

            #populate signals modifies self.df and adds signals to it
            self.PopulateSignals(self.df)
        order_book = self.configData.exchange.fetch_order_book(self.configData.pair, 10)
        self.best_bid = order_book['bids'][0][0]
        self.best_ask = order_book['asks'][0][0]


    def PopulateIndicators(self):
        self.df = self.data_mgt.df.copy()
        
        self.df['midprice'] = round((self.df.high+self.df.low)/2, self.configData.digits)
        boll = BollingerBands(self.df['midprice'], self.period, self.deviation)
        self.df['upper_band'] = boll.bollinger_hband()
        self.df['lower_band'] = boll.bollinger_lband()
        ema = EMAIndicator(self.df['midprice'], self.period)
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

start_time = time.time()
datamgt = Signals(DataManagement(BotConfigClass('/home/kudston/projects/binance_ea/src/config.json')))
datamgt.ConfirmSignals()
print(time.time()-start_time)