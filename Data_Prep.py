import sqlite3
import json
import pandas as pd
pd.set_option("display.max_columns", None)
pd.set_option("display.width", 200)


from pathlib import Path

CSV = r"C:\Users\Zac\Downloads\BTCUSDT-aggTrades-2026-06 (1).zip"
csv_path = Path(CSV)


def load_csv(csv_file):
    trades = pd.read_csv( csv_file, compression="zip")
    trades = trades.rename(columns={"agg_trade_id": "trade_id",
                                    "transact_time": "timestamp"})
    #code set up for "timestamp" and "trade_id"
    required_columns = [ "trade_id", "price", "quantity", "timestamp", "is_buyer_maker"]
    #Binance has an extracolumn of data, not common for all files
    trades = trades[required_columns]
    #better to get rid of extra columns, for tables
    return trades
    






def load_data(data):
    #used for dbs files
    connection = sqlite3.connect(data)
    #connection
    everything = "SELECT * FROM trades"
    #selects all column and rows
    trades = pd.read_sql_query(everything, connection)
    #all columns and rows
    connection.close()
    #no need for connection
    return trades


def clean(trades, time_unit="ms"):
    num_rows = len(trades)

    CleanTrades = trades.drop_duplicates(subset="trade_id")

    columns = [ "price", "quantity", "is_buyer_maker", "timestamp" ]
    CleanTrades = CleanTrades.dropna( subset=columns)
    CleanTrades = CleanTrades[
        (CleanTrades["price"] > 0) &
        (CleanTrades["quantity"] > 0) &
        (CleanTrades["timestamp"] > 0) &
        (CleanTrades["is_buyer_maker"].isin([0,1]))
        ].copy()
    #no negatives should be present in data
    CleanTrades["time"] = pd.to_datetime( CleanTrades["timestamp"], unit=time_unit, utc=True)
    CleanTrades = CleanTrades.sort_values("time")
    CleanTrades = CleanTrades.reset_index(drop=True)

    

    return CleanTrades



def del_timegaps(CleanTrades):
    time_difference = (CleanTrades["time"].diff())
    #difference between columns should be 1

    gap_found = time_difference > 1

    gaps = CleanTrades.loc[gap_found, ["time"]]
    #selects row when True
    gaps["gap"] = time_difference[gap_found]
    #0 gaps found so stopped

    return gaps

def remove_early_data(CleanTrades, start_time):
    #use for selceted start date
    rows_before_removal = len(CleanTrades)

    start_time = pd.to_datetime(start_time, utc=True)
    #translates exchange data
    CleanTrades = CleanTrades[CleanTrades["time"] >= start_time]
    
    CleanTrades = CleanTrades.reset_index(drop=True)

    rows_removed = (rows_before_removal - len(CleanTrades))

    

    return CleanTrades


def prepare_trades(data, start_time=None):
    #trades = load_data(data)
    #CleanTrades = clean(trades)
    #if start_time is not None:
        #CleanTrades = remove_early_data( CleanTrades, start_time)
    #return CleanTrades

    if ((data).lower()).endswith(".db"):
        trades = load_data(data)
        time_unit = "ms"
    elif ((data).lower()).endswith(".csv") or ((data).lower()).endswith(".zip"):
        trades = load_csv(data)
        time_unit = "ms"
    

    CleanTrades = clean(trades, time_unit=time_unit)
    if start_time is not None:
        CleanTrades = remove_early_data(CleanTrades, start_time)

    return CleanTrades

    
        







   


