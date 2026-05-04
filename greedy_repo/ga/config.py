"""
The three Phase 2 GA experiments.

Each experiment uses the same parameter values for all 17 instances; the three
configurations differ in population size, generations, mutation rate, elitism,
crossover rate, and crossover operator so the score effect of changing
parameters is observable.
"""
from ga.ga_solver import GAConfig

EXPERIMENTS = [
    GAConfig(
        name="E1_baseline",
        population_size=50,
        generations=100,
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
        generations=100,
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
        generations=150,
        crossover_rate=0.9,
        mutation_rate=0.15,
        tournament_size=3,
        elitism=3,
        crossover_type="channel",
        time_limit_seconds=300.0,
        seed_with_greedy=True,
    ),
]
