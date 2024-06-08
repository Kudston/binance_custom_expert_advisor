from src.initialize_bot import BotConfigClass
from binance import Client
import pandas as pd
import os

database_folder = os.path.abspath("trades_data")
print(database_folder)

class ordersManager:
    def __init__(self, config_data:BotConfigClass) -> None:
        self.config_data:BotConfigClass = config_data
        self.client: Client = Client(config_data.api_key, config_data.api_secret, testnet=config_data.testnet)
        self.positiondatabase = OrdersDatabaseMgt(self.client)
        self.pairQuantityPrecision = self.config_data.pairsInformation['precision']['amount']
        self.openBuyPositionsIds = []
        self.openSellPositionsIds = []
        self.closedtrades = []

    def BuyOrder(self, pair: str, curr_Ask: float):
        amount = self.GetQuantityPrecised(curr_Ask, self.config_data.stakeAmount)
        takeProfitPrice = curr_Ask + self.config_data.takeProfit
        stopLossPrice = curr_Ask - self.config_data.stopLoss
        trade_result = self.client.futures_create_order(
                symbol=pair,
                type=self.client.FUTURE_ORDER_TYPE_MARKET,
                side="BUY",
                quantity=float(amount),
                positionSide="LONG"
            )
        self.positiondatabase.AddPosition(trade_result)

    def SellOrder(self, pair: str, curr_Ask: float):
        amount = self.GetQuantityPrecised(curr_Ask, self.config_data.stakeAmount)
        takeProfitPrice = curr_Ask + self.config_data.takeProfit
        stopLossPrice = curr_Ask - self.config_data.stopLoss

        trade_result = self.client.futures_create_order(
                symbol=pair,
                type=self.client.FUTURE_ORDER_TYPE_MARKET,
                side="SELL",
                quantity=float(amount),
                positionSide="SHORT"
            )
        self.positiondatabase.AddPosition(trade_result)

    def CloseBuyOrder(self, pair, quantity: float):
        result = self.client.futures_create_order(
            symbol=pair,
            type=self.client.FUTURE_ORDER_TYPE_MARKET,
            quantity=round(quantity, self.pairQuantityPrecision),
            side=self.client.SIDE_BUY,
            positionSide="SHORT"
        )
        print(result)

    def CloseSellOrder(self, pair, quantity: float):
        result = self.client.futures_create_order(
            symbol=pair,
            type=self.client.FUTURE_ORDER_TYPE_MARKET,
            side=self.client.SIDE_SELL,
            quantity=round(quantity,self.pairQuantityPrecision),
            positionSide= "LONG",
        )
        print(result)

    def GetQuantityPrecised(self, price, stakeAmount):
        quantity = round(stakeAmount/price,self.pairQuantityPrecision)
        return quantity


class OrdersDatabaseMgt:
    def __init__(self, client):
        self.trades_dataframe_path = os.path.join(database_folder,"positions.csv")
        self.trades_df: pd.DataFrame = None
        self.client: Client = client
        columns = [

        ]
        
        self.trades_df = pd.DataFrame(columns=columns)

    def AddPosition(self, orders_info: dict):
        columns_availabel = self.trades_df.columns
        new_position = pd.DataFrame(columns=columns_availabel)
        for label in orders_info.keys():
            if label in columns_availabel:
                new_position[label] = orders_info.get(label)
        
        print(new_position)
        self.trades_df = pd.concat([self.trades_df, new_position],axis=0).reset_index(drop=True)
        print(self.trades_df)
        
    def GetPositions(self, type:str, is_open=True):
        positions = self.client.futures_position_information()
        print(positions)
        # positionsdf = self.trades_df.loc[
        #     (self.trades_df['side']==type.upper())
        #     &(self.trades_df.status=='active' if is_open else 'closed')
        # ]
        # return positionsdf
    
    def GetPositionsCount(self, type:str, is_open=True):
        positionsdfcount = self.trades_df.loc[
            (self.trades_df['side']==type.upper())
            &(self.trades_df.status==('active' if is_open else 'closed'))
        ].shape[0]
        return positionsdfcount
    