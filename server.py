# Coinigy server module bn
import logging
from coinigy_api_rest import CoinigyREST
from coinigy_api_websocket import CoinigyWebSocket
from collections import namedtuple

# Coinigy full API (REST + WebSocket)
class CoinigyAPI :
    def __init__(self, apiKey, apiSecret, reconnect=True, wsURL='wss://sc-02.coinigy.com/socketcluster/', restURL='https://api.coinigy.com/api/v1'):
        self.logger = logging.getLogger('root')
        self.logger.debug("Initialize Coinigy API")
        # WEB SOCKET
        self.ws = CoinigyWebSocket()
        self.ws.connect(apiKey, apiSecret, wsURL) # Connect to websocket
        # REST
        credentials = namedtuple('credentials', ('api','secret','endpoint'))
        credentials.api = apiKey
        credentials.secret = apiSecret
        credentials.endpoint =  restURL

        self.rest = CoinigyREST(credentials)


    #get all exchange pairs (asynchronus)
    def getFxPairs(self, exchangeCode):
        return self.rest.markets(exchangeCode)

    # get all available exchanges (synchronus)
    def getAllExchanges(self):
        return self.rest.exchanges()

    def getAsks(self, exchangeCode, pairCode):
        return self.rest.asks(exchangeCode, pairCode)

    def getBids(self, exchangeCode, pairCode):
        return self.rest.bids(exchangeCode, pairCode)

    def getOrders(self, exchangeCode, pairCode):
        return self.rest.orders(exchangeCode, pairCode)

    def getHistory(self, exchangeCode, pairCode):
        return self.rest.history(exchangeCode, pairCode)

    # susbcribe for the channel
    # channelcode: "METHOD-EXCHANGECODE--PRIMARYCURRENCY--SECONDARYCURRENCY"
    # supported methods: TRADE, ORDER, NEWS, BLOCK, TICKER
    def subscribe(self, channelcode, channelhandler):
        return self.ws.subscribe(channelcode, channelhandler)


# executing code
if __name__ == '__main__':
    pass