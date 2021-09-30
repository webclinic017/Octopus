from dateutil.relativedelta import relativedelta


class StrategyScanEarners:

    def __init__(self, octopus):
        self.octopus = octopus

        self.Name = "Scan for Earners"
        self.BackTestFrequency = 60
        self.BackTestValidTimes = ["10:00"]

        self.NotifyLoading = True
        self.NotifyStopping = True
        self.NotifyExceptions = True
        self.NotifyTWSUnexpectedErrors = True
        
        self.NotifyTargets = False
        self.NotifyNoPermissions = True
        self.NotifyRecentlyListedRemoved = True
        self.NotifyMissing5MData = True

        self.NotifyNewDay = True

        self.SkipTradeLogic = False
        self.NotifyGapUps = False

        self.NotifyTradeOpen = True
        self.NotifyTradeClose = True
        self.NotifyTradeClose1dLengths = [100]
        self.NotifyTradeClose5mLengths = []
        self.NotifyTradeCloseOnlyOnProfit = True
        self.NotifyTradeCloseOnlyOnProfitPercentMinimum = 20



    def buy_signal(self, target):
        buy = (self.octopus.currentInterval.replace(tzinfo=None) <= target['5m_ta'].iloc[-1].date)
        buy = buy and len(target['1d_ta']) > 30        
        return buy
             
    def sell_signal(self, openTrade):
        return (self.octopus.currentInterval.replace(tzinfo=None) >= (openTrade['openDateTime']) + relativedelta(days=14))