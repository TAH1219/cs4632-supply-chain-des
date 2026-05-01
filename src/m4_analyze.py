import glob, json, math, csv, os
from collections import defaultdict

OUTDIR = "outputs_m4"  # change if you used a different --out folder

METRICS = [
    ("avg_wait_arrival_to_dispatch", "avg_wait"),
    ("on_time_rate", "on_time_rate"),
    ("completed", "completed"),
    ("max_ready_q", "max_ready_q"),
]

def mean(xs): return sum(xs) / len(xs)

def stdev(xs):
    if len(xs) < 2:
        return 0.0
    m = mean(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1))

def ci95(m, s, n):
    if n <= 1:
        return (m, m)
    half = 1.96 * (s / math.sqrt(n))
    return (m - half, m + half)

# Map run_id -> purpose from config.json (purpose is stored there)
purpose_by_run = {}
for cfg_path in glob.glob(os.path.join(OUTDIR, "run_*_config.json")):
    c = json.load(open(cfg_path, "r", encoding="utf-8"))
    purpose_by_run[str(c.get("run_id"))] = c.get("purpose", "")

groups = defaultdict(list)
for sum_path in glob.glob(os.path.join(OUTDIR, "run_*_summary.json")):
    s = json.load(open(sum_path, "r", encoding="utf-8"))
    rid = str(s.get("run_id", "")).strip() or os.path.basename(sum_path).split("_")[1]
    purpose = purpose_by_run.get(rid, "")
    groups[purpose].append(s)

out_csv = os.path.join(OUTDIR, "stats_summary.csv")
with open(out_csv, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["purpose","metric","n","mean","std","min","max","ci95_low","ci95_high"])
    for purpose, items in sorted(groups.items()):
        if purpose == "":
            purpose = "(no purpose)"
        for key, label in METRICS:
            xs = [float(it.get(key, 0.0)) for it in items]
            n = len(xs)
            m = mean(xs)
            sd = stdev(xs)
            lo, hi = ci95(m, sd, n)
            w.writerow([purpose, label, n,
                        f"{m:.4f}", f"{sd:.4f}", f"{min(xs):.4f}", f"{max(xs):.4f}",
                        f"{lo:.4f}", f"{hi:.4f}"])

print("Wrote:", out_csv)