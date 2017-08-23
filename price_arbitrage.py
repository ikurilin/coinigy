# Price arbitrage algo
import logging
from exchange import Exchange
from anytree import Node, RenderTree,  NodeMixin
from pair import FXPair

class FXNode(NodeMixin):
    def __init__(self, name, fxPair = None, parent = None):
        self.name = name
        self.fxPair = fxPair
        self.parent = parent

    def getFXPair(self):
        return self.fxPair

    def getFullName(self):
        if self.fxPair is not None:
            return self.fxPair.getFullName()
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
    def __init__(self, exchange):
        self.logger = logging.getLogger('root')
        self.exchange = exchange
        self.logger.info("Initiate Price Arbitrage Algo")
        self._buildFxTree()

    #bild tree representing all possible fx conversion rates
    def _buildFxTree(self):
        # build all fx conversion paths
        pairs = self.exchange.getFxPairs()
        self.logger.info(pairs)

        # climb up the tree to check if pair is above the node to prevent loops
        def isNodeInTheTree(c, tree):
            a = c.getFullName()
            b = tree.getFullName()
            if a == b:
                return True
            else:
                if tree.parent is not None:
                    return isNodeInTheTree(c,tree.parent)
                else:
                    return False    # reached the root

        # Generate tree for all possible conversion rate
        def generateFxTree(tree, pairs):
            for c in pairs:
                if isNodeInTheTree(c, tree):
                    continue
                else:
                    base = tree.getBase()
                    quote = c.getQuote()
                    if base != quote and base is not None and quote is not None:
                        continue
                    else:
                        fx_node = FXNode(c.getFullName(), c, parent=tree)
                        generateFxTree(fx_node, pairs)
            return tree

        root = FXNode("root")
        tree = generateFxTree(root, pairs)
        #print(RenderTree(root))
        print("----******-----")
        for pre, _, node in RenderTree(root):
            treestr = u"%s%s" % (pre, node.name)
            print(treestr.ljust(8))

        self.logger.info("-------FX pairs------------")
        self.logger.info(pairs)
        a = 5