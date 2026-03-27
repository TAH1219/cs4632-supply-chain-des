def new_metrics():
    return {
        "completed": 0,
        "on_time": 0,
        "total_wait": 0.0,
        "max_incoming_q": 0,
        "max_ready_q": 0,
        "max_vehicles_in_use": 0,
        "event_counts": {
            "order_created": 0,
            "order_ready": 0,
            "order_dispatched": 0,
            "order_delivered": 0,
        },
    }


def compute_summary(metrics, lam, mu, servers, fleet, vehicle_capacity, horizon, seed, policy):
    completed = metrics["completed"]
    avg_wait = (metrics["total_wait"] / completed) if completed else 0.0
    on_time_rate = (metrics["on_time"] / completed) if completed else 0.0
    rho = lam / (servers * mu)

    return {
        "lam": lam,
        "mu": mu,
        "servers": servers,
        "fleet": fleet,
        "vehicle_capacity": vehicle_capacity,
        "horizon": horizon,
        "seed": seed,
        "policy": policy,
        "rho": rho,
        "completed": completed,
        "avg_wait_arrival_to_dispatch": avg_wait,
        "on_time_rate": on_time_rate,
        "max_incoming_q": metrics["max_incoming_q"],
        "max_ready_q": metrics["max_ready_q"],
        "max_vehicles_in_use": metrics["max_vehicles_in_use"],
        "event_counts": metrics["event_counts"],
    }
