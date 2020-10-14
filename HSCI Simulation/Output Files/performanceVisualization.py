import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Count Summary
def get_count_summary(trade_df):
    review_type_summary = trade_df[
        ["trade_id", "review_type", "change", "ipo_date", "ipo_return", "halt_flag", "delist_date"]].copy()
    review_type_summary["delist"] = [False if pd.isnull(delist_date) else True for delist_date in
                                     review_type_summary["delist_date"]]
    review_type_summary["ipo"] = [False if pd.isnull(ipo_date) else True for ipo_date in
                                  review_type_summary["ipo_date"]]
    review_type_summary["zero_ipo_return"] = [True if ipo_return == 0 else False for ipo_return in
                                              review_type_summary["ipo_return"]]

    count_summary = pd.DataFrame(review_type_summary.groupby(["review_type", "change"]).agg({"trade_id": "count",
                                                                                             "halt_flag": "sum",
                                                                                             "delist": "sum",
                                                                                             "ipo": "sum",
                                                                                             "zero_ipo_return": "sum"}))
    count_summary = count_summary.astype("int64")
    return count_summary


def align_yaxis(ax1, ax2):
    """Align zeros of the two axes, zooming them out by same ratio"""
    axes = (ax1, ax2)
    extrema = [ax.get_ylim() for ax in axes]
    tops = [extr[1] / (extr[1] - extr[0]) for extr in extrema]
    # Ensure that plots (intervals) are ordered bottom to top:
    if tops[0] > tops[1]:
        axes, extrema, tops = [list(reversed(l)) for l in (axes, extrema, tops)]

    # How much would the plot overflow if we kept current zoom levels?
    tot_span = tops[1] + 1 - tops[0]

    b_new_t = extrema[0][0] + tot_span * (extrema[0][1] - extrema[0][0])
    t_new_b = extrema[1][1] - tot_span * (extrema[1][1] - extrema[1][0])
    axes[0].set_ylim(extrema[0][0], b_new_t)
    axes[1].set_ylim(t_new_b, extrema[1][1])

