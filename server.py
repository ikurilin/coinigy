# Coinigy server module bn
from socketclusterclient import Socketcluster
import logging
from time import sleep
import sys

class CoinigySoocket():
    def __init__(self):
        self.logger=logging.getLogger('root')
        self.__reset()

    def connect(self, apiKey, apiSecret, wsURL='"wss://sc-02.coinigy.com/socketcluster/"', channelcode = "TRADE-OK--BTC--CNY", channelHandler = None ):
        # Connects to the Coinigy API websocket and initializes data stores
        self.logger.debug("Connecting Websocket")
        self.logger.info("Conecting to %s" % wsURL)
        self.apiKey = apiKey
        self.apiSecret = apiSecret
        self.bAuthenticated = False # not yet authenticated
        self.bError = False # no errors yet
        self.socket = Socketcluster.socket(wsURL) # create socket connection

        # set basic event listeners
        self.socket.setBasicListener(self.__onconnect, self.__ondisconnect, self.__onconnecterror)
        # set authentication listeners
        self.socket.setAuthenticationListener(self.__onsetauthentication, self.__onauthentication)
        # initiate connecting sequence
        self.socket.connect()

        # wait for authentication
        conn_timeout = 5
        while(not self.bAuthenticated and conn_timeout and not self.bError) :
            sleep(1)
            conn_timeout -= 1

        if not conn_timeout or self.bError:
            self.logger.error("Couldn't authenticate the connection. Exiting")
            self.exit()
            sys.exit(1)

        #subscribe to channels
        if channelHandler :   self.__subscribe(channelcode, channelHandler )
        else: self.__subscribe(channelcode,self.__defaultchannelmessagehandler)

    def __defaultchannelmessagehandler(self, key, object):
        self.logger.info("Got data for key %s" % key)
        self.logger.info(object)


    # SetAuthentication event listener
    def __onsetauthentication(self, socket, token):
        self.logger.info("Authentication token received %s" % token)
        self.socket.setAuthtoken(token)

    def __onsubscribtionerrorhandler(self, channel, error, object):
        if error is '':
            self.logger.info("Subscribed successfully to channel %" % channel)
        else:
            self.logger.error("Cannot subscribe for channel %s" & channel)
            self.logger.info(error)
            self.bError = True

    # subscribe for a channel
    def __subscribe(self, channelCode, messageHandler):
        self.socket.subscribeack(channelCode, self.__onsubscribtionerrorhandler)
        self.socket.onchannel(channelCode, messageHandler)

    # authentication acknowledgement handler
    def __authenticationacknoledgmenthandler(self,eventname, error, object ):
        self.logger.info("authentication ack got called %s" % str(error))
        if error is '':
            # set authentication flag
            self.authenticated = True
        else:
            self.bError = True
            self.logger.error("Cannot authenticate connection %s" % str(error))
            self.logger.info(error)


    # Authentication event listener
    def __onauthentication(self, socket, isauthenticated):
        self.logger.info("Authenticated is %s" % str(isauthenticated))
        # send cridentials to the server
        api_credentials = {
            "apiKey": self.apiKey,
            "apiSecret": self.apiSecret
        }
        socket.emitack("auth", api_credentials, self.__authenticationacknoledgmenthandler)

    # onConnect event handler
    def __onconnect(self, socket):
        self.logger.info("on connect got called")

    # onDisconnect event handler
    def __ondisconnect(self, socket):
        self.logger.info("on disconnect got called")

    # onConnectError event handler
    def __onconnecterror(self, socket, error):
        self.logger.info("On connect error got called %s" % str(error))

