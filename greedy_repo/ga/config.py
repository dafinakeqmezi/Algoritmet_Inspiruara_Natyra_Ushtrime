"""
The three Phase 2 GA experiments.

Each experiment uses the same parameter values for all 17 instances; the three
configurations differ in population size, mutation rate, elitism, crossover
rate, and crossover operator. The number of generations is intentionally set
very high (effectively unbounded) — every run starts at iteration 0 and the
GA does as many iterations as can fit within the 5-minute wall-time cap, per
the assignment requirement.
"""
from ga.ga_solver import GAConfig

# Effectively unbounded — the time cap (300 s) is the real stopping criterion.
UNBOUNDED_GENERATIONS = 10_000_000

EXPERIMENTS = [
    GAConfig(
        name="E1_baseline",
        population_size=50,
        generations=UNBOUNDED_GENERATIONS,
        crossover_rate=0.8,
        mutation_rate=0.10,
        tournament_size=3,
        elitism=2,
        crossover_type="time_window",
        time_limit_seconds=300.0,
        seed_with_greedy=True,
    ),
    GAConfig(
        name="E2_exploration",
        population_size=100,
        generations=UNBOUNDED_GENERATIONS,
        crossover_rate=0.8,
        mutation_rate=0.15,
        tournament_size=3,
        elitism=3,
        crossover_type="time_window",
        time_limit_seconds=300.0,
        seed_with_greedy=True,
    ),
    GAConfig(
        name="E3_exploitation",
        population_size=100,
        generations=UNBOUNDED_GENERATIONS,
        crossover_rate=0.9,
        mutation_rate=0.15,
        tournament_size=3,
        elitism=3,
        crossover_type="channel",
        time_limit_seconds=300.0,
        seed_with_greedy=True,
    ),
]
