from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path
from statistics import mean, pstdev

REPO_ROOT = Path(__file__).resolve().parent
RESULTS = REPO_ROOT / "results"

GREEDY_CSV = RESULTS / "results_phase1_greedy.csv"
ENDRITA_CSV = RESULTS / "results_phase1_endrita.csv"
GA_CSV = RESULTS / "results_phase2_ga.csv"

PER_EXP_CSV = RESULTS / "table_ga_per_experiment.csv"
PER_EXP_MD = RESULTS / "table_ga_per_experiment.md"
FINAL_CSV = RESULTS / "table_final_comparison.csv"
FINAL_MD = RESULTS / "table_final_comparison.md"


def load_score_map(path: Path, score_col: str) -> dict[str, int]:
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


def load_ga_runs() -> dict[tuple[str, str], list[dict]]:
    """Group GA rows by (instance, experiment)."""
    grouped: dict[tuple[str, str], list[dict]] = defaultdict(list)
    if not GA_CSV.exists():
        return grouped
    with open(GA_CSV, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            grouped[(row["instance"], row["experiment"])].append({
                "best_score": int(row["best_score"]),
                "time_seconds": float(row["time_seconds"]),
                "generations_completed": int(row["generations_completed"]),
            })
    return grouped


def build_per_experiment_table(grouped) -> list[dict]:
    rows = []
    instances = sorted({k[0] for k in grouped})
    experiments = sorted({k[1] for k in grouped})
    for inst in instances:
        row = {"instance": inst}
        for exp in experiments:
            runs = grouped.get((inst, exp), [])
            if not runs:
                row[f"{exp}_best"] = ""
                row[f"{exp}_avg"] = ""
                row[f"{exp}_worst"] = ""
                row[f"{exp}_std"] = ""
                row[f"{exp}_avg_time"] = ""
                continue
            scores = [r["best_score"] for r in runs]
            times = [r["time_seconds"] for r in runs]
            row[f"{exp}_best"] = max(scores)
            row[f"{exp}_avg"] = round(mean(scores), 1)
            row[f"{exp}_worst"] = min(scores)
            row[f"{exp}_std"] = round(pstdev(scores), 2) if len(scores) > 1 else 0.0
            row[f"{exp}_avg_time"] = round(mean(times), 1)
        rows.append(row)
    return rows, experiments


def write_per_experiment_csv(rows, experiments):
    fields = ["instance"]
    for exp in experiments:
        fields += [f"{exp}_best", f"{exp}_avg", f"{exp}_worst", f"{exp}_std", f"{exp}_avg_time"]
    with open(PER_EXP_CSV, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def write_per_experiment_md(rows, experiments):
    md = ["# Phase 2 — GA per-experiment results (10 runs each)", ""]
    header = ["instance"]
    for exp in experiments:
        header += [f"{exp} best", "avg", "worst", "std", "avg time (s)"]
    md.append("| " + " | ".join(header) + " |")
    md.append("|---" + "|---:" * (len(header) - 1) + "|")
    for r in rows:
        cells = [r["instance"]]
        for exp in experiments:
            cells += [
                str(r.get(f"{exp}_best", "")),
                str(r.get(f"{exp}_avg", "")),
                str(r.get(f"{exp}_worst", "")),
                str(r.get(f"{exp}_std", "")),
                str(r.get(f"{exp}_avg_time", "")),
            ]
        md.append("| " + " | ".join(cells) + " |")
    PER_EXP_MD.write_text("\n".join(md), encoding="utf-8")


def build_final_comparison(greedy, endrita, grouped):
    rows = []
    instances = sorted(set(greedy) | set(endrita) | {k[0] for k in grouped})
    for inst in instances:
        sf = greedy.get(inst)
        se = endrita.get(inst)
        ga_scores = []
        for k, runs in grouped.items():
            if k[0] == inst:
                ga_scores.extend(r["best_score"] for r in runs)
        ga_best = max(ga_scores) if ga_scores else None

        baseline = max(filter(lambda x: x is not None, [sf, se]), default=None)
        if ga_best is not None and baseline:
            improvement = (ga_best - baseline) / baseline * 100.0
        else:
            improvement = None

        rows.append({
            "instance": inst,
            "score_greedy": sf,
            "score_endrita": se,
            "ga_best": ga_best,
            "improvement_pct_vs_best_baseline": (round(improvement, 2) if improvement is not None else None),
        })
    return rows


def write_final_csv(rows):
    with open(FINAL_CSV, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["instance", "score_greedy", "score_endrita", "ga_best", "improvement_pct_vs_best_baseline"])
        w.writeheader()
        w.writerows(rows)


def write_final_md(rows):
    md = [
        "# Final comparison — Phase 1 baselines vs Phase 2 GA",
        "",
        "Improvement is measured against the **better** of the two Phase 1 baselines (max of Greedy, Endrita).",
        "",
        "| instance | Greedy | Endrita (beam) | GA best | Δ vs best baseline |",
        "|---|---:|---:|---:|---:|",
    ]
    n_better = n_equal = n_worse = 0
    for r in rows:
        sf = r["score_greedy"]
        se = r["score_endrita"]
        gb = r["ga_best"]
        imp = r["improvement_pct_vs_best_baseline"]
        if imp is not None:
            if imp > 0:
                n_better += 1
            elif imp < 0:
                n_worse += 1
            else:
                n_equal += 1
        md.append(
            f"| {r['instance']} | "
            f"{sf if sf is not None else ''} | "
            f"{se if se is not None else ''} | "
            f"{gb if gb is not None else ''} | "
            f"{(str(imp) + '%') if imp is not None else ''} |"
        )
    md += ["", f"**Summary:** GA beats best Phase 1 baseline on {n_better}, ties on {n_equal}, loses on {n_worse} (of {len(rows)})."]
    FINAL_MD.write_text("\n".join(md), encoding="utf-8")


def main():
    greedy = load_score_map(GREEDY_CSV, "score_greedy")
    endrita = load_score_map(ENDRITA_CSV, "score_endrita_beam")
    grouped = load_ga_runs()

    if not grouped:
        print(f"WARNING: no GA results at {GA_CSV}")
    if not greedy:
        print(f"WARNING: no Greedy results at {GREEDY_CSV}")
    if not endrita:
        print(f"WARNING: no Endrita results at {ENDRITA_CSV}")

    rows, experiments = build_per_experiment_table(grouped)
    write_per_experiment_csv(rows, experiments)
    write_per_experiment_md(rows, experiments)
    print(f"wrote {PER_EXP_CSV}")
    print(f"wrote {PER_EXP_MD}")

    final_rows = build_final_comparison(greedy, endrita, grouped)
    write_final_csv(final_rows)
    write_final_md(final_rows)
    print(f"wrote {FINAL_CSV}")
    print(f"wrote {FINAL_MD}")


if __name__ == "__main__":
    main()
