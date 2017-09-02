# Currency pair aaa
import logging
import numpy as np
import pandas as pd

class FXPair():
    def __init__(self, base, quote, exchmkt_id, exchange,
                 currentPrice = None, askBookDepth = 5, bidBookDepth = 5, orderHistoryDepth = 50):
        self.logger = logging.getLogger('FXPair')
        self.logger.disabled = True
        self.base = base
        self.quote = quote
        self.exchmkt_id = exchmkt_id
        self.exchange = exchange
        self.currentFX = currentPrice
        self.askbookDepth = askBookDepth
        self.bidBookDepth = bidBookDepth
        self.orderHistoryDepth = orderHistoryDepth  # history
        self.tradeHistory = pd.DataFrame()
        self.asks = pd.DataFrame()
        self.bids = pd.DataFrame()
        self.orderForceRequestInitiated = [] # keep track of force requests to get bids (call only once, data normally should be received via subscribe)
        #self.asksForceRequestInitiated = [] # keep track of force requests to get bids (call only once, data normally should be received via subscribe)


    #Trade event handler
    def tradeEventHandler(self, channel, *args):
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
        self.tradeHistory = self.tradeHistory.append(newRow)
        self.tradeHistory.index.name = "time_local"
        self.tradeHistory.sort_index(inplace=True, ascending=False)
        self.tradeHistory = self.tradeHistory.head(self.orderHistoryDepth) # keep only first required values
        self.setCurrentFX(self.tradeHistory.ix[0]["price"]) # set current price - the latest price
        self.logger.info(self.tradeHistory)
        # notify exchange of the update
        self.exchange.tradeHandler(self)

    # exchange event handler: ORDER,
    def orderEventHandler(self, channel, *args):
        self.logger.info("PAIR EVENT HANDLER %s with %d arguments" % (channel,len(args)))
        if len(args) != 1:
            return
        # cast data types

        d = args[0]
        dat = pd.DataFrame.from_records(d)
        if dat.empty:
            return # nothing to process
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

        try:
            asks = dat.loc[dat['ordertype'] == "Sell"] \
                .drop(labels=["ordertype"], axis=1) \
                .sort_values(by="price", ascending=False)
            self.updateAskBook(asks)
        except:
            pass

        try:
            bids = dat.loc[dat['ordertype'] == "Buy"] \
                .drop(labels=["ordertype"], axis=1) \
                .sort_values(by="price", ascending=False)
            self.updateBidBook(bids)
        except:
            pass

        #notify exchange of the update
        self.exchange.orderHandler(self)

    # update asks book
    def updateAskBook(self, askDataFrame):
        '''
        ASK DATAFRAME FORMAT
        INFO:    price    quantity      total
        0       36360.0   0.13400       4872.240
        1       36300.0   1.00000       36300.000
        '''
        #if not askDataFrame.empty:
        self.asks = askDataFrame.head(self.askbookDepth)
        if self.asks.empty and self in self.orderForceRequestInitiated:
            self.orderForceRequestInitiated.remove(self) # allow force data request
        self.logger.info("ASKS AFTER UPDATE")
        self.logger.info(self.asks)

    # update bids data
    def updateBidBook(self, bidDataFrame):
        # UPDATE BID BOOK
        #if not bidDataFrame.empty:
        self.bids = bidDataFrame.head(self.bidBookDepth)
        if self.bids.empty and self in self.orderForceRequestInitiated:
            self.orderForceRequestInitiated.remove(self) # allow force data request
        self.logger.info("BIDS AFTER UPDATE")
        self.logger.info(self.bids)

    # set current price
    def setCurrentFX(self, fx):
        self.currentFX = fx

    def getCurrentFX(self):
        return self.currentFX

    def getBase(self):
        return self.base

    def getQuote(self):
        return self.quote

    def getPairCode(self):
        return self.getBase() + "/" + self.getQuote()

    #request ask book from the server
    def requestAskBook(self):
        self.exchange.requestAskBook(self)

    #request bid book from the server
    def requestBidBook(self):
        self.exchange.requestBidBook(self)

    def requestOrderBook(self):
        self.exchange.requestOrderBook(self)

    def addTradingHistory(self, trades):
        pass

    def getAverageAskPrice(self, quoteAmt):
        '''
        Get the average ask book price for the given amt in quote currency
        BIDS DATAFRAME FORMAR
        INFO:  exchange       label       price         quantity            timestamp        total
        0     GATE          BTC/HKD     33951.1000       0.380      2017-08-25 12:54:38     12901.41800
        1     GATE          BTC/HKD     33951.0000       0.300      2017-08-25 12:54:38     10185.30000
        :param amt:
        :return:
        '''
        self.logger.info("Get average ASK price for %d  %s" % (quoteAmt, self.getPairCode()))
        #self.logger.info(self.asks)
        if not self.isAskAvailable():
            return 0 # no price available
        # find how deep need to go to fulfill required qnt
        amt = quoteAmt
        qnt = 0
        sum = 0
        for index, row in self.asks.iterrows():
            bQnt = min(amt / row['price'], row['quantity'] )
            sum += bQnt * row['price']
            amt -= bQnt * row['price']
            qnt += bQnt
            if amt == 0:
                break
        p = sum / qnt
        return p

    def getAverageBidPrice(self, baseAmt):
        '''
        Get the average bid book price for the given amt in base currency
        BIDS DATAFRAME FORMAR
        INFO:  exchange       label       price         quantity            timestamp        total
        0     GATE          BTC/HKD     33951.1000       0.380      2017-08-25 12:54:38     12901.41800
        1     GATE          BTC/HKD     33951.0000       0.300      2017-08-25 12:54:38     10185.30000
        :param amt:
        :return:
        '''
        self.logger.info("Get average BID price for %d %s" % (baseAmt, self.getPairCode()))
        #self.logger.info(self.bids)
        if not self.isBidAvailable():
           return 0 #  no data
        amt = baseAmt
        qnt = 0
        sum = 0
        for index, row in self.bids.iterrows():
            bQnt = min(amt, row['quantity'])
            sum += bQnt * row['price']
            amt -= bQnt
            qnt += bQnt
            if amt == 0:
                break
        p = sum / qnt
        return p


    #is bid price available?
    def isBidAvailable(self):
        if not self.bids.empty:
            return True
        # try to request missing data
        if  self.getPairCode() in self.orderForceRequestInitiated:
            return False # no data
        # initiate forced data request
        self.orderForceRequestInitiated.append(self.getPairCode())  # add record
        self.requestOrderBook()
        return not self.isBidAvailable()

    #is ask price available?
    def isAskAvailable(self):
        # self.logger.info(self)
        if not self.asks.empty:
            return True
        # try to request missing data
        if self.getPairCode() in self.orderForceRequestInitiated:
            return False  # no data available
        # initiate forced data request
        self.orderForceRequestInitiated.append(self.getPairCode())  # force request only once
        self.requestOrderBook()
        return not self.asks.empty

    # synonym names
    def isBitcoin(self, currency_name):
        return currency_name == "BTC" or currency_name == "XBT"

    # Return value of 1 BTC in Quote currency
    def get1BTCinQuote(self): # to remove
        if self.isBitcoin(self.getQuote()):
            return 1 # ETH / BTC
        elif self.isBitcoin(self.getBase()):
            return self.getCurrentFX() # BTC / HKD
        else: return 1 # TBC

    def getAskBookDepth(self):
        pass

    def getBidBookDepth(self):
        pass

    # Get book depth in Quote currency
    def getMaxBookQuote(self, _bid = False): # in quote currency
        book = self.bids if _bid else self.asks

        if (_bid and not self.isBidAvailable()) or \
            (not _bid and self.isAskAvailable()):
            return 0 # no data
        return (book['quantity']*book['price']).sum()

    # Get book depth in Base currency
    def getMaxBookBase(self, _bid=False):
        book = self.bids if _bid else self.asks

        if (_bid and not self.isBidAvailable()) or \
                (not _bid and not self.isAskAvailable()):
            return 0 # no data

        return book['quantity'].sum()

    # converts base currency to quote currency based on order book, caps amount by amt in the book
    def limitedConvertBase2Qnt(self, baseAmt, useAsk = False):
        bAmt = baseAmt
        sum = 0

        book = self.asks if useAsk else self.bids
        if (useAsk and not self.isAskAvailable()) or \
                (not useAsk and not self.isBidAvailable()):
            return 0 # no data

        # iterate book
        for index, row in book.iterrows():
            amt = min(bAmt, row['quantity'])
            sum += amt * row['price']
            bAmt -= amt
            if bAmt == 0:
                break

        return sum

    # converts quote currency to base currency based on order book, caps amount by available amt in the book
    def limitedConvertQnt2Base(self, qntAmt, useBid = False):
        #Convert quote currerncy to base -> standard long operation, use ASK book
        qAmt = qntAmt
        sum = 0

        book = self.bids if useBid else self.asks
        if (useBid and not self.isBidAvailable()) or \
                (not useBid and not self.isAskAvailable()):
            return 0 # no data

        for index, row in book.iterrows():
            amt = min(qAmt, row['quantity'] * row['price'] )
            sum += amt / row['price']
            qAmt -= amt
            if qAmt == 0:
                break

        return sum