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
        self.logger = logging.getLogger('exchange')
        #self.logger.disabled = True
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
            #save pair in the matrix
            self.fxPairs.set_value(index, 'pair_obj', pair)

            # subscribe for events
            # ORDER
            # "METHOD-EXCHANGECODE--PRIMARYCURRENCY--SECONDARYCURRENCY"
            channel = "ORDER-" + row["exch_code"] + "--" + base + "--" + quote
            self.logger.info("SUSBSCRIBE %s" % channel)
            # pair will be in charge of processing all events
            self.coinigyAPI.subscribe(channel, pair.orderEventHandler)
            # TRADE
            channel = "TRADE-" + row["exch_code"] + "--" + base + "--" + quote
            self.logger.info("SUSBSCRIBE %s" % channel)
            # pair will be in charge of processing all events
            self.coinigyAPI.subscribe(channel, pair.tradeEventHandler)

        #self.fxPairs = self.fxPairs.loc[self.fxPairs["pair_obj"].bool()]
        self.fxPairs = self.fxPairs.dropna() # drop raws with nan
        #self.logger.info(self.fxPairs)


    # retrun fx pairs available in the exchange
    def getFxPairs(self):
        return self.fxPairs["pair_obj"]

    def requestAskBook(self, pair):
        asks = self.coinigyAPI.getAsks(self.exchangeCode, pair.getPairCode())
        if asks is not None:
            pair.updateAskBook(asks)

    def requestBidBook(self, pair):
            bids = self.coinigyAPI.getBids(self.exchangeCode, pair.getPairCode())
            if bids is not None:
                pair.updateBidBook(bids)

    def requestOrderBook(self, pair):
            orders = self.coinigyAPI.getOrders(self.exchangeCode, pair.getPairCode())
            if orders is not None:
                pair.updateBidBook(orders["bids"])
                pair.updateAskBook(orders["asks"])

    # set event handler
    def setEventHandler(self, tradeHandler = None, orderHandler = None):
        if tradeHandler is not None: self.userTradeHandler = tradeHandler
        if orderHandler is not None: self.userOrderHandler = orderHandler

    #Trade Handler (called by FXPair)
    def tradeHandler(self, updatedPair):
        if self.userTradeHandler is not None: self.userTradeHandler(updatedPair) # call user call back

    #Order handler (called by FXPair)
    def orderHandler(self, updatedPair):
        if self.userOrderHandler is not None: self.userOrderHandler(updatedPair) # call user call back

    # convert currency
    def getExchangeRate(self, _from, _to, _type='ASK'):
        if _from == _to:
            return 1

        for  index, row in self.fxPairs.iterrows():
            c = row['pair_obj']
            if c.getQuote() == _to and c.getBase() == _from:
                if _type == 'ASK':
                    return c.getAverageAskPrice(1)
                else:
                    return c.getAverageBidPrice(1)
            elif  c.getQuote() == _from and c.getBase() == _to:
                if _type == 'ASK':
                    return 1/c.getAverageAskPrice(1)
                else:
                    return 1/c.getAverageBidPrice(1)
        raise # error