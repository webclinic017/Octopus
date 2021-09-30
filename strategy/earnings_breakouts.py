


class StrategyEarningsBreakouts:

    def __init__(self, octopus):
        self.octopus = octopus

        self.Name = "Earnings Breakouts"
        self.BackTestFrequency = 5
        self.BackTestValidTimes = ["10:00"]
        
        self.NotifyLoading = True
        self.NotifyStopping = True
        self.NotifyExceptions = True
        self.NotifyTWSUnexpectedErrors = True

        self.NotifyTargets = True
        self.NotifyTargetsLong = False
        self.NotifyNoPermissions = True
        self.NotifyRecentlyListedRemoved = True
        self.NotifyMissing5MData = True

        self.NotifyNewDay = True

        self.SkipTradeLogic = False
        self.NotifyGapUps = True

        self.NotifyTradeOpen = True
        self.NotifyTradeClose = True
        self.NotifyTradeClose1dLengths = [100]
        self.NotifyTradeClose5mLengths = []
        self.NotifyTradeCloseOnlyOnProfit = False
        self.NotifyTradeCloseOnlyOnProfitPercentMinimum = 20


    def buy_signal(self, target):
        return False


    def sell_signal(self, openTrade):
        pass