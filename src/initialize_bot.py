import asyncio
import ccxt
import json
import logging
from src.timeframeManagement import TimeframeMgt
from src.exchangeMgt import CustomExchange
import os
import time

logdir = os.path.abspath("logs")
logpath = os.path.join(logdir, "errors.log")

if not os.path.exists(logdir):
    os.makedirs(logdir)

try:
    with open(logpath, 'w') as file:
        pass
except FileExistsError:
    print('Log File already exists.')

logging.basicConfig(filename=logpath, level=logging.DEBUG,
                    format='%(asctime)s:%(levelname)s:%(message)s')

##GET CONFIGURATION PARAMETERS
def get_config_file(file_path):
    with open(file_path, 'r') as conf_file:
        new_json = json.load(conf_file)
        return dict(new_json)

##BOT CLASS FOR A SINGLE PAIR
class BotConfigClass:
    def __init__(self, config_file_path) -> None:
        self.botStartTime = time.time()
        self.configData    = get_config_file(config_file_path)
        self.exchange: ccxt.Exchange = None
        self.pairsInformation = None
        self.pair = None
        self.timeframes = None
        self.timeframe = None
        self.digits = None
        self.points = None
        self.takeProfit = None
        self.stopLoss = None
        self.testnet  = bool(self.configData.get('test_net', True))
        self.demoacc  = bool(self.configData.get('is_demo', True))
        self.api_key    = str(self.configData.get('apiKey', ''))
        self.api_secret = str(self.configData.get('apiSecret', ''))
        self.verify_configurations()
        self.TimeFrameClass = TimeframeMgt(self.timeframe, self.timeframes)
        self.stakeAmount = int(self.configData.get('stakeAmount', 100))
        self.download_new_data = bool(self.configData.get('downloadNewData', False))
        self.trade_start_time = int(self.configData.get('tradeStartTime',0))
        self.trade_end_time   = int(self.configData.get('tradeEndTime', 23))

    async def get_market_data(self):
        cexchange = CustomExchange(self.configData['exchange'])
        self.exchange, self.markets = cexchange.get_exchange(self.api_key, self.api_secret, self.testnet, self.demoacc)
        self.pairs = self.markets.keys()
        self.timeframes = self.exchange.timeframes.keys()

    #CHECKING INPUT VARIABLES FOR CORRECTNESS AND AVAILABILITY, THEN SET OTHER PROPERTIES OF THE BOT CLASS
    #FOR THE SYMBOL SPECIFIC
    def verify_configurations(self):
        asyncio.run(self.get_market_data())
        if self.configData['pair'] not in self.pairs:
            logging.error("The pairs you provided is not part of the ccxt pairs for exchange: {}".
                          format(self.configData['exchange']))
            raise Exception("pair provided does not match any ccxt pair for the exchange.")
        
        if self.configData['timeframe'] not in self.timeframes:            
            logging.error("The timeframe you provided does not match any timeframe for exchange: {}".
                          format(self.configData['exchange']))
            
            raise Exception("timeframe provided does not match any timeframe for the exchange.\
                            \nAvailable timeframes are: {}".format(self.timeframes))
        else:
            self.pairsInformation = self.markets.get(self.configData['pair'])
        
        if not self.exchange.has['fetchOHLCV']:
            logging.info("Cannot fetch OHLCV data, exchange does not support this feature.")
            raise Exception("Cannot fetch ohlcv data because exchange does not support it.")
        
        ##setting other standard parameters
        self.pair   = self.pairsInformation['symbol']
        last_askprice  = self.exchange.fetch_order_book(self.pair,5)['asks'][0][0]
        dot_index = str(last_askprice).index('.')
        self.timeframe = self.configData['timeframe']
        self.digits = len(str(last_askprice)[dot_index+1:])
        self.points = 1/pow(10,self.digits)
        self.takeProfit = round(int(self.configData.get('takeProfit',100))*self.points, self.digits)
        self.stopLoss   = round(int(self.configData.get('stopLoss',100))*self.points, self.digits)
    
        logging.info("digits: {}".format(self.digits))
        logging.info("points: {}".format(self.points))
        logging.info("tp: {}".format(self.takeProfit))
        logging.info("sl: {}".format(self.stopLoss))