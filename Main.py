from Data_Prep import prepare_trades
import pandas as pd
from Charts import scatter_plot, distribution, forward_return_distribution
import openpyxl
import statsmodels.api as sm
from statsmodels.stats.multitest import multipletests
import math
from Indicators import VWAP, CVD
import numpy as np
from scipy import stats
pd.set_option("display.max_columns", None)
pd.set_option("display.width", 200)

Database = [r"placeholer.zip",
            r"placeholder.zip"
            ]


def Main():

    timeframe = input("Enter timeframe:" )
    #input xmin
    table = []
    one_min_table = []
    
    for i in Database:
        trades = prepare_trades(i)
        
        trades = Buy_Sell(trades)
        
        trades = VWAP(trades)
        #add vwap column
        data = create_candles(trades, "1min")
        
        
        one_min_table.append(data[["Close"]])
        #one min candle closes
        
        MinCandle = create_candles(trades,str(timeframe))
        #timeframe candle table
        
        vwap = trades.set_index("time")["VWAP"].resample(timeframe).last()
        #group into same candle readings, takes last value as measure from close
        MinCandle["VWAP"] = vwap
        #match 
        table.append(MinCandle)
       #adds to list, NOT DATAFRAME
        #should be OCHL, vol, buy, sell trades in timeframe + Vwap
    MinPrices = pd.concat(one_min_table)
    MinPrices = MinPrices.sort_index()
    MinPrices = MinPrices[~MinPrices.index.duplicated(keep="last")]
    #should be time and price
    MinCandle = pd.concat(table)
    MinCandle = MinCandle.sort_index()
    MinCandle = MinCandle[~MinCandle.index.duplicated(keep="last")]
    #stack vertically, tail should be 2026/06, 
    
    MinCandle = delta_finder(MinCandle)
    #delta columns added
    MinCandle = CVD(MinCandle)
    #CVD added

    fifth = MinCandle["delta"].quantile(0.05)
    ninety_fifth = MinCandle["delta"].quantile(0.95)
    #selects value that is the 5 quantile and 95th quantile
    print("5%:", fifth)
    print("95%:", ninety_fifth)
    first = MinCandle["delta"].quantile(0.01)
    ninety_nineth = MinCandle["delta"].quantile(0.99)
    print("1%:", first)
    print("99%:", ninety_nineth)
    MinCandle["strong sell delta"] = (MinCandle["delta"] <= fifth)
    MinCandle["strong buy delta"] = (MinCandle["delta"] >= ninety_fifth)
    MinCandle["very strong sell delta"] = (MinCandle["delta"] <= first)
    MinCandle["very strong buy delta"] = (MinCandle["delta"] >= ninety_nineth)
    #creates the needed strong delta columns, should be Boolean
    
    return_periods = [1, 5, 15, 30, 60]
    #mins
    MinCandle = returns(MinCandle, return_periods, timeframe, MinPrices)

    
    testresults = summarise_returns(MinCandle, "strong buy delta", return_periods)
    # should return mean, median, events, std, positive moves + % for ""
    

    ##
    #####
    #NORMALISED
    #####
    ##     
    normalised_fifth = MinCandle["normalised delta"].quantile(0.05)

    normalised_ninety_fifth = MinCandle["normalised delta"].quantile(0.95)

    print("Normalised 5%:", normalised_fifth)
    print("Normalised 95%:", normalised_ninety_fifth)

    normalised_first = MinCandle["normalised delta"].quantile(0.01)

    normalised_ninety_nineth = MinCandle["normalised delta"].quantile(0.99)

    print("Normalised 1%:", normalised_first)
    print("Normalised 99%:", normalised_ninety_nineth)

    MinCandle["strong normalised sell delta"] = (MinCandle["normalised delta"] <= normalised_fifth)
    
    MinCandle["strong normalised buy delta"] = (MinCandle["normalised delta"] >= normalised_ninety_fifth)

    MinCandle["very strong normalised sell delta"] = (MinCandle["normalised delta"] <= normalised_first)

    MinCandle["very strong normalised buy delta"] = (MinCandle["normalised delta"] >= normalised_ninety_nineth)
   #creates normalised as boolean columns linking to normalised delta
    

    
    MinCandle["VWAP distance"] = (MinCandle["Close"] - MinCandle["VWAP"]) / MinCandle["VWAP"] * 100
    MinCandle["above VWAP"] = (MinCandle["VWAP distance"] > 0)
    MinCandle["absolute VWAP distance (%)"] = (MinCandle["VWAP distance"].abs())

    MinCandle["VWAP side"] = np.where(MinCandle["above VWAP"], "Above", "Below")

    MinCandle["VWAP distance"] = pd.qcut(MinCandle["absolute VWAP distance (%)"], q=5, labels=[
                                                                                            "Very close",
                                                                                            "Close",
                                                                                            "Medium",
                                                                                            "Far",
                                                                                            "Very far"])
    
    MinCandle["VWAP"].isna().sum()
    #point should now have all columns above + VWAP conditions 
    
    vwap_database = Robust_VWAP(MinCandle, return_periods, 1)
    
    #final should have data organised as summaried returns + stats
    #export in func
    return trades

