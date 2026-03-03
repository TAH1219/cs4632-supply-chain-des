import math
import random
import simpy

#Helpers
#-------------
#Function will sample an exponential random variable. This will act as a random time delay.
#rng = random.Random instance
#rate = exponential rate parameter
def expTime(rng, rate):
    if rate <= 0:
        raise ValueError("Rate must be positive")
    #Need to sample a uniform random number from 0 to < 1 . Stored as rand
    rand = rng.random()
    #Need to convert rand to exponential time using inverse transform: T = -ln(1-U)/rate
    return -math.log(1.0 - rand) / rate

#Function will return delivery time for a vehicle
#rng = random.Random instance
def travelTime(rng):
    #Function uses a base delivery time of 10.0 with noise of -1 to +1
    #max(1.0,...) is used to ensure delivery time is not below 1.0.
    return max(1.0, 10.0 + rng.uniform(-1.0,1.0))

#-------------
#Order structure class
class Order:
    #Order Constructor
    def __init__(self, orderID, arrivalTime, dueTime, size):
        self.id = orderID
        self.arrival = arrivalTime
        self.due = dueTime
        self.size = size

        #ready: true when order processing finished
        self.ready = False
        #dispatched: true once order is assigned to a vehicle and dispatched
        self.dispatched = False
        #dispatchTime: simulated time of dispatch
        self.dispatchTime = None
        #deliveredTime: simulated time of delivery
        self.deliveredTime = None

#Dispatch policy
#Earliest Due Date:
def pickEDD(readyOrders, vehicleCapacity):
    #possible: possible orders for dispatch
    possible = []

    #Loop to ensure order and constraints matched for orders
    for order in readyOrders:
        #Can't be already dispatched and must not exceed vehicle capacity
        if order.ready and (not order.dispatched) and order.size <= vehicleCapacity:
            #suitable orders are added
            possible.append(order)

    if not possible:
        return None

    #Sorting possible orders by their due time and by First come first serve.
    possible.sort(key=lambda x: (x.due, x.arrival))
    return possible[0]

# Simulation
# Generate orders using Poisson arrival model
def generateOrders(env, rng, lam, incomingStore, horizon):
    orderID = 1

    while env.now < horizon:
        # Wait for next arrival (Exp interarrival => Poisson process)
        yield env.timeout(expTime(rng, lam))
        arrival = env.now
        due = arrival + rng.uniform(10, 40)
        size = rng.choice([1, 2, 5, 7, 9])
        order = Order(orderID, arrival, due, size)
        yield incomingStore.put(order)
        orderID += 1

#Fulfillment center processing
def fulfillmentCenter(env, rng, mu, servers, incomingStore, readyList, horizon):
    #mu: service rate
    #servers: number of processing channels in parallel
    #readyList: processed orders for dispatch list
    #horizon: simulation end time

    #fc: SimPy resource
    fc = simpy.Resource(env, capacity = servers)

    while env.now < horizon:
        order = yield incomingStore.get()

        with fc.request() as req:
            yield req
            yield env.timeout(expTime(rng, mu))

        order.ready = True
        readyList.append(order)

#Dispatch
def dispatcher(env, rng, vehicles, vehicleCapacity, readyList, metrics, horizon):
    #metrics: dictionary storing counters and sums
    #Loop for duration of the simulationn
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

    metrics = {
        "completed": 0,
        "on_time": 0,
        "total_wait": 0.0
    }

    env.process(generateOrders(env, rng, lam, incoming, horizon))
    env.process(fulfillmentCenter(env, rng, mu, servers, incoming, ready, horizon))
    env.process(dispatcher(env, rng, vehicles, vehicle_capacity, ready, metrics, horizon))

    env.run(until=horizon)

    completed = metrics["completed"]
    avg_wait = (metrics["total_wait"] / completed) if completed else 0.0
    on_time_rate = (metrics["on_time"] / completed) if completed else 0.0
    rho = lam / (servers * mu)

    print("=== Supply Chain DES ===")
    print(f"lambda={lam}, mu={mu}, servers={servers}, fleet={fleet}, cap={vehicle_capacity}, horizon={horizon}, seed={seed}")
    print(f"rho=lambda/(s*mu)={rho:.4f}  (stable if rho < 1)")
    print(f"completed={completed}")
    print(f"avg_wait(arrival->dispatch)={avg_wait:.4f}")
    print(f"on_time_rate={on_time_rate:.4f}")

if __name__ == "__main__":
    run_sim()