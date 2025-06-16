"""
IBAPI - Getting Account Summary

@author: Diego Gallo
"""

from ibapi.client import EClient
from ibapi.wrapper import EWrapper
import pandas as pd

class IBAccountSummary(EWrapper, EClient):

    def __init__(self):
        EClient.__init__(self, self)
        self.account_summary = pd.DataFrame(columns=['ReqId', 'Account', 'Tag', 'Value', 'Currency'])
        self.pnl = pd.DataFrame(columns=['ReqId', 'DailyPnL', 'UnrealizedPnL', 'RealizedPnL'])

    def accountSummary(self, reqId, account, tag, value, currency):
        super().accountSummary(reqId, account, tag, value, currency)
        self.account_summary = self.account_summary.append({'ReqId': reqId, 'Account': account, 'Tag': tag, 'Value': value, 'Currency': currency}, ignore_index=True)
    
    def getAccountSummary(self):
        return self.account_summary
    
    def pnl(self, reqId, dailyPnL, unrealizedPnL, realizedPnL):
        super().pnl(reqId, dailyPnL, unrealizedPnL, realizedPnL)
        self.pnl = self.pnl.append({'ReqId': reqId, 'DailyPnL': dailyPnL, 'UnrealizedPnL': unrealizedPnL, 'RealizedPnL': realizedPnL}, ignore_index=True)
    
    def getPnl(self):
        return self.pnl