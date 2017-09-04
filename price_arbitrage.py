# Price arbitrage algo
import logging
from exchange import Exchange
from anytree import Node, RenderTree,  NodeMixin, Walker
from pair import FXPair
from  order_manager import Order, OrderManager

class FXNode(NodeMixin):
    m_samePairDifferentPathPool = {} # pool of leaves with the same pairs
    def __init__(self, name, fxPair = None, parent = None):
        self.name = name
        self.fxPair = fxPair
        self.parent = parent
        # keep track of all alternatives
        if fxPair is not None:
            if fxPair not in FXNode.m_samePairDifferentPathPool.keys():
                FXNode.m_samePairDifferentPathPool[fxPair] = [self] # add first element
            else:
                FXNode.m_samePairDifferentPathPool[fxPair].append(self)


    def getFXPair(self):
        return self.fxPair

    def getPairCode(self):
        if self.fxPair is not None:
            return self.fxPair.getPairCode()
        else: return None

    def getBase(self):
        if self.fxPair is not None:
            return self.fxPair.getBase()
        else:
            return None

    def getQuote(self):
        if self.fxPair is not None:
            return self.fxPair.getQuote()
        else:
            return None


class PriceArbitrage:
    # class variables
    logger = logging.getLogger('price arbitrage')

    def __init__(self, exchange):
        self.exchange = exchange
        self.orderManager = OrderManager()
        self.logger.info("Initiate Price Arbitrage Algo")
        self._buildFxTree() # build fx tree for all possible conversions
        # build list of leaves
        root = self.tree.root  # get root
        w = Walker()  # tree walker
        # unwrap nested tuple returned by Walker to a flat list of FXPair
        def unwrapWalkerToFlatList(x):
            if isinstance(x, tuple):
                if len(x) == 0: return []
                s = []
                for t in x:
                    s.extend(unwrapWalkerToFlatList(t))
                return s
            else:
                if x.getFXPair() is None: return [] # skip root element
                else: return [x.getFXPair()]

        self.conversion_paths = {} # all conversion paths for the pair <pair: [pair1, pair2...]>
        # build list of all conversion paths
        for k in FXNode.m_samePairDifferentPathPool.keys():  # iterate all pairs
            alternative_list = FXNode.m_samePairDifferentPathPool[k]  # get list of leaves representing same pair but with different conversion path
            paths = []
            for c in alternative_list:  # iterate all leaves (same pair but different paths)
                if not c.is_leaf:
                    continue  # iterate only leaves
                path = unwrapWalkerToFlatList(w.walk(root, c))  # get path from root to this leaf
                paths.append(path) # list of lists

            if not k in self.conversion_paths.keys():
                self.conversion_paths[k] = list(paths)
            else:
                self.conversion_paths[k].append(list(paths))

        # set event triggers
        self.exchange.setEventHandler(tradeHandler=self.updateTradeHandler, orderHandler=self.updateOrderHandler)

    #bild tree representing all possible fx conversion rates
    def _buildFxTree(self):
        # build all fx conversion paths
        pairs = self.exchange.getFxPairs()
        #self.logger.info(pairs)
        # Generate tree for all possible conversion rate (recursive)
        def generateFxTree(tree, pairs):
            # climb up the tree (recursive) to check if pair is above the node to prevent loops
            def isNodeInTheTree(c, tree):  # tree is the terminal leaf
                a = c.getPairCode()
                b = tree.getPairCode()
                if a == b:
                    return True
                else:
                    if tree.parent is not None:
                        return isNodeInTheTree(c, tree.parent)
                    else:
                        return False  # reached the root
            for c in pairs:
                if isNodeInTheTree(c, tree):
                    continue
                else:
                    base = tree.getBase()
                    quote = c.getQuote()
                    if base != quote and base is not None and quote is not None:
                        continue
                    else:
                        fx_node = FXNode(c.getPairCode(), c, parent=tree)
                        generateFxTree(fx_node, pairs)
            return tree

        # generate currency exchange options
        root = FXNode("root")
        self.tree = generateFxTree(root, pairs)

        #print(RenderTree(root))
        print("----******-----")
        for pre, _, node in RenderTree(root):
            treestr = u"%s%s" % (pre, node.name)
            print(treestr.ljust(8))

        self.logger.info("-------FX pairs------------")
        #self.logger.info(pairs)

    # update algo for data change
    def updateTradeHandler(self, currencyPair):
        self.logger.info("Process trade update for pair %s" % (currencyPair.getPairCode()))


    def updateOrderHandler(self, pair):
        self.logger.info("Process ORDER update for pair %s" % (pair.getPairCode()))
        nodes = FXNode.m_samePairDifferentPathPool[pair]
        visited_leaves = []
        # check all paths (terminal leaves) which include this pair
        for n in nodes:
            descendants = n.descendants + (n,)
            for r in descendants:
                if not r.is_leaf: continue
                p = r.getFXPair()
                if p in visited_leaves: continue
                visited_leaves.append(p)
                self.checkArbitrageOpportunity(p)

    # maximum conversion path, default is long / ask
    def estimateLongPathMaxThroughoutput(self, path,  startQuoteValue = None, bid=False):
        startValue = path[0].getMaxBookQuote(bid) if startQuoteValue is None else startQuoteValue
        b = startValue
        for p in path:
            b = p.limitedConvertQnt2Base(b, bid)
        lastPair = path[- 1]
        res = {
            'result_val': b,
            'result_currency': lastPair.getBase(),
            'start_val': startValue,
            'start_currency': path[0].getQuote()
        }
        return res #(b, lastPair.getBase(), startValue)  # in base currency of the final leaf

    # Estimate short route, path is given from root to leaf
    def estimateShortPathMaxThroughoutput(self, path, startBaseValue = None, ask=False):
        startValue = path[-1].getMaxBookBase() if startBaseValue is None else startBaseValue
        q = startValue
        for p in reversed(path):
            q = p.limitedConvertBase2Qnt(q, ask)
        lastPair = path[0]  # reverse order
        res = {
            'result_val' : q,
            'result_currency' : lastPair.getQuote(),
            'start_val' : startValue,
            'start_currency' : path[-1].getBase()
         }
        return res #(q, lastPair.getQuote(), startValue)  # in base quote of the final leaf

    # estimate maximum possible value of the arbitrage transaction
    def estimateMaximumThroughOutput(self, pair, longPath, shortPath):
        # first time estimate max throughoutput
        a = self.estimateLongPathMaxThroughoutput(longPath, bid = False)  # root -> leaf, use inverse mode (True) to get actual max initial value
        b = self.estimateShortPathMaxThroughoutput(shortPath, a['result_val'], ask = False)  # leaf -> root
        return b

    def checkArbitrageOpportunity(self, pair):
        arbitrageDescriptor = {
            "long" : {
                "return" : 0,
                "path": []
            },
            "short" : {
                "return" : 0,
                "path" : []
            }
        }
        for path in self.conversion_paths[pair]:
            #for p in path: # iterate all leaves (each leaf is the same pair but different conversion path)
            #long leg
            longMaxVal = self.estimateLongPathMaxThroughoutput(path) # estimate max value
            if longMaxVal['result_val'] == 0:
                continue
            # convert half (to make sure it goes through) of the max value into original currency using ask book
            s = self.estimateShortPathMaxThroughoutput(path, longMaxVal['result_val'] / 2, ask = True)
            #startLongValue = s ['result_val']
            #longVal = self.estimateLongPathMaxThroughoutput(path, startLongValue) # put through half of the max possible value
            #long_ret = longVal['result_val'] / longVal['start_val'] # normalize: 1 Quote currency -> x Base currency, then x is a
            if s['result_val'] == 0:
                continue
            long_ret = s['start_val'] / s['result_val']
            ex = self.exchange.convert_amt(longMaxVal['start_currency'], 'BTC', 1.0)
            if ex == 0:
                self.logger.info('cant conver from %s to BTC' % longMaxVal['start_currency'] )
                continue
            long_ret /= ex # 1 btc - > xx base currency, so all conversions start with 1 btc and thus we can compare then
            if long_ret > arbitrageDescriptor['long']['return']:
                arbitrageDescriptor['long']['return'] = long_ret
                arbitrageDescriptor['long']['path'] = path
            # short leg
            shortMaxVal = self.estimateShortPathMaxThroughoutput(path)
            if shortMaxVal['result_val'] == 0:
                continue
            # convert hald of the max value into the original currency
            s1 = self.estimateLongPathMaxThroughoutput(path, shortMaxVal['result_val'] / 2, bid = True)
            #startShortValue = self.exchange.convert_amt(shortMaxVal[1], path[-1].getBase(), shortMaxVal[0])
            #startShortValue = s['result_val']
            #shortVal = self.estimateShortPathMaxThroughoutput(path, startShortValue)
            #short_ret = self.exchange.convert_amt(shortVal['result_currency'], 'BTC', shortVal['result_val'])
            #short_ret = shortVal['result_val'] / shortVal ['start_val'] # normalize
            short_ret = s1['start_val'] / s1['result_val']
            short_ret = self.exchange.convert_amt(s1['start_currency'],'BTC', short_ret)
            if short_ret > arbitrageDescriptor['short']['return']:
                arbitrageDescriptor['short']['return'] = short_ret
                arbitrageDescriptor['short']['path'] = path
        # calculate arbitrage return
        ret = arbitrageDescriptor['long']['return'] * arbitrageDescriptor['short']['return'] - 1
        print("Arbitrage %s return: %.2f" % (pair.getPairCode(), ret))
        if ret > 0:
            a= 5 # arbitrage opportunity


    # recalculate arbitrage for a given pair
    def checkArbitrageOpportunity_old(self, pair):
        arbitrageDescriptor = {
            "long" : {
                "val" : 0,
                "path": []
            },
            "short" : {
                "val" : 0,
                'btc_val' : 0,
                "path" : []
            }
        }
        for path in self.conversion_paths[pair]:
            # calculate conversion values: we begin with 1 BTC on a long path and 1 unit of local currency on a short path
            firstPair = path[0]  # first element should be the first pair (zero/0 element is a fake "root" element)
            # start with value of 1 btc in local currency
            longVal = float(self.exchange.convert_amt('BTC', firstPair.getQuote(), 1.0, _bid = False))  # use ASK for algo initialization
            if longVal == 0:
                continue
            shortVal = 1.0
            for p in path: # iterate all leaves (each leaf is the same pair but different conversion path)
                # estimate long value: quote -> base conversion which is considered long
                ex_rate1 = float(p.get_average_ask_price_for_quote_amt(longVal))  # at what price I can buy 1 unit of base currency
                if ex_rate1 == 0:
                    break # no data - skip path
                longVal = longVal / ex_rate1  # convert quote currency to base currency
                # estimate short value ( base -> quote)
                ex_rate2 = float(p.get_average_bid_price_for_base_amt(1.0) ) # at what price I can sell 1 unit of base currency and get quote curreny
                if ex_rate2 == 0:
                    break # no data - skip path
                shortVal = shortVal * ex_rate2
            # keep track of max
            # all longVal are expressed in terms of base / local currency of the pair, so we can compare them
            if longVal > arbitrageDescriptor['long']['val']:
                arbitrageDescriptor['long']['val'] = longVal
                arbitrageDescriptor['long']['path'] = path
            # on the other hand, all shortVal are expressed in terms of quote currency of the path root which are different
            # so we need to convert shortVal to btc in order to compare them
            shortVal_btc = self.exchange.convert_amt(firstPair.getQuote(), 'BTC', shortVal, _bid = False)  # buy btc
            if shortVal_btc == 0:
                continue  # no data
            if  shortVal_btc > arbitrageDescriptor['short']['btc_val']:
                arbitrageDescriptor['short']['btc_val'] = shortVal_btc
                arbitrageDescriptor['short']['path'] = path
                arbitrageDescriptor['short']['val'] = shortVal

        arbitrageDescriptor['arb_return'] = arbitrageDescriptor['long']['val'] * arbitrageDescriptor['short']['btc_val'] - 1
        #self.estimateMaximumThroughOutput(pair)
        a = pair.getPairCode()
        b = arbitrageDescriptor['arb_return']
        self.logger.info("Arbitrage %s return: %.2f" % (a,b) )
        if arbitrageDescriptor['arb_return'] > 0:
            self.arbitrageHandler(pair, arbitrageDescriptor) # process arbitrage


    # Process arbitrage event
    def arbitrageHandler(self, pair, arbitrage):
        print(" ****** ARBITRAGE FOR THE PAIR %s " % pair.getPairCode())

        #firstPair = arbitrage['long']['path'][0]  # first element should be first pair (zero/0 element is a fake "root" element)
        # Estimate maximum possible value of the transaction on long-short path (expressed in terms of the last node of short path)
        (transaction_max_amt, arb_val_currency,x)  = self.estimateMaximumThroughOutput(pair, arbitrage['long']['path'], arbitrage['short']['path'])
        arb_max_profit = arbitrage['arb_return'] * transaction_max_amt # max possible arbitrage value
        #shortPath = arbitrage['short']['path']
        #arb_val_currency = shortPath[len(shortPath) - 1].getQuote() # currency in which arbitrage value is expressed
        # get btc value of arbitrage profit
        arbitrage['max_transaction'] = {'val':  transaction_max_amt,
                                        'currency' :  arb_val_currency }
        arb_max_profit_btc = self.exchange.convert_amt(arb_val_currency, 'BTC', arb_max_profit, _bid = False)  # buy BTC
        print('Arbitrage return: %f. Maximum transaction amt %f %s. Arbitrage profit %f %s (%f BTC)' % (arbitrage['arb_return'],
                                                                                        transaction_max_amt, arb_val_currency,
                                                                                        arb_max_profit, arb_val_currency,
                                                                                        arb_max_profit_btc  ))
        self.debug_arbitrage(pair, arbitrage)

        # execute arbitrage sequence
        self.execute_arbitrage(pair, arbitrage)


    def execute_arbitrage(self, pair, arbitrage):
        # long leg
        longPath = arbitrage['long']['path']
        firstPair = longPath[0]  # first element should be the first pair (zero/0 element is a fake "root" element)
        # start with value of 1 btc in local currency
        longVal = self.exchange.convert_amt(
            arbitrage['max_transaction']['currency'], firstPair.getQuote(), arbitrage['max_transaction']['val'],
            _bid=False)  # use ASK for algo initialization/
        for p in longPath:
            e = p.get_average_ask_price_for_quote_amt(longVal)
            longVal = longVal / e
            # create buy order
            o = Order(p, 'BUY', longVal, type = 'LIMIT', price = 0 )
            self.orderManager.execute_order(o)
            status = o.get_status()
            if status == 'OK': # IN_PROGRESS, COMPLETED, FAILED, PARTIALLY_COMPLETED
                pass
            elif status == 'CANCELED':
                pass
            elif status == 'FAILED':
                pass
            elif status == 'PARTIAL':
                pass



    def debug_arbitrage(self, pair, arbitrage):
        longPath = arbitrage['long']['path']
        firstPair = longPath[0]  # first element should be the first pair (zero/0 element is a fake "root" element)
        # start with value of 1 btc in local currency
        longVal =  self.exchange.convert_amt(arbitrage['max_transaction']['currency'], firstPair.getQuote(), arbitrage['max_transaction']['val'], _bid=False)  # use ASK for algo initialization/
        s= ""
        for p in longPath:
            l = longVal
            e = p.get_average_ask_price_for_quote_amt(longVal)
            s = str(longVal) + " " + p.getQuote() + " -> "
            longVal = longVal / e
            s += str(longVal) + " " + p.getBase() + "@" + str(e)
            print(s)
            print("Ask book: AverageAskPrie(%f)=%f" % (l, e))
            print(p.asks)

        shortPath = arbitrage['short']['path']
        print("**** SHORTING:")
        shortVal = longVal
        firstPair = shortPath[- 1]
        for index, p in enumerate(reversed(shortPath)):
            k = shortVal
            e = p.get_average_bid_price_for_base_amt(shortVal)
            s = str(shortVal) + " " + p.getBase() + " -> "
            shortVal = shortVal * e
            s += str(shortVal) + " " + p.getQuote() + "@" + str(e)
            print(s)
            print("Bid book: AverageBidPrie(%f)=%f" % (k, e))
            print(p.bids)
        shortVal_original = self.exchange.convert_amt(firstPair.getQuote(), longPath[0].getQuote(), shortVal, _bid=False)  # buy btc
        print(str(shortVal) + " " + firstPair.getQuote()+ "->" + str(shortVal_original) + longPath[0].getQuote() + "@" + str(e) )
        a = 5