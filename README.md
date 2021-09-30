<br />
<p align="center">
  <a href="https://github.com/mpainenz/octopus">
    <img src="assets/icon.jpg" alt="Logo" width="200" height="200">
  </a>

  <h3 align="center">Octopus Trading Bot</h3>

  <p align="center">
    Algorithmic Swing Trading, Scanning, and Backtesting. 
    Written in Python, for use with the Interactive Brokers TWS API.
</p>


<summary><h2 style="display: inline-block">Table of Contents</h2></summary>
<ol>
<li>
    <a href="#about-the-project">About The Project</a>
    <ul>
    <li><a href="#built-with">Built With</a></li>
    </ul>
</li>
<li>
    <a href="#getting-started">Getting Started</a>
    <ul>
    <li><a href="#prerequisites">Prerequisites</a></li>
    <li><a href="#installation">Installation</a></li>
    </ul>
</li>
<li><a href="#usage">Usage</a></li>
<li><a href="#roadmap">Roadmap</a></li>
<li><a href="#contributing">Contributing</a></li>
<li><a href="#license">License</a></li>
<li><a href="#contact">Contact</a></li>
<li><a href="#acknowledgements">Acknowledgements</a></li>
</ol>



<!-- ABOUT THE PROJECT -->
## About The Project

<!-- [![Product Name Screen Shot][product-screenshot]](https://example.com) -->

This project is an algorithmic trading framework, built for swing trading stocks which have recently reported earnings.

Inspired by the trading methods of <a href="https://qullamaggie.com/">Kristjan Kullamägi</a> (Twitter: [@Qullamaggie](https://twitter.com/Qullamaggie)), this Bot is inteded to provide an algorithmic trading framework compatable with some of the strategies taught by Kris.

The general concept, is that this bot will monitor stocks as they report earnings, and will look for buy and sell signals, based on technical anaylsis.

The bot allows for different strategies to be back-tested against, and also to scan for the best past earners in order to identify what stocks were the best historic performers for research purposes.

The bot is setup to connect to Discord, and/or Telegram, and will send real-time updates as stocks are bought, or sold (Or purely in an informative way). In addition, it can identify when stocks have broken out.

The project uses:
* Python 3.9+
* Interactive Brokers TWS
* SQLLite database to cache historic OHLCV data and Earnings Calendar data
* Discord and Telegram Bot to receieve notifications and interact with the bot



### Built With

* [ib_insync](https://github.com/erdewit/ib_insync) - Interactive Brokers TWS Client
* [pandas](https://pandas.pydata.org/) - Data Analytics
* [pandas-ta](https://github.com/twopirllc/pandas-ta) - Technical Analysis
* [sqlalchemy](https://www.sqlalchemy.org/) - SQL Database ORM
* [aiogram](https://docs.aiogram.dev/en/latest/) - Telegram Bot
* [discord.py](https://discordpy.readthedocs.io/en/stable/) - Discord Bot
* [matplotlib](https://github.com/matplotlib) - Chart Plotting
* [mplfinance](https://github.com/matplotlib/mplfinance) - General Plotting
* [yahoo_fin](https://github.com/atreadw1492/yahoo_fin) - Yahoo Finance


<!-- GETTING STARTED -->
## Getting Started

To get a local copy up and running follow these simple steps.

### Prerequisites

You must have an active Interactive Brokers account, and run the Trader Workstation, or IB Gateway applications on your machine. This Bot needs to use the API functionality exposed by one of those programs.

Follow the instructions here to [Enable the TWS API](https://interactivebrokers.github.io/tws-api/initial_setup.html)


### Installation

1. Clone the repo
   ```sh
   git clone https://github.com/mpainenz/octopus.git
   ```
2. Install Python packages
   ```sh
   pip install -r requirements.txt
   ```

<!-- USAGE EXAMPLES -->
## Usage

From the base directory, the [examply.py](examply.py) file demonstrates how to run a bot instance.

The bot can be as simple as the following code block:


```
from octopus import Octopus
from strategy.scan_earners import StrategyScanEarners


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

octopus = Octopus(settings)
octopus.run(StrategyScanEarners, backTest=True, backTestDateStartStr="2021-01-1", backTestDateEndStr="2021-01-10")
```

Running the above with the Python interpretter, will use the `StrategyScanEarners` Strategy Class, located in [strategy/scan_earners.py](strategy/earnings_breakouts.py), and will run in BackTesting mode. 

This mode is a dry run, and simulates what would occur when Stocks reporting earnings, are bought and sold after a short period.

   ```sh
   python example.py
   ```


If Discord or Telegram are enabled, the bot will run, and provide an output of stocks which gained over a certain threshold through the configured buy/sell period defined in the strategy.

As an example output from backtesting, VOLT reported earnings on the 12th of Jan, 2021. If bought, and sold 14 days later, a 26.83% Profit is detected by the bot:


<img src="assets/BacktestEarnings.JPG" alt="Backtest Result" width="342" height="348">
<img src="assets/BacktestEarnings2.JPG" alt="Backtest Result Daily Chart" width="1280" height="1131">
<img src="assets/BacktestEarnings3.JPG" alt="Backtest Result 5M Chart" width="1280" height="1131">




<!-- ROADMAP -->
## Roadmap

See the [open issues](https://github.com/mpainenz/octopus/issues) for a list of proposed features (and known issues).



<!-- CONTRIBUTING -->
## Contributing

Contributions are what make the open source community such an amazing place to learn, inspire, and create. Any contributions you make are **greatly appreciated**.

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request



<!-- LICENSE -->
## License

Distributed under the MIT License. See `LICENSE` for more information.



<!-- CONTACT -->
## Contact

Your Name - [@Kynuren](https://twitter.com/Kynuren) - mpainenz@gmail.com

Project Link: [https://github.com/mpainenz/octopus](https://github.com/mpainenz/octopus)



<!-- ACKNOWLEDGEMENTS -->
## Acknowledgements

* []()
* []()
* []()





<!-- MARKDOWN LINKS & IMAGES -->
<!-- https://www.markdownguide.org/basic-syntax/#reference-style-links -->
[contributors-shield]: https://img.shields.io/github/contributors/mpainenz/repo.svg?style=for-the-badge
[contributors-url]: https://github.com/mpainenz/octopus/graphs/contributors
[forks-shield]: https://img.shields.io/github/forks/mpainenz/repo.svg?style=for-the-badge
[forks-url]: https://github.com/mpainenz/octopus/network/members
[stars-shield]: https://img.shields.io/github/stars/mpainenz/repo.svg?style=for-the-badge
[stars-url]: https://github.com/mpainenz/octopus/stargazers
[issues-shield]: https://img.shields.io/github/issues/mpainenz/repo.svg?style=for-the-badge
[issues-url]: https://github.com/mpainenz/octopus/issues
[license-shield]: https://img.shields.io/github/license/mpainenz/repo.svg?style=for-the-badge
[license-url]: https://github.com/mpainenz/octopus/blob/master/LICENSE.txt
[linkedin-shield]: https://img.shields.io/badge/-LinkedIn-black.svg?style=for-the-badge&logo=linkedin&colorB=555
[linkedin-url]: https://linkedin.com/in/mpainenz