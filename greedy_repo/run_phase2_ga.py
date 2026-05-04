from __future__ import annotations

import argparse
import csv
import multiprocessing as mp
import os
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from parser.parser import Parser
from utils.utils import Utils
from ga.config import EXPERIMENTS
from ga.ga_solver import GASolver

INSTANCES_DIR = REPO_ROOT / "data" / "input"     
RESULTS_DIR = REPO_ROOT / "results"
CONVERGENCE_DIR = RESULTS_DIR / "convergence"
RUNS_DIR = RESULTS_DIR / "runs"
CSV_PATH = RESULTS_DIR / "results_phase2_ga.csv"


def _exp_filename_tag(exp_name: str) -> str:
    """E1_baseline -> exp1_baseline, E2_exploration -> exp2_exploration, etc."""
    if exp_name.startswith("E") and len(exp_name) >= 2 and exp_name[1].isdigit():
        return "exp" + exp_name[1:]
    return exp_name.lower()

FIELDS = [
    "instance",
    "experiment",
    "run",
    "seed",
    "best_score",
    "avg_score_final_gen",
    "generations_completed",
    "time_seconds",
]


def run_one_task(args):
    instance_path_str, exp_idx, run_idx = args
    instance_path = Path(instance_path_str)
    config = EXPERIMENTS[exp_idx]
    seed = run_idx

    parser = Parser(str(instance_path))
    instance = parser.parse()
    Utils.set_current_instance(instance)

    ga = GASolver(instance, config, seed=seed)
    result = ga.run()

    if run_idx == 0 and result.gen_log:
        CONVERGENCE_DIR.mkdir(parents=True, exist_ok=True)
        log_path = CONVERGENCE_DIR / f"{instance_path.stem}__{config.name}.csv"
        with open(log_path, "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["gen", "best_so_far", "gen_best", "gen_avg", "elapsed_s"])
            for e in result.gen_log:
                w.writerow([e.gen, e.best_so_far, e.gen_best, round(e.gen_avg, 2), round(e.elapsed_s, 3)])


    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    run_filename = f"{instance_path.stem}__{_exp_filename_tag(config.name)}__run{run_idx + 1}.csv"
    run_path = RUNS_DIR / run_filename
    with open(run_path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["program_id", "channel_id", "start", "end", "fitness"])
        for s in result.best_solution.scheduled_programs:
            w.writerow([s.program_id, s.channel_id, s.start, s.end, s.fitness])

    return {
        "instance": instance_path.stem,
        "experiment": config.name,
        "run": run_idx,
        "seed": seed,
        "best_score": result.best_score,
        "avg_score_final_gen": round(result.avg_score_final_gen, 2),
        "generations_completed": result.generations_completed,
        "time_seconds": round(result.time_seconds, 3),
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--instance", help="restrict to a single instance stem (e.g. toy)")
    p.add_argument("--experiment", help="restrict to a single experiment name")
    p.add_argument("--runs", type=int, default=10, help="runs per (instance,experiment)")
    p.add_argument("--workers", type=int, default=None, help="parallel workers")
    args = p.parse_args()

    files = sorted(INSTANCES_DIR.glob("*.json"))
    if args.instance:
        files = [f for f in files if f.stem == args.instance]
        if not files:
            sys.exit(f"no instance with stem {args.instance!r}")

    exps = list(range(len(EXPERIMENTS)))
    if args.experiment:
        exps = [i for i, e in enumerate(EXPERIMENTS) if e.name == args.experiment]
        if not exps:
            sys.exit(f"no experiment named {args.experiment!r}; choose from {[e.name for e in EXPERIMENTS]}")

    tasks = [(str(f), exp_idx, run_idx) for f in files for exp_idx in exps for run_idx in range(args.runs)]
    print(f"Instances: {len(files)} | experiments: {len(exps)} | runs each: {args.runs} | total tasks: {len(tasks)}")

    n_workers = args.workers if args.workers else max(1, (os.cpu_count() or 4) - 1)
    print(f"Parallel workers: {n_workers}")
    print(f"Output: {CSV_PATH}\n")

    try:
        from tqdm import tqdm
        progress = tqdm(total=len(tasks), desc="GA runs", unit="run")
    except ImportError:
        progress = None

    rows = []
    t0 = time.perf_counter()
    with mp.Pool(processes=n_workers) as pool:
        for res in pool.imap_unordered(run_one_task, tasks):
            rows.append(res)
            if progress is not None:
                progress.update(1)
                progress.set_postfix_str(f"last={res['instance'][:14]}/{res['experiment'][:6]}={res['best_score']}")
    if progress is not None:
        progress.close()

    elapsed = time.perf_counter() - t0
    print(f"\nFinished {len(rows)} runs in {elapsed:.1f}s ({elapsed/60:.1f} min)")

    rows.sort(key=lambda r: (r["instance"], r["experiment"], r["run"]))
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(CSV_PATH, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} rows to {CSV_PATH}")


if __name__ == "__main__":
    mp.freeze_support()
    main()
