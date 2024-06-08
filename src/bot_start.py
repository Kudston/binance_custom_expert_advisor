from src.initialize_bot import BotConfigClass
from src.data_mgt import DataManagement
from src.signals import Signals
import time
import os
import asyncio

config_path = os.path.abspath('config.json')

botconfig = BotConfigClass(config_path)
datamgt = DataManagement(botconfig)
signalsMgt = Signals(datamgt)

async def main(signal: Signals):
    signal.ConfirmSignals()
    time.sleep(1000)

if __name__=="__main__":
    while True:
        asyncio.run(main())