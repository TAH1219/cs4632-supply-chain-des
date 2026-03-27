def pickEDD(readyOrders, vehicleCapacity):
    possible = []
    for order in readyOrders:
        if order.ready and (not order.dispatched) and order.size <= vehicleCapacity:
            possible.append(order)

    if not possible:
        return None

    possible.sort(key=lambda x: (x.due, x.arrival))
    return possible[0]


def pickFCFS(readyOrders, vehicleCapacity):
    possible = []
    for order in readyOrders:
        if order.ready and (not order.dispatched) and order.size <= vehicleCapacity:
            possible.append(order)

    if not possible:
        return None

    possible.sort(key=lambda x: x.arrival)
    return possible[0]


POLICIES = {
    "edd": pickEDD,
    "fcfs": pickFCFS,
}
