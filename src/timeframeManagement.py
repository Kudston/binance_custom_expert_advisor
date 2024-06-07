
class TimeframeMgt:
    def __init__(self,timeframe: str, timeframes: dict) -> None:
        self.timeframe = timeframe
        self.timeframes = timeframes

    def GetTimeframeSeconds(self)->int:
        timecat = str(self.timeframe)[-1:]
        if timecat=="s":
            return int(str(self.timeframe)[:-1])
        elif timecat=="m":
            return int(str(self.timeframe)[:-1])*60
        elif timecat=="h":
            return int(str(self.timeframe)[:-1])*60*60
        elif timecat=="d":
            return int(str(self.timeframe)[:-1])*86400
        elif timecat=="W":
            return int(str(self.timeframe)[:-1])*86400*7
        ##using the number of days a month could have
        elif timecat=="M":
            return int(str(self.timeframe)[:-1])*86400*28