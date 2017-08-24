# crypto exchange
import logging
from coinigy_server import CoinigyAPI
from pair import FXPair
import numpy as np

#cridentials
g_apiKey="acc223ec3b64d19d8aa060bde7af0cb1"
g_apiSecret="da3eaed8d1a426b51a447634796373ea"

class Exchange():
    def __init__(self, code, name, coinigyAPI, allowedPairs = [], askbookDepth = 5, bidBookDepth = 5, orderDepth = 50):
        self.logger = logging.getLogger('root')
        self.logger.disabled = True
        self.exchangeName = name
        self.exchangeCode = code
        self.askbookDepth = askbookDepth
        self.bidBookDepth = bidBookDepth
        self.orderDepth = orderDepth
        # get all exchange pairs
        self.coinigyAPI = coinigyAPI

        self.fxPairs = coinigyAPI.getFxPairs(code) # get all pairs

        # subscribe for all pairs in this exchange
        self.fxPairs['pair_obj']=np.nan # new column to store pair object
        self.logger.info(self.fxPairs)
        for i, (index, row) in enumerate(self.fxPairs.iterrows()):
            #c = row["exch_code"]
            #id = row["exch_id"]
            #n = row["exch_name"]
            if not row["mkt_name"] in allowedPairs and not not allowedPairs: # double not to trick Python convert list tp bool
                continue # skipp all pairs which are not present in the allowedlist
            base, quote = row["mkt_name"].split("/")

            # create pair
            pair = FXPair(base, quote,
                          exchmkt_id = row["exchmkt_id"],
                          exchange = self,
                          currentPrice=np.NaN,
                          askBookDepth= askbookDepth,
                          bidBookDepth = bidBookDepth,
                          orderHistoryDepth= orderDepth)

            self.fxPairs.set_value(index, 'pair_obj', pair)

            # subscribe for events
            # ORDER
            # "METHOD-EXCHANGECODE--PRIMARYCURRENCY--SECONDARYCURRENCY"
            channel = "ORDER-" + row["exch_code"] + "--" + base + "--" + quote
            self.logger.info(channel)
            # pair will be in charge of processing all events
            self.coinigyAPI.subscribe(channel, pair.orderEventHandler)
            # TRADE
            channel = "TRADE-" + row["exch_code"] + "--" + base + "--" + quote
            self.logger.info(channel)
            # pair will be in charge of processing all events
            self.coinigyAPI.subscribe(channel, pair.tradeEventHandler)

        #self.fxPairs = self.fxPairs.loc[self.fxPairs["pair_obj"].bool()]
        self.fxPairs = self.fxPairs.dropna() # drop raws with nan
        self.logger.info(self.fxPairs)


    # retrun fx pairs available in the exchange
    def getFxPairs(self):
        return self.fxPairs["pair_obj"]

    # set event handler
    def setEventHandler(self, event, handler):
        self.handlers[event] = handler