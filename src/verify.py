from .simulation import run_sim

def main():
    result1 = run_sim(horizon=50.0, seed=123, lam=2.0, mu=3.0, servers=1, fleet=2, policy="edd")
    s1 = result1["summary"]

    assert s1["completed"] >= 0
    assert s1["avg_wait_arrival_to_dispatch"] >= 0.0
    assert 0.0 <= s1["on_time_rate"] <= 1.0

    result2 = run_sim(horizon=50.0, seed=123, lam=2.0, mu=3.0, servers=1, fleet=2, policy="edd")
    s2 = result2["summary"]
    assert s1["completed"] == s2["completed"]
    assert abs(s1["avg_wait_arrival_to_dispatch"] - s2["avg_wait_arrival_to_dispatch"]) < 1e-9
    assert abs(s1["on_time_rate"] - s2["on_time_rate"]) < 1e-9

    print("Verification passed: invariants + reproducibility OK.")

if __name__ == "__main__":
    main()
