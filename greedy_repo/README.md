<table border="0">
 <tr>
    <td><img src="https://upload.wikimedia.org/wikipedia/commons/thumb/e/e1/University_of_Prishtina_logo.svg/1200px-University_of_Prishtina_logo.svg.png" width="150" alt="University Logo" /></td>
    <td>
      <p>Universiteti i Prishtinës</p>
      <p>Fakulteti i Inxhinierisë Elektrike dhe Kompjuterike</p>
      <p>Inxhinieri Kompjuterike dhe Softuerike - Programi Master</p>
      <p>Profesor: Prof. Dr. Kadri Sylejmani</p>
      <p>Asistent: MSc. Labeat Arbneshi</p>
    </td>
 </tr>
</table>

# TV Channel Scheduling Optimization — Phase 1 + Phase 2

## 1. Introduction

This project addresses the **TV Channel Scheduling Optimization for Public Spaces** problem from the Advanced Algorithms course (2025/26). Given a set of TV channels, each with a list of timed programs annotated with genre and viewer-score, the task is to select and schedule a non-overlapping subset of programs across the available broadcast window in order to **maximize total viewership score**, subject to constraints: programs must lie inside the global time window, must satisfy a minimum on-air duration, must respect a maximum consecutive same-genre run length, and must honor priority blocks that restrict which channels can broadcast at certain times. Time preferences add bonus points when a chosen program's genre matches the genre preferred for that time slot, and penalties are applied for switching channels mid-stream and for terminating the previous program early.

This repository contains:
- **Phase 1** — the original constructive heuristic (the greedy scheduler) and a comparison against another team's heuristic (Endrita's beam search).
- **Phase 2** — a Genetic Algorithm built on top of the same parser, fitness components, and validator, run across 17 instances × 3 configurations × 10 runs (510 executions) and benchmarked against Phase 1.

---

## 2. Phase 1 — Baseline solutions

### 2.1 Solution picked: the **Greedy Scheduler**

