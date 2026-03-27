import argparse
import json
import os
import platform
import sys
import time

import simpy  

from .simulation import run_sim
from .exporter import ensure_dir, utc_now_iso, write_csv, write_json, append_index


def _validate_positive(name, v, allow_zero=False):
    if allow_zero and v == 0:
        return
    if v <= 0:
        raise ValueError(f"{name} must be > 0 (got {v})")


def _env_info():
    return {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "simpy_version": getattr(simpy, "__version__", "unknown"),
    }


def _write_run_outputs(out_dir, run_id, config, result, duration_s, status, purpose=""):
    ensure_dir(out_dir)

    ts_file = f"run_{run_id}_timeseries.csv"
    ev_file = f"run_{run_id}_events.csv"
    sum_file = f"run_{run_id}_summary.json"
    cfg_file = f"run_{run_id}_config.json"

    ts_path = os.path.join(out_dir, ts_file)
    ev_path = os.path.join(out_dir, ev_file)
    sum_path = os.path.join(out_dir, sum_file)
    cfg_path = os.path.join(out_dir, cfg_file)

    
    config_out = dict(config)
    config_out["purpose"] = purpose
    config_out["run_started_utc"] = config.get("run_started_utc")
    config_out["run_finished_utc"] = utc_now_iso()
    config_out["duration_s"] = duration_s
    config_out["status"] = status
    write_json(cfg_path, config_out)

    
    summary_out = dict(result["summary"])
    summary_out["duration_s"] = duration_s
    summary_out["status"] = status
    write_json(sum_path, summary_out)

    
    ts_rows = result["timeseries"]
    ts_fields = [
        "sim_time", "incoming_q", "ready_q",
        "vehicles_in_use", "fleet_capacity", "vehicle_utilization",
        "completed", "on_time", "avg_wait_so_far"
    ]
    write_csv(ts_path, ts_rows, ts_fields)

    
    ev_rows = result["events"]
    ev_fields = [
        "event_type", "sim_time", "order_id", "order_size", "order_due",
        "wait_time", "vehicles_in_use", "delivered_on_time", "time_in_system"
    ]
    
    for r in ev_rows:
        for k in ev_fields:
            r.setdefault(k, "")
    write_csv(ev_path, ev_rows, ev_fields)

   
    index_path = os.path.join(out_dir, "index.csv")
    index_fields = [
        "run_id", "purpose", "lam", "mu", "servers", "fleet", "vehicle_capacity",
        "horizon", "seed", "policy", "duration_s", "status",
        "timeseries_file", "events_file", "summary_file", "config_file"
    ]
    append_index(index_path, {
        "run_id": run_id,
        "purpose": purpose,
        "lam": config["lam"],
        "mu": config["mu"],
        "servers": config["servers"],
        "fleet": config["fleet"],
        "vehicle_capacity": config["vehicle_capacity"],
        "horizon": config["horizon"],
        "seed": config["seed"],
        "policy": config["policy"],
        "duration_s": f"{duration_s:.6f}",
        "status": status,
        "timeseries_file": ts_file,
        "events_file": ev_file,
        "summary_file": sum_file,
        "config_file": cfg_file,
    }, index_fields)

    return ts_path, ev_path, sum_path, cfg_path


def _single_run(args):
    _validate_positive("lam", args.lam)
    _validate_positive("mu", args.mu)
    _validate_positive("servers", args.servers)
    _validate_positive("fleet", args.fleet)
    _validate_positive("vehicle_capacity", args.vehicle_capacity)
    _validate_positive("horizon", args.horizon)
    _validate_positive("sample_dt", args.sample_dt)

    run_id = args.run_id
    out_dir = args.out

    config = {
        "run_id": run_id,
        "lam": args.lam,
        "mu": args.mu,
        "servers": args.servers,
        "fleet": args.fleet,
        "vehicle_capacity": args.vehicle_capacity,
        "horizon": args.horizon,
        "seed": args.seed,
        "policy": args.policy,
        "sample_dt": args.sample_dt,
        "environment": _env_info(),
        "run_started_utc": utc_now_iso(),
    }

    status = "Complete"
    t0 = time.perf_counter()
    try:
        result = run_sim(
            lam=args.lam,
            mu=args.mu,
            servers=args.servers,
            fleet=args.fleet,
            vehicle_capacity=args.vehicle_capacity,
            horizon=args.horizon,
            seed=args.seed,
            policy=args.policy,
            sample_dt=args.sample_dt,
        )
    except Exception as e:
        status = f"Error: {type(e).__name__}"
        result = {"summary": {"error": str(e)}, "timeseries": [], "events": []}
        raise
    finally:
        duration_s = time.perf_counter() - t0

    ts_path, ev_path, sum_path, cfg_path = _write_run_outputs(
        out_dir=out_dir,
        run_id=run_id,
        config=config,
        result=result,
        duration_s=duration_s,
        status=status,
        purpose=args.purpose or "",
    )

    s = result["summary"]
    print("=== Supply Chain DES (M3) ===")
    print(f"Run ID: {run_id} | Policy: {s['policy']}")
    print(f"lambda={s['lam']}, mu={s['mu']}, servers={s['servers']}, fleet={s['fleet']}, cap={s['vehicle_capacity']}, horizon={s['horizon']}, seed={s['seed']}")
    print(f"rho=lambda/(s*mu)={s['rho']:.4f}  (stable if rho < 1)")
    print(f"completed={s['completed']}")
    print(f"avg_wait(arrival->dispatch)={s['avg_wait_arrival_to_dispatch']:.4f}")
    print(f"on_time_rate={s['on_time_rate']:.4f}")
    print(f"duration_s={duration_s:.6f}")
    print("--- files ---")
    print(ts_path)
    print(ev_path)
    print(sum_path)
    print(cfg_path)


