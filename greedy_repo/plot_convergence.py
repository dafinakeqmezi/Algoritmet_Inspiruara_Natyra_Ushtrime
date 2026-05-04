from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

REPO_ROOT = Path(__file__).resolve().parent
INSTANCES_DIR = REPO_ROOT / "data" / "input"
RESULTS = REPO_ROOT / "results"
CONV_DIR = RESULTS / "convergence"
PLOTS_DIR = RESULTS / "plots"

EXPERIMENT_ORDER = ["E1_baseline", "E2_exploration", "E3_exploitation"]
EXPERIMENT_COLORS = {
    "E1_baseline": "tab:blue",
    "E2_exploration": "tab:orange",
    "E3_exploitation": "tab:green",
}


def load_curve(path: Path) -> tuple[list[int], list[int], list[float]]:
    gens, bests, avgs = [], [], []
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            gens.append(int(row["gen"]))
            bests.append(int(row["best_so_far"]))
            avgs.append(float(row["gen_avg"]))
    return gens, bests, avgs


def list_instances_with_logs() -> list[str]:
    if not CONV_DIR.exists():
        return []
    instances = set()
    for f in CONV_DIR.glob("*__*.csv"):
        instances.add(f.stem.split("__")[0])
    return sorted(instances)


def instance_size(instance_stem: str) -> int:
    """Rough size = sum of program counts across all channels."""
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
        fig, ax = plt.subplots(figsize=(7, 4.2))
    plotted = False
    for exp in EXPERIMENT_ORDER:
        path = CONV_DIR / f"{instance}__{exp}.csv"
        if not path.exists():
            continue
        gens, bests, avgs = load_curve(path)
        if not gens:
            continue
        color = EXPERIMENT_COLORS.get(exp, None)
        ax.plot(gens, bests, label=f"{exp} (best so far)", color=color, linewidth=2)
        ax.plot(gens, avgs, label=f"{exp} (gen avg)", color=color, linestyle="--", alpha=0.5)
        plotted = True
    ax.set_xlabel("generation")
    ax.set_ylabel("score")
    ax.set_title(instance)
    ax.grid(True, alpha=0.3)
    if plotted:
        ax.legend(fontsize=8, loc="lower right")
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
    instances = list_instances_with_logs()
    if not instances:
        print(f"no convergence logs found in {CONV_DIR}", file=sys.stderr)
        return

    for inst in instances:
        plot_one_instance(inst)

    rep = representative_set(instances)
    n = len(rep)
    fig, axes = plt.subplots(1, n, figsize=(5.5 * n, 4.2), squeeze=False)
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
