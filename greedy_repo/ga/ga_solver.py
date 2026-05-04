"""
Main GA loop. Composes ChromosomeEncoder (encoding+decode+fitness) with
the operators module (selection, crossover, mutation) into a generational
GA with elitism, optional greedy-seeded initial individual, and a hard
time cap (5 minutes per run by default).
"""
from __future__ import annotations

import random
import time
from dataclasses import dataclass
from typing import List

from models.instance_data import InstanceData
from models.solution import Solution

from ga.chromosome import Chromosome, ChromosomeEncoder
from ga.operators import crossover, mutate, tournament_select


@dataclass
class GAConfig:
    name: str
    population_size: int
    generations: int
    crossover_rate: float
    mutation_rate: float
    tournament_size: int
    elitism: int
    crossover_type: str  # "time_window" | "channel"
    time_limit_seconds: float = 300.0
    seed_with_greedy: bool = True   # warm-start: 1 individual = greedy solution


@dataclass
class GenLogEntry:
    gen: int               # 0 = post-init population
    best_so_far: int       # best score observed up to and including this generation
    gen_best: int          # best score in this generation's population
    gen_avg: float         # mean score across this generation's population
    elapsed_s: float       # wall-clock seconds since run start


@dataclass
class GARunResult:
    best_score: int
    best_solution: Solution
    avg_score_final_gen: float
    generations_completed: int
    time_seconds: float
    gen_log: List[GenLogEntry]


class GASolver:
    def __init__(self, instance: InstanceData, config: GAConfig, seed: int = 0):
        self.instance = instance
        self.config = config
        self.rng = random.Random(seed)
        self.encoder = ChromosomeEncoder(instance)

    # -------- initial population --------

    def _build_initial_population(self) -> List[Chromosome]:
        pop: List[Chromosome] = []
        if self.config.seed_with_greedy:
            try:
                seed = self.encoder.seed_with_greedy_solution()
                # Per-run perturbation of the greedy seed: keep a random prefix
                # and re-extend the tail with the randomized greedy (top-K + rng)
                # so each run starts from a different but high-quality individual.
                # Without this, every run shares the deterministic greedy seed
                # and small instances collapse to identical schedules.
                if seed:
                    k = self.rng.randint(0, len(seed))
                    prefix = list(seed[:k])
                    start_time = prefix[-1].end if prefix else self.encoder.opening
                    seed = self.encoder._greedy_extend(prefix, start_time, rng=self.rng)
                pop.append(seed)
            except Exception:
                pass  # fall back to fully-random init
        while len(pop) < self.config.population_size:
            pop.append(self.encoder.random_chromosome(self.rng))
        return pop

    # -------- main loop --------

    def run(self) -> GARunResult:
        cfg = self.config
        t0 = time.perf_counter()

        population = self._build_initial_population()
        fitnesses = [self.encoder.fitness(c) for c in population]

        best_idx = max(range(len(population)), key=lambda i: fitnesses[i])
        best_score = fitnesses[best_idx]
        best_chrom = list(population[best_idx])
        last_avg = sum(fitnesses) / len(fitnesses) if fitnesses else 0.0

        gen_log: List[GenLogEntry] = [GenLogEntry(
            gen=0,
            best_so_far=best_score,
            gen_best=best_score,
            gen_avg=last_avg,
            elapsed_s=time.perf_counter() - t0,
        )]

        gen = 0
        while gen < cfg.generations:
            if time.perf_counter() - t0 >= cfg.time_limit_seconds:
                break

            # Elitism — top-N copied unchanged into the next generation.
            ranked = sorted(range(len(population)), key=lambda i: fitnesses[i], reverse=True)
            new_pop: List[Chromosome] = [list(population[i]) for i in ranked[:cfg.elitism]]

            # Offspring
            while len(new_pop) < cfg.population_size:
                p1 = tournament_select(population, fitnesses, cfg.tournament_size, self.rng)
                p2 = tournament_select(population, fitnesses, cfg.tournament_size, self.rng)
                if self.rng.random() < cfg.crossover_rate:
                    c1, c2 = crossover(p1, p2, cfg.crossover_type, self.encoder, self.rng)
                else:
                    c1, c2 = list(p1), list(p2)
                if self.rng.random() < cfg.mutation_rate:
                    c1 = mutate(c1, self.encoder, self.rng)
                if self.rng.random() < cfg.mutation_rate:
                    c2 = mutate(c2, self.encoder, self.rng)
                new_pop.append(c1)
                if len(new_pop) < cfg.population_size:
                    new_pop.append(c2)

            population = new_pop
            fitnesses = [self.encoder.fitness(c) for c in population]
            last_avg = sum(fitnesses) / len(fitnesses)

            gen_best_idx = max(range(len(population)), key=lambda i: fitnesses[i])
            gen_best = fitnesses[gen_best_idx]
            if gen_best > best_score:
                best_score = gen_best
                best_chrom = list(population[gen_best_idx])

            gen += 1
            gen_log.append(GenLogEntry(
                gen=gen,
                best_so_far=best_score,
                gen_best=gen_best,
                gen_avg=last_avg,
                elapsed_s=time.perf_counter() - t0,
            ))

        elapsed = time.perf_counter() - t0
        best_solution = self.encoder.decode(best_chrom)
        return GARunResult(
            best_score=best_score,
            best_solution=best_solution,
            avg_score_final_gen=last_avg,
            generations_completed=gen,
            time_seconds=elapsed,
            gen_log=gen_log,
        )

    # convenience: same API shape as the greedy / beam schedulers
    def generate_solution(self) -> Solution:
        return self.run().best_solution
