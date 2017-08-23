# Coinigy server module bn
from socketclusterclient import Socketcluster
import logging
from time import sleep
import sys
import threading

# Websocket API
class CoinigyWebSocket:
    def __init__(self):
        self.logger = logging.getLogger('root')

    def connect(self,
                apiKey,
                apiSecret,
                wsURL='wss://sc-02.coinigy.com/socketcluster/'):
        # Connects to the Coinigy API websocket and initializes data stores
        self.logger.debug("Connecting Websocket")
        self.logger.info("Conecting to %s" % wsURL)
        self.apiKey = apiKey
        self.apiSecret = apiSecret
        self.bReadyToUse = False  # not yet authenticated
        self.bError = False  # no errors yet
        self.socket = Socketcluster.socket(wsURL)  # create socket connection

        # set basic event listeners
        self.socket.setBasicListener(self.__onconnect, self.__ondisconnect, self.__onconnecterror)
        # set authentication listeners
        self.socket.setAuthenticationListener(self.__onsetauthentication, self.__onauthentication)
        # initiate connecting sequence in a separate thread
        self.socketThread = threading.Thread(target=lambda: self.__socketClusterThread())
        self.socketThread.daemon = True
        self.socketThread.start()
        self.logger.info("Started thread")

        # wait for authentication
        conn_timeout = 50
        while (not self.bReadyToUse and conn_timeout and not self.bError):
            sleep(1)
            conn_timeout -= 1

        if (not conn_timeout or self.bError) and not self.bReadyToUse:
            self.logger.error("Couldn't get connected. Exiting")
            # self.exit()
            sys.exit(1)

    # susbcribe for the channel
    # channelcode: "METHOD-EXCHANGECODE--PRIMARYCURRENCY--SECONDARYCURRENCY"
    def subscribe(self, channelcode, channelhandler):
        if not channelcode or \
                not channelhandler or \
                not self.bReadyToUse: return None

        return self.__subscribe(channelcode, channelhandler)

    # private members --------------------------------------------------------

    # Thread for Socket Cluster connect method (it is looping forever in this method)
    def __socketClusterThread(self):
        self.logger.info("Launching Socket Cluster thread")
        self.socket.connect()
        # if connect method has finished - close communication
        self.__closeSocketCluster()

    # close socker cluster
    def __closeSocketCluster(self):
        self.logger.info("Close Socket Cluster")
        self.bReadyToUse = False

    def __defaultchannelmessagehandler(self, key, object):
        self.logger.info("Got data for key %s" % key)
        self.logger.info(object)

    # SetAuthentication event listener
    def __onsetauthentication(self, socket, token):
        self.logger.info("Authentication token received %s" % token)
        self.socket.setAuthtoken(token)

    def __onsubscribtionerrorhandler(self, channel, error, *args):
        if error is '':
            self.logger.info("Subscribed successfully to channel %s" % channel)
        else:
            self.logger.error("Cannot subscribe for channel %s" % channel)
            self.logger.info(error)
            self.bError = True

    # subscribe for a channel
    def __subscribe(self, channelCode, messageHandler):
        self.socket.subscribeack(channelCode, self.__onsubscribtionerrorhandler)  # subscribe for the channel
        self.socket.onchannel(channelCode, messageHandler)  # set channel message handler

    # authentication acknowledgement handler
    def __authenticationacknoledgmenthandler(self, eventname, error, object):
        self.logger.info("Authentication ack got called %s" % str(error))
        if error is '':
            # set authentication flag
            self.bReadyToUse = True
            self.logger.info("Successful authentication")
        else:
            self.bError = True
            self.logger.error("Cannot authenticate connection %s" % str(error))
            self.logger.info(error)

    # Authentication event listener
    def __onauthentication(self, socket, isauthenticated):
        self.logger.info("On authentication got called")
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
        self.bReadyToUse = False

    # onConnectError event handler
    def __onconnecterror(self, socket, error):
        self.logger.info("On connect error got called")
        self.logger.error(error)


# executing code
if __name__ == '__main__':
    pass