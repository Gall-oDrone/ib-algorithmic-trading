orders = {
    "buy":{
        "limit":{
            "test_1": {"action":"BUY", "orderType":"LMT", "orderTotalQuantity":1, "orderLmtPrice":80, "orderDiscretionaryAmt":False},
            "test_2": {"action":"BUY", "orderType":"LMT", "orderTotalQuantity":2, "orderLmtPrice":50, "orderDiscretionaryAmt":False},
        },
        "market":{
            "test_1": {"action":"BUY", "orderType":"MKT", "orderTotalQuantity":1, "orderDiscretionaryAmt":False}
        },
        "stop":{
            "test_1": {"action":"BUY", "orderType":"STP", "orderTotalQuantity":1, "orderAuxPrice":40, "orderDiscretionaryAmt":False}
        },
        "trailStop":{
            "test_1": {"action":"BUY", "orderType":"TRAIL", "orderTotalQuantity":1, "orderAuxPrice":40, "orderDiscretionaryAmt":False, "orderTrailStopPrice":10, "orderTrailingStop":1}
        }
    },
    "sell":{
        "limit":{
            "test_1": {"action":"SELL", "orderType":"LMT", "orderTotalQuantity":1, "orderLmtPrice":80, "orderDiscretionaryAmt":False},
        },
        "market":{
            "test_1": {"action":"SELL", "orderType":"MKT", "orderTotalQuantity":1, "orderDiscretionaryAmt":False}
        },
        "stop":{
            "test_1": {"action":"SELL", "orderType":"STP", "orderTotalQuantity":1, "orderAuxPrice":40, "orderDiscretionaryAmt":False}
        }
    }
}