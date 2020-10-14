import pandas as pd
import numpy as np
import holidays
from config import log
from datetime import date
from pandas.tseries.offsets import BDay
from collections import defaultdict
from xbbg import blp

logger = log.get_logger()

class clean_trade_file():
    def __init__(self, trade_file, reuse_ticker_dict):
        self.trade_file = trade_file
        self.reuse_ticker_dict = reuse_ticker_dict

    def run(self):
        def adjust_reuse_ticker(trade_file, reuse_ticker_dict):
            for key, value in reuse_ticker_dict.items():
                this_reuse_index = trade_file[(trade_file["bbg_ticker"] == key) &
                                              (trade_file["effective_date"] <= pd.Timestamp(value[-1]))].index
                trade_file.loc[this_reuse_index, "bbg_ticker"] = value[0]
            return trade_file

        def adjust_holiday(trade_file):
            country_list = list(trade_file["listing_place"].drop_duplicates())
            start_date_dict = defaultdict(list)
            end_date_dict = defaultdict(list)
            for country in country_list:
                this_country_df = trade_file[trade_file["listing_place"] == country].copy()
                this_holiday = holidays.CountryHoliday(country)
                holiday_start_date = [start_date for start_date in list(this_country_df["trade_start_date"].drop_duplicates())
                                      if start_date in this_holiday]
                holiday_end_date = [end_date for end_date in list(this_country_df["trade_end_date"].drop_duplicates())
                                    if end_date in this_holiday]

                if holiday_start_date != []:
                    for date in holiday_start_date:
                        adjust_date = date + BDay(1)
                        while adjust_date in this_holiday:
                            adjust_date += BDay(1)
                        start_date_dict[date] = [adjust_date]

                if holiday_end_date != []:
                    for date in holiday_end_date:
                        adjust_date = date - BDay(1)
                        while adjust_date in this_holiday:
                            adjust_date -= BDay(1)
                        end_date_dict[date] = [adjust_date]

            adjust_num = 0
            for adjust_dict in [start_date_dict, end_date_dict]:
                date_column = "trade_start_date" if adjust_num == 0 else "trade_end_date"
                for key, value in adjust_dict.items():
                    adjust_index = trade_file[trade_file[date_column] == key].index
                    trade_file.loc[adjust_index, date_column] = value[0]
                adjust_num += 1
            return trade_file

        # get trade id
        trade_file = self.trade_file.reset_index().rename(columns={"index": "trade_id"})
        logger.info("Created Trade Id")

        # adjust end date beyond today
        trade_file["trade_end_date"] = [
            pd.Timestamp(date.today() - BDay(1)) if end_date >= pd.Timestamp(date.today()) else end_date
            for end_date in trade_file["trade_end_date"]
        ]
        logger.info("Adjusted End Date beyond Today")

        # update reuse ticker
        trade_file = adjust_reuse_ticker(trade_file=trade_file, reuse_ticker_dict=self.reuse_ticker_dict)
        logger.info("Updated re-used BBG ticker")

        # adjust holiday
        trade_file = adjust_holiday(trade_file=trade_file)
        logger.info("Adjusted Start Date and End Date based on Holidays")
        return trade_file

