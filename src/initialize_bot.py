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
        self.pairsInformation = {}
        self.timeframes = None
        self.timeframe = None
        self.digits = {}
        self.points = {}
        self.takeProfit = {}
        self.stopLoss = {}
        self.tradable_pairs = []
        self.market_pairs = []
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
        self.bollinger_period = int(self.configData.get('bollingerPeriod', 20))
        self.bollinger_deviation = int(self.configData.get('bollingerDeviation',2))
        self.ema_period     = int(self.configData.get('emaPeriod', 20))
        self.atr_period     = int(self.configData.get('atrPeriod', 14))

    async def get_market_data(self):
        cexchange = CustomExchange(self.configData['exchange'])
        self.exchange, self.markets = cexchange.get_exchange(self.api_key, self.api_secret, self.testnet, self.demoacc)
        self.market_pairs = self.markets.keys()
        self.timeframes = self.exchange.timeframes.keys()

    #CHECKING INPUT VARIABLES FOR CORRECTNESS AND AVAILABILITY, THEN SET OTHER PROPERTIES OF THE BOT CLASS
    #FOR THE SYMBOL SPECIFIC
    def verify_configurations(self):
        asyncio.run(self.get_market_data())
        pairs = self.configData['pairs']
        for pair in pairs:
            if pair not in self.market_pairs:
                logging.error("The pairs you provided is not part of the ccxt pairs for exchange: {}".
                            format(self.configData['exchange']))
                raise Exception(f"pair provided {pair} does not match any ccxt pair for the exchange.")
            
            self.tradable_pairs.append(pair)
            self.pairsInformation[pair] = self.markets[pair]

        if self.configData['timeframe'] not in self.timeframes:            
            logging.error("The timeframe you provided does not match any timeframe for exchange: {}".
                          format(self.configData['exchange']))
            
            raise Exception("timeframe provided does not match any timeframe for the exchange.\
                            \nAvailable timeframes are: {}".format(self.timeframes))    
        
        if not self.exchange.has['fetchOHLCV']:
            logging.info("Cannot fetch OHLCV data, exchange does not support this feature.")
            raise Exception("Cannot fetch ohlcv data because exchange does not support it.")
        
        ##setting other standard parameters
        for pair in self.tradable_pairs:
            last_askprice  = self.exchange.fetch_order_book(pair,5)['asks'][0][0]
            dot_index = str(last_askprice).index('.')
            self.digits[pair] = len(str(last_askprice)[dot_index+1:])
            self.points[pair] = 1/pow(10,self.digits[pair])
            self.takeProfit[pair] = round(int(self.configData.get('takeProfit',100))*self.points[pair], self.digits[pair])
            self.stopLoss[pair]   = round(int(self.configData.get('stopLoss',100))*self.points[pair], self.digits[pair])

        self.timeframe = self.configData['timeframe']

        logging.info("digits: {}".format(self.digits))
        logging.info("points: {}".format(self.points))
        logging.info("tp: {}".format(self.takeProfit))
        logging.info("sl: {}".format(self.stopLoss))