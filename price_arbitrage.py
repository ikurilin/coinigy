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
    logger = logging.getLogger('root')

    def __init__(self, exchange):
        self.exchange = exchange
        self.logger.info("Initiate Price Arbitrage Algo")
        self._buildFxTree()

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

        # set event triggers
        self.exchange.setEventHandler(tradeHandler=self.updateTradeHandler, orderHandler=self.updateOrderHandler)

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
        #self.findArbitrageOpportunity()

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

    def findArbitrageOpportunity2(self):
        root = self.tree.root  # get root
        #a = FXNode.m_samePairDifferentPathPool.keys()
        w = Walker() # tree walker
        # unwrap nested tuple returned by Walker to a flat list
        def unwrapWalkerToFlatList(x):
            if isinstance(x, tuple):
                if len(x) == 0: return []
                s = []
                for t in x:
                    s.extend(unwrapWalkerToFlatList(t))
                return s
            else:
                return [x]

        for k in FXNode.m_samePairDifferentPathPool.keys(): # iterate all pairs
            alternative_list = FXNode.m_samePairDifferentPathPool[k] # get list of leaves representing same pair but with different conversion path
            print("------PAIR %s" % (k.getPairCode()))
            for c in alternative_list: # iterate all leaves (same pair but different paths)
                if not c.is_leaf:
                    continue  # iterate only leaves
                path = unwrapWalkerToFlatList(w.walk(root, c)) # get path from root to this leaf
                # calculate conversion rates
                n= path[1] # first element should be first pair (zero/0 element is a fake "root" element)
                pair = n.getFXPair()
                longVal = self.exchange.getExchangeRate('BTC', pair.getQuote(), 'BID')
                s1 = "1 BTC -> " + str(longVal) + " " + pair.getQuote()
                shortVal = 1
                for m in path:
                    mp = m.getFXPair()
                    if mp is None: continue # skip "root" element
                    ex_rate1 = mp.getAverageAskPrice(longVal)  # at what price I can buy
                    if ex_rate1 != 0:
                        longVal = longVal / ex_rate1  # convert val to Node base currency
                    s1 = s1 + "-> " + str(longVal) + " " + mp.getBase() + "@" + str(ex_rate1)
                    ex_rate2 = mp.getAverageBidPrice(shortVal)  # at what price I can sell
                    shortVal = shortVal * ex_rate2
                c.longVal = longVal
                c.shortVal = shortVal
                print("LONG: %f : %s" % (c.longVal,  s1))
                print("SHORT: %f  " % (c.shortVal))
        print("FINISH")