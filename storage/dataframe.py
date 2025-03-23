from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract
import pandas as pd

def dataDataFrame(tradeAppObj,tickers):
    df_dict = {}
    for ticker in tickers:
        df_dict[ticker] = pd.DataFrame(tradeAppObj.data[tickers.index(ticker)])
        df_dict[ticker].set_index("Date",inplace=True)
    return df_dict