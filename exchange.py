# crypto exchange
import logging
from server import CoinigyAPI
from pair import FXPair

#cridentials
g_apiKey="acc223ec3b64d19d8aa060bde7af0cb1"
g_apiSecret="da3eaed8d1a426b51a447634796373ea"

class Exchange():
    def __init__(self, code, name, coinigyAPI, askbookDepth = 5, bidBookDepth = 5, orderDepth = 5):
        self.logger = logging.getLogger('root')
        self.exchangeName = name
        self.exchangeCode = code
        self.askbookDepth = askbookDepth
        self.bidBookDepth = bidBookDepth
        self.orderDepth = orderDepth
        # get all exchange pairs
        self.coinigyAPI = coinigyAPI

        self.fxPairs = coinigyAPI.getFxPairs(code) # get all pairs
        self.logger.info(self.fxPairs)
        #self.fxPairs["base"], self.fxPairs["quote"] = self.fxPairs["mkt_name"].split("/")
        #"METHOD-EXCHANGECODE--PRIMARYCURRENCY--SECONDARYCURRENCY"
        # subscribe for all pairs
        for index, row in self.fxPairs.iterrows():
            #c = row["exch_code"]
            #id = row["exch_id"]
            #n = row["exch_name"]
            base, quote = row["mkt_name"].split("/")
            #self.fxPairs[index]["base"] = base
            #self.fxPairs[index]["quote"] = quote
            # create channel name
            channel = "ORDER-" + row["exch_code"] + "--" + base + "--" + quote
            self.logger.info(channel)
            self.coinigyAPI.subscribe(channel, self.__orderhandler)

        self.logger.info(self.fxPairs)
            #askSubscribtion = "ASKS-" + code + "--" + pair.getBase() + "--" + pair.getQuote()
            #coinigyAPI.subscribe(askSubscribtion, self.__askhandler)
            #bidSubscribtion = "BIDS-" + code + "--" + pair.getBase() + "--" + pair.getQuote()
            #coinigyAPI.subscribe(bidSubscribtion, self.__bidhandler)
            #orderSubscribtion = "ORDERS-" + code + "--" + pair.getBase() + "--" + pair.getQuote()
            #coinigyAPI.subscribe(orderSubscribtion, self.__orderhandler)

    # process ask handlers
    def __askhandler(self, channel, error, *args):
        pass

    def __bidhandler(self, channel, error, *args):
        pass

    def __orderhandler(self, channel, error, *args):
        pass