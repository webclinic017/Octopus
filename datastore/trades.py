import datetime

import pandas as pd
from ib_insync import Stock

import sqlalchemy
from sqlalchemy.orm import Session
from sqlalchemy.sql.base import Executable
from sqlalchemy.sql.sqltypes import Float
from sqlalchemy import Table, Column, Integer, String, MetaData, Date, DateTime, func
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Trade(Base):
    __tablename__ = 'trades'
   
    instanceID = Column(String, primary_key=True)
    tradeID = Column(Integer, primary_key=True)

    strategy = Column(String)

    symbol = Column(String)
    primaryExchange = Column(String)
    longName = Column(String)
    industry = Column(String)
    category = Column(String)
    subcategory = Column(String)

    earningsDate = Column(Date)
    earningsTiming = Column(String)

    status = Column(String) # Open or Closed
    
    openDateTime = Column(DateTime)
    closeDateTime = Column(DateTime)

    buyPrice = Column(Float)
    sellPrice = Column(Float)
    profitUSD = Column(Float)
    profitPCT = Column(Float)



class ContractDetailMock:
    longName = ""
    industry = ""
    category = "" 
    subcategory = ""


class TradeCache:

    def __init__(self, octopus):
        print("Initializing Trade Cache")
        self.sql_engine = sqlalchemy.create_engine('sqlite:///datastore/trades.db', echo = False)
        Base.metadata.create_all(self.sql_engine)

        self.octopus = octopus

    
    def GetOpenTrades(self):
        result = {}
        with Session(self.sql_engine) as session:
            openTrades = session.query(Trade).filter(Trade.instanceID == self.octopus.instanceID, Trade.status == "Open").all()
            for trade in openTrades:

                result[trade.symbol] = self._convert(trade)
        return result

    def _convert(self, trade):

        detail = ContractDetailMock()
        detail.longName = trade.longName
        detail.industry = trade.industry
        detail.category = trade.category
        detail.subcategory = trade.subcategory

        return {
            'symbol': trade.symbol,
            'primaryExchange': trade.primaryExchange,

            'contract': Stock(trade.symbol, "SMART", "USD", primaryExchange=trade.primaryExchange),
            'detail': detail,

            'tradeID': trade.tradeID,

            'earningsDate': trade.earningsDate,
            'earningsTiming': trade.earningsTiming,      

            'status': trade.status,

            'openDateTime': trade.openDateTime,
            'closeDateTime': trade.closeDateTime,
            
            'buyPrice': trade.buyPrice,
            'sellPrice': trade.sellPrice,

            'profitUSD': trade.profitUSD,
            'profitPCT': trade.profitPCT
        }        

    def OpenTrade(self, target):
        result = target

        symbol = target['symbol']
        if symbol in self.GetOpenTrades():
            raise Exception(f"Symbol {symbol} already found in Open Trades when trying to open a new order")

        with Session(self.sql_engine) as session:

            tradeID = session.query(func.max(Trade.tradeID)).filter(Trade.instanceID == self.octopus.instanceID).scalar()
            if tradeID == None:
                tradeID = 0
            else:
                tradeID += 1

            tradedb = Trade()
            tradedb.instanceID = self.octopus.instanceID
            tradedb.tradeID = tradeID
            tradedb.strategy = self.octopus.strategy.Name
            tradedb.symbol = target['symbol']
            tradedb.primaryExchange = target['contract'].primaryExchange
            tradedb.longName = target['detail'].longName
            tradedb.industry = target['detail'].industry
            tradedb.category = target['detail'].category
            tradedb.subcategory = target['detail'].subcategory
            tradedb.earningsDate = target['earningsDate']
            tradedb.earningsTiming = target['earningsTiming']

            tradedb.status = "Open"
            tradedb.buyPrice = target['currentPrice']
            tradedb.openDateTime = self.octopus.currentInterval

            session.add(tradedb)
            session.commit()

            result['status'] = tradedb.status
            result['buyPrice'] = tradedb.buyPrice
            result['openDateTime'] = tradedb.openDateTime

        return result

    def CloseTrade(self, trade):
        result = trade
        with Session(self.sql_engine) as session:
            
            tradedb = session.query(Trade).filter(Trade.instanceID == self.octopus.instanceID, Trade.status == "Open", Trade.tradeID == trade['tradeID']).one()

            tradedb.status = "Closed"
            tradedb.closeDateTime = self.octopus.currentInterval
            tradedb.sellPrice = trade['currentPrice']
            tradedb.profitUSD = tradedb.sellPrice - tradedb.buyPrice
            tradedb.profitPCT = round((tradedb.profitUSD / tradedb.sellPrice) * 100, 2)

            result['status'] = tradedb.status
            result['closeDateTime'] = tradedb.closeDateTime
            result['sellPrice'] = tradedb.sellPrice
            result['profitUSD'] = tradedb.profitUSD
            result['profitPCT'] = tradedb.profitPCT
            
            session.commit()

        return result
        

