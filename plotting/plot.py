
from datetime import datetime, timedelta, time

# Mat Plot Lib Finance (Plotting)
import mplfinance as mpf

import pandas
import numpy as np


class Plotter:

    def __init__(self, octopus):
        self.octopus = octopus

    def GenerateChart(self, symbol, dataFrame, barSize, length, target=None):

        #https://github.com/matplotlib/mplfinance/blob/master/examples/styles.ipynb

        # Market Colors
        mc = mpf.make_marketcolors(
            base_mpf_style='nightclouds',
            up='#26A69A', 
            down='#EF5350',
            inherit=True)

        
        # https://matplotlib.org/stable/api/matplotlib_configuration_api.html#matplotlib.rcParams
        overrides = {
            # 'figure.facecolor':'#182533' #0e1621
            'savefig.facecolor': '#182533',
            'savefig.dpi': 200,
            'savefig.bbox': 'tight',
            'savefig.pad_inches': 0.3
        }


        # Build Style
        s = mpf.make_mpf_style(
            base_mpf_style='nightclouds', 
            marketcolors=mc,
            rc=overrides,
            gridcolor='#232632',
            gridstyle='-',
            facecolor='#151924' # behind main axes
        )


        # TradingView Standard Colors https://kodify.net/tradingview/colours/basic-colours/
        aqua = "#00BCD4"
        blue = "#2196F3"
        teal = "#00897B"
        green = "#4CAF50"
        olive = "#808000"
        lime = "#00E676"
        yellow = "#FFEB3B"
        orange = "#FF9800"
        maroon = "#880E4F"
        red = "#FF5252"
        fuchsia = "#E040FB"
        purple = "#9C27B0"
        navy = "#311B92"
        black = "#363A45"
        gray = "#787B86"
        silver = "#B2B5BE"
        white = "#FFFFFF"

        addplotdict = []

        if barSize in ('1 day'):
            # Filter Data
            # df = dataFrame[dataFrame.date <= self.currentInterval.date()] # Should already have occured in the Technical Analysis function
            # df = dataFrame.tail(length)

            df = dataFrame.tail(length)

            # Add Custom Plots
            if 'SMA_10' in df.columns: 
                addplotdict.append(mpf.make_addplot(df['SMA_10'], color=red, width=0.8))
            if 'SMA_20' in df.columns: 
                addplotdict.append(mpf.make_addplot(df['SMA_20'], color=orange, width=0.8))
            if 'SMA_50' in df.columns: 
                addplotdict.append(mpf.make_addplot(df['SMA_50'], color=yellow, width=0.8))
            if 'SMA_100' in df.columns: 
                addplotdict.append(mpf.make_addplot(df['SMA_100'], color=lime, width=0.8))
            if 'SMA_150' in df.columns: 
                addplotdict.append(mpf.make_addplot(df['SMA_150'], color=blue, width=0.8))            

            title = f"{symbol} Daily ({length} days)"

        elif barSize == "15 mins":
            # Filter Data
            df = dataFrame[dataFrame.date <= self.octopus.currentInterval.replace(tzinfo=None)]
            startDateTime = self.octopus.currentInterval.replace(tzinfo=None) - timedelta(days=length) 
            df = dataFrame[dataFrame.date >= startDateTime]

            # Add Custom Plots
            addplotdict.append(mpf.make_addplot(df['EMA_10'], color='#c000c0', width=0.8))

            title = f"{symbol} 15m ({length} days)"

        elif barSize == "5 mins":

            # Filter Data
            df = dataFrame[dataFrame.date <= self.octopus.currentInterval.replace(tzinfo=None)]

            days_df = dataFrame.mdDate.drop_duplicates().tail(length)
            if not days_df.empty:
                startDateTime = datetime.combine(days_df[0], datetime.min.time())
            else:
                startDateTime = self.octopus.currentInterval.replace(tzinfo=None) - timedelta(days=length) 


            df = dataFrame[dataFrame.date >= startDateTime]

            # Add Custom Plots
            # addplotdict.append(mpf.make_addplot(df['EMA_10'], color='#c000c0', width=0.8))

            title = f"{symbol} 5m ({length} days)"

        if target != None:

            if 'earningsDate' in target:
                high = df['high'].max()
                low = df['low'].min()
                if (barSize == "1 day"):
                    high = self._getMax(df, 'SMA_10', high)
                    high = self._getMax(df, 'SMA_20', high)
                    high = self._getMax(df, 'SMA_50', high)
                    high = self._getMax(df, 'SMA_100', high)
                    high = self._getMax(df, 'SMA_150', high)
                    low = self._getMin(df, 'SMA_10', low)
                    low = self._getMin(df, 'SMA_20', low)
                    low = self._getMin(df, 'SMA_50', low)
                    low = self._getMin(df, 'SMA_100', low)
                    low = self._getMin(df, 'SMA_150', low)               
                diff = high - low
                yPos = low - (diff * 0.05)

                earningsTiming = target['earningsTiming']
                timingColourDict = {
                    'BMO': blue,
                    'TNS': green,
                    'TAS': yellow,
                    'AMC': red
                }
                earningsSignal = self._populateEarningsSignal(target, barSize, df, yPos)
                addplotdict.append(mpf.make_addplot(earningsSignal, type='scatter', markersize=50, marker='$E$', color=timingColourDict[earningsTiming]))


            if 'openDateTime' in target:
                tradeOpenSignal = self._populateTradeOpenSignal(target, barSize, df)
                addplotdict.append(mpf.make_addplot(tradeOpenSignal, type='scatter', markersize=20, marker='^', color=blue))

            if 'closeDateTime' in target:
                tradeCloseSignal = self._populateTradeCloseSignal(target, barSize, df)
                addplotdict.append(mpf.make_addplot(tradeCloseSignal, type='scatter', markersize=20, marker='v', color=orange))
        

        df.index = pandas.DatetimeIndex(df['date'])
        mpf.plot(df, 
            type='candle',
            volume=True,
            savefig='plot.jpg',
            style=s,
            figratio=(15,11),
            figscale=0.9,
            title=title,
            addplot=addplotdict)



    def _getMax(self, df, key, currentMax):
        if key in df:
            try:
                tmp = df[key].max()
                return max(currentMax, tmp) 
            except:
                return currentMax
        else:
            return currentMax
    
    def _getMin(self, df, key, currentMin):
        if key in df:
            try:
                tmp = df[key].min()
                return min(currentMin, tmp)
            except:
                return currentMin 
        else:
            return currentMin 

        
    def _populateEarningsSignal(self, target, barSize, df, yPos):
        signal   = []
        earningsDate = target['earningsDate']
        earningsTiming = target['earningsTiming']
        found = False
        for date, date2 in df['date'].iteritems():

            if not found:
                if barSize == "1 day":
                    found = date >= earningsDate
                else:
                    earningsTiming = target['earningsTiming']
                    if earningsTiming == "AMC":
                        
                        found = (date.date() >= earningsDate)
                        if found:
                            dateMin = datetime.combine(date.date(), datetime.min.time())
                            dateMax = datetime.combine(date.date(), datetime.max.time())
                            tmp_df = df[df.date >= dateMin]
                            tmp_df = tmp_df[tmp_df.date <= dateMax]
                            found = date == tmp_df.iloc[-1]['date']
                            

                    else:
                        found = date.date() >= earningsDate

                if found:
                    signal.append(yPos)
                else:
                    signal.append(np.nan)
                
            else:
                signal.append(np.nan)
        return signal

    def _populateTradeOpenSignal(self , target, barSize, df):
        signal   = []
        openDateTime = target['openDateTime']
        buyPrice = target['buyPrice']
        found = False
        for date, date2 in df['date'].iteritems():

            if not found:
                if barSize == "1 day":
                    found = date >= openDateTime.date()
                else:
                    found = date >= openDateTime

                if found:
                    signal.append(buyPrice)
                else:
                    signal.append(np.nan)
                
            else:
                signal.append(np.nan)
        return signal

    def _populateTradeCloseSignal(self , target, barSize, df):
        signal   = []
        closeDateTime = target['closeDateTime'].replace(tzinfo=None)
        sellPrice = target['sellPrice']
        found = False
        for date, date2 in df['date'].iteritems():

            if not found:
                if barSize == "1 day":
                    found = date >= closeDateTime.date()
                else:
                    found = date >= closeDateTime

                if found:
                    signal.append(sellPrice)
                else:
                    signal.append(np.nan)
                
            else:
                signal.append(np.nan)
        return signal

        