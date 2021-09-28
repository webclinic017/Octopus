import datetime

import pandas as pd

import sqlalchemy
from sqlalchemy.orm import Session
from sqlalchemy.sql.sqltypes import Float
from sqlalchemy import Table, Column, Integer, String, MetaData, Date
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class TargetCacheItem(Base):
    __tablename__ = 'targetCache'
   
    date = Column(Date, primary_key=True)
    symbol = Column(String, primary_key=True)
    primaryExchange = Column(String)
    longName = Column(String)
    industry = Column(String)
    category = Column(String)
    subcategory = Column(String)
    # earningsDate = Column(Date)
    # earningsTiming = Column(String)



class ContractDetailMock:
    longName = ""
    industry = ""
    category = "" 
    subcategory = ""

#    startdatetime = Column(String)
#    companyshortname = Column(String)
#    startdatetimetype = Column(String)
#    epsestimate = Column(Float)
#    epsactual = Column(Float)
#    epssurprisepct = Column(Float)
#    timeZoneShortName = Column(String)
#    gmtOffsetMilliSeconds = Column(Integer)
#    quoteType = Column(String)
#    index = Column(Integer)


class TargetCache:

    def __init__(self):
        print("Initializing Target Cache")
        self.sql_engine = sqlalchemy.create_engine('sqlite:///datastore/target_cache.db', echo = False)
        Base.metadata.create_all(self.sql_engine)
    
    def GetTargetCache(self, date): # Date Object
        result = {}
        with Session(self.sql_engine) as session:
            targetCacheList = session.query(TargetCacheItem).filter(TargetCacheItem.date == date).all()
            for targetCache in targetCacheList:

                detail = ContractDetailMock()
                detail.longName = targetCache.longName
                detail.industry = targetCache.industry
                detail.category = targetCache.category
                detail.subcategory = targetCache.subcategory

                result[targetCache.symbol] = {
                    'primaryExchange': targetCache.primaryExchange,
                    'detail': detail,
                    # 'earningsDate': targetCache.earningsDate,
                    # 'earningsTiming': targetCache.earningsTiming
                }

        return result

    def SaveTargetCache(self, date, targetDict): # Date Object
        with Session(self.sql_engine) as session:
            for symbol, target in targetDict.items():

                targetCache = TargetCacheItem()
                targetCache.date = date
                targetCache.symbol = symbol
                targetCache.primaryExchange = target['contract'].primaryExchange
                targetCache.longName = target['detail'].longName
                targetCache.industry = target['detail'].industry
                targetCache.category = target['detail'].category
                targetCache.subcategory = target['detail'].subcategory
                
                # targetCache.earningsDate = target['earningsDate']
                # targetCache.earningsTiming = target['earningsTiming']
                session.add(targetCache)

            session.commit()       

    def RemoveTargetsFromCache(self, date, symbols):
        with Session(self.sql_engine) as session:
            for symbol in symbols:
                session.query(TargetCacheItem).filter(TargetCacheItem.date == date, TargetCacheItem.symbol == symbol).delete()

            session.commit()


#e = EarningsCalendarGrabber()
#print(e.GetEarnings("2021-08-12"))