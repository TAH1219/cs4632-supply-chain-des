def new_metrics():
    return {
        "completed": 0,
        "on_time": 0,
        "total_wait": 0.0
    }

def compute_stats(metrics):
    completed = metrics["completed"]
    avg_wait = (metrics["total_wait"] / completed) if completed else 0.0
    on_time_rate = (metrics["on_time"] / completed) if completed else 0.0
    return completed, avg_wait, on_time_rate