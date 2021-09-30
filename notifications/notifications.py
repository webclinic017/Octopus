
from notifications.telegram_notifications import TelegramBot
from notifications.discord_notifications import DiscordBot
from plotting.plot import Plotter

from datetime import datetime, timedelta, time
from dateutil.relativedelta import relativedelta
import traceback


# Emojis
# https://apps.timwhitlock.info/emoji/tables/unicode

class Notifier:

    def __init__(self, octopus):
        self.octopus = octopus
        self.plotter = Plotter(octopus)
        self.Start()

    def Start(self):
        if self.octopus.settings["TELEGRAM"]["TOKEN"] != "":
            self.telegramBot = TelegramBot(self.octopus)
            self.telegramBot.Start()

        if self.octopus.settings["DISCORD"]["TOKEN"] != "":
            self.discordBot = DiscordBot(self.octopus)
            self.discordBot.Start()

    def Stop(self):
        if self.octopus.settings["TELEGRAM"]["TOKEN"] != "":
            self.telegramBot.Stop()

        if self.octopus.settings["DISCORD"]["TOKEN"] != "":
            self.discordBot.Stop()


    # Send Messages / Media

    def SendNotification(self, msg):
        if self.octopus.settings["TELEGRAM"]["TOKEN"] != "":
            self.telegramBot.SendNotification(msg)

        if self.octopus.settings["DISCORD"]["TOKEN"] != "":
            self.discordBot.SendNotification(msg)

    def SendImage(self, imageLocation):

        if self.octopus.settings["TELEGRAM"]["TOKEN"] != "":
            self.telegramBot.SendImage(imageLocation)

        if self.octopus.settings["DISCORD"]["TOKEN"] != "":
            self.discordBot.SendImage(imageLocation)


    # Bot Start / Stop

    def NotifyLoading(self):
        if self.octopus.strategy.NotifyLoading:
            self.SendNotification(f"\U0001F419 Octopus Bot loading!\n  └  Strategy - {self.octopus.strategy.Name}")                

    def NotifyStopping(self):
        if self.octopus.strategy.NotifyStopping:
            self.SendNotification(f"Octopus Bot is stopping, see ya! \U0000270C") 

    def NotifyBackTestingStart(self, fromDateStr, toDateStr):
        self.SendNotification(f"\U0001F3AC Back Testing from {fromDateStr} to {toDateStr}")                            

    def NotifyBackTestingEnd(self):
        self.SendNotification(f"\U0001F3C1 Back Testing Completed")             


    # Exceptions / Errors

    def NotifyException(self, exceptionMessage):
        
        if self.octopus.strategy.NotifyExceptions:
            self.SendNotification("\U000026D4 Unexpected exception\!")
            self.SendNotification(f"```\n{exceptionMessage}\n```")

        print(exceptionMessage)

    def NotifyEarningsWhileClosed(self, symbol, primaryExchange):
        if self.octopus.strategy.NotifyExceptions:
            self.SendNotification(f"{symbol} ({primaryExchange}) is closed today\. Earnings Report outside normal market hours\n")

    def NotifyTWSError(self, errorCode, errorString):
        if self.octopus.strategy.NotifyTWSUnexpectedErrors:
            self.SendNotification(f"Unexpected TWS Error Detected, Error Code: {errorCode}\n\n```{errorString}```\n")

    def NotifyFailedTechnicalAnalysis(self, symbol, task):
        if self.octopus.strategy.NotifyExceptions:
            self.SendNotification(f"Failed Technical Analysis on {symbol}, failed task: {task}")


    # Describing Stocks

    def NotifyEarningsTargets(self, count, messageStr):
        if self.octopus.strategy.NotifyTargets:
            todayStr = self.octopus.currentInterval.date().strftime("%Y-%m-%d")
            if count == 0:
                msg = f"\U0001F4C5 No earnings targets found for {todayStr}"
            else:
                msg = f"\U0001F4C5 Found {count} earnings targets for {todayStr}\n{messageStr}"
                self.SendNotification(msg)

    def NotifyEarningsTargetsShort(self):
        if self.octopus.strategy.NotifyTargets:
            self.SendNotification(self.GetEarningsTargetsShort())

    def GetEarningsTargetsShort(self):
        msg = f"Found {len(self.octopus.targetDict)}/{len(self.octopus.earningsTargets)} Symbols from Calendar"
        for industry in sorted(self.octopus.industryDict.keys()):
            symbols = sorted(self.octopus.industryDict[industry])
            msg +=f"\n\n{self._getIndustryDesc(industry)}\n  └ {' '.join(symbols)}"

        if len(self.octopus.pinkSymbols) > 0:
            msg+= f"\n\n\U0001F6AF Ignored {len(self.octopus.pinkSymbols)} OTC (PINK) stocks:\n  └ {' '.join(self.octopus.pinkSymbols)}"        

        if len(self.octopus.unknownSymbols) > 0:
            msg+= f"\n\n\U00002753 Could not find {len(self.octopus.unknownSymbols)} stocks:\n  └ {' '.join(self.octopus.unknownSymbols)}"
        return msg

    def NotifyEarningsTargetsLong(self):
        if self.octopus.strategy.NotifyTargetsLong:
            self.SendNotification(self.GetEarningsTargetsLong())        

    def GetEarningsTargetsLong(self):
        msg = f"Found {len(self.octopus.targetDict)}/{len(self.octopus.earningsTargets)} Symbols from Calendar"
    
        for industry in sorted(self.octopus.industryDict.keys()):
            symbols = sorted(self.octopus.industryDict[industry])
            msg += f"\n\n{self._getIndustryDesc(industry)}"
            for symbol in symbols:
                if symbol in self.octopus.targetDict:
                    msg += f"\n\n{self._getTargetDesc(self.octopus.targetDict[symbol])}"

        if len(self.octopus.pinkSymbols) > 0:
            msg+= f"\n\n\U0001F6AF Ignored {len(self.octopus.pinkSymbols)} OTC (PINK) stocks:\n  └ {' '.join(self.octopus.pinkSymbols)}"        

        if len(self.octopus.unknownSymbols) > 0:
            msg+= f"\n\n\U00002753 Could not find {len(self.octopus.unknownSymbols)} stocks:\n  └ {' '.join(self.octopus.unknownSymbols)}"

        return msg

    def _getIndustryDesc(self, industry):
        emoji = ""
        emojis = {
            "Utilities": "\U0001F50C ",
            "Financial": "\U0001F4B5 ",
            "Consumer, Non-cyclical": "\U0001F37A ",
            "Consumer, Cyclical": "\U0001F45F ",
            "Basic Materials": "\U0001F5FB ",
            "Communications": "\U0001F4E1 ",
            "Energy": "\U000026A1 ",
            "Industrial": "\U0001F3ED ",
            "Technology": "\U0001F4F1 ",
            "Diversified": "\U0001F4CA ",
            "Government": "\U0001F47A ",
            "": "\U00002754 " #Unknown
        }
        if industry in emojis.keys():
            emoji = emojis[industry]

        if industry == "":
            industry = "Unknown"
        return f"{emoji}{industry}" 

    def _getTargetDesc(self, target):
        msg = f"[{target['symbol']}] {target['detail'].longName} ({target['contract'].primaryExchange})"
        
        if target['detail'].industry != "":
            msg += f"\n └ {target['detail'].category} - {target['detail'].subcategory}"
        
        return msg

    def _getTargetDescLong(self, target, includeGap=False):
        msg = f"[{target['symbol']}] {target['detail'].longName} ({target['contract'].primaryExchange})"
        
        if target['detail'].industry != "":
            msg += f"\n └ {self._getIndustryDesc(target['detail'].industry)}"
            msg += f"\n  └ {target['detail'].category} - {target['detail'].subcategory}"
        
        msg += f"\n"

        adrStr = "{:.1f}%".format(target['adr'])
        msg += f"\n ADR: {adrStr}"

        if includeGap:
            gapStr = "{:.2f}%".format(target['gap_pc'])
            yesterdayClose = "${:.2f}".format(target['yesterday_close'])
            todayOpen = "${:.2f}".format(target['today_open'])
                
            msg += "\n"
            msg += f"\n Gap: {gapStr}"
            msg += f"\n Yesterday Close: {yesterdayClose}"
            msg += f"\n Today Open: {todayOpen}"
        
        if 'earningsDate' in target:
            earningsDateStr = target['earningsDate'].strftime("%Y-%m-%d")
            earningsTiming = target['earningsTiming']

            timingDescDict = {
                'AMC': "After Market Close",
                'TAS': "Transfer Agent System",
                'TNS': "Time Not Specified",
                'BMO': "Before Market Opens"

            }
            earningsTimingDesc = timingDescDict[earningsTiming]

            msg += "\n"
            msg += f"\n Earnings Date: {earningsDateStr}"
            msg += f"\n Earnings Timing: {earningsTimingDesc}"

        if 'status' in target:
            
            msg += "\n"
            msg += f"\n Trade Status: {target['status']}"
            openDateStr = target['openDateTime'].strftime("%Y-%m-%d %H:%M:%S")
            msg += f"\n Open Date: {openDateStr}"
            if 'closeDateTime' in target:
                closeDateStr = target['closeDateTime'].strftime("%Y-%m-%d %H:%M:%S")
                msg += f"\n Close Date: {closeDateStr}"
                msg += "\n"
                msg += f"\n Buy Price: {target['buyPrice']}"
            if 'sellPrice' in target:
                msg += f"\n Sell Price: {target['sellPrice']}"
                msg += f"\n Profit: {target['profitPCT']}"

        return msg


    # Misc Events

    def NotifyNewDay(self):
        if self.octopus.strategy.NotifyNewDay:
            self.SendNotification(f"\U0001F5FD Goodmorning NY: {self.octopus.currentTick.strftime('%a %d %B, %H:%M:%S')}")

    def NotifyESTTime(self):
        self.SendNotification(self.GetESTTime())

    def GetESTTime(self):
        return f"\U0001F5FD NY Time: {self.octopus.currentTick.strftime('%a %d %B, %H:%M:%S')}"
    
    
    def NotifyEarningTargetsMarketState(self):
        self.SendNotification(self.GetEarningTargetsMarketState())
    
    def GetEarningTargetsMarketState(self):
        tomorrow = datetime.combine(self.octopus.currentTick, time(tzinfo=self.octopus.timezone)) + timedelta(days=1) 
        rdtomorrow = relativedelta(tomorrow, self.octopus.currentTick)

        if len(self.octopus.targetDict) > 0:

            close_times = []
            open_times = []
            for symbol, target in self.octopus.targetDict.items():
                close_times.append(target["market_close_time"])
                open_times.append(target["market_open_time"])        
            open_time = min(open_times)
            close_time = max(close_times)
            
            rdopen = relativedelta(open_time, self.octopus.currentTick)
            rdclose = relativedelta(close_time, self.octopus.currentTick)
            
            if self.octopus.marketOpen:
                msg = f"Markets are Open \U00002615"
                msg += f"\n  └  Monitoring {len(self.octopus.targetDict)} stocks"
                msg += f"\n  └  Markets closing in  {rdclose.hours} hours, {rdclose.minutes} minutes"
                
            else:

                if self.octopus.currentInterval < open_time:
                    msg = f"Markets are Closed \U0000231B\n  └  Markets opening in  {rdopen.hours} hours, {rdopen.minutes} minutes"
                else: 
                    msg = f"Markets are Closed \U0000231B\n  └  Midnight in {rdtomorrow.hours} hours, {rdtomorrow.minutes} minutes"
        else:
            msg = f"No Earnings occuring today.  \U0000231B\n  └  Midnight in {rdtomorrow.hours} hours, {rdtomorrow.minutes} minutes"

        return msg





    def NotifyNoPermissions(self, symbols):
        if self.octopus.strategy.NotifyNoPermissions:
            self.SendNotification(f"\U0001F46E No Market Data Permissions for the following {len(symbols)} stocks\n └ {' '.join(symbols)}")

    def NotifyRecentlyListedRemoved(self, symbols):
        if self.octopus.strategy.NotifyRecentlyListedRemoved:
            self.SendNotification(f"\U0001F51E Removed {len(symbols)} recently listed stocks\n └ {' '.join(symbols)}")

    def NotifyMissing5MData(self, symbols):
        if self.octopus.strategy.NotifyMissing5MData:
            self.SendNotification(f"\U0001F51E Removed {len(symbols)} stocks with incomplete 5M data\n └ {' '.join(symbols)}")


    # Target Gapped Up

    def NotifyTargetGapUp(self, target):
        if self.octopus.strategy.NotifyGapUps:
            gapUpStr = "{:.2f}".format(target['gap_pc'])
            msg = f"{target['symbol']} has gapped up {gapUpStr}% pre-market:"
            msg += f"\n\n{self._getTargetDescLong(target, includeGap=True)}\n"
            self.SendNotification(msg)
            self.NotifyPlot(target['symbol'], target['1d_ta'], '1 day', 75, target=target)
            self.NotifyPlot(target['symbol'], target['5m_ta'], '5 mins', 6, target=target)


    # Buy / Sell triggered

    def NotifyTradeOpen(self, symbol, trade):
        if self.octopus.strategy.NotifyTradeOpen:
            msg = f"Opening trade: {symbol}\n"
            msg += f"\n"
            msg += f"{self._getTargetDescLong(trade)}"
            self.SendNotification(msg)

            # self._notifyPlot(symbol, target['1d_ta'], '1 day', 365, target=target)
            self.NotifyPlot(symbol, trade['1d_ta'], '1 day', 75, target=trade)
            self.NotifyPlot(symbol, trade['5m_ta'], '5 mins', 6, target=trade)

    def NotifyTradeClose(self, symbol, trade):
        notify = self.octopus.strategy.NotifyTradeClose
        if notify:
            if self.octopus.strategy.NotifyTradeCloseOnlyOnProfit:
                notify = self.octopus.strategy.NotifyTradeCloseOnlyOnProfitPercentMinimum <= trade['profitPCT']

        if notify:
            
            msg = f"Closing trade: {symbol}\n"
            msg += f"\n"
            msg += f"{self._getTargetDescLong(trade)}"
            self._notify(msg)

            for days in self.octopus.strategy.NotifyTradeClose1dLengths:
                self.NotifyPlot(symbol, trade['1d_ta'], '1 day', days, target=trade)

            for days in self.octopus.strategy.NotifyTradeClose5mLengths:
                self.NotifyPlot(symbol, trade['5m_ta'], '5 mins', days, target=trade)


    def NotifyPlot(self, symbol, dataFrame, barSize, length, target=None):

        print(f"Sending Plot for {symbol}, {barSize}, {length} days")
        try:
            self.plotter.GenerateChart(symbol, dataFrame, barSize, length, target)
            self.SendImage("plot.jpg")
        except:
            self.NotifyException(traceback.format_exc())

