# Currency pair aaa
import logging


class FXPair():
    def __init__(self, base, quote, fx = None):
        self.logger = logging.getLogger('root')
        self.base = base
        self.quote = quote
        self.currentFX = fx

    # set current price
    def setCurrentFX(self, fx):
        self.currentFX = fx

    def getCurrentFX(self):
        return self.currentFX

    def getBase(self):
        return self.base

    def getQuote(self):
        return self.quote

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

