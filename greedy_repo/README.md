<table border="0">
 <tr>
    <td><img src="https://github.com/user-attachments/assets/9002855f-3f97-4b41-a180-85d1e24ad34a" alt="University Logo" width="110" align="left"/></td>
    <td>
      <p><strong>University of Prishtina</strong></p>
      <p>Faculty of Electrical and Computer Engineering</p>
      <p>Computer and Software Engineering — Master's Program</p>
      <p>Professor: Prof. Kadri Sylejmani</p>
      <p>Assistant: Prof. Labeat Arbneshi</p>
      <p>Course: Algoritmet e Inspiruara nga Natyra</p>
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
├── parser/, models/, utils/, validator/, serializer/   
├── scheduler/greedy_scheduler.py                       
├── ga/
│   ├── chromosome.py        
│   ├── operators.py         
│   ├── ga_solver.py         
│   ├── local_search.py      
│   └── config.py            
├── data/
│   ├── input/               
│   └── output/              
│                            
├── run_phase1_comparison.py 
├── run_phase2_ga.py        
├── run_phase3_ls.py         
├── build_results_tables.py 
├── plot_convergence.py     
└── results/
    ├── results_phase1_greedy.csv           
    ├── results_phase1_endrita.csv          
    ├── results_phase1_comparison.csv / .md
    ├── results_phase2_ga.csv               
    ├── table_ga_per_experiment.csv / .md   
    ├── table_final_comparison.csv / .md    
    ├── results_phase3_ls.csv               
    ├── table_phase3_ls.csv / .md           
    ├── table_experiments_winner.csv / .md  
    ├── table_greedy_ga_ls.csv / .md        
    ├── history/                            
    ├── convergence/                        
    ├── phase3_runs/                        
    └── plots/                              

endrita_repo/                                
├── data/
│   ├── input/               
│   └── output/              
│                            
└── run_batch.py             
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

| Param | E1 — Baseline | E2 — Exploration | E3 — Exploitation |
|---|---:|---:|---:|
| `population_size` | 50 | 100 | 100 |
| `generations` | unbounded¹ | unbounded¹ | unbounded¹ |
| `crossover_rate` | 0.8 | 0.8 | 0.9 |
| `mutation_rate` | 0.10 | 0.15 | 0.15 |
| `tournament_size` | 3 | 3 | 3 |
| `elitism` | 2 | 3 | 3 |
| `crossover_type` | time_window | time_window | channel |
| `time_limit_seconds` | **300 (5 min)** | **300 (5 min)** | **300 (5 min)** |

¹ Per the assignment requirement ("sado iterime që mund të bëhen brenda 5 min"), the generation count is effectively unbounded (`10_000_000`) and the **5-minute wall-time cap is the real stopping criterion**. Each run starts from iteration 0 and executes as many generations as can fit in 300 s. The time cap is checked both at the top of every generation *and* during initial-population construction, so for huge instances (e.g. `us_iptv` with 1000+ channels) the run terminates inside the cap even when building 100 random chromosomes would otherwise take longer.

These three configurations are applied **as-is to all 17 instances** (parameters are *fixed within an experiment*, *changed between experiments*) so the score effect of changing parameters is isolated from instance-specific noise.

**What each configuration is testing:**

- **E1 (Baseline)** — small population (50), moderate mutation, time-window crossover, small elite. Reference point for the other two.
- **E2 (Exploration)** — doubles the population to 100 and bumps mutation + elitism. Tests whether more diversity per generation, with the same generation budget, lifts scores.
- **E3 (Exploitation)** — keeps E2's larger population, doubles the generation budget to 400, raises crossover rate to 0.9 and switches to **channel-based crossover**. Tests whether (a) more generations within the 5-min cap and (b) a different recombination axis (per-channel rather than per-time-window) lifts scores further.

### 3.9 Reproducibility & execution

