import datetime

import pandas as pd

import sqlalchemy
from sqlalchemy.orm import Session
from sqlalchemy.sql.sqltypes import Float
from sqlalchemy import Table, Column, Integer, String, MetaData, Date
from sqlalchemy.ext.declarative import declarative_base

import yahoo_fin.stock_info as si

Base = declarative_base()

class Earnings(Base):
   __tablename__ = 'earnings'
   
   erDate = Column(Date, primary_key=True)
   ticker = Column(String, primary_key=True)
   startdatetime = Column(String)
   companyshortname = Column(String)
   startdatetimetype = Column(String) # BMO = Before Market Open, AMC = After Market Close, TNS = Time Not Supplied
   epsestimate = Column(Float)
   epsactual = Column(Float)
   epssurprisepct = Column(Float)
   timeZoneShortName = Column(String)
   gmtOffsetMilliSeconds = Column(Integer)
   quoteType = Column(String)
   index = Column(Integer)


class EarningsCalendar:

    def __init__(self):
        print("Initializing Earnings Calendar Store")
        self.sql_engine = sqlalchemy.create_engine('sqlite:///datastore/earnings_calendary.db', echo = False)
        Base.metadata.create_all(self.sql_engine)
    
    def GetEarnings(self, erDate): # "2021-08-10"
        earningsDate = datetime.datetime.strptime(erDate, "%Y-%m-%d")

        with Session(self.sql_engine) as session:
            count = session.query(Earnings).filter(Earnings.erDate == earningsDate).count()

            if (count == 0):
                df = pd.DataFrame(si.get_earnings_for_date(erDate))
                df["erDate"] = earningsDate
                df.drop_duplicates(subset="ticker", inplace=True )
                df.to_sql('earnings', self.sql_engine, if_exists='append')

            
            query = session.query(Earnings).filter(Earnings.erDate == earningsDate)
            return pd.read_sql(query.statement, query.session.bind)

#e = EarningsCalendarGrabber()
#print(e.GetEarnings("2021-08-12"))