def Buy_Sell(trades):
    
    buy_volume = trades["quantity"].where(trades["is_buyer_maker"] == 0,0)

    sell_volume = trades["quantity"].where(trades["is_buyer_maker"] == 1,0)

    trades["buy_volume"] = buy_volume
    trades["sell_volume"] = sell_volume
    return trades
    
def create_candles(trades, interval):
    
    trades = trades.set_index("time")

    candle = trades.resample(interval).agg(
        Open=("price", "first"),
        Close=("price", "last"),
        High=("price", "max"),
        Low=("price", "min"),
        volume=("quantity", "sum"),
        buy_volume=("buy_volume", "sum"),
        sell_volume=("sell_volume", "sum"),
        trade_count=("trade_id", "count")
        )
    candle = candle.dropna(subset=["Open"])
    
    return candle
        
def delta_finder(candle):
    

    candle["delta"] = (candle["buy_volume"] - candle["sell_volume"])
    #create delta column

    candle["normalised delta"] = (candle["delta"] / candle["volume"]) * 100
    #create normalised delta column

    return candle


def returns(candle, time_periods, timeframe, MinPrices):
    

    Min = int(pd.Timedelta(timeframe).total_seconds() / 60)
    
    close_time = ( candle.index + pd.Timedelta(minutes=Min - 1))

    for i in time_periods:

        future_intervals = (close_time + pd.Timedelta(minutes=i))
        future_close = MinPrices["Close"].reindex(future_intervals)
        future_close.index = candle.index

       
        
        column_name = (f"forward_{i}m_return")

        candle[column_name] = ((future_close / candle["Close"]) - 1) * 100

    return candle

def summarise_returns(candle, condition, time_periods):
    
    selected_candles = candle[candle[condition]]
    results = []
    for i in time_periods:
        return_column = (f"forward_{i}m_return")

        if return_column not in candle.columns:
            continue

        returns = selected_candles[return_column].dropna()




        results.append(
            {
                "condition": condition,
                "minutes forward": i,
                "events": len(returns),
                "average movement(%)": (returns.mean()),
                "median movement(%)": (returns.median()),
                "standard deviation (%)": returns.std(),
                "positive movements": (returns > 0).sum(),
                "Positive movements (%)": ((returns > 0).mean() * 100)
            }
        )

    return pd.DataFrame(results)

def correlation(candle):
    results = []
    periods = [1, 5, 15, 30, 60]
    delta_columns = ["delta", "normalised delta"]
    for i in delta_columns:
        for j in periods:
            return_column = f"forward_{j}m_return"
            data = candle[[i, return_column]].dropna()

            pearson = data[i].corr(data[return_column])
            Drank = data[i].rank()
            Rrank = data[return_column].rank()

            spearman = Drank.corr(Rrank)
            results.append({"Condition": i,
                            "Minutes Forward": j,
                            "Pearson Correlation": pearson,
                            "Spearman Correlation": spearman})
    
        
    table = pd.DataFrame(results)
    
    excel_file = r"C:\Users\Zac\OneDrive\Documents\BTC_delta_results_15min.xlsx"

    with pd.ExcelWriter(excel_file, engine="openpyxl", mode="a", if_sheet_exists="replace") as writer:
        table.to_excel(writer, sheet_name="Correlations", index=False)

    return table
    
