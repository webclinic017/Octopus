
from datetime import timedelta, datetime

import pandas as pd
from ib_insync import *
from pandas.core.frame import DataFrame

import sqlalchemy
from sqlalchemy.orm import Session
from sqlalchemy.sql.sqltypes import Float
from sqlalchemy import Table, Column, Integer, String, MetaData, Date, DateTime
from sqlalchemy.ext.declarative import declarative_base


Base = declarative_base()

class CacheLookup(Base):
    __tablename__ = 'marketDataCacheLookup'

    mdDate = Column(Date, primary_key=True)
    symbol = Column(String, primary_key=True)
    barSize = Column(String, primary_key=True)

class MarketData(Base):
    __tablename__ = 'marketData'

    mdDate = Column(Date, primary_key=True)
    symbol = Column(String, primary_key=True)
    barSize = Column(String, primary_key=True)    

    date = Column(DateTime, primary_key=True)
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float)
    volume = Column(Integer)
    average = Column(Float)
    barCount = Column(Integer)
    index = Column(Integer)

class MarketDataDaily(Base):
    __tablename__ = 'marketDataDaily'

    mdDate = Column(Date, primary_key=True)
    symbol = Column(String, primary_key=True)
    barSize = Column(String, primary_key=True)    

    date = Column(Date, primary_key=True)
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float)
    volume = Column(Integer)
    average = Column(Float)
    barCount = Column(Integer)
    index = Column(Integer)    