# Aggregate Performance Chart
def get_aggregate_performance_chart(backtest_df, trade_df, review_type, change, flip_side=False, ipo_only=False):
    if not ipo_only:
        this_id_list = list(trade_df[(trade_df["review_type"] == review_type) &
                                     (trade_df["change"] == change)]["trade_id"])
        ipo_string = ""
    else:
        this_id_list = list(trade_df[(trade_df["review_type"] == review_type) &
                                     (trade_df["change"] == change) &
                                     (trade_df["ipo_date"].isnull() == False) &
                                     (trade_df["ipo_return"] != 0)]["trade_id"])
        ipo_string = " (IPO Only)"

    this_backtest_df = backtest_df[backtest_df["trade_id"].isin(this_id_list)].copy()

    # chart
    fig = plt.figure(figsize=(14, 28))

    # chart 1 - aggregate performance chart
    ax1 = fig.add_subplot(4, 1, 1)
    agg_performance_df = this_backtest_df.groupby(["date_index"]).agg({"long_short_return": "mean",
                                                                       "stock_return": "mean",
                                                                       "fund_return": "mean",
                                                                       "trade_id": "count"}).reset_index()
    agg_performance_df["long_short_return_diff"] = agg_performance_df["long_short_return"].diff()
    agg_performance_df["long_short_return_diff"] = agg_performance_df["long_short_return_diff"].fillna(0)
    agg_performance_df = agg_performance_df.set_index("date_index")

    up = agg_performance_df[agg_performance_df["long_short_return_diff"] > 0].index
    down = agg_performance_df[agg_performance_df["long_short_return_diff"] <= 0].index

    ax1.plot(agg_performance_df.index, agg_performance_df["long_short_return"], color="b")

    ax2 = ax1.twinx()
    try:
        ax2.bar(up, agg_performance_df.loc[up, "long_short_return_diff"], width=0.7, alpha=0.2, color="g")
    except:
        pass
    try:
        ax2.bar(down, agg_performance_df.loc[down, "long_short_return_diff"], width=0.7, alpha=0.2, color="r")
    except:
        pass

    align_yaxis(ax1, ax2)

    ax2.set_title(
        "HSCI Rebal [" + str(agg_performance_df.index[0]) + "D ~ " + str(agg_performance_df.index[-1]) + "D] - "
        + review_type + " " + change + " - long_short_return" + ipo_string + " Return: "
        + "{:,.2f}%".format(agg_performance_df.loc[agg_performance_df.index[-1], "long_short_return"]), fontsize=16)
    ax2.axhline(y=0, color="k")
    ax2.axvline(x=0, color="k", linestyle="--")

    ax1.set_ylabel("Cumulative Return (%)", fontsize=14)
    ax2.set_ylabel("Daily Return (%)", fontsize=14, rotation=270)

    # chart 2 - aggregate long short chart
    ax3 = fig.add_subplot(4, 1, 2)
    if flip_side:
        long_column = "fund_return"
        short_column = "stock_return"
    else:
        long_column = "stock_return"
        short_column = "fund_return"

    ax3.plot(agg_performance_df.index, agg_performance_df[long_column], color="g", label="Long: " + long_column)
    ax3.plot(agg_performance_df.index, agg_performance_df[short_column], color="r", label="Short: " + short_column)

    ax3.axhline(y=0, color="k")
    ax3.axvline(x=0, color="k", linestyle="--")

    ax3.set_title("Long Return: " + "{:,.2f}%".format(agg_performance_df.loc[agg_performance_df.index[-1], long_column]) + "   " +
                  "Short Return: " + "{:,.2f}%".format(agg_performance_df.loc[agg_performance_df.index[-1], short_column]), fontsize=16)
    ax3.legend()
    ax3.set_ylabel("Cumulative Return (%)", fontsize=14)

    # chart 3 - aggregate drawdown chart
    ax4 = fig.add_subplot(4, 1, 3)

    agg_performance_df["roll_max_return"] = agg_performance_df["long_short_return"].cummax()
    agg_performance_df["roll_ls_drawdown"] = agg_performance_df["long_short_return"] - agg_performance_df[
        "roll_max_return"]
    ax4.plot(agg_performance_df.index, agg_performance_df["roll_ls_drawdown"], color="dimgray")

    ax4.set_ylabel("Drawdown (%)", fontsize=14)
    ax4.set_title("Max Drawdown: " +
                  "{:,.2f}%".format(agg_performance_df["roll_ls_drawdown"].min()), fontsize=16)
    ax4.axvline(x=0, color="k", linestyle="--")

    # chart 4 - count chart
    ax5 = fig.add_subplot(4, 1, 4)
    ax5.plot(agg_performance_df.index, agg_performance_df["trade_id"], color="k")
    ax5.set_ylabel("Count ", fontsize=14)
    ax5.axvline(x=0, color="k", linestyle="--")
    ax5.set_title("Stock Count Average: " + "{:,.0f}".format(agg_performance_df["trade_id"].mean()), fontsize=16)
    return fig

# Group Performance Chart
def get_group_performance_df(backtest_df, trade_df, review_type, change, group_by, ipo_only=False):
    if not ipo_only:
        this_id_list = list(trade_df[(trade_df["review_type"] == review_type) &
                                     (trade_df["change"] == change)]["trade_id"])
    else:
        this_id_list = list(trade_df[(trade_df["review_type"] == review_type) &
                                     (trade_df["change"] == change) &
                                     (trade_df["ipo_date"].isnull() == False) &
                                     (trade_df["ipo_return"] != 0)]["trade_id"])

    this_backtest_df = backtest_df[backtest_df["trade_id"].isin(this_id_list)].copy()

    if group_by == "year_month":
        this_backtest_df["year"] = this_backtest_df["effective_date"].dt.year
        this_backtest_df["month"] = this_backtest_df["effective_date"].dt.month
        this_backtest_df["year_month"] = this_backtest_df["year"].astype(str) + "-" + this_backtest_df["month"].astype(
            str)

    elif group_by == "year":
        this_backtest_df["year"] = this_backtest_df["effective_date"].dt.year

    elif group_by == "month":
        this_backtest_df["month"] = this_backtest_df["effective_date"].dt.month

    else:
        raise Exception("group_by only accepts year_month, year, month")

    df_list = []
    group_list = []
    for group in list(this_backtest_df[group_by].drop_duplicates()):
        this_df = this_backtest_df[this_backtest_df[group_by] == group].copy()
        df_list.append(this_df)
        group_list.append(group)
    return df_list, group_list


