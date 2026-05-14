from __future__ import annotations

import argparse
import csv
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from parser.parser import Parser
from scheduler.greedy_scheduler import GreedyScheduler
from serializer.serializer import SolutionSerializer
from utils.utils import Utils

INSTANCES_DIR = REPO_ROOT / "data" / "input"    
RESULTS_DIR = REPO_ROOT / "results"
DATA_OUTPUT_DIR = REPO_ROOT / "data" / "output"  
ENDRITA_REPO = REPO_ROOT.parent / "endrita_repo"

GREEDY_CSV = RESULTS_DIR / "results_phase1_greedy.csv"
ENDRITA_CSV = RESULTS_DIR / "results_phase1_endrita.csv"
COMPARISON_CSV = RESULTS_DIR / "results_phase1_comparison.csv"
COMPARISON_MD = RESULTS_DIR / "results_phase1_comparison.md"


def run_greedy(instance_filter: str | None = None) -> None:
    files = sorted(INSTANCES_DIR.glob("*.json"))
    if instance_filter:
        files = [f for f in files if f.stem == instance_filter]
        if not files:
            sys.exit(f"no instance with stem {instance_filter!r} in {INSTANCES_DIR}")
    print(f"[Greedy] {len(files)} instance(s)")
    print(f"[Greedy] per-instance JSONs -> {DATA_OUTPUT_DIR}")
    DATA_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    rows = []
    for f in files:
        parser = Parser(str(f))
        instance = parser.parse()
        Utils.set_current_instance(instance)
        scheduler = GreedyScheduler(instance)
        t0 = time.perf_counter()
        sol = scheduler.generate_solution()
        elapsed = time.perf_counter() - t0
        serializer = SolutionSerializer(input_file_path=str(f),
                                        algorithm_name=type(scheduler).__name__.lower())
        serializer.serialize(sol)
        print(f"  {f.stem:30s}  score={sol.total_score:>8}  scheduled={len(sol.scheduled_programs):>3}  t={elapsed:6.2f}s", flush=True)
        rows.append((f.stem, sol.total_score, len(sol.scheduled_programs), f"{elapsed:.3f}", "ok"))

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    if instance_filter:
        existing: dict[str, tuple] = {}
        if GREEDY_CSV.exists():
            with open(GREEDY_CSV, newline="", encoding="utf-8") as fh:
                for row in csv.reader(fh):
                    if row and row[0] != "instance":
                        existing[row[0]] = tuple(row)
        for r in rows:
            existing[r[0]] = r
        rows = sorted(existing.values(), key=lambda r: r[0])
    with open(GREEDY_CSV, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["instance", "score_greedy", "scheduled_programs", "elapsed_seconds", "status"])
        w.writerows(rows)
    print(f"[Greedy] wrote {GREEDY_CSV}")

def run_endrita_beam() -> bool:
    """Run Endrita's beam search via subprocess. Returns True if endrita CSV ends up in results/."""
    endrita_runner = ENDRITA_REPO / "run_batch.py"
    if not endrita_runner.exists():
        print(f"[Endrita / BeamSearch] runner not found at {endrita_runner} — skipping")
        return False

    print(f"[Endrita / BeamSearch] subprocess into {ENDRITA_REPO}")
    env = dict(os.environ)
    env.setdefault("PYTHONUNBUFFERED", "1")
    proc = subprocess.run(
        [sys.executable, "-u", str(endrita_runner)],
        cwd=str(ENDRITA_REPO),
        env=env,
    )
    if proc.returncode != 0:
        print(f"[Endrita / BeamSearch] subprocess returned {proc.returncode}")
        return False

    src = ENDRITA_REPO.parent / "results_phase1_endrita.csv"
    if src.exists():
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(ENDRITA_CSV))
        print(f"[Endrita / BeamSearch] moved CSV -> {ENDRITA_CSV}")
        return True
    return ENDRITA_CSV.exists()

def _load_score_map(path: Path, score_col: str) -> dict[str, int]:
    out: dict[str, int] = {}
    if not path.exists():
        return out
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            try:
                out[row["instance"]] = int(row[score_col])
            except (ValueError, KeyError):
                continue
    return out


def build_comparison() -> None:
    fis = _load_score_map(GREEDY_CSV, "score_greedy")
    end = _load_score_map(ENDRITA_CSV, "score_endrita_beam")

    if not fis:
        print(f"[Comparison] missing {GREEDY_CSV}")
        return
    if not end:
        print(f"[Comparison] missing {ENDRITA_CSV} — comparison will only include Greedy")

    instances = sorted(set(fis) | set(end))
    rows = []
    n_fis_wins = n_end_wins = n_tie = 0
    for inst in instances:
        sf = fis.get(inst)
        se = end.get(inst)
        if sf is None or se is None:
            best = "missing"
        elif sf > se:
            best = "Greedy"; n_fis_wins += 1
        elif se > sf:
            best = "Endrita"; n_end_wins += 1
        else:
            best = "tie"; n_tie += 1
        rows.append((inst, sf, se, best))

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(COMPARISON_CSV, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["instance", "score_greedy", "score_endrita", "best"])
        w.writerows(rows)

    md = [
        "# Phase 1 Comparison — Greedy vs Endrita (BeamSearch)",
        "",
        "| instance | score_greedy | score_endrita | best |",
        "|---|---:|---:|:---:|",
    ]
    for inst, sf, se, best in rows:
        md.append(f"| {inst} | {sf if sf is not None else ''} | {se if se is not None else ''} | {best} |")
    md += ["", f"**Summary:** Greedy wins on {n_fis_wins}, Endrita wins on {n_end_wins}, ties on {n_tie} (out of {len(instances)})."]
    COMPARISON_MD.write_text("\n".join(md), encoding="utf-8")

    print(f"[Comparison] wrote {COMPARISON_CSV}")
    print(f"[Comparison] wrote {COMPARISON_MD}")
    print(f"[Comparison] Greedy={n_fis_wins}  Endrita={n_end_wins}  ties={n_tie}  total={len(instances)}")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--skip-endrita", action="store_true", help="don't run Endrita's beam search")
    p.add_argument("--skip-greedy", action="store_true", help="don't run the greedy")
    p.add_argument("--instance", help="run only one instance (e.g. canada_pw); merges into existing CSV")
    args = p.parse_args()

    if not args.skip_greedy:
        run_greedy(instance_filter=args.instance)
    if not args.skip_endrita and not args.instance:
        run_endrita_beam()
    build_comparison()

if __name__ == "__main__":
    main()
