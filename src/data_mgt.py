import sys
import time
sys.path.append("..")
from src.initialize_bot import BotConfigClass
import os
import pandas as pd
import datetime

data_path_folder = os.path.join(".",'data')
a = os.path.abspath(data_path_folder)

def GenerateDataFileName(pair: str, timeframe: str):
    return os.path.join(data_path_folder,"DataFrame_for_{}_timeframe_{}.csv".format(pair, timeframe))

class DataManagement:
    def __init__(self, bot_config=None, initial_counts: int= 5000)->None:
        self.configData: BotConfigClass = bot_config
        self.data_path = GenerateDataFileName(bot_config.pairsInformation['id'], bot_config.timeframe)
        self.initial_data_counts = initial_counts
        self.df: pd.DataFrame = None
        
        self.next_candle_time = None    #datetime timestamp in seconds
        self.last_candle_time = None    #datetime timestamp in seconds

        self.columns = ['datetime','open','high','low','close','volume']

    def InitializeDataFrame(self, download_new: bool):
        try:
            if download_new:
                if not os.path.exists(data_path_folder):
                   os.mkdir(data_path_folder)
                time.sleep(self.configData.exchange.rateLimit / 1000)
                price_data = self.configData.exchange.fetch_ohlcv(self.configData.pair, self.configData.timeframe)
                self.df = pd.DataFrame(price_data, columns=self.columns)
                self.df = self.df.iloc[:-1,:]
                self.df.to_csv(self.data_path,index=False)
            else:
                if not os.path.exists(data_path_folder):
                   raise ("Data file does not already exist.")
                self.df = pd.read_csv(self.data_path)         

            last_candle = self.df.iloc[-1].squeeze()
            self.last_candle_time = int(last_candle['datetime'] /1000)
            self.next_candle_time = (self.last_candle_time + 
                                     self.configData.TimeFrameClass.GetTimeframeSeconds()*2)
                
        except Exception as raised_exception:
            raise Exception(str(raised_exception))
        
    def GetNewData(self):
        price_data = self.configData.exchange.fetch_ohlcv(self.configData.pair, self.configData.timeframe, 
                                                          self.next_candle_time*1000)
        new_df = pd.DataFrame(price_data, columns=self.columns)
        new_df = new_df.iloc[:-1,:]
        return new_df

    def UpdateData(self)->bool:
        try:
            if datetime.datetime.now().timestamp()>self.next_candle_time:
                new_df = self.GetNewData()
                self.df = pd.concat([self.df, new_df], axis=0).reset_index(drop=True)
                self.last_candle_time = self.df.iloc[-1].squeeze()['datetime']/1000
                self.next_candle_time = (self.last_candle_time + 
                                        self.configData.TimeFrameClass.GetTimeframeSeconds()*2)
                print("current last bar: ",datetime.datetime.fromtimestamp(self.last_candle_time))
                print("next bar time: ",datetime.datetime.fromtimestamp(self.next_candle_time))
                return True
            return False
        except Exception as raised_exception:
            raise Exception(str(raised_exception))