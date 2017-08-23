# main file

from coinigy_server import CoinigyAPI
from exchange import Exchange
from price_arbitrage import PriceArbitrage

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
okExchange = Exchange('GATE', 'GATECOIN',coinigyAPI, allowedPairs=["BTC/EUR", "BTC/HKD", "ETH/BTC", "ETH/EUR","PAY/ETH", "PAY/BTC", "WGC/ETH"])

algo = PriceArbitrage(okExchange)

while (True) :
    pass