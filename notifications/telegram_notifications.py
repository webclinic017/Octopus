import aiogram
import asyncio

class TelegramBot:

    def __init__(self, octopus):
        self.octopus = octopus

    def Start(self):
        loop = asyncio.get_event_loop()
        print(f'Starting Telegram Polling')
        self.telegramClient = aiogram.Bot(token=self.octopus.settings["TELEGRAM"]["TOKEN"])
        self.dispatcher = aiogram.Dispatcher(self.telegramClient)
        self._createActions()
        self.pollingTask = loop.create_task(self.dispatcher.start_polling())
        print(f'Telegram Polling Active')

    def Stop(self):
        print(f'Stopping Telegram Polling')
        self.pollingTask.cancel()
        print(f'Telegram Polling Inactive')

    
    def _createActions(self):
        @self.dispatcher.message_handler(commands=['help'])
        async def help(message: aiogram.types.Message):
            msg = "The following commands are available: \n"
            msg += "  /time - Current NY (EST Time)\n"
            msg += "  /market - Market state\n"
            msg += "  /earnings - Todays Earnings calendar\n"
            msg += "  /earnings_detailed - Todays Earnings calendar (Detailed Version)\n"
            await message.reply(msg)

        @self.dispatcher.message_handler(commands=['time'])
        async def time(message: aiogram.types.Message):
            await message.reply(self.octopus.notifier.GetESTTime())
        
        @self.dispatcher.message_handler(commands=['market'])
        async def market(message: aiogram.types.Message):
            await message.reply(self.octopus.notifier.GetEarningTargetsMarketState())

        @self.dispatcher.message_handler(commands=['earnings'])
        async def earnings(message: aiogram.types.Message):
            await message.reply(self.octopus.notifier.GetEarningsTargetsShort())

        @self.dispatcher.message_handler(commands=['earnings_detailed'])
        async def earnings_detailed(message: aiogram.types.Message):
            await message.reply(self.octopus.notifier.GetEarningsTargetsLong())




    def SendNotification(self, msg):
        future = self.telegramClient.send_message(self.octopus.settings["TELEGRAM"]["CHANNEL"], msg)
        loop = asyncio.get_event_loop()
        loop.run_until_complete(future)

    def SendImage(self, imageLocation):
        future = self.telegramClient.send_photo(self.octopus.settings["TELEGRAM"]["CHANNEL"], photo=open(imageLocation, 'rb'))
        loop = asyncio.get_event_loop()
        loop.run_until_complete(future)        
        # print(future.result())