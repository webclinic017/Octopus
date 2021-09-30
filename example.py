from octopus import Octopus

from strategy.market_data_download import MarketDataDownloader
from strategy.scan_earners import StrategyScanEarners
from strategy.earnings_breakouts import StrategyEarningsBreakouts


settings = {

    # Give each instance of the bot, a unique name.
    "INSTANCEID": "Example Name",

    # Trader Workstation (TWS) Settings
    "TWS":
        {
            "HOST": "127.0.0.1",
            "PORT": 7496, # Paper defaults to 7497
            "CLIENTID": 1000, #this needs to be a unique value for each bot instance. Chose a widely different value between bot instances, as each time a connection is retried, it's incremented by one.
            "MAXRETRY": 100
        },

    # Discord Notifications
    "DISCORD":
        {
            "TOKEN": "", # You can optionally setup a Discord Bot, and insert it's Token here to have Discord Chat Notifications enabled
            "CHANNEL": 0 # Channel to send alerts to
        },

    # Telegram Notifications
    "TELEGRAM":
        {
            "TOKEN": "", # You can optionally setup a Telegram Bot, and insert it's Token here to have Telegram Chat Notifications enabled
            "CHANNEL": 0 # Chat to send alerts to
        }
}

octopus = Octopus(settings)

# Main Strategy
octopus.run(StrategyEarningsBreakouts) # Live mode
# octopus.run(StrategyEarningsBreakouts, backTest=True, backTestDateStartStr="2021-01-1", backTestDateEndStr="2021-01-10")


# Scan for market earners, will always buy on earnings, and then detect the ones which were profitable, selling a week later, or when the stoploss triggers
# octopus.run(StrategyScanEarners, backTest=True, backTestDateStartStr="2021-01-1", backTestDateEndStr="2021-03-1")
# octopus.run(StrategyScanEarners, backTest=True, backTestDateStartStr="2021-08-4", backTestDateEndStr="2021-08-4")


# Use this to download Market Data only (Useful to run prior to backtesting)
# octopus.run(MarketDataDownloader, backTest=True, backTestDateStartStr="2021-06-9", backTestDateEndStr="2021-09-1")

