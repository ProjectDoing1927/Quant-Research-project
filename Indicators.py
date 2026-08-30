import numpy as np
import pandas as pd

def CVD(candle):
    reset = candle.index.floor("7D")
    candle["CVD"] = candle.groupby(reset)["delta"].cumsum()
    candle["CVD condition"] = pd.Series(pd.NA, index=candle.index, dtype="string")
    candle.loc[candle["CVD"] > 0, "CVD condition"] = "Positive"
    candle.loc[candle["CVD"] < 0, "CVD condition"] = "Negative"
    return candle
    
    
  

def VWAP(trades):
    trades = trades.sort_values("time")
    daily = trades["time"].dt.floor("1D")
    

    PriceVol = trades["price"] * trades["quantity"]
    CumPriceVol = PriceVol.groupby(daily).cumsum()
    CumVol = trades["quantity"].groupby(daily).cumsum()
    trades["VWAP"] = CumPriceVol / CumVol
    


    return trades
   
    
def Absorption(candle):
    candle["price change (%)"] = (candle["Close"] - candle["Open"]) / candle["Open"] * 100

    candle["directional price response"] = candle["price change (%)"] * np.sign(candle["normalised_delta"])
    
    candle["weak price response"] = candle["directional price response"] <= 0.05

    candle["strong buy absorption"] = candle["strong buy delta"] & candle["weak price response"]

    candle["strong sell absorption"] = candle["strong sell delta"] & candle["weak price response"]

    candle["very strong buy absorption"] = candle["very strong buy delta"] & candle["weak price response"]

    candle["very strong sell absorption"] = candle["very strong sell delta"] & candle["weak price response"]

    return candle
