def pickEDD(readyOrders, vehicleCapacity):
    possible = []
    for order in readyOrders:
        if order.ready and (not order.dispatched) and order.size <= vehicleCapacity:
            possible.append(order)

    if not possible:
        return None

    possible.sort(key=lambda x: (x.due, x.arrival))
    return possible[0]