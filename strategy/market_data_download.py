
class MarketDataDownloader:

    def __init__(self, octopus):
        self.octopus = octopus

        self.Name = "Market data download"
        self.BackTestFrequency = 60
        
        self.NotifyTargets = True
        
        self.SkipTradeLogic = True   

        


    def buy_signal(self, target):
        pass

    def sell_signal(self, target):
        pass    