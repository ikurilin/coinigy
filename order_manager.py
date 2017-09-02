# order manager

# order class
class Order:
    def __init__(self, pair, direction, qnt, type = 'MARKET', price = 0 ):
        '''
        :param pair: pair to trade
        :param direction: BUY, SELL
        :param qnt: quantity to trade
        :param type:  order type: MARKET, LIMIT
        '''
        self.pair = pair
        self.type = type
        self.qnnt = qnt
        self.price = price
        self.direction = direction

    def get_status(self):
        pass # CREATED  / SUBMITTED / EXECUTING / FULLFILLED / CANCELED

class BuyOrder(Order):
    def __init(self, pair, type):
        self.super().__init__(pair, type)
        self.direction = "BUY"

# Execution Engine
class OrderManager:
    def __init__(self):
        pass

    def init(self):
        pass

    def reset(self):
        pass

    def print_status(self):
        pass

    # async order - just place and don't wait for the execution
    def place_order(self, order):
        pass

    # sync order - wait until order is exectuted or canceleld
    def execute_order(self, order):
        pass
