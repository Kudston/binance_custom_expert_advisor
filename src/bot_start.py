import sys
sys.path.append("..")
from src.initialize_bot import BotConfigClass
from src.data_mgt import DataManagement
from src.signals import Signals
import time
import os
import asyncio

config_path = os.path.abspath('config.json')
throttle_seconds = 2

botconfig = BotConfigClass(config_path)
datamgt = DataManagement(botconfig)
signalsMgt = Signals(datamgt)

async def main(signal: Signals):
    while True:
        signal.ConfirmSignals()
        time.sleep(throttle_seconds)

if __name__=="__main__":
    asyncio.run(main(signalsMgt))