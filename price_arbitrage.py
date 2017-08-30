# Price arbitrage algo
import logging
from exchange import Exchange
from anytree import Node, RenderTree,  NodeMixin, Walker
from pair import FXPair

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
        self.logger.info("Initiate Price Arbitrage Algo")
        self._buildFxTree() # build fx tree for all possible conversions
        # build leaf lists
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
                paths.append(path)

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
        self.logger.info(pairs)
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
        self.logger.info(pairs)

        #find opportunity
        #self.findArbitrageOpportunity()

    # update algo for data change
    def updateTradeHandler(self, currencyPair):
        self.logger.info("Process trade update for pair %s" % (currencyPair.getPairCode()))
        #self.findArbitrageOpportunity()

    def updateOrderHandler(self, currencyPair):
        self.logger.info("Process ORDER update for pair %s" % (currencyPair.getPairCode()))
        self.pairUpdateHandler(currencyPair)

    def findArbitrageOpportunity(self):
        # find spot arbitrage opportunity in the exchange
        # calculate conversion value
        # LONG position: from top to leaf

        #ierate tree from root to the leaves to calculate terminal conversion rate in the leaves
        def estimateRates(longVal, shortVal, root, longStr, shortStr):
            r = root.getFXPair()
            # rates reflect current order book status and amt to exchange

            v1 = 0
            ex_rate1 = r.getAverageAskPrice(longVal)  # at what price I can buy
            if ex_rate1 != 0:
                v1 = longVal / ex_rate1  # convert val to Node base currency
            ex_rate2 = r.getAverageBidPrice(shortVal)  # at what price I can sell
            v2 = shortVal * ex_rate2

            # conversion line for debug purposes
            s1 = longStr + "-> " + str(v1) + " " + r.getBase() + "@" + str(ex_rate1)
            s2 = str(v2) + " " + r.getBase() + "@" +  str(ex_rate2) + "->" + shortStr

            if root.is_leaf: # reached leaf - save accumulated long value
                root.longValue = v1  # value of 1 BTC expressed in terms of base value of this currency (base)
                root.longStr = s1
                root.shortValue = v2 # value of 1 unit of this base currency expressed in terms of quote currency of the tree root
                root.shortStr = s2
            else:
                for n in root.children:
                    estimateRates(v1, v2, n, s1, s2)

        # Combined LONG / SHORT LOOP: start with 1 BTC
        root = self.tree.root # get root
        for n in root.children:
            pair = n.getFXPair()
            x = self.exchange.getExchangeRate('BTC',pair.getQuote(), 'BID')
            # x = pair.get1BTCinQuote()
            # get value of 1 BTC expressed in quote currency of n
            #ex_rate1 = pair.getAverageBidPrice(x) # use bid price here
            #ex_rate2 = pair.getAverageAskPrice(1)
            v1 = x  # 1 * ex_rate1 # long local currency worth of 1 BTC
            v2 = 1  # short value
            s1 = "1 BTC -> " + str(x) + " " + pair.getQuote()
            s2 = pair.getBase()
            estimateRates(v1, v2, n, s1, s2)
        # print alternatives
        # unwrap nested tuples
        def unwrap(x):
            if isinstance(x, tuple):
                s = ""
                for t in x:
                    s += unwrap(t)
                return s
            else:
                return x.name + " "

        a = FXNode.m_samePairDifferentPathPool.keys()
        w = Walker()
        for k in FXNode.m_samePairDifferentPathPool.keys():
            alternative_list = FXNode.m_samePairDifferentPathPool[k]
            print("------PAIR %s" % (k.getPairCode()))
            for c in alternative_list:
                if not c.is_leaf:
                    continue # iterate only leaves
                path = w.walk(root, c)
                print("LONG: %f : %s >> %s"  % (c.longValue, unwrap(path), c.longStr))
                print("SHORT: %f : %s " % (c.shortValue,  c.shortStr))


        print("FINISH")


    def pairUpdateHandler(self, pair):
        nodes = FXNode.m_samePairDifferentPathPool[pair]
        list_to_update = []
        for n in nodes:
            descendants = n.descendants + (n,)
            for r in descendants:
                if not r.is_leaf: continue
                p = r.getFXPair()
                if p in list_to_update: continue
                list_to_update.append(p)
                self.updateArbitrageDataForPair(p)

    # recalculate arbitrage for a given pair
    def estimateMaximumThroughOutput(self, pair):
        # self.logger.info("------PAIR %s" % (pair.getPairCode()))
        # maximum conversion path, default is long / ask
        def estimateLongPathMaxThroughoutput(path, bid=False):
            firstNode = path[0]  # first element
            b = firstNode.getMaxBookQuote(bid)
            #b = firstNode.limitedConvertQnt2Base(q, bid)
            #(q,b) = (b,q) # swap
            for p in path:
                #q1 = min(p.getMaxBookQuote(bid), b)
                b = p.limitedConvertQnt2Base(b, bid)
                #b = b1
                #q = q1
            lastPair = path[len(path) - 1]
            return (b, lastPair.getBase(), lastPair)  # in base currency of the final leaf

        # Estimate short route, path is given from root to leaf
        def estimateShortPathMaxThroughoutput(path, startBaseValue = None, ask=False):
            firstNode = path[len(path) - 1]  # first element
            if startBaseValue is None:
                q = firstNode.getMaxBookBase(ask)
            else:
                q = startBaseValue
            for p in reversed(path):
                q = p.limitedConvertBase2Qnt(q, ask)

            lastPair = path[0]
            return (q, lastPair.getQuote(), lastPair)  # in base quote of the final leaf

        max = 0
        max_path= None
        for path in self.conversion_paths[pair]:
            # first time estimate max throughoutput
            a = estimateLongPathMaxThroughoutput(path, True)  #root -> leaf, use inverde mode (True) to get actual max initial value
            b = estimateShortPathMaxThroughoutput(path, a[0], True) # leaf -> root
            initialMaxValue = b[0] # maximum value possible to convert with current books state
            pair.maxInitialConversionValue = {}
            pair.maxInitialConversionValue['long'] = a # in local currency
            #ex = self.exchange.getExchangeRate(pair.getQuote(), 'BTC', 'ASK')
            # convert initial value to btc
            pair.maxInitialConversionValue['short'] = b # in btc
            if initialMaxValue > max:
                max = initialMaxValue
                max_path = path
        return (max, max_path)


        # recalculate arbitrage for a given pair

    def estimateMaximumThroughOutput2(self, pair, longPath, shortPath):
        # self.logger.info("------PAIR %s" % (pair.getPairCode()))
        # maximum conversion path, default is long / ask
        def estimateLongPathMaxThroughoutput(path, bid=False):
            firstNode = path[0]  # first element
            b = firstNode.getMaxBookQuote(bid)
            # b = firstNode.limitedConvertQnt2Base(q, bid)
            # (q,b) = (b,q) # swap
            for p in path:
                # q1 = min(p.getMaxBookQuote(bid), b)
                b = p.limitedConvertQnt2Base(b, bid)
                # b = b1
                # q = q1
            lastPair = path[len(path) - 1]
            return (b, lastPair.getBase(), lastPair)  # in base currency of the final leaf

        # Estimate short route, path is given from root to leaf
        def estimateShortPathMaxThroughoutput(path, startBaseValue=None, ask=False):
            firstNode = path[len(path) - 1]  # first element
            if startBaseValue is None:
                q = firstNode.getMaxBookBase(ask)
            else:
                q = startBaseValue
            for p in reversed(path):
                q = p.limitedConvertBase2Qnt(q, ask)

            lastPair = path[0]
            return (q, lastPair.getQuote(), lastPair)  # in base quote of the final leaf

        #max = 0
        #max_path = None
        #for path in self.conversion_paths[pair]:
        # first time estimate max throughoutput
        a = estimateLongPathMaxThroughoutput(longPath, True)  # root -> leaf, use inverde mode (True) to get actual max initial value
        b = estimateShortPathMaxThroughoutput(shortPath, a[0], True)  # leaf -> root
        #initialMaxValue = b[0]  # maximum value possible to convert with current books state
        return b[0]

    # recalculate arbitrage for a given pair
    def updateArbitrageDataForPair(self, pair):
        #self.logger.info("------PAIR %s" % (pair.getPairCode()))

        maxValue = {
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
        a = self.conversion_paths.keys()
        b = self.conversion_paths[pair]
        for path in self.conversion_paths[pair]:
            # calculate conversion rates: we begin with 1 BTC on long path and 1 unit of local currency on the short path
            # it is convenient arrangement to see percentage return
            firstPair = path[0]  # first element should be the first pair (zero/0 element is a fake "root" element)
            # start with value of 1 btc in local currency
            longVal = self.exchange.getExchangeRate('BTC', firstPair.getQuote(), 'ASK') # use ASK for convenience
            #s1 = "1 BTC -> " + str(longVal) + " " + firstPair.getQuote()
            shortVal = 1
            #s2 = " " + firstPair.getQuote()
            leaf_base = ""
            for p in path: # iterate all leaves (each leaf is the same pair but different conversion path)
                # estimate long value: quote -> base conversion which is considered long
                ex_rate1 = p.getAverageAskPrice(longVal)  # at what price I can buy
                if ex_rate1 != 0:
                    longVal = longVal / ex_rate1  # convert val to Node base currency
                else:
                    longVal = 0 # error - no book data
                    #leaf_base = p.getBase()
                #s1 = s1 + "-> " + str(longVal) + " " + p.getBase() + "@" + str(ex_rate1)
                # estimate short value ( base -> quote)
                ex_rate2 = p.getAverageBidPrice(shortVal)  # at what price I can sell
                shortVal = shortVal * ex_rate2
                #s2 = str(shortVal) + " " + p.getBase() + "@" + str(ex_rate2) + "-> " +s2
            # keep track of max
            # all longVal are expressed in terms of base / local currency of the pair, so we can campare them
            if longVal > maxValue['long']['val']:
                maxValue['long']['val'] = longVal
                maxValue['long']['path'] = path
            # on the other hand, all shortVal are expressed in terms of quote currency of the path root which are different
            # so we need to convert shortVal to btc in order to compare them
            ex_rate3 = self.exchange.getExchangeRate(firstPair.getQuote(), 'BTC', 'BID') # buy btc
            if shortVal * ex_rate3 > maxValue['short']['btc_val']:
                maxValue['short']['btc_val'] = shortVal * ex_rate3
                maxValue['short']['path'] = path
                maxValue['short']['val'] = shortVal

        pair.arbitrage = {} # save arbitrage data
        pair.arbitrage['val'] = maxValue['long']['val'] * maxValue['short']['btc_val'] - 1
        # to remove
        #self.estimateMaximumThroughOutput(pair)
        if pair.arbitrage['val'] > 0:
            self.logger.info(" ****** ARBITRAGE FOR THE PAIR %s " % pair.getPairCode())

            def unwrap_path(_path, _val, firstPair, inverse = False):
                path = _path
                val = _val
                if inverse:
                    s = str(val) + " " + firstPair.getBase()
                else:
                    s =  str(val) + " " + firstPair.getQuote()
                for p in path:
                    if inverse :
                        ex_rate = p.getAverageBidPrice(val)
                        val = val * ex_rate
                    else:
                        ex_rate = p.getAverageAskPrice(val)  # at what price I can buy
                        if ex_rate != 0:
                            val = val / ex_rate  # convert val to Node base currency
                        else:
                            val = 0
                    if inverse:
                        s = s + "-> " + str(val) + " " + p.getQuote() + "@" + str(ex_rate)
                    else:
                        s = s + "-> " + str(val) + " " + p.getBase() + "@" + str(ex_rate)
                return (val, s)

            firstPair = maxValue['long']['path'][0]  # first element should be first pair (zero/0 element is a fake "root" element)
            longVal = self.exchange.getExchangeRate('BTC', firstPair.getQuote(), 'ASK')
            max_arb_size = self.estimateMaximumThroughOutput2(pair, maxValue['long']['path'], maxValue['short']['path'])
            ppp = maxValue['short']['path']
            profit = pair.arbitrage['val'] * max_arb_size
            currency = ppp[len(ppp)-1].getQuote()
            self.logger.info('Arbitrage return: %f. Maximum size %f %s. Profit %f %s' % (pair.arbitrage['val'], max_arb_size,currency,profit, currency  ))

            pp =  unwrap_path(maxValue['long']['path'],longVal,maxValue['long']['path'][0]  )
            self.logger.info("LONG: %f %s : %s" % (pp[0], pair.getBase(), pp[1]))
            shortVal = pp[0]
            lp = maxValue['short']['path']
            pp2 = unwrap_path(reversed(lp), shortVal, lp[len(lp)-1], True )
            self.logger.info("SHORT: %f %s : %s" % (pp2[0], pair.getQuote(), pp2[1]))
            b = 4