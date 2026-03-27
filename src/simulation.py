import random
import simpy

from .models import expTime, travelTime
from .entities import Order
from .policies import POLICIES
from .metrics import new_metrics, compute_summary


def _log_event(events, event_type, sim_time, order=None, extra=None):
    rec = {
        "event_type": event_type,
        "sim_time": sim_time,
        "order_id": getattr(order, "id", None),
        "order_size": getattr(order, "size", None),
        "order_due": getattr(order, "due", None),
    }
    if extra:
        rec.update(extra)
    events.append(rec)


def generateOrders(env, rng, lam, incomingStore, horizon, events, metrics):
    orderID = 1
    while env.now < horizon:
        yield env.timeout(expTime(rng, lam))

        arrival = env.now
        due = arrival + rng.uniform(10, 40)
        size = rng.choice([1, 2, 5, 7, 9])

        order = Order(orderID, arrival, due, size)
        yield incomingStore.put(order)

        metrics["event_counts"]["order_created"] += 1
        _log_event(events, "order_created", env.now, order)

        orderID += 1


def fulfillmentCenter(env, rng, mu, servers, incomingStore, readyList, horizon, events, metrics):
    fc = simpy.Resource(env, capacity=servers)

    while env.now < horizon:
        order = yield incomingStore.get()

        with fc.request() as req:
            yield req
            yield env.timeout(expTime(rng, mu))

        order.ready = True
        readyList.append(order)

        metrics["event_counts"]["order_ready"] += 1
        _log_event(events, "order_ready", env.now, order)


def dispatcher(env, rng, vehicles, vehicleCapacity, readyList, metrics, horizon, events, pick_policy):
    while env.now < horizon:
        yield env.timeout(0.5)

        
        if vehicles.count >= vehicles.capacity:
            continue

        order = pick_policy(readyList, vehicleCapacity)
        if order is None:
            continue

        with vehicles.request() as req:
            yield req

            order.dispatched = True
            order.dispatchTime = env.now

            metrics["total_wait"] += (order.dispatchTime - order.arrival)
            metrics["event_counts"]["order_dispatched"] += 1
            _log_event(events, "order_dispatched", env.now, order, extra={
                "wait_time": (order.dispatchTime - order.arrival),
                "vehicles_in_use": vehicles.count,
            })

           
            yield env.timeout(travelTime(rng))
            order.deliveredTime = env.now

            metrics["completed"] += 1
            if order.deliveredTime <= order.due:
                metrics["on_time"] += 1

            metrics["event_counts"]["order_delivered"] += 1
            _log_event(events, "order_delivered", env.now, order, extra={
                "delivered_on_time": int(order.deliveredTime <= order.due),
                "time_in_system": (order.deliveredTime - order.arrival),
            })

            
            yield env.timeout(travelTime(rng))


def snapshotter(env, incomingStore, readyList, vehicles, metrics, horizon, sample_dt, timeseries):
    while env.now < horizon:
        inc_q = len(incomingStore.items)
        ready_q = len(readyList)
        in_use = vehicles.count
        util = (in_use / vehicles.capacity) if vehicles.capacity else 0.0

        metrics["max_incoming_q"] = max(metrics["max_incoming_q"], inc_q)
        metrics["max_ready_q"] = max(metrics["max_ready_q"], ready_q)
        metrics["max_vehicles_in_use"] = max(metrics["max_vehicles_in_use"], in_use)

        completed = metrics["completed"]
        avg_wait_so_far = (metrics["total_wait"] / completed) if completed else 0.0

        timeseries.append({
            "sim_time": env.now,
            "incoming_q": inc_q,
            "ready_q": ready_q,
            "vehicles_in_use": in_use,
            "fleet_capacity": vehicles.capacity,
            "vehicle_utilization": util,
            "completed": completed,
            "on_time": metrics["on_time"],
            "avg_wait_so_far": avg_wait_so_far,
        })

        yield env.timeout(sample_dt)


def run_sim(
    lam=2.0,
    mu=3.0,
    servers=1,
    fleet=3,
    vehicle_capacity=8,
    horizon=500.0,
    seed=123,
    policy="edd",
    sample_dt=1.0,
):
    rng = random.Random(seed)
    env = simpy.Environment()

    incoming = simpy.Store(env)
    ready = []
    vehicles = simpy.Resource(env, capacity=fleet)

    metrics = new_metrics()
    events = []
    timeseries = []

    policy_key = (policy or "edd").strip().lower()
    pick_policy = POLICIES.get(policy_key, POLICIES["edd"])

    env.process(generateOrders(env, rng, lam, incoming, horizon, events, metrics))
    env.process(fulfillmentCenter(env, rng, mu, servers, incoming, ready, horizon, events, metrics))
    env.process(dispatcher(env, rng, vehicles, vehicle_capacity, ready, metrics, horizon, events, pick_policy))
    env.process(snapshotter(env, incoming, ready, vehicles, metrics, horizon, sample_dt, timeseries))

    env.run(until=horizon)

    summary = compute_summary(metrics, lam, mu, servers, fleet, vehicle_capacity, horizon, seed, policy_key)

    return {
        "summary": summary,
        "timeseries": timeseries,
        "events": events,
    }
