from __future__ import annotations

import csv
import json
import sys
from pathlib import Path
from statistics import mean

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

REPO_ROOT = Path(__file__).resolve().parent
INSTANCES_DIR = REPO_ROOT / "data" / "input"
RESULTS = REPO_ROOT / "results"
HIST_DIR = RESULTS / "history"
PLOTS_DIR = RESULTS / "plots"

EXPERIMENT_ORDER = ["exp1_baseline", "exp2_exploration", "exp3_exploitation"]
EXPERIMENT_LABELS = {
    "exp1_baseline": "E1 baseline",
    "exp2_exploration": "E2 exploration",
    "exp3_exploitation": "E3 exploitation",
}
EXPERIMENT_COLORS = {
    "exp1_baseline": "tab:blue",
    "exp2_exploration": "tab:orange",
    "exp3_exploitation": "tab:green",
}


def load_history_runs(instance: str, exp_tag: str) -> list[tuple[list[int], list[int], list[float]]]:
    """Return one (gens, best, avg) triple per run for the given (instance, exp_tag)."""
    runs = []
    for path in sorted(HIST_DIR.glob(f"{instance}__{exp_tag}__run*.csv")):
        gens, best, avg = [], [], []
        with open(path, newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                gens.append(int(row["generation"]))
                best.append(int(row["best_score"]))
                avg.append(float(row["avg_score"]))
        if gens:
            runs.append((gens, best, avg))
    return runs

def aggregate_across_runs(runs: list[tuple[list[int], list[int], list[float]]]):
    """Return common gens + per-gen mean/min/max of best_score across runs (truncate
    to the shortest run)."""
    if not runs:
        return [], [], [], [], []
    n = min(len(r[0]) for r in runs)
    gens = runs[0][0][:n]
    best_mean, best_min, best_max, avg_mean = [], [], [], []
    for i in range(n):
        col_best = [r[1][i] for r in runs]
        col_avg = [r[2][i] for r in runs]
        best_mean.append(mean(col_best))
        best_min.append(min(col_best))
        best_max.append(max(col_best))
        avg_mean.append(mean(col_avg))
    return gens, best_mean, best_min, best_max, avg_mean


def list_instances_with_history() -> list[str]:
    if not HIST_DIR.exists():
        return []
    instances = set()
    for f in HIST_DIR.glob("*__*__run*.csv"):
        instances.add(f.stem.split("__")[0])
    return sorted(instances)


def instance_size(instance_stem: str) -> int:
    p = INSTANCES_DIR / f"{instance_stem}.json"
    if not p.exists():
        return 0
    try:
        data = json.loads(p.read_text(encoding="utf-8", errors="ignore"))
        return sum(len(ch.get("programs", [])) for ch in data.get("channels", []))
    except Exception:
        return 0

def plot_one_instance(instance: str, ax=None) -> bool:
    own_fig = ax is None
    if own_fig:
        fig, ax = plt.subplots(figsize=(7.5, 4.6))
    plotted = False
    for exp_tag in EXPERIMENT_ORDER:
        runs = load_history_runs(instance, exp_tag)
        if not runs:
            continue
        gens, b_mean, b_min, b_max, a_mean = aggregate_across_runs(runs)
        color = EXPERIMENT_COLORS[exp_tag]
        label = EXPERIMENT_LABELS[exp_tag]
        ax.plot(gens, b_mean, label=f"{label} — best (mean of 10)", color=color, linewidth=2)
        ax.fill_between(gens, b_min, b_max, color=color, alpha=0.15,
                        label=f"{label} — best (min/max band)")
        ax.plot(gens, a_mean, color=color, linestyle="--", alpha=0.5,
                label=f"{label} — gen avg (mean)")
        plotted = True
    ax.set_xlabel("generation")
    ax.set_ylabel("score")
    ax.set_title(instance)
    ax.grid(True, alpha=0.3)
    if plotted:
        ax.legend(fontsize=7, loc="lower right")
    if own_fig:
        fig.tight_layout()
        out = PLOTS_DIR / f"convergence_{instance}.png"
        fig.savefig(out, dpi=130)
        plt.close(fig)
        print(f"wrote {out}")
    return plotted

def representative_set(all_instances: list[str]) -> list[str]:
    sized = [(inst, instance_size(inst)) for inst in all_instances]
    sized = [s for s in sized if s[1] > 0]
    if not sized:
        return all_instances[:3]
    sized.sort(key=lambda x: x[1])
    n = len(sized)
    return [sized[0][0], sized[n // 2][0], sized[-1][0]]

def main():
    PLOTS_DIR.mkdir(parents=True, exist_ok=True)
    instances = list_instances_with_history()
    if not instances:
        print(f"no history logs in {HIST_DIR}", file=sys.stderr)
        return

    for inst in instances:
        plot_one_instance(inst)

    rep = representative_set(instances)
    n = len(rep)
    fig, axes = plt.subplots(1, n, figsize=(5.5 * n, 4.4), squeeze=False)
    for ax, inst in zip(axes[0], rep):
        plot_one_instance(inst, ax=ax)
    fig.suptitle(f"GA convergence on representative instances: {rep[0]} (small) -> {rep[-1]} (large)")
    fig.tight_layout()
    out = PLOTS_DIR / "convergence_representative.png"
    fig.savefig(out, dpi=130)
    plt.close(fig)
    print(f"wrote {out}")

if __name__ == "__main__":
    main()