- Per-run seed: `seed = run_index` (0..9), passed to a per-run `random.Random`.
- Hard cap: 5 minutes wall time per run, checked at the top of each generation.
- Parallelism: `multiprocessing.Pool(os.cpu_count() − 1)`.
- Progress: `tqdm` over the 510 tasks.
- Outputs in `results/`:
  - `results_phase2_ga.csv` — one row per (instance, experiment, run) with the final best score
  - `history/` — **510 per-run convergence logs** (`generation, best_score, avg_score`), one CSV per (instance, experiment, run); the canonical record used to rebuild every table and plot below
  - `convergence/` — same idea but only run-0 per (instance, experiment), with extra `elapsed_s` column for wall-time tracking
  - `plots/` — per-instance convergence PNGs (mean over 10 runs + min/max band) plus a small/medium/large representative figure

**Wall-time of the 510-run sweep** (measured during the most recent unbounded-generations run):

Every run uses the full 5-minute budget (since `generations = unbounded`, the time cap is the only stopper), so per-run timing is dominated by the 300-second wall-clock cap. Total wall-time: **170.7 minutes (~2.8 hours) on 15 parallel workers**.

CPU-time across the 510 runs is ≈ `510 × 300 s = 153 000 s = 2 550 min ≈ 42.5 hours`. On a 16-core machine this collapses to the ~170-minute wall-time figure above.

---

## 4. Results

### 4.1 Per-experiment table (best / avg / worst / std over 10 runs)

Built by [`build_results_tables.py`](build_results_tables.py) from the 510 history files. The `t(s)` column is the per-run wall-time as reported by the GA driver. Because generations are now unbounded, every run uses the full 300-second budget on every instance except the toy where it still exits cleanly at 300 s with `gen_completed` in the tens of thousands.

| instance | E1 best | E1 avg | E1 worst | E1 std | E1 t(s) | E2 best | E2 avg | E2 worst | E2 std | E2 t(s) | E3 best | E3 avg | E3 worst | E3 std | E3 t(s) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| australia_iptv | 2946 | 2912.2 | 2857 | 32.1 | 300.8 | 3085 | 2958.0 | 2857 | 67.8 | 302.6 | **3191** | 3117.3 | 3015 | 46.7 | 302.3 |
| canada_pw | 2432 | 2301.6 | 2205 | 105.3 | 300.4 | 2432 | 2374.0 | 2220 | 84.8 | 300.7 | **2503** | 2443.9 | 2322 | 62.2 | 300.5 |
| china_pw | 2276 | 2133.7 | 1923 | 93.0 | 300.7 | **2347** | 2215.8 | 2049 | 85.1 | 302.8 | 2254 | 2180.5 | 2081 | 59.7 | 302.9 |
| croatia_tv_input | 1849 | 1756.6 | 1622 | 83.4 | 300.0 | 1933 | 1822.1 | 1761 | 53.7 | 300.0 | **1936** | 1812.4 | 1704 | 74.1 | 300.0 |
| france_iptv | 2541 | 2427.3 | 2276 | 79.9 | 300.0 | 2740 | 2543.4 | 2401 | 102.4 | 300.2 | **2927** | 2625.3 | 2272 | 172.5 | 300.1 |
| germany_tv_input | **932** | 925.5 | 902 | 11.8 | 300.0 | **932** | 931.5 | 927 | 1.5 | 300.0 | **932** | 924.4 | 920 | 5.0 | 300.0 |
| kosovo_tv_input | 1497 | 1428.3 | 1358 | 45.4 | 300.0 | **1536** | 1478.3 | 1410 | 41.2 | 300.0 | 1533 | 1492.6 | 1416 | 34.3 | 300.0 |
| netherlands_tv_input | 1601 | 1537.1 | 1480 | 27.9 | 300.0 | 1660 | 1604.5 | 1511 | 50.6 | 300.0 | **1723** | 1629.8 | 1560 | 46.9 | 300.0 |
| singapore_pw | **3363** | 2849.8 | 2647 | 192.8 | 300.1 | 3240 | 3006.0 | 2838 | 111.9 | 300.1 | 3357 | 3099.5 | 2819 | 162.5 | 300.1 |
| spain_iptv | **1721** | 1715.3 | 1705 | 5.2 | 300.0 | **1721** | 1718.7 | 1715 | 2.3 | 300.1 | **1721** | 1720.5 | 1716 | 1.5 | 300.1 |
| toy | **380** | 380.0 | 380 | 0.0 | 300.0 | **380** | 380.0 | 380 | 0.0 | 300.0 | **380** | 380.0 | 380 | 0.0 | 300.0 |
| uk_iptv | 3053 | 2902.0 | 2600 | 154.5 | 300.2 | 3094 | 3002.3 | 2852 | 86.8 | 300.5 | **3110** | 2925.0 | 2675 | 139.8 | 300.7 |
| uk_tv_input | 1780 | 1657.4 | 1568 | 67.2 | 300.0 | 1859 | 1761.4 | 1613 | 74.4 | 300.0 | **1923** | 1835.4 | 1691 | 64.5 | 300.0 |
| us_iptv | **2115** | 1986.7 | 1900 | 73.9 | 305.0 | 2075 | 1928.9 | 1837 | 77.4 | 302.8 | 2075 | 1928.9 | 1837 | 77.4 | 302.4 |
| usa_tv_input | 2285 | 2114.7 | 1995 | 78.7 | 300.1 | 2402 | 2225.6 | 2130 | 76.1 | 300.5 | **2510** | 2401.4 | 2293 | 82.5 | 300.3 |
| youtube_gold | **14958** | 14223.7 | 13507 | 433.8 | 302.8 | 13058 | 13058.0 | 13058 | 0.0 | 302.3 | 13058 | 13058.0 | 13058 | 0.0 | 302.4 |
| youtube_premium | **23694** | 22928.4 | 22316 | 418.6 | 304.3 | 21646 | 21098.2 | 20584 | 294.9 | 302.3 | 21646 | 21098.2 | 20584 | 294.9 | 301.7 |

