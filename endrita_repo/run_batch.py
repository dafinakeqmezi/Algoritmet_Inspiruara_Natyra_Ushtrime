"""
Phase 1 batch runner — Endrita's BeamSearch on all 17 instances.

For each input in data/input/ this:
  - runs BeamSearch in a child process with a 10-min hard timeout
  - on success, serializes the per-instance Solution to data/output/
    via the existing SolutionSerializer (filename pattern unchanged:
    {base}_output_beamsearchscheduler_{score}.json)
  - records score / status in the CSV

If a per-instance output JSON already exists in data/output/ the
instance is skipped (resume mode). Use --force to re-run everything.

Writes results to ../greedy_repo/results/results_phase1_endrita.csv
(or workspace root if greedy_repo/results/ doesn't exist).
"""
import argparse
import csv
import multiprocessing as mp
import re
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
WORKSPACE_ROOT = REPO_ROOT.parent
INPUT_DIR = REPO_ROOT / "data" / "input"
OUTPUT_DIR = REPO_ROOT / "data" / "output"

PRIMARY_OUT = WORKSPACE_ROOT / "greedy_repo" / "results" / "results_phase1_endrita.csv"
FALLBACK_OUT = WORKSPACE_ROOT / "results_phase1_endrita.csv"

PER_INSTANCE_TIMEOUT_SECONDS = 600  # 10 minutes

# Instances on which Endrita's beam (width auto-bumped to 500 for n_channels > 50)
# does not finish inside the 10-minute cap. Recorded as 'timeout' in the CSV
# without re-running by default. Use --no-skip-timeouts to actually re-attempt.
KNOWN_TIMEOUT_INSTANCES = {
    "china_pw",
    "uk_iptv",
    "us_iptv",
    "youtube_gold",
    "youtube_premium",
}


def _existing_output_score(instance_stem: str) -> int | None:
    """If data/output/ already has a serialized result for this instance,
    return the score parsed from its filename. Otherwise None."""
    base = instance_stem.replace("_input", "")
    pattern = re.compile(rf"^{re.escape(base)}_output_beamsearchscheduler_(-?\d+)\.json$")
    if not OUTPUT_DIR.exists():
        return None
    for f in OUTPUT_DIR.iterdir():
        m = pattern.match(f.name)
        if m:
            return int(m.group(1))
    return None


def _worker(input_path_str, q):
    """Runs in a child process so we can timeout via Process.terminate()."""
    sys.path.insert(0, str(REPO_ROOT))
    from parser.parser import Parser
    from scheduler.beam_search_scheduler import BeamSearchScheduler
    from serializer.serializer import SolutionSerializer
    from utils.utils import Utils
    try:
        parser = Parser(input_path_str)
        instance = parser.parse()
        Utils.set_current_instance(instance)
        scheduler = BeamSearchScheduler(
            instance_data=instance,
            beam_width=100,
            lookahead_limit=4,
            density_percentile=25,
            verbose=False,
        )
        sol = scheduler.generate_solution()
        # Serialize per-instance Solution JSON to data/output/
        serializer = SolutionSerializer(input_file_path=input_path_str,
                                        algorithm_name=type(scheduler).__name__.lower())
        serializer.serialize(sol)
        q.put(("ok", sol.total_score, len(sol.scheduled_programs)))
    except Exception as e:
        q.put(("error", str(e), 0))


def run_one(input_path: Path):
    q = mp.Queue()
    p = mp.Process(target=_worker, args=(str(input_path), q))
    t0 = time.perf_counter()
    p.start()
    p.join(timeout=PER_INSTANCE_TIMEOUT_SECONDS)
    if p.is_alive():
        p.terminate()
        p.join(timeout=10)
        if p.is_alive():
            p.kill()
        return None, 0, time.perf_counter() - t0, "timeout"
    elapsed = time.perf_counter() - t0
    try:
        status, score_or_msg, n = q.get_nowait()
    except Exception:
        return None, 0, elapsed, "no_result"
    if status == "ok":
        return score_or_msg, n, elapsed, "ok"
    return None, 0, elapsed, f"error: {score_or_msg}"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--force", action="store_true", help="re-run even if output JSON exists")
    p.add_argument("--no-skip-timeouts", action="store_true",
                   help="actually re-attempt the known-timeout instances (~50 min)")
    args = p.parse_args()

    files = sorted(INPUT_DIR.glob("*.json"))
    print(f"Found {len(files)} instance files in {INPUT_DIR}", flush=True)
    out_path = PRIMARY_OUT if PRIMARY_OUT.parent.exists() else FALLBACK_OUT
    print(f"Output CSV   : {out_path}", flush=True)
    print(f"Per-instance JSONs: {OUTPUT_DIR}", flush=True)
    print(f"Per-instance timeout: {PER_INSTANCE_TIMEOUT_SECONDS}s\n", flush=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    rows = []
    for f in files:
        name = f.stem
        if not args.force:
            existing = _existing_output_score(name)
            if existing is not None:
                print(f"  {name:30s}  score={existing:>8}  [skipped — existing output JSON]", flush=True)
                rows.append((name, existing, "", "", "ok"))
                continue
        if (not args.no_skip_timeouts) and name in KNOWN_TIMEOUT_INSTANCES:
            print(f"  {name:30s}  score=       —  scheduled=  0  [skipped — known to time out at {PER_INSTANCE_TIMEOUT_SECONDS}s]", flush=True)
            rows.append((name, "", 0, f"{PER_INSTANCE_TIMEOUT_SECONDS:.3f}", "timeout"))
            continue
        score, n_scheduled, elapsed, status = run_one(f)
        score_disp = score if score is not None else "—"
        print(f"  {name:30s}  score={str(score_disp):>8}  scheduled={n_scheduled:>3}  time={elapsed:7.2f}s  [{status}]", flush=True)
        rows.append((name, score if score is not None else "", n_scheduled, f"{elapsed:.3f}", status))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["instance", "score_endrita_beam", "scheduled_programs", "elapsed_seconds", "status"])
        writer.writerows(rows)
    print(f"\nDone. Wrote {len(rows)} rows to {out_path}", flush=True)


if __name__ == "__main__":
    mp.freeze_support()
    main()