def get_group_performance_chart(backtest_df, trade_df, review_type, change, group_by, ipo_only=False):
    df_list, gruop_list = get_group_performance_df(backtest_df=backtest_df, trade_df=trade_df,
                                                   review_type=review_type, change=change,
                                                   group_by=group_by, ipo_only=ipo_only)

    ipo_string = "" if not ipo_only else " (IPO Only)"

    fig = plt.figure(figsize=(14, 21))
    ax1 = fig.add_subplot(3, 1, 1)
    ax2 = fig.add_subplot(3, 1, 2)
    ax3 = fig.add_subplot(3, 1, 3)

    long_short_return_list = []
    max_drawdown_list = []
    stock_count_list = []
    for df, group in zip(df_list, gruop_list):
        this_group_df = df.groupby(["date_index"]).agg({"long_short_return": "mean",
                                                        "trade_id": "count"}).reset_index()
        this_group_df = this_group_df.set_index("date_index")

        this_group_df["roll_max_return"] = this_group_df["long_short_return"].cummax()
        this_group_df["roll_ls_drawdown"] = this_group_df["long_short_return"] - this_group_df["roll_max_return"]

        # long short return chart
        ax1.plot(this_group_df.index, this_group_df["long_short_return"], label=group)
        long_short_return_list.append(this_group_df.loc[this_group_df.index[-1], "long_short_return"])
        # drawdown chart
        ax2.plot(this_group_df.index, this_group_df["roll_ls_drawdown"], label=group)
        max_drawdown_list.append(this_group_df["roll_ls_drawdown"].min())
        # count
        ax3.plot(this_group_df.index, this_group_df["trade_id"], label=group)
        stock_count_list.append(this_group_df["trade_id"].mean())

    ax1.axhline(y=0, color="k")
    ax1.axvline(x=0, color="k", linestyle="--")
    ax2.axvline(x=0, color="k", linestyle="--")
    ax3.axvline(x=0, color="k", linestyle="--")

    ax1.legend(bbox_to_anchor=(1.02, 1), loc="upper left")
    ax2.legend(bbox_to_anchor=(1.02, 1), loc="upper left")
    ax3.legend(bbox_to_anchor=(1.02, 1), loc="upper left")

    ax1.set_title("HSCI Rebal [" + str(backtest_df["date_index"].min()) + "D ~ " + str(backtest_df["date_index"].max()) + "D] - " +
                  review_type + " " + change + " - long_short_return" + ipo_string + " by " + group_by
                  + " - Average Return: " + "{:,.2f}%".format(sum(long_short_return_list) / len(long_short_return_list)) +
                  " - Hit Ratio: " + "{:,.2f}%".format(len([ls_return for ls_return in long_short_return_list if ls_return > 0]) /
                                                       len(long_short_return_list) * 100),
                  fontsize=16)
    ax2.set_title("Drawdown by " + group_by + " - Average Max Drawdown: "
                  + "{:,.2f}%".format(sum(max_drawdown_list) / len(max_drawdown_list)), fontsize=16)
    ax3.set_title("Count by " + group_by + " - Average Stock Count: "
                  + "{:,.0f}".format(sum(stock_count_list) / len(stock_count_list)), fontsize=16)
    return fig