def _batch_runs(args):
    out_dir = args.out
    ensure_dir(out_dir)

    with open(args.batch, "r", encoding="utf-8") as f:
        runs = json.load(f)

    if not isinstance(runs, list) or len(runs) == 0:
        raise ValueError("Batch file must be a non-empty JSON list of run configs.")

    for run_cfg in runs:
        run_id = str(run_cfg.get("run_id", "")).strip()
        if not run_id:
            raise ValueError("Each run in batch must include a non-empty run_id (e.g., '001').")

        lam = float(run_cfg.get("lam", args.lam))
        mu = float(run_cfg.get("mu", args.mu))
        servers = int(run_cfg.get("servers", args.servers))
        fleet = int(run_cfg.get("fleet", args.fleet))
        vehicle_capacity = int(run_cfg.get("vehicle_capacity", args.vehicle_capacity))
        horizon = float(run_cfg.get("horizon", args.horizon))
        seed = int(run_cfg.get("seed", args.seed))
        policy = str(run_cfg.get("policy", args.policy))
        sample_dt = float(run_cfg.get("sample_dt", args.sample_dt))
        purpose = str(run_cfg.get("purpose", ""))

        # validation
        _validate_positive("lam", lam)
        _validate_positive("mu", mu)
        _validate_positive("servers", servers)
        _validate_positive("fleet", fleet)
        _validate_positive("vehicle_capacity", vehicle_capacity)
        _validate_positive("horizon", horizon)
        _validate_positive("sample_dt", sample_dt)

        config = {
            "run_id": run_id,
            "lam": lam,
            "mu": mu,
            "servers": servers,
            "fleet": fleet,
            "vehicle_capacity": vehicle_capacity,
            "horizon": horizon,
            "seed": seed,
            "policy": policy,
            "sample_dt": sample_dt,
            "environment": _env_info(),
            "run_started_utc": utc_now_iso(),
        }

        status = "Complete"
        t0 = time.perf_counter()
        try:
            result = run_sim(
                lam=lam,
                mu=mu,
                servers=servers,
                fleet=fleet,
                vehicle_capacity=vehicle_capacity,
                horizon=horizon,
                seed=seed,
                policy=policy,
                sample_dt=sample_dt,
            )
        except Exception as e:
            status = f"Error: {type(e).__name__}"
            result = {"summary": {"error": str(e)}, "timeseries": [], "events": []}
        duration_s = time.perf_counter() - t0

        _write_run_outputs(
            out_dir=out_dir,
            run_id=run_id,
            config=config,
            result=result,
            duration_s=duration_s,
            status=status,
            purpose=purpose,
        )

        print(f"[{run_id}] {purpose} -> {status} ({duration_s:.3f}s)")


def main():
    p = argparse.ArgumentParser(description="CS4632 Supply Chain DES (Milestone 3 runner)")
    p.add_argument("--out", default="outputs", help="Output directory (default: outputs)")
    p.add_argument("--run-id", default="001", help="Run ID string (default: 001)")
    p.add_argument("--purpose", default="", help="Short purpose label for the run (for index table)")
    p.add_argument("--lam", type=float, default=2.0, help="Arrival rate lambda (>0)")
    p.add_argument("--mu", type=float, default=3.0, help="Service rate mu (>0)")
    p.add_argument("--servers", type=int, default=1, help="Number of fulfillment servers (>0)")
    p.add_argument("--fleet", type=int, default=3, help="Vehicle fleet size (>0)")
    p.add_argument("--vehicle-capacity", type=int, default=8, help="Vehicle capacity (>0)")
    p.add_argument("--horizon", type=float, default=500.0, help="Simulation end time (>0)")
    p.add_argument("--seed", type=int, default=123, help="Random seed")
    p.add_argument("--policy", default="edd", choices=["edd", "fcfs"], help="Dispatch policy")
    p.add_argument("--sample-dt", type=float, default=1.0, help="Time-series sampling interval (>0)")
    p.add_argument("--batch", default="", help="Path to batch runs JSON (runs.json). If set, runs batch mode.")
    args = p.parse_args()

    if args.batch:
        _batch_runs(args)
    else:
        _single_run(args)


if __name__ == "__main__":
    main()
