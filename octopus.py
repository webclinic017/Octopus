import threading
import traceback
import time as t
import re #regular expression
from pytz import timezone
import datetime as dt
from datetime import datetime, timedelta, time

# Third Party
from ib_insync import IB, Stock

# Technical Analysis
import pandas
from pandas.core.frame import DataFrame
import pandas_ta as ta


# Custom
from datastore.earnings_calendar import EarningsCalendar
from datastore.market_data import MarketDataGrabber
from datastore.target_cache import TargetCache
from datastore.trades import TradeCache

from notifications.notifications import Notifier


HOURS_OF_OPERATION_START = 9 # 9 AM
HOURS_OF_OPERATION_END = 17 # 5 PM

MINIUMUM_DAILY_CANDLES = 10
MINIUMUM_5M_CANDLES = 78

class Octopus:

    def __init__(self, settings):

        self.settings = settings

    def _clean(self):

        print("Cleaning up")
        # Don't clean these, it will break the main loop
        # All Datetimes
        #self.lastTick = -1         
        #self.lastInterval = -1     
        #self.currentTick = -1  
        #self.currentInterval = -1

        self.frequency = 5 #mins
        
        
        self.targetDict = {}
        # key = symbol
        # value = {
        #   'symbol':   'AMZN'
        #   'contract': <object>,
        #   'detail': <object>,
        #   'market_state': "Open" #or "Closed"
        #   'market_open_today': True/False
        #   'market_open_time': DateTime
        #   'market_close_time': DateTime
        #
        #   'earningsDate': DateTime
        #   'earningsTiming': DateTime
        #
        #   '1d': DataFrame
        #   '15m: DataFrame
        #   'gap_pc': float - Gap Up/Down Percentage 
        #   'gap_notified': True/False - Has notified via Telegram
        # }

        self.industryDict = {}
        # key = industry
        # value = ["symbol", "symbol"]

        self.unknownSymbols = []
        self.pinkSymbols = []
        self.noMarketDataPermissionSymbols = []

        self.earningsTargets = {} #dataframe

        self.marketOpen = False
        self.twsConnectionLost = False
        self.apiLimitReached = False 
        self.noMarketDataPermission = False


    def run(self, strategy, backTest=False, backTestDateStartStr="", backTestDateEndStr=""):
        self.backTest = backTest
        self.strategy = strategy(self)

        self.timezone = timezone('EST')
        self.twsRetryCount = 0
        self.twsClientID = self.settings["TWS"]["CLIENTID"]

        instanceID = self.settings["INSTANCEID"]
        if self.backTest:
            nowStr = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            self.instanceID = f"{instanceID} {nowStr}"

            self.backTestDateStart = datetime.now().strptime(backTestDateStartStr, "%Y-%m-%d").replace(tzinfo=self.timezone)
            self.backTestDateEnd = datetime.now().strptime(backTestDateEndStr, "%Y-%m-%d").replace(tzinfo=self.timezone)
            self.backTestError = False
        else:
            self.instanceID = instanceID


        self.lastTick = -1
        self.lastInterval = -1

        self.polling_thread = None
        self.message_queue = []

        while True:

            self.ib = None
            
            self.earningsCalendar = EarningsCalendar()
            self.marketDataGrabber = MarketDataGrabber(self)
            self.trades = TradeCache(self)

            if self.backTest:
                self.targetCache = TargetCache()

            if not self.backTest:
                self.lastTick = -1
                self.lastInterval = -1

            try:
                self._clean()
                self._connectTWS()

                self.notifier = Notifier(self)
                self.ib.sleep(5) # Give Discord/Telegram some time to load
                self.notifier.NotifyLoading()
                
                # Bot Loop
                while (True):
                    
                    firstLoad = self.lastTick == -1
                    firstInterval = self.lastInterval == -1

                    if self.backTest:
                        if firstLoad:

                            self.notifier.NotifyBackTestingStart(backTestDateStartStr, backTestDateEndStr)
                            self.currentTick = datetime.combine(self.backTestDateStart, time(tzinfo=self.timezone)) 
                        else:

                            if self.backTestError:
                                self.backTestError = False
                            else:
                                self.currentTick = self.lastTick + timedelta(minutes = self.strategy.BackTestFrequency)
                                if self.currentTick >= (self.backTestDateEnd + timedelta(days=1)):
                                    self.notifier.NotifyBackTestingEnd()
                                    break

                    else:
                        self.currentTick = datetime.now(self.timezone)

                    self.currentInterval = self.currentTick - timedelta(
                        minutes=self.currentTick.minute % self.frequency,
                        seconds=self.currentTick.second,
                        microseconds=self.currentTick.microsecond)

                    
                    newDay = firstLoad or (self.lastTick.date() != self.currentTick.date())

                    if firstLoad and not self.backTest:
                        self.notifier.NotifyESTTime()

                    elif newDay and (not self.backTest):
                        self.notifier.NotifyNewDay()                    
                    
                    # Load Earnings Targets
                    if newDay:
                        self._clean()                        
                    if firstLoad or newDay:
                        self._identifyEarningsTargets()
                    
                        if len(self.earningsTargets) > 0:
                            # Load Targets
                            self._loadTargets(allowCache=self.backTest)
                            self.notifier.NotifyEarningsTargetsShort()
                            self.notifier.NotifyEarningsTargetsLong()

                            # Load Market Data
                            self._loadMarketData()    
                            if self.apiLimitReached:
                                raise Exception("API Limit Reached")
                            if self.twsConnectionLost:
                                raise Exception("TWS Connection Lost")

                    
                    if firstInterval or (self.currentInterval > self.lastInterval):

                        # New Interval!
                        print(f"Processing Interval: {self.currentInterval.strftime('%a %d %B, %H:%M:%S')}")
                        self.lastInterval = self.currentInterval

                        # Check Market State
                        if not self.backTest:
                            market_open = False
                            for symbol, target in self.targetDict.items():
                                if ('market_open_today' in target) and ('market_close_time' in target):
                                    market_open = target['market_open_today'] and self.currentInterval >= target['market_open_time'] and self.currentInterval < target['market_close_time']
                                    if market_open:
                                        break
                            if (self.marketOpen != market_open) or (self.lastTick == -1):
                                self.marketOpen = market_open
                                self.notifier.NotifyEarningTargetsMarketState()
                            else:
                                self.marketOpen = market_open

                            if self.marketOpen:

                                # Update Market Data
                                self._loadMarketData()

                        else:
                            # Backtesting - no way to know when markets open, so use some logic here, and the strategy config
                            market_open = HOURS_OF_OPERATION_START <= self.currentInterval.hour <= HOURS_OF_OPERATION_END
                            market_open = market_open and self.IsBusinessDay(self.currentInterval.date())

                            if market_open:
                                if len(self.strategy.BackTestValidTimes) > 0:
                                    market_open = self.currentInterval.strftime("%H:%M") in self.strategy.BackTestValidTimes

                        if market_open:
                            # Perform Trading Logic
                            if not self.strategy.SkipTradeLogic:
                                self._technicalAnalysis()

                                self._notifyTargetGapUps()

                                self._processSellSignals()
                                self._processBuySignals()


                    
                    # Process Messages
                    if not self.backTest:
                        while len(self.message_queue) > 0:

                            msg = self.message_queue.pop(0)
                            self._processTBotMessage(msg)

                    self.lastTick = self.currentTick

                    if not self.backTest:
                        self.ib.sleep(1)

                # Bot Loop End, requires a Break to get here
                if self.backTest:
                    if (self.currentTick >= self.backTestDateEnd):
                        break

            
            except (KeyboardInterrupt, SystemExit):
                self._disconnectTWS()
                self.notifier.NotifyStopping()
                self.notifier.Stop()
                
            except:
                print("Unexpected exception")
                self.notifier.NotifyException(traceback.format_exc())
                self.notifier.Stop()
                self._disconnectTWS()
                
                if self.backTest:
                    self.backTestError = True

                print(f"Waiting {self.frequency} Minutes")
                self.ib.sleep(60 * self.frequency)
                
                
                self.twsRetryCount += 1
                if self.twsRetryCount > self.settings["TWS"]["MAXRETRY"]:
                    break # Exit Python
                self.twsClientID += 1
                


    def _connectTWS(self):
        print("Connecting to TWS API")
        self.ib = IB()
        self.ib.errorEvent += self.onErrorEvent                
        self.ib.connect(host=self.settings["TWS"]["HOST"], port=self.settings["TWS"]["PORT"], clientId=self.twsClientID, timeout=600)

    def _disconnectTWS(self):
        print("Disconnecting from TWS API")
        try:
            self.ib.disconnect()
        except:
            pass


    # Error Codes -> #https://interactivebrokers.github.io/tws-api/message_codes.html
    def onErrorEvent(self, reqId, error_code, error_string, contract):
        
        # Warnings / Notifications
        if (error_code in [2104, 2106, 2158, 2103, 2105, 1102]):
            print(f"TWS API Notification: {error_string}")

        # Expected/Handled Errors
        elif (error_code == 200):
            self.stockNotFound = True

        elif (error_code == 162):
            if "HMDS query returned no data" in error_string:
                pass #This is normal, when there's no data for a particular day yet. If run just after midnight, before market open this occurs. Seems to occur for PINK stocks more regularly.

            elif "API historical data query cancelled" in error_string:
                print(f"TWS API Notification, Error Code: {error_code}, Error String: {error_string}")
                self.marketDataQueryFailed = True                

            else:
                self.noMarketDataPermission = True
                if "Historical data request pacing violation" in error_string:
                    self.apiLimitReached = True            
        
        elif (error_code == 1100):
            self.twsConnectionLost = True

        else:
            self.notifier.NotifyTWSError(error_code, error_string)
            raise Exception


    def _identifyEarningsTargets(self):
        today = self.currentInterval.date()
        if (self.IsBusinessDay(today)):
            lastBusinessDay = today - timedelta(days=1)
            while not self.IsBusinessDay(lastBusinessDay):
                lastBusinessDay = lastBusinessDay - timedelta(days=1)

            earningsTargets = DataFrame()

            aDate = lastBusinessDay
            count = 0
            msg = ""
            while aDate <= today:
                
                dateStr = aDate.strftime("%Y-%m-%d")
                earnings = self.earningsCalendar.GetEarnings(dateStr)
                count += len(earnings)

                if len(earnings) > 0:
                    if aDate == lastBusinessDay:
                        earnings = earnings[earnings.startdatetimetype.isin(['AMC'])] 

                        if len(earnings) > 0:
                            earningsTargets = earningsTargets.append(earnings)
                            msg += f"\n  └  {dateStr} - {len(earnings)} after market"

                    elif aDate < today:
                        earningsTargets = earningsTargets.append(earnings)
                        msg += f"\n  └  {dateStr} - {len(earnings)} while market was closed"

                    else:
                        earnings = earnings[earnings.startdatetimetype.isin(['BMO', 'TNS'])] 
                        if len(earnings) > 0:    
                            earningsTargets = earningsTargets.append(earnings)
                            msg += f"\n  └  {dateStr} - {len(earnings)} pre market/unknown time"

                aDate = aDate + timedelta(days=1)

            self.notifier.NotifyEarningsTargets(count, msg)

            self.earningsTargets = earningsTargets


    def _loadTargets(self, allowCache=False):
        
        symbols = self.earningsTargets['ticker']
        print(f'Loading {len(symbols)} symbols')

        loadFromTWS = True
        if allowCache:
            targetCacheDict = self.targetCache.GetTargetCache(self.currentInterval.date())
            loadFromTWS = len(targetCacheDict) == 0

        if not loadFromTWS:

            # Found in cache, load from Cache (Only while backtesting)
            
            for symbol in symbols:
                if '-' not in symbol: # Fixes a bug when symbols have a hyphen
                    if symbol in targetCacheDict:
                        targetCache = targetCacheDict[symbol]

                        # Load from Target Cache
                        detail = targetCache['detail']
                        contract = Stock(symbol, "SMART", "USD", primaryExchange=targetCache['primaryExchange'])

                        earningsItem = self.earningsTargets[self.earningsTargets.ticker == symbol].iloc[0]
                        earningsDate = earningsItem.erDate
                        earningsTiming = earningsItem.startdatetimetype

                        target = self._createTarget(symbol, contract, detail, earningsDate=earningsDate, earningsTiming=earningsTiming)

                        self.targetDict[symbol] = target

                        if detail.industry not in self.industryDict.keys():
                            self.industryDict[detail.industry] = []
                        self.industryDict[detail.industry].append(target['symbol'])
                        
                        print(f"Loaded From Cache - {symbol}: {detail.longName} ({contract.primaryExchange}) ({detail.industry} - {detail.category} - {detail.subcategory})")
                    else:
                        self.unknownSymbols.append(symbol)

        else:

            for symbol in symbols:
                if '-' not in symbol: # Fixes a bug when symbols have a hyphen
                    
                    self.stockNotFound = False
                    try:
                        contract = Stock(symbol, "SMART", "USD")
                        detail = self.ib.reqContractDetails(contract)[0]
                        contract = Stock(symbol, "SMART", "USD", primaryExchange=detail.contract.primaryExchange)
                    except:
                        if (self.stockNotFound): 
                            print(f"Could not load Symbol: {symbol}")
                            self.unknownSymbols.append(symbol)
                        else:
                            raise

                    if (not self.stockNotFound):

                        if detail.contract.primaryExchange == "PINK":
                            print(f"Symbol {symbol} is PINK")
                            self.pinkSymbols.append(symbol)

                        else:

                            earningsItem = self.earningsTargets[self.earningsTargets.ticker == symbol].iloc[0]
                            earningsDate = earningsItem.erDate
                            earningsTiming = earningsItem.startdatetimetype

                            target = self._createTarget(symbol, contract, detail, earningsDate=earningsDate, earningsTiming=earningsTiming)
                            
                            print(f"Found {symbol}: {detail.longName} ({contract.primaryExchange}) ({detail.industry} - {detail.category} - {detail.subcategory})")

                            # Check Timezone
                            if detail.timeZoneId != "US/Eastern":
                                raise Exception(f"Unexpected Timezone: {detail.timeZoneId}")


                            # Parse Hours. Find Today, and get open/close time (if market is open)
                            days = detail.liquidHours.split(';')
                            # 20210811:0930-20210811:1600
                            # 20210812:0930-20210812:1600
                            # 20210813:0930-20210813:1600
                            # 20210814:CLOSED
                            # 20210815:CLOSED
                            # 20210816:0930-20210816:1600        
                            tickday = self.currentTick.strftime("%Y%m%d")
                            
                            target['market_open_today'] = False

                            for day in days:
                                slist = day.split('-')
                                start = slist[0]
                                startparts = start.split(':')
                                if startparts[0] == tickday:

                                    if startparts[1] == "CLOSED":
                                        
                                        # Reporting earnings when the market is closed? Odd situation, treat like an exception for now (Probably needs to be improved, as not taking into acount public holidays)
                                        self.notifier.NotifyEarningsWhileClosed(symbol, contract.primaryExchange)
                                        
                                    else:
                                        target['market_open_today'] = True
                                        end = slist[1]
                                        endparts = end.split(':')
                                        target['market_open_time'] = self.currentTick.replace(hour=int(startparts[1][0:2]), minute=int(startparts[1][2:]), second=0, microsecond=0)
                                        target['market_close_time'] = self.currentTick.replace(hour=int(endparts[1][0:2]), minute=int(endparts[1][2:]), second=0, microsecond=0)

                                        print(f"{symbol} ({contract.primaryExchange}) is open today - {target['market_open_time']} - {target['market_close_time']}\n")

                                    break
                            
                            #print(f"Min Tick: {detail.minTick}")
                            
                            self.targetDict[symbol] = target

                            if detail.industry not in self.industryDict.keys():
                                self.industryDict[detail.industry] = []
                            self.industryDict[detail.industry].append(target['symbol'])
            
            if allowCache and len(self.targetDict) > 0:
                self.targetCache.SaveTargetCache(self.currentInterval.date(), self.targetDict)

    def _createTarget(self, symbol, contract, detail, earningsDate=None, earningsTiming=""):
        return { 
            "symbol": symbol,
            "contract": contract,
            "detail": detail,

            "earningsDate": earningsDate,
            "earningsTiming": earningsTiming,

            "gap_pc": 0,
            "gap_notified": False,
        }


    def GetMidnight(self, date):
        return datetime.combine(date, datetime.min.time()).replace(tzinfo=self.timezone)

    def GetToday(self):
        return datetime.now(self.timezone).date()

    def IsBusinessDay(self, aDate):
        return (aDate.weekday() not in (5, 6))


    def _loadMarketData(self):
        print("Loading Market Data\n\n")
        start = t.time()
        for symbol, target in self.targetDict.items():
            self._loadMarketDataTarget(target)
            
        if not self.apiLimitReached and not self.twsConnectionLost:

            # Remove Targets which are missing permissions
            removalList = []
            for badSymbol in self.noMarketDataPermissionSymbols:
                if badSymbol in self.targetDict.keys():
                    removalList.append(badSymbol)
                    del self.targetDict[badSymbol]
            if len(removalList) > 0:
                self.notifier.NotifyNoPermissions(removalList)

                if self.backTest:
                    self.targetCache.RemoveTargetsFromCache(self.currentInterval.date(), removalList)


            # Remove Targets which have insufficient daily candle data
            removalList = []
            for symbol, target in list(self.targetDict.items()):
                print(f"Checking {symbol} 1D data validity")
                df = target['1d']
                if df.empty or (len(df) < MINIUMUM_DAILY_CANDLES):
                    removalList.append(symbol)
                    del self.targetDict[symbol]
            if len(removalList) > 0:
                self.notifier.NotifyRecentlyListedRemoved(removalList)

                if self.backTest:
                    self.targetCache.RemoveTargetsFromCache(self.currentInterval.date(), removalList)            


            # Remove Targets which have insufficient 5M candle data
            removalList = []
            for symbol, target in list(self.targetDict.items()):
                print(f"Checking {symbol} 5M data validity")
                df = target['5m']
                if df.empty or (len(df) < MINIUMUM_5M_CANDLES):
                    removalList.append(symbol)
                    del self.targetDict[symbol]
            if len(removalList) > 0:
                self.notifier.NotifyMissing5MData(removalList)

                if self.backTest:
                    self.targetCache.RemoveTargetsFromCache(self.currentInterval.date(), removalList)  

            
            end = t.time()
            delta = end - start
            print("Took %.2f seconds to process\n" % delta)

    def _checkMarketDataForDuplicates(self, target, df, desc):
        dupes = df[df.duplicated(['date'])]
        if not dupes.empty:
            raise Exception(f"Duplicated {desc} OHLCV data found for {target['symbol']}")
        


    def _loadMarketDataTarget(self, target):
        symbol = target['symbol']
        print(f"\nLoading data for {symbol}")

        if (not self.twsConnectionLost) and (not self.apiLimitReached):                

            target['1d'] = DataFrame()
            target['5m'] = DataFrame()
            # target['15m'] = DataFrame()
            
            self.noMarketDataPermission = False
            df = self.marketDataGrabber.LoadBatchMarketData(target, "1 day", self.currentInterval.date(), 330, limit=30)
            if not df.empty:
                target['1d'] = df.copy()
                self._checkMarketDataForDuplicates(target, target['1d'], "1 day")


            if (not self.noMarketDataPermission):
                df = self.marketDataGrabber.LoadBatchMarketData(target, "5 mins", self.currentInterval.date(), 10, limit=2)
                if not df.empty:
                    target['5m'] = df.copy()
                    self._checkMarketDataForDuplicates(target, target['5m'], "5 min")                          

            # if (not self.noMarketDataPermission):
            #     df = self.marketDataGrabber.LoadBatchMarketData(target, "15 mins", self.currentInterval.date(), 3, limit=5)
            #     if not df.empty:
            #         target['15m'] = target['15m'].append(df)                    

            if self.noMarketDataPermission:
                self.noMarketDataPermissionSymbols.append(symbol)
                print(f"No Market Data Permission for {symbol}\n")


    def _technicalAnalysis(self):
        for symbol, target in list(self.targetDict.items()):
            self._technicalAnalysisTarget(target)

    def _technicalAnalysisTarget(self, target):
        symbol = target['symbol']
        print(f"Performing Technical Analysis on {symbol}")

        try:
            task = "Loading"
            df_1D = target['1d'].copy()
            df_5M = target['5m'].copy()

            # df_15M = target['15m'].copy()
            # df_15M.index = pandas.DatetimeIndex(df_15M['date'])

            task = "Filtering"
            # Filter out dataframes later than the current interval
            df_1D = df_1D[df_1D['date'] <= self.currentInterval.date()] # Allow Partial Daily Candles
            df_5M = df_5M[df_5M['date'] <= self.currentInterval.replace(tzinfo=None)] 
            #df_15M = df_15M[df_15M['date'] <= self.currentInterval.replace(tzinfo=None)]

            
            if df_1D.empty:
                raise Exception(f"Symbol {symbol} empty 1d candle data")

            if df_5M.empty:
                raise Exception(f"Symbol {symbol} empty 5m candle data")

            target['currentPrice'] = df_5M.iloc[-1].close

            # Recreate the daily candle for today, based on todays 5m candles
            if self.backTest:
                task = "Recreating Last Daily Candle"
                aDate = self.currentInterval.date()
                aDateTime = self.GetMidnight(self.currentInterval).replace(tzinfo=None)
                df = df_5M[df_5M['date'] >= aDateTime]
                
                aggregation = { 
                    'open'  :'first',
                    'high'  :'max',
                    'low'   :'min',
                    'close' :'last',
                    'volume':'sum' 
                }
                df = df.resample('1D').agg(aggregation)
                if df.empty:
                    today_df = df_1D[df_1D['date'] == aDate]
                    if not today_df.empty:
                        df_1D = df_1D.drop(aDate)
                else:
                    df_1D.at[aDateTime, 'open'] = df.at[aDateTime, 'open']
                    df_1D.at[aDateTime, 'high'] = df.at[aDateTime, 'high']
                    df_1D.at[aDateTime, 'low'] = df.at[aDateTime, 'low']
                    df_1D.at[aDateTime, 'close'] = df.at[aDateTime, 'close']
                    df_1D.at[aDateTime, 'volume'] = df.at[aDateTime, 'volume']


            task = "Technical Analysis"

            # 1 Day
            # SMA_10
            df_1D.ta.sma(length=10, append=True)
            # SMA_20
            df_1D.ta.sma(length=20, append=True)
            # SMA_50
            df_1D.ta.sma(length=50, append=True)
            # SMA_100
            df_1D.ta.sma(length=100, append=True)
            # SMA_150
            df_1D.ta.sma(length=150, append=True)
            target['1d_ta'] = df_1D

            # 15 Min
            # EMA_10
            # df_15M.ta.ema(length=10, append=True)
            # target['15m_ta'] = df_15M

        
            # 5 Min
            target['5m_ta'] = df_5M



            # Calculate ADR
            # Regarding the ADR formula in TC2000; its using division to get a percent change each day. It adds up these percentage gains for last 20 periods, then divides the sum by 20 periods. Then it subtracts 1 from that number to have a decimal number. Then the decimal number is times by 100 to get it back into a full percentage.
            # 100*((H0/L0+H1/L1+H2/L2+H3/L3+H4/L4+H5/L5+H6/L6+H7/L7+H8/L8+H9/L9+H10/L10+H11/L11+H12/L12+H13/L13+H14/L14+H15/L15+H16/L16+H17/L17+H18/L18+H19/L19)/20-1)
            task = "Calculating ADR"
            pandas.set_option('mode.chained_assignment', None)
            # Get the last 20 days from a Pandas DataFrame containing daily OHLCV candle data (open, high, low, close, volume).
            df = df_1D.tail(20)
            # Get the range for each day, as a fractional value
            df['range_f'] = df['high'] / df['low']
            # Convert to Decimal
            df['range_px'] = 100 * (df['range_f'] - 1)
            adr = df['range_px'].mean() #Average
            
            target['adr'] = adr
            pandas.set_option('mode.chained_assignment', 'warn')




            # Get first candle of the current day
            task = "Loading 1D Open Candle"
            df = df_1D[df_1D.date == self.currentInterval.date()]
            if df.empty:
                print(f"Skipping {symbol}, no opening candle data")
            else:
                today_open = df.iloc[0]

                # Get last candle of the most recent day
                task = "Loading last 1D Close Candle"
                df_yesterday = df_1D[df_1D.date < self.currentInterval.date()]
                yesterday_close = df_yesterday.iloc[-1]


                target['yesterday_close'] = yesterday_close.close
                target['today_open'] = today_open.open

                gap = today_open.open - yesterday_close.close 
                target['gap_pc'] = (gap / yesterday_close.close) * 100.0

                # if gap > 3:
                #     print("test")

        except (KeyboardInterrupt):
            raise

        except:
            if target in self.targetDict:
                del self.targetDict[symbol]

            self.notifier.NotifyFailedTechnicalAnalysis(symbol, task)


            print(traceback.format_exc())

            self.notifier.NotifyException(traceback.format_exc())
                
        
    def _processBuySignals(self):
        for symbol, target in list(self.targetDict.items()):
            self._processBuySignalsTarget(target)

    def _processBuySignalsTarget(self, target):
        symbol = target['symbol']

        if symbol in self.trades.GetOpenTrades():
            print(f"Found open trade for {symbol}, removed from target dict")
            del self.targetDict[symbol]
        else:
            if self.strategy.buy_signal(target):

                trade = self.trades.OpenTrade(target)
                del self.targetDict[symbol]

                self.notifier.NotifyTradeOpen(symbol, trade)
                

    def _processSellSignals(self):
        openTrades = self.trades.GetOpenTrades()
        for symbol, trade in openTrades.items():
            self._processSellSignalsTrade(trade)

    def _processSellSignalsTrade(self, trade):
        symbol = trade['symbol']

        self._loadMarketDataTarget(trade)
        self._technicalAnalysisTarget(trade)
        if self.strategy.sell_signal(trade):

            closedTrade = self.trades.CloseTrade(trade)
            self.notifier.NotifyTradeClose(symbol, closedTrade)

    # todo - Respond to bot chart request
    def todoProcessChartRequest(self, msg):

        cleanedStr = re.sub(r'[^a-zA-Z0-9 ]', '', msg.strip()).split(' ')
        symbol = ""
        try:
            self.stockNotFound = False
            
            symbol = cleanedStr[0].upper()
            
            try:
                contract = Stock(symbol, "SMART", "USD")
                detail = self.ib.reqContractDetails(contract)[0]
                contract = Stock(symbol, "SMART", "USD", primaryExchange=detail.contract.primaryExchange)

                target = self._createTarget(symbol, contract, detail)


                # self._loadMarketDataTarget(target)

                target['1d'] = DataFrame()
                target['5m'] = DataFrame()

                self.noMarketDataPermission = False
                df = self.marketDataGrabber.LoadBatchMarketData(target, "1 day", self.currentInterval.date(), 360, limit=30)
                if not df.empty:
                    target['1d'] = df.copy()
                    self._checkMarketDataForDuplicates(target, target['1d'], "1 day")


                    df = self.marketDataGrabber.LoadBatchMarketData(target, "5 mins", self.currentInterval.date(), 10, limit=2)
                    if not df.empty:
                        target['5m'] = df.copy()

                    self._technicalAnalysisTarget(target)
                    # self._notifyPlot(symbol, target['1d_ta'], '1 day', 365)
                    self.GenerateChart(symbol, target['1d_ta'], '1 day', 150)
                    # self._notifyPlot(symbol, target['5m_ta'], '5 mins', 6)

                if self.noMarketDataPermission:
                    self.noMarketDataPermissionSymbols.append(symbol)
                    print(f"No Market Data Permission for {symbol}\n")

            except:
                if (self.stockNotFound): 
                    print(f"Could not load Symbol: {symbol}")
                    self.unknownSymbols.append(symbol)
                else:
                    self._notify(f"\U00002755 Unexpected error")

        except:
            self._notify(f"\U00002754 Unable to locate symbol {symbol}")


    def _notifyTargetGapUps(self):
        for symbol, target in self.targetDict.items():
            if not target['gap_notified']:
                if target['gap_pc'] >= 3:
                    self.notifier.NotifyTargetGapUp(target)
                    target['gap_notified'] = True

                   


    # def test(self):
    #     self.backTest = True
    #     self.timezone = timezone('EST')
        
    #     # target = { 
    #     #     'symbol': 'TSLA',
    #     #     'contract': Stock('TSLA', "SMART", "USD", primaryExchange="NASDAQ")       
    #     # }

    #     self._connectTWS()
    #     self.marketDataGrabber = MarketDataGrabber(self)
    #     # self.marketDataGrabber.DeleteFromCache("TSLA")
    #     # df = self.marketDataGrabber.LoadBatchMarketData(target, "15 mins", datetime.now(self.timezone).date(), 3)
    #     # self._disconnectTWS()

    #     self._clean()
        
    #     testDateStr = "20210802 09:45:00" 
    #     testSymbol = "GLT"

    #     self.currentInterval = datetime.strptime(testDateStr, '%Y%m%d %H:%M:%S').replace(tzinfo=self.timezone)

    #     target = { 
    #         'symbol': testSymbol,
    #         'contract': Stock(testSymbol, "SMART", "USD", primaryExchange="NASDAQ")       
    #     }
    #     self.targetDict[target['symbol']] = target

    #     # df = self.marketDataGrabber.LoadBatchMarketData(target, "1 day", aDate, 300, limit=100)
    #     self._loadMarketDataTarget(target)
    #     self._technicalAnalysisTarget(target)
    #     # self._notifyPlot(target['symbol'], df, "1 day", 60)