# get hindsight df
def get_hindsight_backtest_df(backtest_df, trade_df, review_type, change,
                              begin_business_day, end_business_day, flip_side=False, ipo_only=False):
    # adjust backtest df trade df
    if not ipo_only:
        this_id_list = list(trade_df[(trade_df["review_type"] == review_type) &
                                     (trade_df["change"] == change)]["trade_id"])
    else:
        this_id_list = list(trade_df[(trade_df["review_type"] == review_type) &
                                     (trade_df["change"] == change) &
                                     (trade_df["ipo_date"].isnull() == False) &
                                     (trade_df["ipo_return"] != 0)]["trade_id"])

    this_backtest_df = backtest_df[(backtest_df["trade_id"].isin(this_id_list)) &
                                   (backtest_df["date_index"] >= -begin_business_day) &
                                   (backtest_df["date_index"] <= end_business_day)].copy()

    this_backtest_df = this_backtest_df[["trade_id", "bbg_ticker", "daily_stock_return", "daily_fund_return",
                                         "date", "date_index", "effective_date"]].copy()

    # re-calculate backtest data
    this_stock_pivot_df = pd.pivot_table(this_backtest_df, index="date_index", columns="trade_id",
                                         values="daily_stock_return")

    this_fund_pivot_df = pd.pivot_table(this_backtest_df, index="date_index", columns="trade_id",
                                        values="daily_fund_return")

    this_fund_pivot_df = this_fund_pivot_df[this_stock_pivot_df.columns].copy()

    # assume entering the trade at close on the first day
    this_stock_pivot_df.iloc[0, :] = 0
    this_stock_pivot_df = this_stock_pivot_df.fillna(0)
    this_stock_pivot_df = (1 + this_stock_pivot_df / 100).cumprod() - 1

    this_fund_pivot_df.iloc[0, :] = 0
    this_fund_pivot_df = this_fund_pivot_df.fillna(0)
    this_fund_pivot_df = (1 + this_fund_pivot_df / 100).cumprod() - 1

    this_stock_return_df = this_stock_pivot_df.stack().reset_index().rename(columns={0: "stock_return"})
    this_fund_return_df = this_fund_pivot_df.stack().reset_index().rename(columns={0: "fund_return"})

    this_backtest_df = pd.merge(this_backtest_df, this_stock_return_df,
                                on=["trade_id", "date_index"], how="left")
    this_backtest_df = pd.merge(this_backtest_df, this_fund_return_df,
                                on=["trade_id", "date_index"], how="left")
    this_backtest_df[["stock_return", "fund_return"]] *= 100

    if flip_side:
        this_backtest_df["long_short_return"] = this_backtest_df["fund_return"] - this_backtest_df["stock_return"]
    else:
        this_backtest_df["long_short_return"] = this_backtest_df["stock_return"] - this_backtest_df["fund_return"]

    this_backtest_df = this_backtest_df.sort_values(["trade_id", "date_index"])
    this_backtest_df["roll_max_abs_return"] = this_backtest_df.groupby(["trade_id"])["stock_return"].cummax()
    this_backtest_df["roll_max_ls_return"] = this_backtest_df.groupby(["trade_id"])["long_short_return"].cummax()
    this_backtest_df["roll_abs_drawdown"] = this_backtest_df["stock_return"] - this_backtest_df["roll_max_abs_return"]
    this_backtest_df["roll_ls_drawdown"] = this_backtest_df["long_short_return"] - this_backtest_df[
        "roll_max_ls_return"]
    this_backtest_df = this_backtest_df.drop(columns=["roll_max_abs_return", "roll_max_ls_return"])

    return this_backtest_df

