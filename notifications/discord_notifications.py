import discord
from discord.ext import commands
import asyncio

class DiscordBot:

    def __init__(self, octopus):
        self.octopus = octopus

    def Start(self):
        loop = asyncio.get_event_loop()
        print(f'Starting Discord Polling')
        help_command = commands.DefaultHelpCommand(
            no_category = 'Commands'
        )   
        self.discordClient = commands.Bot(command_prefix=commands.when_mentioned_or('$'), help_command=help_command)
        self._createActions()
        self.pollingTask = loop.create_task(self.discordClient.start(self.octopus.settings["DISCORD"]["TOKEN"]))
        print(f'Discord Polling Active')

    def Stop(self):
        print(f'Stopping Discord Polling')
        self.pollingTask.cancel()
        print(f'Telegram Discord Inactive')

    
    def _createActions(self):
        @self.discordClient.event
        async def on_ready():
            print(f'{self.discordClient.user} has connected to Discord!')

        # @self.discordClient.command()
        # async def test (ctx):
        #     msg = "The following commands are available: \n"
        #     msg += "  /market - Market state\n"
        #     msg += "  /time - Current NY (EST Time)\n"
        #     msg += "  /earnings - Todays Earnings calendar\n"
        #     msg += "  /earningslong - Todays Earnings calendar (long)\n"
        #     await ctx.send(msg)

        # time
        @self.discordClient.command(
            brief="gives the current EST Time",
            help="Output the Current New York (EST Time)"
            
        )
        async def time (ctx):
            await ctx.send(self.octopus.notifier.GetESTTime())

        # market
        @self.discordClient.command(
            brief="displays the current Market Open/Closed state",
            help="Output the current state of the market, and how long until it opens when applicable"
        )
        async def market (ctx):
            await ctx.send(self.octopus.notifier.GetEarningTargetsMarketState())

        # earnings
        @self.discordClient.command(
            brief="gives todays effective Earnings Calendar",
            help="Output a list of Stocks reporting earnings Today, or on the last previous days outside of hours"
        )
        async def earnings (ctx):
            await ctx.send(self.octopus.notifier.GetEarningsTargetsShort())

        # earnings_detailed
        @self.discordClient.command(
            brief="gives todays effective Earnings Calendar - With more detail",
            help="Output a list of Stocks reporting earnings Today, or on the last previous days outside of hours"
        )
        async def earnings_detailed (ctx):
            await ctx.send(self.octopus.notifier.GetEarningsTargetsLong())

        # chart
        @self.discordClient.command(
            brief="display a chart for the given stock",
            help="Displays a chart for the given stock"
        )
        async def chart (ctx, symbol):
            await ctx.send(self.octopus.notifier.GetEarningsTargetsLong())  



    def SendNotification(self, msg):
        channel = self.discordClient.get_channel(self.octopus.settings["DISCORD"]["CHANNEL"])
        future = channel.send(msg)
        loop = asyncio.get_event_loop()
        loop.run_until_complete(future)
        # print(future.result())

    def SendImage(self, imageLocation):
        channel = self.discordClient.get_channel(self.octopus.settings["DISCORD"]["CHANNEL"])
        future = channel.send(file=discord.File(imageLocation))
        loop = asyncio.get_event_loop()
        loop.run_until_complete(future)
        # print(future.result()) 