def Statistics(candle, timeframe):
    results= []
    periods = [1, 5, 15, 30, 60]
    timeframes = int(pd.Timedelta(timeframe).total_seconds() / 60)
    Tests = [{"Measure": "Raw delta",
              "Strength": "Strong",
              "Buy": "strong buy delta",
              "Sell": "strong sell delta"},
             {"Measure": "Raw delta",
              "Strength": "Very strong",
              "Buy": "very strong buy delta",
              "Sell": "very strong sell delta"},
             {"Measure": "Normalised delta",
              "Strength": "Strong",
              "Buy": "strong normalised buy delta",
              "Sell": "strong normalised sell delta"},
             {"Measure": "Normalised delta",
              "Strength": "Very strong",
              "Buy": "very strong normalised buy delta",
              "Sell": "very strong normalised sell delta"}]
    for i in Tests:
        buy = i["Buy"]
        sell = i["Sell"]
        for j in periods:
            return_column = f"forward_{j}m_return"
            returns = pd.to_numeric(candle.loc[complete, return_column], errors="coerce").dropna()
            data = candle[[return_column, buy, sell]].dropna()
            y = data[return_column]
            x = data[[buy, sell]].astype(int)
            x = sm.add_constant(x)
            lag = max(math.ceil(j / timeframes) - 1, 0)
            model = sm.OLS(y, x).fit(cov_type="HAC", cov_kwds={ "maxlags": lag, "use_correction": True})
            for z in [buy, sell]:
                observations = len(returns)
                mean = returns.mean()
                median = returns.median()
                positivePercentage = (returns > 0).mean() * 100
                SD = returns.std()
                t_statistic, p_value = stats.ttest_1samp(returns, popmean=0)
                error = stats.sem(returns)
                CI = stats.t.interval(confidence=0.95, df=observations - 1, loc=mean, scale=error)
                
                results.append({"Measure": i["Measure"],
                                "Strength": i["Strength"],
                                "Condition": z,
                                "Minutes Forward": j,
                                "Observations": len(data),
                                "Events": observations,
                                "t-statistic": t_statistic,
                                "p-value": p_value,
                                "95% CI lower": low,
                                "95% CI upper": upper})
    results_table = pd.DataFrame(results)
    rejected, adjusted_p_values, _, _ = multipletests(results_table["p-value"], method="holm")
    results_table["Adjusted p-value"] = adjusted_p_values
    results_table["Significant at 5%"] = results_table["p-value"] < 0.05
    results_table["Significant after adjustment"] = rejected
    #adjusted using multiple testing return 
    excel_file = r"BTC_delta_results_15min.xlsx"

    with pd.ExcelWriter(excel_file, engine="openpyxl", mode="a", if_sheet_exists="replace") as writer:
        results_table.to_excel(writer, sheet_name="Statistics", index=False)
    #export
    return results_table



def economic(MinCandle, condition, Exit):
    
   invest = 100
    x = 1
    maker = 0.001
    taker = 0.001

    returns = MinCandle.loc[MinCandle[condition] == True, (f"forward_{Exit}m_return")].dropna()
    gross = returns
    
    gross_profit = invest * (gross / 100)
    
    entry = invest * maker
    exit_value = invest * (1 + returns / 100)

    exit_fee = exit_value * taker
    total_fees = entry + exit_fee
    net_profit = gross_profit - total_fees
    net_returns = (net_profit / invest) * 100
    
    
    print(total_fees)
    print("gross profit:", (gross_profit.sum()))
    print("gross profit (%):", ((gross_profit / 100) * 100).sum())
    print(net_profit.sum())
    
    
    print("net profit:", net_returns.sum())
    print("profitable trades after fees", (net_profit > 0).sum())
    
    

