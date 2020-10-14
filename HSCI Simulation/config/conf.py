import os
import time
import getpass

simulation_params = {
    "index": "HSCI",
    "start_year": 2009,
    "end_year": 2020,
    "begin_business_day":  60,
    "end_business_day": 30,
    "funding_source": "2800 HK Equity",
    "update_hsci_file": True,
    "hsci_file_name": "hsci_hist_change.xlsx",
    "trade_file_name": "hsci_trade_file.csv",
    "backtest_file_name": "hsci_backtest_file.csv"
}

program_path = os.getcwd()
chrome_driver_path = program_path + "/chromedriver"

working_directories = {
    "log_history": program_path + "/Log History",
    "raw_data_files": program_path + "/Raw Data Files",
    "output_files": program_path + "/Output Files"
}
for path in [program_path] + list(working_directories.values()):
    print(path)
    if not os.path.exists(path):
        os.makedirs(path)

# manual mapping for reuse ticker in BBG
reuse_ticker_dict = {
    "368 HK Equity": ["1811727D HK Equity", "2018-12-17"],
    "382 HK Equity": ["1730563D HK Equity", "2018-02-07"],
    "2168 HK Equity": ["1679085D HK Equity", "2017-06-12"],
    "1833 HK Equity": ["1612890D HK Equity", "2017-05-11"],
    "1968 HK Equity": ["1631059D HK Equity", "2016-10-25"],
    "1025 HK Equity": ["1697750D HK Equity", "2015-12-31"],
    "6199 HK Equity": ["1773005D HK Equity", "2015-05-21"],
    "302 HK Equity": ["1760018D HK Equity", "2014-08-04"],
    "1633 HK Equity": ["1456071D HK Equity", "2014-04-02"],
    "331 HK Equity": ["1347063D HK Equity", "2013-09-02"],
    "589 HK Equity": ["1787744D HK Equity", "2012-05-14"],
    "968 HK Equity": ["0905737D HK Equity", "2012-01-13"],
    "636 HK Equity": ["0916159D HK Equity", "2011-05-16"],
    "203 HK Equity": ["1429071D HK Equity", "2010-08-09"]
}


log_config = {
    "version" : 1,
    "disable_existing_loggers": False,
    "formatters":
        {
            "standard":
                {
                    "format" : "%(asctime)s -%(filename)25s:%(lineno)4d - %(levelname)8s:%(message)s",
                    "datefmt": "%Y-%m-%d %H:%M:%S"
                }
        },
    "handlers":
        {
            "console":
                {
                    "level": "INFO",
                    "formatter": "standard",
                    "class": "logging.StreamHandler"
                        },
            "rotateFile":
                {
                    "level": "DEBUG",
                    "formatter": "standard",
                    "class": "logging.FileHandler",
                    "filename": working_directories["log_history"] + "/" + time.strftime("%Y%m%d") + getpass.getuser() + ".log"
                }
        },
    "loggers": {
        "": {
            "handlers": ["console", "rotateFile"],
            "level": "DEBUG"
        }
    }
}
