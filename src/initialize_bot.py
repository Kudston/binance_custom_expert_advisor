import asyncio
import ccxt
import json
import logging
from src.timeframeManagement import TimeframeMgt

logging.basicConfig(filename='/home/kudston/projects/binance_ea/src/logs/errors.log', level=logging.DEBUG, 
                    format='%(asctime)s:%(levelname)s:%(message)s')

##GET CONFIGURATION PARAMETERS
def get_config_file(file_path):
    with open(file_path, 'r') as conf_file:
        new_json = json.load(conf_file)
        return dict(new_json)

##GET EXCHANGE INFORMATION FOR VERIFICATIONS
async def get_exchange_info(exchange_name: str):
    try:
        exchange = getattr(ccxt, exchange_name)
        exchange = exchange()
        markets = exchange.load_markets()
        return (exchange, markets)
    except:
        logging.error("Exchange not available in ccxt list.")
        raise Exception("Error getting exchange from ccxt.")

##BOT CLASS FOR A SINGLE PAIR
class BotConfigClass:
    def __init__(self, config_file_path) -> None:
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
        self.verify_configurations()
        self.TimeFrameClass = TimeframeMgt(self.timeframe, self.timeframes)
        self.stakeAmount = int(self.configData.get('stakeAmount', 100))
        self.api_key    = str(self.configData.get('apiKey', ''))
        self.api_secret = str(self.configData.get('apiSecret', ''))
        self.testnet  = bool(self.configData.get('test_net', True))
        self.download_new_data = bool(self.configData.get('downloadNewData', False))

    async def get_market_data(self):
        self.exchange, self.markets = await get_exchange_info(self.configData['exchange'])
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
        self.timeframe = self.configData['timeframe']
        self.digits = self.pairsInformation['precision']['price']
        self.points = 1/pow(10,self.digits)
        self.takeProfit = round(int(self.configData.get('takeProfit',100))*self.points, self.digits)
        self.stopLoss   = round(int(self.configData.get('stopLoss',100))*self.points, self.digits)
                
        logging.info("digits: {}".format(self.digits))
        logging.info("points: {}".format(self.points))
        logging.info("tp: {}".format(self.takeProfit))
        logging.info("sl: {}".format(self.stopLoss))