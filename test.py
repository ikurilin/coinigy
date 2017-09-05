# test unit
import pandas as pd
from exchange import Exchange
from price_arbitrage import *

class FileReaderAPI:
    def __init__(self, fileName):
        # read book data
        self.inputData = pd.read_json(fileName, orient='split')
        print(self.inputData)
        self.eventHandlers = dict()

    def getFxPairs(self, code):
        pairs = pd.DataFrame(self.inputData['base'] + '/' + self.inputData['quote'], columns=['mkt_name'])
        pairs["exchmkt_id"] = 'exchmkt_id'
        pairs["exch_code"]="exch_code"
        # mkt_name
        #pairs.column=['mkt_name']
        #drop duplicates
        pairs.drop_duplicates(inplace=True)
        return pairs

    def subscribe(self, channel, orderEventHandler):
        # channel = "ORDER-" + row["exch_code"] + "--" + base + "--" + quote
        a = channel.split('--')
        b = a[0].split('-')
        type = b[0]
        base=a[1]
        quote = a[2]
        pair = base + '/' + quote
        if not pair in self.eventHandlers.keys():
            self.eventHandlers[pair] = {type : { 'handler' : orderEventHandler,
                                             'channel' : channel}}
        else:
            self.eventHandlers[pair][type] = { 'handler' : orderEventHandler,
                                             'channel' : channel}

    def getAsks(self, exchangeCode, pairCode):
        # df.to_records
        pass

    def getBids(self, exchangeCode, pairCode):
        pass

    def getOrders(self, exchangeCode, pairCode):
        pass

    def start(self):
        start_row = -1
        # split file into order blocks
        for i, row in self.inputData.iterrows():
            if start_row == -1:
                start_row = i
                continue

            if self.inputData.iloc[start_row]['base'] == row['base'] and \
                            self.inputData.iloc[start_row]['quote'] == row['quote'] and \
                            self.inputData.iloc[start_row]['ordertype'] == row['ordertype'] and \
                            i != (len(self.inputData) - 1) :
                continue
            # we got block from start_row to i
            block = self.inputData.iloc[start_row:i if i != (len(self.inputData) - 1) else i + 1]
            self.__process_block(block)
            start_row = i

    def __process_block(self, dataBlock):
        s =  dataBlock.iloc[0]['base'] + "/" + dataBlock.iloc[0]['quote']
        bookType = dataBlock.iloc[0]['ordertype']
        verb = 'ORDER' if bookType == 'Sell' or bookType =='Buy' else 'TRADE'
        print("Data book %s for %s" % (bookType,s ))
        print(dataBlock)
        # call handler
        handler = self.eventHandlers[s][verb]['handler']
        channel = self.eventHandlers[s][verb]['channel']
        json = dataBlock.to_records()
        handler(channel, json)


file_name = "sample.json"
apiSimulation = FileReaderAPI(file_name)
testExchange = Exchange('TST','TEST-INTERFACE', apiSimulation)
algo = PriceArbitrage(testExchange)
apiSimulation.start()
a = 5