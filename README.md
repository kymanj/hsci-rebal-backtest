# hsci-rebal-backtest
HSCI Rebalance BackTesting

It's a sample program to cover all aspects to evaluate index rebalance performance of a particular index.

I am using HSCI in this case with Bloomberg Python API (xbbg) to get relevant price and volume data. I tried to look for various public source like yfinance, but it didn't help as historical index rebalance contains certain amount of inactive tickers. Another tricky problem is that tickers in HK will be re-used after it has been delisted, so a mapping table is needed.

The program has below key components.

1. <a href="https://github.com/kymanj/hsci-rebal-backtest/tree/main/HSCI%20Simulation">HSCI Simulation</a> is a Python program. It contains 2 major functions. <br>
a) Scrape Index Historical Change from https://www.hsi.com.hk/eng/indexes/all-indexes/hsci to <a href="https://github.com/kymanj/hsci-rebal-backtest/tree/main/HSCI%20Simulation/Raw%20Data%20Files">Raw Data Files</a> <br> b) Get relevant data from Bloomberg Python API <br> 

2. Running procedures: <br> a) Modify configuration in <a href="https://github.com/kymanj/hsci-rebal-backtest/blob/main/HSCI%20Simulation/config/conf.py">config.conf.py</a> <br> b) Run program by running <a href="https://github.com/kymanj/hsci-rebal-backtest/blob/main/HSCI%20Simulation/__main__.py">__main__.py</a>

3. The program will generate 2 csv files in <a href="https://github.com/kymanj/hsci-rebal-backtest/tree/main/HSCI%20Simulation/Output%20Files">Output Files</a>. Two files are hsci_backtest_file.csv [return data] and hsci_trade_file.csv 

After running the programs, we use <a href="https://github.com/kymanj/hsci-rebal-backtest/blob/main/HSCI%20Simulation/Output%20Files/HSCI%20Index%20Rebal%20Performance%20Visualization.ipynb"> HSCI Index Rebal Performance Visualization.ipynb </a> with a custom package <a href="https://github.com/kymanj/hsci-rebal-backtest/blob/main/HSCI%20Simulation/Output%20Files/performanceVisualization.py"> performanceVisualization.py </a> to visualise Index Rebalance Performance.

The visualization is part 1 of the whole index rebalance evaluation. Part 2 will be parameter's optimization.