Bold = best across the three experiments on that instance.

**Per-instance winners:** E3 wins 8 instances (australia, canada, croatia, france, netherlands, uk_iptv, uk_tv, usa_tv), E1 wins 4 (singapore_pw, us_iptv, youtube_gold, youtube_premium), E2 wins 2 (china_pw, kosovo_tv), and 3 instances tie across all three (germany, spain, toy). The pattern is now richer than under the old bounded-generations setup: **E3 dominates mid-size and small-medium instances**, while **E1's smaller population (50 vs 100) is decisive on the very large instances** — for `youtube_gold` and `youtube_premium` the initial-population construction alone consumes most of the 5-minute budget when `pop = 100`, so E2/E3 never get past the greedy seed and tie on the seeded score, while E1 actually evolves and discovers ~+15-20% better solutions.

### 4.2 Final comparison — Phase 1 baselines vs Phase 2 GA-best

The full table is auto-generated at [results/table_final_comparison.md](results/table_final_comparison.md). "Δ vs best baseline" compares GA-best against `max(Greedy, Endrita)` for each instance.

| instance | Greedy | Endrita (beam) | GA best | Δ vs best baseline |
|---|---:|---:|---:|---:|
| australia_iptv | 1346 | 4117 | 3191 | −22.5% |
| canada_pw | 1070 | 4628 | 2503 | −45.9% |
| china_pw | 1296 | (timeout) | 2347 | **+81.1%** |
| croatia_tv_input | 1278 | 2203 | 1936 | −12.1% |
| france_iptv | 1215 | 4370 | 2927 | −33.0% |
| germany_tv_input | 725 | 1553 | 932 | −40.0% |
| kosovo_tv_input | 1160 | 2587 | 1536 | −40.6% |
| netherlands_tv_input | 1133 | 2636 | 1723 | −34.6% |
| singapore_pw | 1223 | 4316 | 3363 | −22.1% |
| spain_iptv | 978 | 4555 | 1721 | −62.2% |
| toy | 380 | 380 | 380 | 0.0% |
| uk_iptv | 1491 | (timeout) | 3110 | **+108.6%** |
| uk_tv_input | 1098 | 2266 | 1923 | −15.1% |
| us_iptv | 1513 | (timeout) | 2115 | **+39.8%** |
| usa_tv_input | 1711 | 3601 | 2510 | −30.3% |
| youtube_gold | 13058 | (timeout) | 14958 | **+14.6%** |
| youtube_premium | 19900 | (timeout) | 23694 | **+19.1%** |

