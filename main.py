# main file

from server import CoinigyAPI
from exchange import Exchange

def suback(channel, error, *args):
    if error is '':
        # print "Subscribed successfully to channel " + channel
        # set channel listener
        # socket.onchannel(channel_code, channelmessage)
        pass

print("Start")
# initialize coinigy API
coinigyAPI = CoinigyAPI(apiKey="acc223ec3b64d19d8aa060bde7af0cb1",
                apiSecret="da3eaed8d1a426b51a447634796373ea")
# create OK COIN exchange
exchange = Exchange('OK', 'OKCOIN',coinigyAPI, ["BTC/CNY"])

a = coinigyAPI.getAllExchanges();
b = coinigyAPI.getFxPairs('OK')
#coinigyAPI.subscribe('ORDER-BMEX--XBT--USD', suback)
#coinigyAPI.subscribe('ORDER-OK--BTC--CNY', suback)
while (True) :
    pass