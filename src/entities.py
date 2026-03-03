class Order:
    def __init__(self, orderID, arrivalTime, dueTime, size):
        self.id = orderID
        self.arrival = arrivalTime
        self.due = dueTime
        self.size = size
        self.ready = False
        self.dispatched = False
        self.dispatchTime = None
        self.deliveredTime = None