import sys
sys.path.append("..")
from src.initialize_bot import BotConfigClass
from src.data_mgt import DataManagement
from src.signals import Signals
import time
import os
import asyncio

config_path = os.path.abspath('config.json')
throttle_seconds = 4

botconfig = BotConfigClass(config_path)
pairs_ = botconfig.tradable_pairs
signalsMgt_objects = []

for pair in pairs_:
    signalsMgt_objects.append(Signals(pair, botconfig))

async def main(signals: list[Signals]):
    while True:
        for signal in signals:
            signal.ConfirmSignals()
        time.sleep(throttle_seconds)

if __name__=="__main__":
    asyncio.run(main(signalsMgt_objects))