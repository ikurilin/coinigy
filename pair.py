# Currency pair aaa
import logging
import numpy as np
import pandas as pd

class FXPair():
    def __init__(self, base, quote, exchmkt_id,
                 currentPrice = None, orderHistory = None, asks = None, bids = None,
                 askBookDepth = 5, bidBookDepth = 5, orderHistoryDepth = 50):
        self.logger = logging.getLogger('root')
        self.base = base
        self.quote = quote
        self.exchmkt_id = exchmkt_id
        self.currentFX = currentPrice
        self.askbookDepth = askBookDepth
        self.bidBookDepth = bidBookDepth
        self.orderHistoryDepth = orderHistoryDepth  # history
        # save initial data
        if orderHistory is not None:
            self.orderHistory = orderHistory.head(orderHistoryDepth) # history
            self.orderHistory.drop(labels=["base_ccy","counter_ccy"], axis=1, inplace=True)
        else:
            self.orderHistory = pd.DataFrame()
        if asks is not None:
            self.asks = asks.head(askBookDepth)
            self.asks.drop(labels=["base_ccy","counter_ccy"], axis=1, inplace=True)
        else:
            self.asks = pd.DataFrame()
        if  bids is not None:
            self.bids = bids.head(bidBookDepth)
            self.bids.drop(labels=["base_ccy", "counter_ccy"], axis=1, inplace=True)
        else:
            self.bids = pd.DataFrame()

    #Trade event handler
    def tradeEventHandler(self, channel, *args):
        return
        self.logger.info("PAIR %s/%s TRADE EVENT HANDLER %s with %d arguments" % (self.base, self.quote, channel, len(args)))
        if len(args) != 1:
            return
        d = args[0]
        #self.logger.info(d)
        #create a data frame row
        list = [{
            #"time_local" : d["timestamp"],
            "price" : d["price"],
            "quantity" : d["quantity"],
            "type" : d["type"],
            "base_ccy" : self.base,
            "counter_ccy" : self.quote
                 }]
        newRow = pd.DataFrame(list, index=[ pd.to_datetime(d["timestamp"])])
        self.orderHistory = self.orderHistory.append(newRow)
        self.orderHistory.index.name = "time_local"
        self.orderHistory.sort_index(inplace=True, ascending=False)
        self.orderHistory = self.orderHistory.head(self.orderHistoryDepth) # keep only first required values
        self.logger.info(self.orderHistory)

    # exchange event handler: ORDER,
    def orderEventHandler(self, channel, *args):
        return
        self.logger.info("PAIR EVENT HANDLER %s with %d arguments" % (channel,len(args)))
        if len(args) != 1:
            return
        # cast data types

        d = args[0]
        dat = pd.DataFrame.from_records(d)
        if 'price' in dat.columns:
            dat.price = dat.price.astype(np.float)
        if 'quantity' in dat.columns:
            dat.quantity = dat.quantity.astype(np.float)
        if 'total' in dat.columns:
            dat.total = dat.total.astype(np.float)
        if 'time_local' in dat.columns:
            dat.time_local = pd.to_datetime(dat.time_local)
            dat.set_index('time_local', inplace=True)
        if 'type' in dat.columns:
            dat.type = dat.type.astype(str)
        if not dat.empty:
            pass
            #dat['base_ccy'] = d['primary_curr_code']
            #dat['counter_ccy'] = d['secondary_curr_code']

        #self.logger.info(dat)
        #self.logger.info("BIDS BEFORE UPDATE")
        #self.logger.info( self.bids)
        asks = dat.loc[dat['ordertype'] == "Sell"]
        asks.drop(labels=["ordertype"], axis=1, inplace=True)
        asks.sort_values(by="price", ascending=False, inplace=True)
        bids = dat.loc[dat['ordertype'] == "Buy"]
        bids.drop(labels=["ordertype"], axis=1, inplace=True)
        bids.sort_values(by="price", ascending=False, inplace=True )
        # UPDATE BID BOOK
        self.bids = bids.head(self.bidBookDepth)
        self.logger.info("BIDS AFTER UPDATE")
        self.logger.info(self.bids)

        # UPDATE ASK BOOK
        #self.logger.info("ASKS BEFORE UPDATE")
        #self.logger.info(self.asks)
        self.asks = asks.head(self.askbookDepth)
        self.logger.info("ASKS AFTER UPDATE")
        self.logger.info(self.asks)

    # set current price
    def setCurrentFX(self, fx):
        self.currentFX = fx

    def getCurrentFX(self):
        return self.currentFX

    def getBase(self):
        return self.base

    def getQuote(self):
        return self.quote

    def getFullName(self):
        return self.getBase() + "/" + self.getQuote()

    def updateAskBook(self, asks):
        pass

    def updateBidBook(self, bids):
        pass

    def addTradingHistory(self, trades):
        pass

    def getAverageAskPrice(self, amt):
        pass

    def getAverageBidPrice(self, amt):
        pass

    def getAskBookDepth(self):
        pass

    def getBidBookDepth(self):
        pass