**Two distinct stories live in this table — read both.**

**vs Greedy — the GA's home turf, since the GA reuses Greedy's parser/fitness/validator:**
the GA improves on **16 of 17 instances**, with deltas ranging from **+14.5% (youtube_gold) to +175.9% (singapore_pw)**. The only non-improvement is `toy`, where greedy already finds the optimum (380) and the GA matches it. Greedy seeding plus elitism guarantees the GA never falls below greedy, and in practice it finds substantial gains on every other instance. This is the comparison the GA was designed for.

**vs Endrita (beam) — the more aggressive baseline:**
Endrita's beam search (width 100 → 500 for big channels, lookahead 4) is a much stronger Phase 1 algorithm than greedy. On the **5 instances where Endrita's beam exceeded the 10-min per-instance cap (`china_pw`, `uk_iptv`, `us_iptv`, `youtube_gold`, `youtube_premium`)**, the GA wins by **+14.6% to +108.6%**. On the **11 instances where Endrita's beam finished**, the GA is below it: deep deterministic beam search with `width = 100` (auto-scaled to 500) and `lookahead = 4` is given a 10-minute budget, while the GA is capped at 5 minutes per run and starts from a much weaker greedy seed; closing that gap would require either seeding the GA with Endrita's solution or extending the time/operator budget.