# statistic per trade
def get_trade_summary(backtest_df, trade_df):
    trade_id_list = list(backtest_df["trade_id"].drop_duplicates())
    this_trade_df = trade_df[trade_df["trade_id"].isin(trade_id_list)].copy()
    backtest_df = backtest_df.sort_values(["trade_id", "date_index"])
    trade_data_df = backtest_df.groupby("trade_id").agg({"long_short_return": "last",
                                                         "roll_ls_drawdown": "min"}).reset_index()
    this_trade_df = pd.merge(this_trade_df, trade_data_df, on=["trade_id"], how="left")

    # return
    mean_return = this_trade_df["long_short_return"].mean()
    median_return = this_trade_df["long_short_return"].median()

    # max drawdown
    mean_max_drawdown = this_trade_df["roll_ls_drawdown"].mean()
    median_max_drawdown = this_trade_df["roll_ls_drawdown"].median()

    # hit ratio
    hit_ratio = (len(this_trade_df[this_trade_df["long_short_return"] > 0].index) / len(this_trade_df.index)) * 100

    # win loss ratio
    mean_win_loss_ratio = abs((this_trade_df[this_trade_df["long_short_return"] > 0]["long_short_return"].mean() /
                               this_trade_df[this_trade_df["long_short_return"] <= 0]["long_short_return"].mean()))
    median_win_loss_ratio = abs((this_trade_df[this_trade_df["long_short_return"] > 0]["long_short_return"].median() /
                                 this_trade_df[this_trade_df["long_short_return"] <= 0]["long_short_return"].median()))

    # sharpe ratio
    this_pivot_df = pd.pivot_table(backtest_df, index="date_index", columns="trade_id", values="long_short_return")
    this_pivot_df = this_pivot_df.diff()
    this_pivot_df = this_pivot_df.iloc[1:, :]
    holding_business_days = abs(this_pivot_df.index[0]) + abs(this_pivot_df.index[-1])
    this_std_df = this_pivot_df.std().reset_index().rename(columns={0: "ls_return_std"})
    this_trade_df = pd.merge(this_trade_df, this_std_df, on=["trade_id"], how="left")

    mean_std = this_trade_df["ls_return_std"].mean()
    median_std = this_trade_df["ls_return_std"].median()
    mean_sharpe_ratio = ((1 + mean_return / 100) ** (252 / holding_business_days) - 1) / ((252 ** 0.5) * mean_std / 100)
    median_sharpe_ratio = ((1 + median_return / 100) ** (252 / holding_business_days) - 1) / (
                (252 ** 0.5) * median_std / 100)
    trade_count = this_trade_df["trade_id"].count()

    trade_dict = {"mean_return": [mean_return],
                  "mean_trade_max_drawdown": [mean_max_drawdown],
                  "mean_sharpe_ratio": [mean_sharpe_ratio],
                  "mean_win_loss_ratio": [mean_win_loss_ratio],
                  "hit_ratio": [hit_ratio],
                  "median_return": [median_return],
                  "median_max_drawdown": [median_max_drawdown],
                  "median_sharpe_ratio": [median_sharpe_ratio],
                  "median_win_loss_ratio": [median_win_loss_ratio],
                  "trade_count": [trade_count]}
    trade_summary = pd.DataFrame.from_dict(trade_dict).round(2)
    return trade_summary

def get_group_trade_summary(backtest_df, trade_df, group_by):
    if group_by == "year_month":
        backtest_df["year"] = backtest_df["effective_date"].dt.year
        backtest_df["month"] = backtest_df["effective_date"].dt.month
        backtest_df["year_month"] = backtest_df["year"].astype(str) + "-" + backtest_df["month"].astype(
            str)

    elif group_by == "year":
        backtest_df["year"] = backtest_df["effective_date"].dt.year

    elif group_by == "month":
        backtest_df["month"] = backtest_df["effective_date"].dt.month

    else:
        raise Exception("group_by only accepts year_month, year, month")

    yearly_summary_df_list = []
    for group in list(backtest_df[group_by].drop_duplicates()):
        this_backtest_df = backtest_df[backtest_df[group_by] == group].copy()
        this_trade_summary = get_trade_summary(this_backtest_df, trade_df)
        this_trade_summary.index = [group]
        yearly_summary_df_list.append(this_trade_summary)
    yearly_summary_df = pd.concat(yearly_summary_df_list).T
    yearly_summary_df_index = list(yearly_summary_df.columns)
    yearly_summary_df["mean"] = yearly_summary_df.mean(axis=1)
    yearly_summary_df["median"] = yearly_summary_df.median(axis=1)
    yearly_summary_df = yearly_summary_df[["mean", "median"] + yearly_summary_df_index].round(2)
    return yearly_summary_df

# return vs. item scatter plot
def get_return_scatter_plot(backtest_df, trade_df, item):
    backtest_df = backtest_df.sort_values(["trade_id", "date_index"])
    ls_return_df = backtest_df.groupby(["trade_id"])["long_short_return"].last().reset_index()
    trade_df = pd.merge(trade_df, ls_return_df, on=["trade_id"], how="left")

    fig = plt.figure(figsize=(14, 7))
    ax1 = fig.add_subplot(1, 1, 1)
    ax1.scatter(trade_df[item], trade_df["long_short_return"])
    ax1.set_title("long_short_return (Y) vs. " + item + "(X)", fontsize=16)
    ax1.set_ylabel("long_short_return", fontsize=14)
    ax1.set_xlabel(item, fontsize=14)
    ax1.axhline(y=0, color="k", linestyle="--")
    ax1.axvline(x=0, color="k", linestyle="--")
    return fig