class MarketDataGrabber:

    def __init__(self, octopus):
        print("Initializing Market Data Collector")

        self.octopus = octopus

        self.debug = False

        self.sql_engine = sqlalchemy.create_engine('sqlite:///datastore/market_data.db', echo = False)
        Base.metadata.create_all(self.sql_engine)

        self.session = Session(self.sql_engine)



    def _attemptBulkCacheLoad(self, target, barSize, effectiveDate, days):
        symbol = target['symbol']
        if self.debug:
            print(f"Checking Cache for {symbol}")

        result = DataFrame()

        isToday = effectiveDate == self.octopus.GetToday()
        if not isToday:

            startDate = effectiveDate - timedelta(days=days-1) # Used to have a -1 here, but seems wrong. No, cancel that, it's right!
            # with Session(self.sql_engine) as session:
            count = self.session.query(CacheLookup).\
                    filter(CacheLookup.mdDate >= startDate).\
                    filter(CacheLookup.mdDate <= effectiveDate).\
                    filter(CacheLookup.symbol == target['symbol']).\
                    filter(CacheLookup.barSize == barSize).\
                    count()

            if count == days:

                if self.debug:
                    print(f"Bulk Cache located for {symbol}")

                if barSize in ('1 day'):
                    cls = MarketDataDaily
                else:
                    cls = MarketData

                query = self.session.query(cls).\
                    filter(cls.mdDate >= startDate).\
                    filter(cls.mdDate <= effectiveDate).\
                    filter(cls.symbol == target['symbol']).\
                    filter(cls.barSize == barSize).\
                    order_by(cls.mdDate, cls.index)
                result = pd.read_sql(query.statement, query.session.bind)

                if self.debug:
                    print(f"Bulk load complete")

        return result        


    def LoadBatchMarketData(self, target, barSize, effectiveDate, days, limit=10): # effectiveDate must be Date, not DateTime.
        symbol = target['symbol']
        if self.debug:
            print(f"Loading Batch Market Data for {symbol}")

        result = DataFrame()
        
        df = self._attemptBulkCacheLoad(target, barSize, effectiveDate, days)
        if not df.empty:
            if self.debug:
                print(f"Found Bulk Cached data for {barSize}, {symbol}, {effectiveDate.strftime('%Y-%m-%d')} ({days} days)")
            result = df
        else:


            # Bulk load failed. Perhaps it's trying to look at a date from today's real date, in which case try and bulk load from yesterday and back
            isToday = effectiveDate == self.octopus.GetToday()
            if isToday and (days > 1):
                df = self._attemptBulkCacheLoad(target, barSize, effectiveDate - timedelta(days=1), days-1)

            if not df.empty:
                print(f"Found Bulk Cached data for {barSize}, {target['symbol']}, {(effectiveDate - timedelta(days=1)).strftime('%Y-%m-%d')} ({days-1} days)")
                result = df

                # Trigger a load of just today
                aDate = effectiveDate
            else:
                # Gotta load each day individually :(
                aDate = effectiveDate - timedelta(days=days-1)

            while (aDate <= effectiveDate) and (not self.octopus.noMarketDataPermission):

                isToday = aDate == self.octopus.GetToday()                
                if isToday:
                    if self.debug:
                        print("Forcing download, todays date")
                    result = result.append(self.LoadMarketData(target, barSize, aDate)) # Will trigger an API Download
                    break # Assume this is the end of the batch load. Never going to get dates in the future

                    
                # Check Cache
                inCache = self._isInCache(aDate, target['symbol'], barSize)
                if inCache:
                    if self.debug:
                        print("Found Cached Date, triggering Cached Load")
                    result = result.append(self.LoadMarketData(target, barSize, aDate)) # Will trigger a Cached Load
                    aDate = aDate + timedelta(days=1)

                else:

                    # Batch Download of "limit" days
                    daysToLoad = 0
                    dayList = []
                    while (aDate <= effectiveDate) and (daysToLoad < limit):

                        isToday = aDate == self.octopus.GetToday()
                        if isToday:
                            break

                        inCache = self._isInCache(aDate, target['symbol'], barSize)
                        if inCache:
                            if self.debug:
                                print("Found Cached Item while bulk loading. May occur when loading more historic data than usual")
                            break


                        daysToLoad += 1
                        dayList.append(aDate)
                        aDate = aDate + timedelta(days=1)
                    
                    # Bulk load
                    df = self._getOHLCV(target, barSize, aDate - timedelta(days=1), daysToLoad)
                    if (not self.octopus.noMarketDataPermission):
                        if not df.empty:
                            for index in df.index:
                                date = df.loc[index, 'date']
                                if isinstance(date, datetime):
                                    df.loc[index, 'mdDate'] = date.date()
                                else:
                                    df.loc[index, 'mdDate'] = date
                            df['symbol'] = target['symbol']
                            df['barSize'] = barSize

                            # Add to result
                            result = result.append(df)

                        # Save to Cache
                        for day in dayList:

                            # Check Cache
                            inCache = self._isInCache(day, target['symbol'], barSize)
                            if not inCache:

                                # Filter by day
                                if not df.empty:
                                    day_df = df[df['mdDate'] == day]

                                    # Add to Cache
                                    if not day_df.empty:

                                        tmp = day_df.copy()
                                        del tmp['date']
                                        if barSize in ('1 day'):
                                            tmp.to_sql('marketDataDaily', self.sql_engine, if_exists='append')
                                        else:
                                            tmp.to_sql('marketData', self.sql_engine, if_exists='append')
                                        
                                self._saveCacheLookup(day, target['symbol'], barSize)    

        if not result.empty:
            result.index = pd.DatetimeIndex(result['date'])    
            result["volume"] = result.volume.astype(int)
        return result     
            

                
    def _isInCache(self, date, symbol, barSize):
        # with Session(self.sql_engine) as session:
        count = self.session.query(CacheLookup).\
            filter(CacheLookup.mdDate == date).\
            filter(CacheLookup.symbol == symbol).\
            filter(CacheLookup.barSize == barSize).\
            count()
        return count == 1

    def _saveCacheLookup(self, date, symbol, barSize):
        # with Session(self.sql_engine) as session:
        lookup = CacheLookup()
        lookup.mdDate = date
        lookup.symbol = symbol
        lookup.barSize = barSize
        self.session.add(lookup)
        self.session.commit()

    def DeleteFromCache(self, symbol):
        # with Session(self.sql_engine) as session:
        self.session.query(CacheLookup).filter_by(symbol=symbol).delete()
        self.session.query(MarketDataDaily).filter_by(symbol=symbol).delete()
        self.session.query(MarketData).filter_by(symbol=symbol).delete()
        self.session.commit()




    def LoadMarketData(self, target, barSize, effectiveDate): #date object

        isToday = effectiveDate == self.octopus.GetToday()

        # with Session(self.sql_engine) as session:

        inCache = False
        if not isToday:
            
            inCache = self._isInCache(effectiveDate, target['symbol'], barSize)

        if inCache:
            
            #Load from Cache
            if self.debug:
                print(f"Found Cached data for {barSize}, {target['symbol']}, {effectiveDate.strftime('%Y-%m-%d')}")

            if barSize in ('1 day'):
                cls = MarketDataDaily
            else:
                cls = MarketData

            query = self.session.query(cls).\
                filter(cls.mdDate == effectiveDate).\
                filter(cls.symbol == target['symbol']).\
                filter(cls.barSize == barSize).\
                order_by(cls.mdDate, cls.index)
            df = pd.read_sql(query.statement, query.session.bind)

        else:

            # Get Live Data from TWS
            df = self._getOHLCV(target, barSize, effectiveDate)
            if not df.empty:
                df['mdDate'] = effectiveDate
                df['symbol'] = target['symbol']
                df['barSize'] = barSize


            if (not isToday) and (not df.empty):

                # Save to Cache

                if self.debug:
                    print(df)
                    print("\n")

                tmp = df.copy()
                del tmp['date']
                if barSize in ('1 day'):
                    tmp.to_sql('marketDataDaily', self.sql_engine, if_exists='append')
                else:
                    tmp.to_sql('marketData', self.sql_engine, if_exists='append')
                self._saveCacheLookup(self.session, effectiveDate, target['symbol'], barSize)


        if not df.empty:
            df.index = pd.DatetimeIndex(df['date'])    
        return df


    #https://interactivebrokers.github.io/tws-api/historical_bars.html
    def _getOHLCV(self, target, barSize, endDate, days=1):
        symbol = target["symbol"]

        if self.debug:
            print(f"TWS: Downloading {barSize} Market Data for {symbol}. Date: {endDate.strftime('%Y-%m-%d')}. Days: {days}")

        startDate = endDate - timedelta(days-1)

        businessDays = 0
        aDate = startDate
        while aDate <= endDate:
            if aDate.weekday() not in (5, 6):
                businessDays += 1
            aDate = aDate + timedelta(days=1)

        data = {}

        if businessDays > 0:


            
            

            attempt = 1
            success = False

            while (attempt <= 3) and (not success):

                self.octopus.marketDataQueryFailed = False

                data = self.octopus.ib.reqHistoricalData(
                        target["contract"],
                        endDateTime=endDate.strftime('%Y%m%d 23:59:59'), #yyyyMMdd HH:mm:ss’
                        durationStr=f"{businessDays} D",
                        barSizeSetting=barSize,
                        whatToShow='TRADES',
                        useRTH=True,
                        formatDate=1
                    )

                success = not self.octopus.marketDataQueryFailed
                attempt += 1

                if self.octopus.marketDataQueryFailed:
                    print(f'Retrying, attempt... {attempt-1}')
                    self.octopus.ib.sleep(300)

            if not success:
                raise Exception("Failed downloading candle data, Query Cancel limit reached")



        if len(data) == 0:
            return DataFrame()
        else:
            df = util.df(data)
            df.index = pd.DatetimeIndex(df['date'])
            if barSize in ('1 day'):
                df = df[df.date >= startDate]
            else:
                df = df[df.date >= datetime.combine(startDate, datetime.min.time())]


            return df