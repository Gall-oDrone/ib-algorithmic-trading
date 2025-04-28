import pandas as pd

def getOpenOrderDF():
    return pd.DataFrame(columns=["PermId","ClientID","OrderId",
                                 "Account","Symbol","SecType",
                                 "Exchange","Action","OrderType",
                                 "TotalQty","CastQty","LastPrice",
                                 "AuxPrice","Status"])