class get_backtest_files():
    def __init__(self, trade_file, funding_source, output_hsci_trade_file_path, output_hsci_backtest_file_path):
        self.trade_file = trade_file
        self.funding_source = funding_source
        self.output_hsci_trade_file_path = output_hsci_trade_file_path
        self.output_hsci_backtest_file_path = output_hsci_backtest_file_path

    def run(self):

        def reconstruct_price_data(price_data):
            price_data = price_data.unstack().reset_index()
            price_data.columns = ["bbg_ticker", "item_name", "date", "item_value"]
            price_data["item_value"] = price_data["item_value"].astype("float")
            price_data["date"] = price_data["date"].astype("datetime64[ns]")
            return price_data

        def adjust_start_end_date_based_on_trade_data(this_trade_df, price_data):
            # halt flag dataframe
            active_df = price_data[price_data["item_name"] == "volume"].copy()
            active_df = active_df.dropna(subset=["item_value"])
            active_stock = list(active_df["bbg_ticker"].drop_duplicates())
            halt_list = [stock for stock in this_stock_list if stock not in active_stock]
            halt_df = pd.DataFrame(index=halt_list).reset_index().rename(columns={"index": "bbg_ticker"})
            halt_df["halt_flag"] = True
            logger.info("Got Halt Flag")

            # ipo or delist dataframe
            start_end_date_df = active_df.groupby(["bbg_ticker"])["date"].agg(["min", "max"])
            ipo_df = start_end_date_df[start_end_date_df["min"] != start_date].reset_index().rename(
                columns={"min": "ipo_date"}).drop(columns="max")
            delist_df = start_end_date_df[start_end_date_df["max"] != end_date].reset_index().rename(
                columns={"max": "delist_date"}).drop(columns="min")
            logger.info("Got IPO Date and Delist Date")

            # ipo return
            ipo_return_list = []
            if not ipo_df.empty:
                for ticker in list(ipo_df["bbg_ticker"].drop_duplicates()):
                    ipo_return = list(price_data[(price_data["item_name"] == "last_price") &
                                                 (price_data["bbg_ticker"] == ticker)].sort_values("date")[
                                          "item_value"].dropna())[:2]
                    ipo_return = (ipo_return[-1] / ipo_return[0] - 1) * 100
                    ipo_return_list.append(ipo_return)
            ipo_df["ipo_return"] = ipo_return_list
            logger.info("Got IPO Return")

            # get adjusted trade df
            if not halt_df.empty:
                this_trade_df = pd.merge(this_trade_df, halt_df, on=["bbg_ticker"], how="left")
                this_trade_df["halt_flag"] = this_trade_df["halt_flag"].fillna(False)
            else:
                this_trade_df["halt_flag"] = False

            if not ipo_df.empty:
                this_trade_df = pd.merge(this_trade_df, ipo_df, on=["bbg_ticker"], how="left")
            else:
                this_trade_df["ipo_date"] = pd.NaT
                this_trade_df["ipo_return"] = np.nan

            if not delist_df.empty:
                this_trade_df = pd.merge(this_trade_df, delist_df, on=["bbg_ticker"], how="left")
            else:
                this_trade_df["delist_date"] = pd.NaT

            this_trade_df["trade_start_date"] = [trade_start_date if pd.isnull(ipo_date) else ipo_date
                                                 for trade_start_date, ipo_date
                                                 in np.array(this_trade_df[["trade_start_date", "ipo_date"]])]
            this_trade_df["trade_end_date"] = [trade_end_date if pd.isnull(delist_date) else delist_date
                                               for trade_end_date, delist_date
                                               in np.array(this_trade_df[["trade_end_date", "delist_date"]])]
            return this_trade_df

        def get_beta(this_trade_df, price_data, funding_source):
            stock_beta_df = price_data[(price_data["item_name"] == "beta_adj_overridable") &
                                       (price_data["date"].isin(
                                           list(this_trade_df["trade_start_date"].drop_duplicates())))].copy()
            stock_beta_df = stock_beta_df[["bbg_ticker", "date", "item_value"]].rename(
                columns={"item_value": "stock_beta",
                         "date": "trade_start_date"})
            this_trade_df = pd.merge(this_trade_df, stock_beta_df, on=["bbg_ticker", "trade_start_date"], how="left")
            fund_beta_df = stock_beta_df[stock_beta_df["bbg_ticker"] == funding_source].rename(
                columns={"stock_beta": "fund_beta"})
            this_trade_df = pd.merge(this_trade_df, fund_beta_df.drop(columns=["bbg_ticker"]), on=["trade_start_date"],
                                     how="left")
            return this_trade_df

        def get_backtesting_returns(this_trade_df, price_data, funding_source, trade_start_date, trade_end_date):
            this_return_df = this_trade_df[(this_trade_df["trade_start_date"] == trade_start_date) &
                                           (this_trade_df["trade_end_date"] == trade_end_date) &
                                           (this_trade_df["halt_flag"] == False)].copy()
            if not this_return_df.empty:
                this_ticker_list = list(this_return_df["bbg_ticker"].drop_duplicates())
                this_price_data = price_data[(price_data["bbg_ticker"].isin(this_ticker_list + [funding_source])) &
                                             (price_data["date"] >= trade_start_date) &
                                             (price_data["date"] <= trade_end_date) &
                                             (price_data["item_name"] == "last_price")].copy()

                # calculate return [stock, funding, long_short]
                this_pivot_return_df = pd.pivot_table(this_price_data, index="date", columns="bbg_ticker",
                                                      values="item_value")
                this_pivot_return_df = this_pivot_return_df.pct_change()
                this_pivot_return_df = this_pivot_return_df.fillna(0)

                this_daily_stock_return_df = this_pivot_return_df.stack().reset_index().rename(columns={0: "daily_stock_return"})
                this_daily_fund_return_df = this_daily_stock_return_df[this_daily_stock_return_df["bbg_ticker"] == funding_source].rename(
                    columns={"daily_stock_return": "daily_fund_return"})

                this_pivot_return_df = (1 + this_pivot_return_df).cumprod() - 1
                this_stock_return_df = this_pivot_return_df.stack().reset_index().rename(columns={0: "stock_return"})
                this_fund_return_df = this_stock_return_df[this_stock_return_df["bbg_ticker"] == funding_source].rename(
                    columns={"stock_return": "fund_return"})

                this_backtest_df = this_return_df[["trade_id", "bbg_ticker"]].copy()
                this_backtest_df = pd.merge(this_backtest_df, this_daily_stock_return_df, on=["bbg_ticker"], how="left")
                this_backtest_df = pd.merge(this_backtest_df, this_daily_fund_return_df.drop(columns=["bbg_ticker"]), on=["date"], how="left")
                this_backtest_df = pd.merge(this_backtest_df, this_stock_return_df, on=["bbg_ticker", "date"], how="left")
                this_backtest_df = pd.merge(this_backtest_df, this_fund_return_df.drop(columns=["bbg_ticker"]), on=["date"], how="left")

                this_backtest_df[["stock_return", "fund_return", "daily_fund_return", "daily_stock_return"]] *= 100
                this_backtest_df["long_short_return"] = this_backtest_df["stock_return"] - this_backtest_df["fund_return"]

                # get date index
                this_backtest_df = pd.merge(this_backtest_df, this_trade_df[["trade_id", "effective_date"]],
                                            on=["trade_id"], how="left")
                this_backtest_df["date_index"] = [np.busday_count(pd.Timestamp(effect_date).date(), pd.Timestamp(date).date())
                                                  for date, effect_date in np.array(this_backtest_df[["date", "effective_date"]])]
                this_backtest_df = this_backtest_df.sort_values(["trade_id", "date_index"])

                # calculate drawdown
                this_backtest_df["roll_max_abs_return"] = this_backtest_df.groupby(["trade_id"])["stock_return"].cummax()
                this_backtest_df["roll_max_ls_return"] = this_backtest_df.groupby(["trade_id"])["long_short_return"].cummax()
                this_backtest_df["roll_abs_drawdown"] = this_backtest_df["stock_return"] - this_backtest_df["roll_max_abs_return"]
                this_backtest_df["roll_ls_drawdown"] = this_backtest_df["long_short_return"] - this_backtest_df["roll_max_ls_return"]
                this_backtest_df = this_backtest_df.drop(columns=["roll_max_abs_return", "roll_max_ls_return"])

            else:
                this_backtest_df = pd.DataFrame()
            return this_backtest_df

        trade_df_list = []
        backtest_df_list = []
        for date, start_date, end_date in np.array(self.trade_file[["effective_date",
                                                                    "trade_start_date",
                                                                    "trade_end_date"]].drop_duplicates()):

            logger.info("Updateing Effective Date: " + pd.Timestamp(date).strftime("%Y-%m-%d"))
            this_trade_df = self.trade_file[self.trade_file["effective_date"] == date].copy()
            this_stock_list = list(this_trade_df["bbg_ticker"].drop_duplicates())
            this_id_list = this_stock_list + [self.funding_source]

            # get price_data from bloomberg from xbbg
            price_data = blp.bdh(
                tickers=this_id_list, flds=["last_price", "volume", "beta_adj_overridable"],
                start_date=start_date.strftime("%Y-%m-%d"), end_date=end_date.strftime("%Y-%m-%d"),
            )
            logger.info("Got Price Data from BBG for Effective Date: " + date.strftime("%Y-%m-%d"))

            # Reconstruct price_data
            price_data = reconstruct_price_data(price_data=price_data)
            logger.info("Reconstructed Price Data for Effective Date: " + pd.Timestamp(date).strftime("%Y-%m-%d"))

            # Adjust Start End Date based on Halt Flag, IPO Date and Delist Date
            this_trade_df = adjust_start_end_date_based_on_trade_data(this_trade_df=this_trade_df, price_data=price_data)
            logger.info("Adjusted Trade Start End Date based on Halt Flag, IPO Date and Delist Date for Effective Date: " + pd.Timestamp(date).strftime("%Y-%m-%d"))

            # get final trade dataframe with beta
            this_trade_df = get_beta(this_trade_df=this_trade_df, price_data=price_data,
                                     funding_source=self.funding_source)
            trade_df_list.append(this_trade_df)
            logger.info("Got Final Trade DataFrame with Beta for Effective Date: " + pd.Timestamp(date).strftime("%Y-%m-%d"))

            # get backtesting returns
            for trade_start_date, trade_end_date in np.array(this_trade_df[["trade_start_date",
                                                                            "trade_end_date"]].drop_duplicates()):
                this_backtest_df = get_backtesting_returns(this_trade_df=this_trade_df, price_data=price_data,
                                                           funding_source=self.funding_source,
                                                           trade_start_date=trade_start_date, trade_end_date=trade_end_date)
                if not this_backtest_df.empty:
                    backtest_df_list.append(this_backtest_df)
            logger.info("Got BackTesting Returns for Effective Date: " + pd.Timestamp(date).strftime("%Y-%m-%d"))

        trade_df = pd.concat(trade_df_list, sort=True)
        backtest_df = pd.concat(backtest_df_list, sort=True)

        trade_df.to_csv(self.output_hsci_trade_file_path, index=False)
        backtest_df.to_csv(self.output_hsci_backtest_file_path, index=False)

        logger.info('''
        Output Trade DataFrame to:
        %s
        Output BackTest DataFrame to:
        %s
        ''' % (self.output_hsci_trade_file_path, self.output_hsci_backtest_file_path))