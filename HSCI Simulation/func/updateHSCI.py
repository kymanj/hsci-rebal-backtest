import pandas as pd
import numpy as np
from config import log
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support import expected_conditions as EC
from pandas.tseries.offsets import BDay
import os
import time
import glob

logger = log.get_logger()

def scrape_hsci_change(download_path, download_hsci_file_path, chrome_driver_path):
    # check if chromedriver exists
    if os.path.exists(chrome_driver_path):
        logger.info('''
        chromedriver exists.
        Start scraping HSCI historical change from https://www.hsi.com.hk/eng/indexes/all-indexes/hsci
        ''')
    else:
        raise Exception("No chromedriver. Please update chrome_driver_path in config.conf")

    # download historical change of HSCI from internet to Raw Data Files
    chrome_options = Options()
    chrome_options.headless = True
    prefs = {}
    prefs["download.default_directory"] = download_path
    prefs["download.prompt_for_download"] = False
    chrome_options.add_experimental_option("prefs", prefs)

    driver = webdriver.Chrome(chrome_driver_path, chrome_options=chrome_options)
    driver.get("https://www.hsi.com.hk/eng/indexes/all-indexes/hsci")
    element = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "constituentsSelect"))
    )
    hist_cons_select = Select(element)
    hist_cons_select.select_by_visible_text("Hang Seng Composite Index")
    download_button = driver.find_element_by_xpath('//button[text()="View Now"]')
    driver.execute_script("arguments[0].click();", download_button)

    # rename the downloaded file
    time.sleep(0.5)
    download_files = glob.glob(download_path + "/*.xlsx")
    latest_file = max(download_files, key=os.path.getctime)
    os.rename(latest_file, download_hsci_file_path)

class get_hsci_trade_file():
    def __init__(self, start_year, end_year, begin_business_day, end_business_day, download_hsci_file_path):
        self.start_year = start_year
        self.end_year = end_year
        self.begin_business_day = begin_business_day
        self.end_business_day = end_business_day
        self.download_hsci_file_path = download_hsci_file_path

    def run(self):
        def clean_hsci_raw_file(main_file, start_year, end_year):
            column_list = ["effective_date", "number_of_cons", "change", "count", "stock_code",
                           "listing_place", "stock_name", "stock_name_chinese"]
            main_file = main_file.iloc[5:-5, :].copy()
            main_file.columns = column_list
            main_file["effective_date"] = main_file["effective_date"].astype("datetime64[ns]")
            main_file["year"] = main_file["effective_date"].dt.year
            main_file = main_file[(main_file["year"] >= start_year) & (main_file["year"] <= end_year)].copy()
            main_file["change"] = main_file["change"].replace({"Add 加入": "Add", "Delete 刪除": "Delete"})
            main_file["listing_place"] = "HK"
            main_file["count"] = [-int(num[1:]) if num[0] == "-" else int(num[1:]) for num in main_file["count"]]
            return main_file

        def get_hsci_review_type(main_file):
            review_type_file = main_file[["effective_date", "count"]].drop_duplicates()
            review_type_file["month"] = review_type_file["effective_date"].dt.month
            review_type_file["review_type"] = ["Regular" if month in [3, 9] and abs(count) >= 3 else "Interim" for
                                               month, count in np.array(review_type_file[["month", "count"]])]
            review_type_file = review_type_file.sort_values(["effective_date", "review_type"])
            review_type_file = review_type_file.groupby(["effective_date"])["review_type"].last().reset_index()
            main_file = pd.merge(main_file, review_type_file, on=["effective_date"], how="left")
            return main_file

        def flag_out_name_change(main_file):
            name_change_file = main_file.groupby(["effective_date", "stock_code"])["stock_name"].count().reset_index()
            name_change_file = name_change_file[name_change_file["stock_name"] > 1]
            if not name_change_file.empty:
                for date, code in np.array(name_change_file[["effective_date", "stock_code"]]):
                    this_index = main_file[(main_file["effective_date"] == date) &
                                           (main_file["stock_code"] == code)].index
                    main_file.loc[this_index, "review_type"] = "Name Change"
            return main_file

        def get_hsci_sector(hsci_excel, main_file):
            sectorDfList = []
            for sheet_name in hsci_excel.sheet_names:
                if "-" in sheet_name:
                    sector = sheet_name.split("-")[-1]
                    this_excel = hsci_excel.parse(sheet_name)
                    this_excel = this_excel.iloc[5:-5, [0, 2, 4]]
                    this_excel.columns = ["effective_date", "change", "stock_code"]
                    this_excel["effective_date"] = this_excel["effective_date"].astype("datetime64[ns]")
                    this_excel["change"] = this_excel["change"].replace({"Add 加入": "Add", "Delete 刪除": "Delete"})
                    this_excel["sector"] = sector
                    sectorDfList.append(this_excel)
            sectorDf = pd.concat(sectorDfList).drop_duplicates()
            sectorDf["sector"] = sectorDf["sector"].replace({"CD": "Consumer Discretionary", "CONG": "Conglomerates",
                                                             "CS": "Consumer Staples", "ENG": "Energy",
                                                             "FIN": "Financials",
                                                             "H": "Healthcare", "IND": "Industrials",
                                                             "IT": "Information Technology", "MAT": "Materials",
                                                             "PROP": "Properties & Construction",
                                                             "TEL": "Telecommunications",
                                                             "UTI": "Utilities"})
            main_file = pd.merge(main_file, sectorDf, on=["effective_date", "change", "stock_code"], how="left")
            main_file["sector"] = main_file["sector"].fillna("Unknown")
            return main_file

        def get_trade_start_end_date(main_file, begin_business_day, end_business_day):
            date_list = list(main_file["effective_date"].drop_duplicates())
            begin_date_list = []
            end_date_list = []
            for date in date_list:
                begin_date = date - BDay(begin_business_day)
                end_date = date + BDay(end_business_day)

                begin_date_list.append(begin_date)
                end_date_list.append(end_date)
            date_file = pd.DataFrame.from_dict({"effective_date": date_list,
                                                "trade_start_date": begin_date_list,
                                                "trade_end_date": end_date_list})
            main_file = pd.merge(main_file, date_file, on=["effective_date"], how="left")
            return main_file

        def get_bbg_ticker(main_file):
            main_file["bbg_ticker"] = main_file["stock_code"].astype(str) + " " + main_file["listing_place"] + " Equity"
            return main_file

        hsci_excel = pd.ExcelFile(self.download_hsci_file_path)
        main_file = hsci_excel.parse(hsci_excel.sheet_names[0])
        logger.info('''Read Excel from %s''' % (self.download_hsci_file_path))

        # clean raw file
        main_file = clean_hsci_raw_file(main_file=main_file, start_year=self.start_year, end_year=self.end_year)
        logger.info("Cleaned Raw File")

        # get review type
        main_file = get_hsci_review_type(main_file=main_file)
        logger.info("Got Review Type in Trade File [Interim, Regular]")

        # flag out name change
        main_file = flag_out_name_change(main_file=main_file)
        logger.info("Flagged out Name Change Cases")

        # get hang seng sector
        main_file = get_hsci_sector(hsci_excel=hsci_excel, main_file=main_file)
        logger.info("Got Hang Seng Sector")

        # get trade start date and trade end date
        main_file = get_trade_start_end_date(main_file=main_file,
                                             begin_business_day=self.begin_business_day,
                                             end_business_day=self.end_business_day)
        logger.info("Got Trade Start Date and Trade End Date")

        main_file = get_bbg_ticker(main_file=main_file)
        logger.info("Got BBG Ticker")
        return main_file




