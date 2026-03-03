import random
import simpy

from .models import expTime, travelTime
from .entities import Order
from .policies import pickEDD
from .metrics import new_metrics, compute_stats


def generateOrders(env, rng, lam, incomingStore, horizon):
    orderID = 1

    while env.now < horizon:
        yield env.timeout(expTime(rng, lam))
        arrival = env.now
        due = arrival + rng.uniform(10, 40)
        size = rng.choice([1, 2, 5, 7, 9])
        order = Order(orderID, arrival, due, size)
        yield incomingStore.put(order)
        orderID += 1


def fulfillmentCenter(env, rng, mu, servers, incomingStore, readyList, horizon):
    fc = simpy.Resource(env, capacity=servers)

    while env.now < horizon:
        order = yield incomingStore.get()

        with fc.request() as req:
            yield req
            yield env.timeout(expTime(rng, mu))

        order.ready = True
        readyList.append(order)


def dispatcher(env, rng, vehicles, vehicleCapacity, readyList, metrics, horizon):
    while env.now < horizon:
        yield env.timeout(0.5)

        if vehicles.count >= vehicles.capacity:
            continue

        order = pickEDD(readyList, vehicleCapacity)
        if order is None:
            continue

        with vehicles.request() as req:
            yield req

            order.dispatched = True
            order.dispatchTime = env.now

            metrics["total_wait"] += (order.dispatchTime - order.arrival)

            yield env.timeout(travelTime(rng))
            order.deliveredTime = env.now

            metrics["completed"] += 1
            if order.deliveredTime <= order.due:
                metrics["on_time"] += 1

            yield env.timeout(travelTime(rng))


def run_sim(lam=2.0, mu=3.0, servers=1, fleet=3, vehicle_capacity=8, horizon=500.0, seed=123):
    rng = random.Random(seed)
    env = simpy.Environment()

    incoming = simpy.Store(env)
    ready = []
    vehicles = simpy.Resource(env, capacity=fleet)

    metrics = new_metrics()

    env.process(generateOrders(env, rng, lam, incoming, horizon))
    env.process(fulfillmentCenter(env, rng, mu, servers, incoming, ready, horizon))
    env.process(dispatcher(env, rng, vehicles, vehicle_capacity, ready, metrics, horizon))

    env.run(until=horizon)

    completed, avg_wait, on_time_rate = compute_stats(metrics)
    rho = lam / (servers * mu)

    print("=== Supply Chain DES ===")
    print(f"lambda={lam}, mu={mu}, servers={servers}, fleet={fleet}, cap={vehicle_capacity}, horizon={horizon}, seed={seed}")
    print(f"rho=lambda/(s*mu)={rho:.4f}  (stable if rho < 1)")
    print(f"completed={completed}")
    print(f"avg_wait(arrival->dispatch)={avg_wait:.4f}")
    print(f"on_time_rate={on_time_rate:.4f}")

    return metrics