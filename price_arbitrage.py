# Price arbitrage algo
import logging
from exchange import Exchange
from anytree import Node, RenderTree,  NodeMixin, Walker
from pair import FXPair

class FXNode(NodeMixin):
    m_alternatives = {} # pool of paths leading to the same BASE/QUOTE pairs
    def __init__(self, name, fxPair = None, parent = None):
        self.name = name
        self.fxPair = fxPair
        self.parent = parent
        # keep list of alternatives
        if fxPair is not None:
            if fxPair not in FXNode.m_alternatives.keys():
                FXNode.m_alternatives[fxPair] = [self] # add first element
            else:
                FXNode.m_alternatives[fxPair].append(self)


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
        self.findArbitrageOpportunity()

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
        def estimateRates(longVal, shortVal, root, longStr):
            r = root.getFXPair()
            # rates reflect current order book status and amt to exchange

            ex_rate1 = 0 # error signal
            v1 = 0
            if r.isBidAvailable():
                ex_rate1 = r.getAverageBidPrice(longVal)  # use bid price here
                v1 = longVal / ex_rate1  # convert val to Node base currency
            ex_rate2 = 0 # error signal
            v2 = 0
            if r.isAskAvailable():
                ex_rate2 = r.getAverageAskPrice(shortVal)  # use ask price
                v2 = shortVal * ex_rate2

            s1 = longStr + "-> " + str(v1) + " " + r.getBase() + "@" + str(ex_rate1)

            if root.is_leaf: # reached leaf - save accumulated long value
                root.longValue = v1  # value of 1 BTC expressed in terms of base value of this currency (base)
                root.longStr = s1
                root.shortValue = v2 # value of 1 unit of this base currency expressed in terms of quote currency of the tree root
            else:
                for n in root.children:
                    estimateRates(v1, v2, n, s1)

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
            estimateRates(v1, v2, n, s1)
        # print alternatives
        a = FXNode.m_alternatives.keys()
        w = Walker()
        for k in FXNode.m_alternatives.keys():
            alternative_list = FXNode.m_alternatives[k]
            print("------PAIR %s" % (k.getPairCode()))
            for c in alternative_list:
                if not c.is_leaf:
                    continue # iterate only leaves
                # unwrap nested tuples
                def unwrap(x):
                    if isinstance(x, tuple):
                        s = ""
                        for t in x:
                            s += unwrap(t)
                        return s
                    else:
                        return x.name + " "
                path = w.walk(root, c)
                print("LONG: %f : %s >> %s"  % (c.longValue, unwrap(path), c.longStr))


        print("FINISH")