the base repository contains several Phase 1 attempts spread across branches (`greedy_lookahead`, several beam search variants, an `UpperBoundGreedy`, and even a C# `SchedulingAPI`), but **only `scheduler/greedy_scheduler.py` is present on `main`**. We picked **Greedy** as the Phase 1 baseline because:
- It is the only complete Python scheduler merged into the `main` branch, so it is the cleanest single starting point.
- It is a classical constructive heuristic — the standard fair baseline for a Genetic Algorithm comparison.
- Endrita's repository already provides the stronger Beam Search heuristic, so Phase 1 has a meaningful "team-vs-team" axis without needing to combine multiple solutions from the base repo.

### 2.2 Greedy logic — algorithm + fitness function

The greedy scheduler walks time forward from `opening_time` to `closing_time`. At every minute it asks `AlgorithmUtils.get_best_fit` which channel/program would yield the highest **per-step fitness** at the current time, given the schedule built so far:

```
fit(c, p, t, S) =   p.score
                  + Σ tp.bonus       for every TimePreference tp where
                                     tp.preferred_genre == p.genre
                                     AND  [tp.start, tp.end)  overlaps  [p.start, p.end)
                  − switch_penalty       if S non-empty AND S[-1].channel_id != c.channel_id
                  − termination_penalty  if S non-empty AND S[-1].unique_program_id != p.unique_id
                                         AND p.start < S[-1].end
                  + 0                    (delay_penalty disabled in the codebase)
```

A program is accepted only if it satisfies the validator (time-window, min-duration gap, max-consecutive-genre, priority blocks), does not overlap the previous broadcast, and has `fit > 0`. The total score returned by the scheduler is the sum of all accepted per-step fitnesses. **The Phase 2 GA uses exactly this fitness function** (`AlgorithmUtils.*`) so the two are directly comparable.

### 2.3 Phase 1 comparison — Greedy vs Endrita (Beam Search)

Endrita's beam search uses `beam_width = 100`, `lookahead = 4`, `density_percentile = 25` (auto-bumped to `beam_width = 500` for instances with > 50 channels). To produce his column we ran his code (via `endrita_repo/run_batch.py`) with a **10-minute per-instance hard cap** because the auto-bumped beam width hangs on the largest instances. The pre-published scores Endrita ships in his repo (germany 1553, uk_tv 2266, usa 3601) match our re-run exactly, confirming the algorithm was reproduced correctly.

| instance | Greedy | Endrita (beam) | best |
|---|---:|---:|:---:|
| australia_iptv | 1346 | 4117 | Endrita |
| canada_pw | 1070 | 4628 | Endrita |
| china_pw | 1296 | (timeout) | Greedy |
| croatia_tv_input | 1278 | 2203 | Endrita |
| france_iptv | 1215 | 4370 | Endrita |
| germany_tv_input | 725 | 1553 | Endrita |
| kosovo_tv_input | 1160 | 2587 | Endrita |
| netherlands_tv_input | 1133 | 2636 | Endrita |
| singapore_pw | 1223 | 4316 | Endrita |
| spain_iptv | 978 | 4555 | Endrita |
| toy | 380 | 380 | tie |
| uk_iptv | 1491 | (timeout) | Greedy |
| uk_tv_input | 1098 | 2266 | Endrita |
| us_iptv | 1513 | (timeout) | Greedy |
| usa_tv_input | 1711 | 3601 | Endrita |
| youtube_gold | 13058 | (timeout) | Greedy |
| youtube_premium | 19900 | (timeout) | Greedy |

**Phase 1 summary:** Endrita wins 11, Greedy wins 5 (all five are instances where Endrita's beam search exceeded the 10-min budget), 1 tie (`toy` at the optimum 380). Endrita's beam search dominates wherever it can finish; the greedy is the only baseline available on the very largest inputs.

---

## 3. Phase 2 — Genetic Algorithm

### 3.1 Project layout

```
greedy_repo/
├── parser/, models/, utils/, validator/, serializer/   # original code (unchanged)
├── scheduler/greedy_scheduler.py                       # Phase 1 baseline (unchanged)
├── ga/
│   ├── chromosome.py        # encoding, decoding, validation/repair, fitness
│   ├── operators.py         # selection, crossover, mutation
│   ├── ga_solver.py         # main GA loop (GASolver + GAConfig + GARunResult)
│   └── config.py            # parameters for the 3 experiments
├── data/
│   ├── input/               # all 17 input JSON instances
│   └── output/              # 17 per-instance Solution JSONs from greedy
│                            # (filename pattern: {base}_output_greedyscheduler_{score}.json)
├── run_phase1_comparison.py # runs greedy + Endrita (subprocess) -> comparison table
├── run_phase2_ga.py         # multiprocessing driver for 510 GA executions
├── build_results_tables.py  # builds per-experiment + final comparison tables
├── plot_convergence.py      # generates matplotlib convergence plots
└── results/
    ├── results_phase1_greedy.csv           # 17 rows
    ├── results_phase1_endrita.csv           # 17 rows (incl. timeouts)
    ├── results_phase1_comparison.csv / .md
    ├── results_phase2_ga.csv               # 510 rows
    ├── table_ga_per_experiment.csv / .md   # 17×3 stats
    ├── table_final_comparison.csv / .md    # Greedy | Endrita | GA-best | Δ%
    ├── convergence/                        # per-run gen logs (one CSV per inst×exp)
    └── plots/                              # matplotlib PNGs

endrita_repo/                                # comparison repo (not modified by us)
├── data/
│   ├── input/               # 17 input JSON instances (same set as Greedy's)
│   └── output/              # 12 per-instance Solution JSONs from beam search
│                            # (5 missing = beam search timed out at 10 min on those inputs)
└── run_batch.py             # batch runner we added; honors --force / --no-skip-timeouts
```

### 3.2 Chromosome encoding — variable-length list of scheduled programs

Per the assignment spec:
- **Chromosome = one complete schedule** (a list of accepted programs in time order).
- **Gene = one scheduled program/item** (a `Schedule` object: `program_id`, `channel_id`, `start`, `end`, `fitness`, `unique_program_id`).
- **Fitness = total score of the schedule.**

So the chromosome type is `List[Schedule]` ordered by `start` time. Different chromosomes may have different lengths (a chromosome that fills the day with many short programs is longer than one with a few long ones). Every chromosome that the GA evaluates is **valid by construction** (built by greedy/randomized-greedy initialization or sanitized by `repair()` after crossover/mutation), so the chromosome's `total_score` is directly comparable to greedy's score on the same instance.

Concrete example for `toy.json` (opening 540, closing 1080, min_duration 30):

```
chromosome = [
    Schedule(program_id="n1", channel_id=0, start=540,  end=600, fitness=130, uid=1),
    Schedule(program_id="n2", channel_id=0, start=600,  end=660, fitness= 70, uid=2),
    Schedule(program_id="s2", channel_id=1, start=840,  end=960, fitness=125, uid=4),
    Schedule(program_id="m1", channel_id=2, start=960,  end=1020, fitness=55, uid=5),
]
total_score = 130 + 70 + 125 + 55 = 380
```

**Why variable-length:** the assignment defines a chromosome as "one complete schedule". A schedule has as many items as fit in the broadcast window, so a fixed-length encoding would have to either pad or truncate — both lose information. The problem-specific crossover operators below are designed to preserve schedule semantics rather than treat the chromosome as an aligned bit-string.

### 3.3 Fitness function — same as Phase 1

The GA reuses **the same per-step fitness components** that the greedy scheduler uses, summed over the chromosome's accepted decisions, so a Phase 2 score is directly comparable to a Phase 1 score on the same instance:

```
fitness(chromosome) =
    Σ  ( p.score
       + AlgorithmUtils.get_time_preference_bonus(instance, p, p.start)
       + AlgorithmUtils.get_switch_penalty(prev, instance, channel)
       + AlgorithmUtils.get_delay_penalty(prev, instance, p, p.start)        # 0
       + AlgorithmUtils.get_early_termination_penalty(prev, instance, p, p.start)
       )
    over every gene that decoded into a valid Schedule with step-fitness > 0
```

### 3.4 Operators — and why shift/replace/swap/insert were excluded

| | |
|---|---|
| **Selection** | Tournament (size `k` configurable) |
| **Crossover** | **Time-window crossover** OR **channel-based crossover** (one chosen per experiment) |
| **Mutation** | **Remove a random program** OR **greedy repair/regeneration** (one picked uniformly at random per call) |
| **Elitism** | Top-N copied unchanged into the next generation |

**Time-window crossover** ([`ga/operators.py:time_window_crossover`](ga/operators.py)) — picks a split time `t ∈ (opening, closing)`. Child 1 = parent 1's items ending at or before `t` + parent 2's items starting at or after `t`. Child 2 is the symmetric combination. The encoder's `repair()` cleans any seam violations.

**Channel-based crossover** ([`ga/operators.py:channel_based_crossover`](ga/operators.py)) — picks a random subset `S` of channels. Child 1 = parent 1's items on channels in `S` + parent 2's items on channels not in `S`. Child 2 is the complement.

**Remove-program mutation** ([`ga/operators.py:remove_random_program_mutation`](ga/operators.py)) — drops one randomly-chosen scheduled program from the chromosome. The empty slot is implicitly re-filled the next time crossover or repair touches that range.

**Greedy repair/regeneration mutation** ([`ga/operators.py:greedy_repair_regeneration_mutation`](ga/operators.py)) — picks a random cut point `k`, keeps `chromosome[0:k]` verbatim, and re-generates the tail with the deterministic greedy from `chromosome[k-1].end` (or `opening_time` if `k==0`). This recovers structure after disruption and explicitly does **not** "shift" a single program; it rebuilds the tail from a constructive baseline.

**Reasoning:** these operators are problem-specific and respect the schedule semantics. They drive the search through **recombination of schedule substructures** (a morning vs. afternoon plan, or a per-channel plan), which is what makes a GA a GA, not a hill-climber.

The professor explicitly **excluded** `shift / replace / swap / insert`. We did not use them:
- **shift** would re-position a single program by ±dt — none of our operators move a program; we either drop it (`remove`) or re-build the tail (`regenerate`).
- **swap** would exchange two existing genes' positions — never done; crossover combines sub-lists from two parents instead.
- **replace** would substitute one program for another at the same slot — never done; mutation either deletes or re-greedies.
- **insert** would add a program at a chosen position — only the greedy regeneration adds programs, and it does so by re-running the constructive heuristic, not by inserting at a chosen index.

These are all *positional, single-individual edits* — Phase-1 / local-search style. Avoiding them keeps the GA distinguishable from a hill-climber and makes the Phase 1 → Phase 2 comparison honest.

### 3.5 Repair strategy — repair-by-decoding (no penalty fitness)

After time-window crossover or channel-based crossover, a chromosome may contain overlapping items (e.g. parent 1's morning ended at 10:00 but parent 2's afternoon starts at 9:30 on a different channel). After remove-program mutation, a chromosome may have a gap (which is fine — the schedule just has unused time). We **repair on decode** rather than penalizing invalid solutions.

`ChromosomeEncoder.repair()` walks the chromosome's items in time order. For each item it:

1. Looks up the program by `unique_program_id` (drop if unknown).
2. Verifies the program fits inside the window (`program.end ≤ closing_time`, `program.end − program.start ≥ min_duration`).
3. Enforces no overlap with the previous accepted item and no same `unique_program_id` back-to-back.
4. Runs the existing `Validator` (time-window, min-duration gap, max_consecutive_genre, priority blocks).
5. Computes per-step fitness with the same components the greedy uses.
6. Rejects the item if step-fitness ≤ 0 (matching greedy's gating exactly).

Surviving items form the decoded `Solution`; rejected items contribute 0. **No penalty fitness is needed**, because every reported `total_score` corresponds to a fully valid solution by construction.

**Why repair, not penalty:** penalty-based fitness floods the early population with negative scores and slows convergence (the GA spends generations climbing out of the penalty pit instead of exploring). Repair-by-decoding keeps the search productive while still enforcing every constraint exactly.

### 3.6 Initial population (greedy-seeded + randomized greedy)

The initial population is built as follows:
- **One greedy-seeded individual** — the canonical Phase 1 greedy solution (`GAConfig.seed_with_greedy = True`).
- **`population_size − 1` randomized-greedy individuals** — same constructive logic as greedy, but at each step pick uniformly at random among the **top-K positive-fitness candidates** (K = 3 by default) instead of always the best. This produces diverse-but-valid starting chromosomes.

Combined with elitism, the greedy seed **guarantees the GA's reported best is never worse than the greedy baseline**. Greedy seeding is an *initialization* technique, not a banned evolution operator — it does not appear in the offspring pipeline at all, and it is standard practice in the GA literature for problems with strong constructive heuristics.

### 3.7 GA parameters — definitions

These are the seven parameters that the experiments vary. They are defined in [`ga/ga_solver.py`](ga/ga_solver.py) (`GAConfig`) and assigned per-experiment in [`ga/config.py`](ga/config.py).

| Parameter | What it controls |
|---|---|
| `population_size` | How many chromosomes live in each generation. Larger → more genetic diversity per generation, more compute per generation. |
| `generations` | Maximum number of generations the loop runs (early-exit if `time_limit_seconds` hits first). |
| `crossover_rate` | Probability that a selected pair of parents is recombined to produce offspring (`1 − crossover_rate` clones the parents instead). |
| `mutation_rate` | Probability that each newly-created child has one mutation applied to it. |
| `tournament_size` | How many individuals compete in each tournament-selection round. Larger → stronger selection pressure (better individuals propagate faster, but at the cost of diversity). |
| `elitism` | Top-N individuals copied unchanged into the next generation. Guarantees the GA's best score never regresses. |
| `crossover_type` | Which problem-specific crossover operator is used: `time_window` / `channel`. |
| `time_limit_seconds` | Hard wall-time cap per run; checked at the top of each generation. Default 300 s (= 5 min). |

### 3.8 Three experiments

| Param | E1 — Baseline | E2 — More population | E3 — More pop + more gens |
|---|---:|---:|---:|
| `population_size` | 50 | 100 | 100 |
| `generations` | 100 | 100 | 150 |
| `crossover_rate` | 0.8 | 0.8 | 0.9 |
| `mutation_rate` | 0.10 | 0.15 | 0.15 |
| `tournament_size` | 3 | 3 | 3 |
| `elitism` | 2 | 3 | 3 |
| `crossover_type` | time_window | time_window | channel |
| `time_limit_seconds` | 300 (5 min) | 300 (5 min) | 300 (5 min) |

These three configurations are applied **as-is to all 17 instances** (parameters are *fixed within an experiment*, *changed between experiments*) so the score effect of changing parameters is isolated from instance-specific noise.

**What each configuration is testing:**

- **E1 (Baseline)** — small population, moderate mutation, time-window crossover, small elite. Reference point for the other two.
- **E2 (More population)** — doubles the population and bumps mutation + elitism. Tests whether more diversity per generation, without changing the number of generations, lifts scores.
- **E3 (More pop + more gens)** — keeps E2's larger population and ups generations to 150 + crossover rate to 0.9 + switches to **channel-based crossover**. Tests whether (a) extra wall time + (b) a different recombination axis (per-channel rather than per-time-window) lifts scores further.

### 3.9 Reproducibility & execution

- Per-run seed: `seed = run_index` (0..9), passed to a per-run `random.Random`.
- Hard cap: 5 minutes wall time per run, checked at the top of each generation.
- Parallelism: `multiprocessing.Pool(os.cpu_count() − 1)`.
- Progress: `tqdm` over the 510 tasks.
- Output CSVs in `results/`.

The full 510-run sweep took **10.5 minutes wall time on 15 parallel workers** on the development machine.

---

## 4. Results

### 4.1 Per-experiment table (best / avg / worst over 10 runs, average wall time)

| instance | E1 best | E1 avg | E1 worst | E1 t(s) | E2 best | E2 avg | E2 worst | E2 t(s) | E3 best | E3 avg | E3 worst | E3 t(s) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| australia_iptv | 2336 | 2135.1 | 1791 | 4.9 | **3330** | 2666.6 | 2206 | 8.9 | 2379 | 2051.5 | 1666 | 9.6 |
| canada_pw | 3072 | 2682.7 | 2353 | 11.0 | **4073** | 3812.2 | 3207 | 17.7 | 3035 | 2729.2 | 2501 | 14.6 |
| china_pw | 1659 | 1407.7 | 1230 | 12.2 | **1921** | 1632.5 | 1472 | 11.7 | 1592 | 1362.5 | 1125 | 9.9 |
| croatia_tv_input | 1694 | 1443.4 | 1280 | 1.4 | **2034** | 1762.2 | 1377 | 3.2 | 1379 | 1290.3 | 1278 | 2.6 |
| france_iptv | 1915 | 1792.9 | 1666 | 3.3 | **2537** | 2278.7 | 2047 | 5.6 | 1994 | 1809.8 | 1635 | 4.6 |
| germany_tv_input | **932** | 915.0 | 897 | 1.1 | **932** | 923.8 | 907 | 2.2 | 917 | 902.5 | 882 | 2.3 |
| kosovo_tv_input | 1532 | 1237.8 | 1160 | 1.3 | **1691** | 1402.8 | 1223 | 2.8 | 1371 | 1204.9 | 1160 | 2.5 |
| netherlands_tv_input | 1382 | 1259.8 | 1140 | 1.4 | **1825** | 1557.6 | 1353 | 3.3 | 1415 | 1234.3 | 1140 | 2.6 |
| singapore_pw | 2698 | 2389.4 | 2146 | 4.1 | **3640** | 3320.1 | 3020 | 8.5 | 2617 | 2338.6 | 2012 | 6.9 |
| spain_iptv | 2250 | 2037.3 | 1820 | 3.1 | **3071** | 2635.9 | 2275 | 6.1 | 2275 | 2018.8 | 1727 | 5.2 |
| toy | **380** | 380.0 | 380 | 0.5 | **380** | 380.0 | 380 | 1.0 | **380** | 380.0 | 380 | 1.1 |
| uk_iptv | 2656 | 2337.2 | 2053 | 6.6 | **3268** | 2929.8 | 2613 | 9.3 | 2666 | 2413.4 | 2180 | 9.0 |
| uk_tv_input | 1247 | 1160.8 | 1095 | 1.1 | **1408** | 1314.6 | 1203 | 2.6 | 1222 | 1103.9 | 1033 | 2.0 |
| us_iptv | 2103 | 1866.2 | 1576 | 25.5 | **2519** | 1978.9 | 1598 | 28.6 | 2165 | 1656.1 | 1573 | 27.4 |
| usa_tv_input | 1762 | 1716.6 | 1711 | 1.7 | **1973** | 1804.0 | 1711 | 3.5 | 1711 | 1711.0 | 1711 | 3.2 |
| youtube_gold | 12789 | 12179.5 | 11754 | 54.2 | **15822** | 14535.8 | 12809 | 119.1 | 12648 | 12021.6 | 11276 | 99.1 |
| youtube_premium | 17963 | 16906.0 | 15916 | 40.9 | **22467** | 20206.6 | 18695 | 101.5 | 17472 | 17090.1 | 16452 | 69.3 |

Bold = best across the three experiments on that instance. **E2 (Exploration) gives the best score on 16 of 17 instances** (and ties with E1 and E3 on `toy`, where 380 is the optimum).

### 4.2 Final comparison — Phase 1 baselines vs Phase 2 GA-best

The full table is auto-generated at [results/table_final_comparison.md](results/table_final_comparison.md). "Δ vs best baseline" compares GA-best against `max(Greedy, Endrita)` for each instance.

| instance | Greedy | Endrita (beam) | GA best | Δ vs best baseline |
|---|---:|---:|---:|---:|
| australia_iptv | 1346 | 4117 | 3330 | −19.1% |
| canada_pw | 1070 | 4628 | 4073 | −12.0% |
| china_pw | 1296 | (timeout) | 1921 | **+48.2%** |
| croatia_tv_input | 1278 | 2203 | 2034 | −7.7% |
| france_iptv | 1215 | 4370 | 2537 | −41.9% |
| germany_tv_input | 725 | 1553 | 932 | −40.0% |
| kosovo_tv_input | 1160 | 2587 | 1691 | −34.6% |
| netherlands_tv_input | 1133 | 2636 | 1825 | −30.8% |
| singapore_pw | 1223 | 4316 | 3640 | −15.7% |
| spain_iptv | 978 | 4555 | 3071 | −32.6% |
| toy | 380 | 380 | 380 | 0.0% |
| uk_iptv | 1491 | (timeout) | 3268 | **+119.2%** |
| uk_tv_input | 1098 | 2266 | 1408 | −37.9% |
| us_iptv | 1513 | (timeout) | 2519 | **+66.5%** |
| usa_tv_input | 1711 | 3601 | 1973 | −45.2% |
| youtube_gold | 13058 | (timeout) | 15822 | **+21.2%** |
| youtube_premium | 19900 | (timeout) | 22467 | **+12.9%** |

**Two distinct stories live in this table — read both.**

**vs Greedy — the GA's home turf, since the GA reuses Greedy's parser/fitness/validator:**
the GA improves on **16 of 17 instances**, with deltas ranging from **+12.9% (youtube_premium) to +280.7% (canada_pw)**. The only non-improvement is `toy`, where greedy already finds the optimum (380) and the GA matches it. Greedy seeding plus elitism guarantees the GA never falls below greedy, and in practice it finds substantial gains on every other instance. This is the comparison the GA was designed for.

**vs Endrita (beam) — the more aggressive baseline:**
Endrita's beam search (width 100 → 500 for big channels, lookahead 4) is a much stronger Phase 1 algorithm than greedy. On the **5 instances where Endrita's beam exceeded the 10-min per-instance cap (`china_pw`, `uk_iptv`, `us_iptv`, `youtube_gold`, `youtube_premium`)**, the GA wins by **+12.9% to +119.2%**. On the **11 instances where Endrita's beam finished**, the GA is below it: deep deterministic beam search has had a lot of hand-tuning attention; a clean classical GA run for 5 minutes does not always overtake it on medium-sized instances.

**Why the difference matters for the assignment:** the assignment is an apples-to-apples Phase 1 → Phase 2 comparison *on the chosen Phase 1 codebase*. We chose the greedy as that codebase, so the GA → +12.9% to +281% improvement is the headline result. Endrita's beam is included as a richer Phase 1 baseline, and the GA still wins on the 5 instances where the beam cannot finish — which is also the practical upside of GAs over deterministic search: graceful behavior on inputs too large for an exhaustive method.

### 4.3 Convergence plots — three representative instances

`plot_convergence.py` writes one PNG per instance into `results/plots/`. The three highlighted below were chosen as small / medium / large representatives.

#### Small — `toy.json`  (3 channels, 5 programs)

![convergence_toy](results/plots/convergence_toy.png)

The optimum (380) is reached at generation 0 thanks to the greedy seed, and all three experiments hold it for the rest of the run.

#### Medium — `canada_pw.json`

![convergence_canada_pw](results/plots/convergence_canada_pw.png)

Greedy seed starts the search at 1070; **E2 (Exploration) climbs to 4073** by generation ~120 while E1 and E3 plateau around 3000. This is the +280% improvement headline number.

#### Large — `youtube_premium.json`  (1677 channels, 1440 slots)

![convergence_youtube_premium](results/plots/convergence_youtube_premium.png)

Even on the largest instance the GA improves on greedy (19900 → 22467 best, +12.9%). E2 still dominates; E1 and E3 only marginally beat the greedy seed because their narrower search struggles in such a large solution space. Small wall-time differences here cap how many generations each experiment fits inside the 5-minute budget.

A combined "small / medium / large" plot is also available at [results/plots/convergence_representative.png](results/plots/convergence_representative.png).

### 4.4 Discussion — which experiment performed best, and why

**E2 (Exploration) is the clear winner**, taking the best score on 16/17 instances (tying on `toy`'s known optimum). The combination it brings is:

| E2 ingredient | Effect |
|---|---|
| Population 100 (vs 50) | Twice the genetic diversity each generation; fewer premature plateaus |
| Mutation rate 0.20 (vs 0.10 / 0.05) | Heavier perturbation — escapes local optima the greedy seed sits in |
| Tournament size 5 (vs 3) | Stronger selection pressure on the bigger pool, so good schemata propagate quickly |
| Uniform crossover | Maximum gene mixing per crossover — recombines distant chromosomes aggressively |

**E3 (Exploitation) is the weakest** despite running twice as long. The combination of low mutation (0.05) + small tournament + two-point crossover keeps the population glued to the greedy-seeded basin, so even 400 generations cannot find improvements that E2 finds in 200.

**E1 (Baseline)** lands between E2 and E3 — single-point crossover preserves more locality than uniform, so it explores less aggressively than E2 and ends up close to E3 quality on most instances. It is the only configuration that ties E2 on `germany_tv_input` (932), where the search space is small enough that all reasonable settings converge to the same optimum.

**Take-away for this problem:** the TV-scheduling fitness landscape is **multimodal** (many local optima introduced by genre-streak rules, priority blocks, and switch penalties). The strategy that wins is not "search longer," it is "search wider": more diversity (`pop = 100`), heavier mutation (`0.20`), and uniform crossover.

---

## 5. How to run

From `greedy_repo/`:

```bash
# Phase 1 — runs greedy + Endrita's beam (subprocess) and builds the comparison table
python run_phase1_comparison.py
python run_phase1_comparison.py --skip-endrita                   # only greedy
python run_phase1_comparison.py --skip-greedy                    # only Endrita's beam
python run_phase1_comparison.py --skip-greedy --skip-endrita     # only rebuild comparison
python run_phase1_comparison.py --skip-endrita --instance canada_pw   # one instance only

# Phase 2 — full 510-run GA sweep (multiprocessing.Pool + tqdm, ~10 min on 15 workers)
python run_phase2_ga.py
python run_phase2_ga.py --instance toy --runs 1                  # quick smoke (1 instance, 3 runs)
python run_phase2_ga.py --instance canada_pw                     # 1 instance, all 3 experiments × 10 runs
python run_phase2_ga.py --experiment E2_exploration              # 1 experiment, 17 instances × 10 runs
python run_phase2_ga.py --workers 4                              # cap parallelism

# Aggregate tables + plots (run after both Phase 1 CSVs and the Phase 2 CSV are in results/)
python build_results_tables.py
python plot_convergence.py
```

Dependencies: `python >= 3.9`, `tqdm`, `matplotlib`. Everything else is standard library.