def Robust_VWAP(candle, return_periods, timeframe):
    conditions = [
        "strong sell delta",
        "strong buy delta",
        "very strong sell delta",
        "very strong buy delta",
        "strong normalised sell delta",
        "strong normalised buy delta",
        "very strong normalised sell delta",
        "very strong normalised buy delta"
    ]
    vwap = []
    for x in candle["VWAP side"].dropna().unique():
        side = candle["VWAP side"] == x
        vwap.append({ "VWAP test type": "VWAP position",
                         "VWAP condition": str(x),
                         "Mask": side})
        #list of conditions for position
        #Mask select row with condition
    for z in candle["VWAP distance"].dropna().unique():
        distance =(candle["VWAP distance"] == z)
        vwap.append({"VWAP test type": "VWAP distance",
                     "VWAP condition": str(z),
                     "Mask": distance})
            
        #list of conditions for distance
    for x in candle["VWAP side"].dropna().unique():
        for z in candle["VWAP distance"].dropna().unique():
            combine = (candle["VWAP side"] == x) & (candle["VWAP distance"] == z)
            vwap.append({"VWAP test type": "Position and distance",
                         "VWAP condition": f"{x} / {z}",
                         "Mask": combine})
        #combine for distance and position
    results = []
    

    for i in conditions:
        delta = candle[i]
        #condition loop
        for z in vwap:
            complete = (delta & z["Mask"])
                 # True if both
            for j in return_periods:
                 
                return_column = f"forward_{j}m_return"
                returns = pd.to_numeric(candle.loc[complete, return_column], errors="coerce").dropna()

                observations = len(returns)
                mean = returns.mean()
                median = returns.median()
                positivePercentage = (returns > 0).mean() * 100
                SD = returns.std()
                t_statistic, p_value = stats.ttest_1samp(returns, popmean=0)
                error = stats.sem(returns)
                CI = stats.t.interval(confidence=0.95, df=observations - 1, loc=mean, scale=error)
                #mean, n-1, standard
                
                results.append({
                    "Condition": i,
                    "Forward period": f"{j} minutes",
                    "VWAP test type": z["VWAP test type"],
                    "VWAP condition": z["VWAP condition"],
                    "Observations": observations,
                    "Mean return (%)": mean,
                    "Median return (%)": median,
                    "Positive returns (%)": positivePercentage,
                    "Standard deviation": SD,
                    "T-statistic": t_statistic,
                    "P-value": p_value,
                    "95% CI lower": CI[0],
                    "95% CI upper": CI[1]
                })
   
    
    results = pd.DataFrame(results)
    if results.empty:
        return results
    results["P-value accepted"] = (results["P-value"].notna() & (results["P-value"] < 0.05))
    results["P-value"] = pd.to_numeric(results["P-value"], errors="coerce")
    
    valid = results.index[results["P-value"].notna()]
    
    
    results["Adjusted P-value"] = np.nan
    results["Reject null"] = False
    
    
    
    rejected, adjusted_p_values, _, _ = multipletests(results.loc[valid, "P-value"].astype(float), alpha=0.05, method="fdr_bh")
    results.loc[valid, "Adjusted P-value"] = adjusted_p_values
    results.loc[valid, "Reject null"] = rejected
    
##    file_name = f"Robustness Test.xlsx"
##   
##
##    with pd.ExcelWriter(file_name, engine="openpyxl") as writer:
##        results.to_excel(writer, sheet_name="VWAP Robust", index=False)


    
    
    return results
def Robust_CVD(candle, return_periods, timeframe):
    conditions = [
        "strong sell delta",
        "strong buy delta",
        "very strong sell delta",
        "very strong buy delta",
        "strong normalised sell delta",
        "strong normalised buy delta",
        "very strong normalised sell delta",
        "very strong normalised buy delta"
    ]
    CVDConditions = ["Positive", "Negative"]
    results = []
    
    for i in conditions:
        delta = (candle[i].fillna(False).astype(bool))

        for z in CVDConditions:
            cvdM = candle["CVD condition"].eq(z)
            
            complete = (delta & cvdM)
                 
            for j in return_periods:
                 
                return_column = f"forward_{j}m_return"
                returns = pd.to_numeric(candle.loc[complete, return_column], errors="coerce").dropna()

                observations = len(returns)
                mean = returns.mean()
                median = returns.median()
                positivePercentage = (returns > 0).mean() * 100
                SD = returns.std()
                t_statistic, p_value = stats.ttest_1samp(returns, popmean=0)
                error = stats.sem(returns)
                CI = stats.t.interval(confidence=0.95, df=observations - 1, loc=mean, scale=error)
                
                
                results.append({
                    "Condition": i,
                    "Forward period": f"{j} minutes",
                    "CVD condition": z,
                    "Observations": observations,
                    "Mean return (%)": mean,
                    "Median return (%)": median,
                    "Positive returns (%)": positivePercentage,
                    "Standard deviation": SD,
                    "T-statistic": t_statistic,
                    "P-value": p_value,
                    "95% CI lower": CI[0],
                    "95% CI upper": CI[1]
                })
    results = pd.DataFrame(results)
    results["P-value accepted"] = (results["P-value"].notna() & (results["P-value"] < 0.05))
    results["P-value"] = pd.to_numeric(results["P-value"], errors="coerce")
    
    valid = results.index[results["P-value"].notna()]
    
    
    results["Adjusted P-value"] = np.nan
    results["Reject null"] = False
    
    
    
    rejected, adjusted_p_values, _, _ = multipletests(results.loc[valid, "P-value"].astype(float), alpha=0.05, method="fdr_bh")
    results.loc[valid, "Adjusted P-value"] = adjusted_p_values
    results.loc[valid, "Reject null"] = rejected
    file_name = r"Robustness Test.xlsx"
    with pd.ExcelWriter(file_name, engine="openpyxl", mode="a", if_sheet_exists="replace") as writer:
        results.to_excel(writer, sheet_name="CVD Robust", index=False)
        sheet = writer.sheets["CVD Robust"]
        sheet.freeze_panes = "A2"
        sheet.auto_filter.ref = sheet.dimensions

    

Main()
