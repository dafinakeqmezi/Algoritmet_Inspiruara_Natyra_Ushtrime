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
from ga.local_search import GuidedLocalSearchSolver

INSTANCES_DIR = REPO_ROOT / "data" / "input"
RESULTS_DIR = REPO_ROOT / "results"
PHASE3_DIR = RESULTS_DIR / "phase3_runs"
CSV_PATH = RESULTS_DIR / "results_phase3_ls.csv"

E3_CONFIG = next(e for e in EXPERIMENTS if e.name == "E3_exploitation")

FIELDS = [
    "instance",
    "run",
    "seed",
    "ga_score",
    "ls_score",
    "improvement_abs",
    "improvement_pct",
    "ga_generations",
    "ga_time_seconds",
    "ls_iterations",
    "ls_time_seconds",
]


def run_one_task(args):
    instance_path_str, run_idx = args
    instance_path = Path(instance_path_str)
    seed = run_idx

    parser = Parser(str(instance_path))
    instance = parser.parse()
    Utils.set_current_instance(instance)

    ga = GASolver(instance, E3_CONFIG, seed=seed)
    ga_result = ga.run()
    ga_score = ga_result.best_score
    ga_chrom = list(ga_result.best_solution.scheduled_programs)

    gls = GuidedLocalSearchSolver(
        ga.encoder,
        time_limit_seconds=90.0,
        max_outer_iters=30,
        inner_time_limit=5.0,
        inner_no_improve_limit=30,
        lambda_factor=0.1,
        seed=seed,
    )
    ls_result = gls.run(ga_chrom)
    ls_score = ls_result.best_score

    PHASE3_DIR.mkdir(parents=True, exist_ok=True)
    sched_path = PHASE3_DIR / f"{instance_path.stem}__run{run_idx + 1}.csv"
    final_solution = ga.encoder.decode(ls_result.best_chromosome)
    with open(sched_path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["program_id", "channel_id", "start", "end", "fitness"])
        for s in final_solution.scheduled_programs:
            w.writerow([s.program_id, s.channel_id, s.start, s.end, s.fitness])

    imp_abs = ls_score - ga_score
    imp_pct = (imp_abs / ga_score * 100.0) if ga_score > 0 else 0.0

    return {
        "instance": instance_path.stem,
        "run": run_idx,
        "seed": seed,
        "ga_score": ga_score,
        "ls_score": ls_score,
        "improvement_abs": imp_abs,
        "improvement_pct": round(imp_pct, 3),
        "ga_generations": ga_result.generations_completed,
        "ga_time_seconds": round(ga_result.time_seconds, 3),
        "ls_iterations": ls_result.iterations,
        "ls_time_seconds": round(ls_result.time_seconds, 3),
    }

def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--instance", help="restrict to a single instance stem")
    p.add_argument("--runs", type=int, default=10, help="runs per instance")
    p.add_argument("--workers", type=int, default=None, help="parallel workers")
    args = p.parse_args()

    files = sorted(INSTANCES_DIR.glob("*.json"))
    if args.instance:
        files = [f for f in files if f.stem == args.instance]
        if not files:
            sys.exit(f"no instance with stem {args.instance!r}")

    tasks = [(str(f), run_idx) for f in files for run_idx in range(args.runs)]
    print(f"Instances: {len(files)} | runs each: {args.runs} | total tasks: {len(tasks)}")

    n_workers = args.workers if args.workers else max(1, (os.cpu_count() or 4) - 1)
    print(f"Parallel workers: {n_workers}")
    print(f"Output: {CSV_PATH}\n")

    try:
        from tqdm import tqdm
        progress = tqdm(total=len(tasks), desc="Phase 3 GA+GLS", unit="run")
    except ImportError:
        progress = None

    rows = []
    t0 = time.perf_counter()
    with mp.Pool(processes=n_workers) as pool:
        for res in pool.imap_unordered(run_one_task, tasks):
            rows.append(res)
            if progress is not None:
                progress.update(1)
                progress.set_postfix_str(
                    f"last={res['instance'][:14]}/run{res['run']+1} "
                    f"GA={res['ga_score']} LS={res['ls_score']} +{res['improvement_pct']}%"
                )
    if progress is not None:
        progress.close()

    elapsed = time.perf_counter() - t0
    print(f"\nFinished {len(rows)} (GA+LS) runs in {elapsed:.1f}s ({elapsed/60:.1f} min)")

    rows.sort(key=lambda r: (r["instance"], r["run"]))
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(CSV_PATH, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    print(f"Wrote {len(rows)} rows to {CSV_PATH}")

if __name__ == "__main__":
    mp.freeze_support()
    main()