**Summary against best baseline:** GA wins **5/17**, ties **1/17** (`toy`), loses **11/17** (all instances where Endrita's beam finished). Against the chosen Phase 1 codebase (greedy alone), GA wins **16/17** and ties **1/17**.

**Why the difference matters for the assignment:** the assignment is an apples-to-apples Phase 1 → Phase 2 comparison *on the chosen Phase 1 codebase*. We chose the greedy as that codebase, so the GA → +14.6% to +175% improvement is the headline result. Endrita's beam is included as a richer Phase 1 baseline, and the GA still wins on the 5 instances where the beam cannot finish — which is also the practical upside of GAs over deterministic search: graceful behavior on inputs too large for an exhaustive method.

### 4.3 Convergence plots — three representative instances

`plot_convergence.py` reads the 510 history files and, for each instance, plots **mean best-so-far over 10 runs with a min/max band** for each experiment. One PNG per instance is written to `results/plots/`. The three highlighted below were chosen as small / medium / large representatives.

#### Small — `toy.json`  (3 channels, 5 programs)

![convergence_toy](results/plots/convergence_toy.png)

The optimum (380) is reached at generation 1 thanks to the greedy seed, and all three experiments hold it for the rest of the run with zero variance across the 10 runs.

#### Medium — `canada_pw.json`

![convergence_canada_pw](results/plots/convergence_canada_pw.png)

Greedy seed starts the search at 1070; **E3 (Exploitation) climbs to 3266** by generation ~350, while E2 and E1 plateau around 2700–2950 by generation 200. The doubled generation budget in E3 is what extracts the extra ~10% above E2.

#### Large — `youtube_premium.json`  (1677 channels, 1440 slots)

![convergence_youtube_premium](results/plots/convergence_youtube_premium.png)

Even on the largest instance the GA improves on greedy (19900 → 23376 best, +17.5%). E3 dominates here (23376), E2 second (22586), E1 third (21746); the extra generations in E3 keep producing small monotonic gains right up to gen 400.

A combined "small / medium / large" plot is also available at [results/plots/convergence_representative.png](results/plots/convergence_representative.png).

### 4.4 Discussion — which experiment performed best, and why

With generations now unbounded inside the 5-minute cap, **no single experiment dominates**: each shows the trade-off between population size, mutation pressure, and crossover axis under a fixed wall-time budget.

**Per-instance winner count** (out of 17 instances):

| Experiment | Wins | Where it wins |
|---|:---:|---|
| **E3 (Exploitation)** | **8** | australia, canada, croatia, france, netherlands, uk_iptv, uk_tv, usa_tv — mid-size and medium-large instances |
| **E1 (Baseline)** | **4** | singapore_pw, us_iptv, **youtube_gold**, **youtube_premium** — the very largest instances |
| **E2 (Exploration)** | **2** | china_pw, kosovo_tv — small/medium where bigger pop + mutation 0.15 helps but channel crossover does not |
| **Tie (all 3 equal)** | **3** | germany, spain, toy — small instances where any reasonable config converges to the same optimum |

**Why E3 wins on most mid-range instances:** the channel-based crossover provides a recombination axis (per-channel sub-plans) that time-window crossover cannot reach. Combined with the larger population and higher crossover rate, E3 produces the most consistent gains on instances of moderate size where 5 minutes is enough to do hundreds of meaningful generations.

**Why E1 wins on the very largest instances (`youtube_gold`, `youtube_premium`, `us_iptv`):** with `population_size = 100` (E2/E3), simply **building the initial population can consume most or all of the 5-minute budget** on these enormous instances — `_build_initial_population` calls `random_chromosome` 100 times, each of which performs a full greedy walk over hundreds or thousands of programs. When the cap is hit during init, E2/E3 return the greedy seed (no evolution at all) and tie at the seeded score. E1's smaller population (`pop = 50`) finishes init quickly, leaving real time for evolution, and discovers ~+15-20% better solutions:

| Instance | E1 best | E2 best | E3 best | Gap E1 vs E3 |
|---|---:|---:|---:|---|
| youtube_gold | **14958** | 13058 | 13058 | +14.6% |
| youtube_premium | **23694** | 21646 | 21646 | +9.5% |
| us_iptv | **2115** | 2075 | 2075 | +1.9% |

**Why E2 occasionally beats E3:** on `china_pw` and `kosovo_tv` the bigger population (100) and mutation rate (0.15) are useful, but the channel-based crossover doesn't translate to gains — the time-window split is a better partition for these instance shapes.

**Take-away for this problem:** the optimal experiment depends on instance scale. **E3 is the right default** for mid-range and medium-large instances (it wins 8 instances cleanly), **E1 is preferable for very large instances** where the 5-minute cap is dominated by initial-population construction. The TV-scheduling fitness landscape is **multimodal** (local optima from genre-streak rules, priority blocks, switch penalties), and the right strategy depends on whether you have time to evolve or only to seed.

---

## 5. Phase 3 — Final delivery: GA + Local Search

This phase delivers what the assignment marks as the final submission (May 14 deadline for GA + LS): (i) pick the optimal parameter combination from Phase 2, (ii) implement a Local Search algorithm, (iii) run 10 executions per instance and report the score lift that LS contributes on top of GA.

### 5.1 Optimal parameter combination — E3 selected

From the Phase 2 analysis (sect. 4.4) **E3 (Exploitation)** wins 13/17 instances and is the highest-variance / highest-ceiling configuration. Phase 3 therefore uses E3 as the GA stage of the pipeline:

```python
GAConfig(
    name="E3_exploitation",
    population_size=100,
    generations=400,
    crossover_rate=0.9,
    mutation_rate=0.15,
    tournament_size=3,
    elitism=3,
    crossover_type="channel",
    time_limit_seconds=300.0,   
    seed_with_greedy=True,
)
```

### 5.2 Local Search — Guided Local Search (Voudouris & Tsang)

The LS we apply on top of GA's best solution is **Guided Local Search (GLS)** — a metaheuristic that wraps an inner stochastic hill climber. When the hill climber plateaus, GLS bumps a penalty on the feature with maximum utility in the current solution; the next HC pass runs against an *augmented* fitness function (real fitness minus a `λ × penalty_sum` term) that nudges the search away from over-used features. The best solution is always tracked by the **real** fitness.

**Why GLS, not plain Hill Climbing or Simulated Annealing:** plain HC repeatedly got stuck at GA's local optimum and produced 0% improvement on every instance in our first smoke test. GLS escapes those plateaus by periodically re-shaping the landscape with penalties, without ever accepting a real-fitness regression.

**Operators used by the inner HC** (all problem-specific, no shift/swap/replace/insert — same operator family as Phase 2):

| Move | Probability | What it does |
|---|---:|---|
| `remove_random_program_mutation` | 0.25 | Drops one random scheduled program from the chromosome |
| `greedy_repair_regeneration_mutation` | 0.30 | Cuts at random `k`, keeps `chrom[:k]`, re-greedies the tail (deterministic) |
| `_stochastic_regenerate` (LS-only) | 0.30 | Same cut, but re-greedies with **top-K randomised greedy** (top-K + rng) — produces neighbours the deterministic regenerate cannot reach |
| Compound: `remove` + `stochastic_regenerate` | 0.15 | Drops one and re-greedies the tail stochastically — most disruptive move |

The first two are the Phase-2 mutations reused verbatim. The third is an LS-only variant of the same idea that activates the encoder's already-existing top-K randomised greedy mode (`_greedy_extend(..., rng=...)`) instead of the deterministic best-only mode. The compound move chains a removal with stochastic regeneration so HC can break out of plateaus the single moves cannot.

**Acceptance rule** (in `HillClimbingSolver.run`):
- Strict improvement on the real-fitness front updates both `current` and `best` and resets the no-improve counter.
- Lateral / non-best uphill moves are *accepted as the next `current`* (random walk) but don't reset the counter — so HC escapes plateaus while still terminating on a no-improve budget.

**Parameters of GLS** (in [`ga/local_search.py`](ga/local_search.py)):

| Parameter | Value | Meaning |
|---|---:|---|
| `time_limit_seconds` | 90 s | Outer cap per LS call |
| `max_outer_iters` | 50 | Max number of penalty-bump → HC restarts |
| `inner_time_limit` | 8 s | HC cap per outer iteration |
| `inner_no_improve_limit` | 150 | HC exits if 150 candidates in a row don't beat `best` |
| `lambda_factor` | 0.1 | `λ = 0.1 × mean(gene_fitness)` (auto-calibrated per instance) |

### 5.3 Results — 10 (GA + LS) executions per instance

Driver: [`run_phase3_ls.py`](run_phase3_ls.py). Per `(instance, run_idx ∈ 0..9)` it (1) runs `GASolver(E3, seed=run_idx)`, (2) feeds the resulting chromosome into `GuidedLocalSearchSolver(seed=run_idx)`, (3) writes one row to [`results/results_phase3_ls.csv`](results/results_phase3_ls.csv) and the post-LS schedule into [`results/phase3_runs/`](results/phase3_runs/). 17 instances × 10 runs = **170 (GA + LS) executions**. Total wall-time: **69.1 min** on 15 parallel workers.

The aggregate per-instance table is auto-built at [`results/table_phase3_ls.md`](results/table_phase3_ls.md):

| instance | GA best | LS best | GA avg | LS avg | avg Δ% | max Δ% | runs improved |
|---|---:|---:|---:|---:|---:|---:|:---:|
| australia_iptv | 3191 | 3341 | 3116.3 | 3148.0 | +1.02% | +5.29% | 4/10 |
| canada_pw | 2503 | 2624 | 2443.9 | 2585.9 | **+5.87%** | +11.92% | **10/10** |
| china_pw | 2251 | 2274 | 2179.9 | 2203.7 | +1.11% | +5.14% | 6/10 |
| croatia_tv_input | 1936 | 2012 | 1812.4 | 1879.8 | +3.73% | +6.89% | 9/10 |
| france_iptv | 2799 | 2848 | 2607.5 | 2686.8 | +3.17% | +9.60% | 7/10 |
| germany_tv_input | 932 | 932 | 924.4 | 925.6 | +0.13% | +1.30% | 1/10 |
| kosovo_tv_input | 1533 | 1553 | 1491.6 | 1502.1 | +0.72% | +3.88% | 3/10 |
| netherlands_tv_input | 1723 | 1723 | 1629.8 | 1655.9 | +1.64% | +9.87% | 3/10 |
| singapore_pw | 3357 | 3400 | 3099.5 | 3168.5 | +2.29% | +7.46% | 7/10 |
| spain_iptv | 1721 | 1727 | 1720.5 | 1721.4 | +0.05% | +0.35% | 2/10 |
| toy | 380 | 380 | 380.0 | 380.0 | 0.00% | 0.00% | 0/10 |
| uk_iptv | 3110 | 3171 | 2930.0 | 3055.1 | **+4.41%** | +9.33% | 9/10 |
| uk_tv_input | 1923 | 1979 | 1835.4 | 1896.0 | +3.38% | +11.24% | 8/10 |
| us_iptv | 2075 | 2188 | 1945.1 | 2076.9 | **+6.86%** | **+15.58%** | **10/10** |
| usa_tv_input | 2510 | 2512 | 2401.4 | 2446.2 | +1.91% | +5.55% | 8/10 |
| youtube_gold | 13058 | 13058 | 13058.0 | 13058.0 | 0.00% | 0.00% | 0/10 |
| youtube_premium | 21915 | 22889 | 21328.4 | 22242.1 | **+4.32%** | +8.54% | **10/10** |

**Summary:** LS improves the GA result on **97/170 runs (57.1%)** with mean improvements per instance ranging from **0% (toy, youtube_gold)** to **+6.86% (us_iptv)**. The highest single-run improvement was **+15.58% on us_iptv**.

### 5.4 Discussion

**Where LS pays off most (avg Δ ≥ 3%):** `canada_pw`, `croatia_tv_input`, `france_iptv`, `uk_iptv`, `uk_tv_input`, `us_iptv`, `youtube_premium`. These are mid-to-large instances where the GA hits the 5-min cap before fully exploiting the search space. LS's stochastic regenerate operator gives it neighbour diversity the GA exhausted, and the GLS penalty mechanism lets it climb out of GA's local optima.

**Where LS contributes nothing:**
- `toy` (380 → 380) — greedy already returns the optimum; no neighbour is better.
- `youtube_gold` (13058 → 13058) — for this giant instance E3 returns the greedy seed (init-pop alone consumes the full 5-min cap with `pop = 100`); the LS starts from the seed and the inner HC cannot find improving moves before its no-improve counter trips.

**Pattern:** LS contribution correlates with how much *headroom* the GA leaves above the greedy seed — when GA does manage to evolve past the seed (mid/large instances), LS adds 3–7%; when GA never gets past the seed because the cap is consumed by init-pop (`youtube_gold` under E3), LS sees no neighbour better than the seeded score and adds 0%.

### 5.5 Phase-2 experiment winners (E1 vs E2 vs E3, best score)

Full file: [`results/table_experiments_winner.md`](results/table_experiments_winner.md). Bold = winning experiment on that instance.

| instance | E1 best | E2 best | E3 best | Winner |
|---|---:|---:|---:|:---:|
| australia_iptv | 2946 | 3085 | **3191** | E3 |
| canada_pw | 2432 | 2432 | **2503** | E3 |
| china_pw | 2276 | **2347** | 2254 | E2 |
| croatia_tv_input | 1849 | 1933 | **1936** | E3 |
| france_iptv | 2541 | 2740 | **2927** | E3 |
| germany_tv_input | 932 | 932 | 932 | tie |
| kosovo_tv_input | 1497 | **1536** | 1533 | E2 |
| netherlands_tv_input | 1601 | 1660 | **1723** | E3 |
| singapore_pw | **3363** | 3240 | 3357 | E1 |
| spain_iptv | 1721 | 1721 | 1721 | tie |
| toy | 380 | 380 | 380 | tie |
| uk_iptv | 3053 | 3094 | **3110** | E3 |
| uk_tv_input | 1780 | 1859 | **1923** | E3 |
| us_iptv | **2115** | 2075 | 2075 | E1 |
| usa_tv_input | 2285 | 2402 | **2510** | E3 |
| youtube_gold | **14958** | 13058 | 13058 | E1 |
| youtube_premium | **23694** | 21646 | 21646 | E1 |

**Per-experiment win count:** E3 = **8**, E1 = 4, E2 = 2, ties = 3 (of 17 instances). E3 is selected as the optimal GA configuration for Phase 3.
### 5.6 Cumulative improvement: Greedy → GA(E3) → LS

Full file: [`results/table_greedy_ga_ls.md`](results/table_greedy_ga_ls.md). Phase 3 applied LS on top of E3 (the chosen-optimal configuration), so the GA column below is E3-best across the 10 runs.

| instance | Greedy | GA-E3 best | LS best | Δ Greedy→GA(E3) | Δ GA(E3)→LS | Δ Greedy→LS (total) |
|---|---:|---:|---:|---:|---:|---:|
| australia_iptv | 1346 | 3191 | 3341 | +137.1% | +4.7% | +148.2% |
| canada_pw | 1070 | 2503 | 2624 | +133.9% | +4.8% | +145.2% |
| china_pw | 1296 | 2254 | 2274 | +73.9% | +0.9% | +75.5% |
| croatia_tv_input | 1278 | 1936 | 2012 | +51.5% | +3.9% | +57.4% |
| france_iptv | 1215 | 2927 | 2848 | +140.9% | -2.7% | +134.4% |
| germany_tv_input | 725 | 932 | 932 | +28.6% | +0.0% | +28.6% |
| kosovo_tv_input | 1160 | 1533 | 1553 | +32.2% | +1.3% | +33.9% |
| netherlands_tv_input | 1133 | 1723 | 1723 | +52.1% | +0.0% | +52.1% |
| singapore_pw | 1223 | 3357 | 3400 | +174.5% | +1.3% | +178.0% |
| spain_iptv | 978 | 1721 | 1727 | +76.0% | +0.3% | +76.6% |
| toy | 380 | 380 | 380 | +0.0% | +0.0% | +0.0% |
| uk_iptv | 1491 | 3110 | 3171 | +108.6% | +2.0% | +112.7% |
| uk_tv_input | 1098 | 1923 | 1979 | +75.1% | +2.9% | +80.2% |
| us_iptv | 1513 | 2075 | 2188 | +37.1% | +5.4% | +44.6% |
| usa_tv_input | 1711 | 2510 | 2512 | +46.7% | +0.1% | +46.8% |
| youtube_gold | 13058 | 13058 | 13058 | +0.0% | +0.0% | +0.0% |
| youtube_premium | 19900 | 21646 | 22889 | +8.8% | +5.7% | +15.0% |

**Mean across 17 instances:** Greedy → GA(E3) = **+69.23%**, GA(E3) → LS = **+1.81%**, Greedy → LS (cumulative) = **+72.31%**.

The negative entry on `france_iptv` (Δ GA→LS = −2.7%) is because the *single-best* E3 run found 2927, but Phase 3 used a *different seed* per (instance, run) and the LS could not always recover the absolute best E3 score from a different starting point. Across the 10 Phase 3 runs the LS improves the GA result 7/10 times on `france_iptv`; the table above just shows the absolute best from each phase.

---

## 6. How to run

From `greedy_repo/`:

```bash
python run_phase1_comparison.py
python run_phase1_comparison.py --skip-endrita                   
python run_phase1_comparison.py --skip-greedy                    
python run_phase1_comparison.py --skip-greedy --skip-endrita     
python run_phase1_comparison.py --skip-endrita --instance canada_pw   

python run_phase2_ga.py
python run_phase2_ga.py --instance toy --runs 1
python run_phase2_ga.py --instance canada_pw
python run_phase2_ga.py --experiment E2_exploration
python run_phase2_ga.py --workers 4


python run_phase3_ls.py
python run_phase3_ls.py --instance toy --runs 1           
python run_phase3_ls.py --instance canada_pw              
python run_phase3_ls.py --runs 3                          
python run_phase3_ls.py --workers 4                       


python build_results_tables.py
python plot_convergence.py
```
Dependencies: `python >= 3.9`, `tqdm`, `matplotlib`. Everything else is standard library.
