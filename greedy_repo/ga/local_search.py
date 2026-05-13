"""Local Search solvers for the TV scheduling problem.

Provides:
- HillClimbingSolver: stochastic hill climbing using the Phase-2 mutation
  operators (remove-program / greedy-regenerate).
- GuidedLocalSearchSolver: Voudouris & Tsang's Guided Local Search wrapper
  that penalises features (scheduled (channel, program, start) triples) to
  escape local optima reached by the inner hill climber.

Both solvers reuse encoder.repair() to keep every candidate valid.
"""
from __future__ import annotations

import random
import time
from dataclasses import dataclass
from typing import Callable, Optional

from ga.chromosome import Chromosome, ChromosomeEncoder
from ga.operators import (
    remove_random_program_mutation,
    greedy_repair_regeneration_mutation,
)


def _stochastic_regenerate(chrom: Chromosome, encoder: ChromosomeEncoder, rng) -> Chromosome:
    """LS-specific variant of greedy_repair_regeneration_mutation: cuts at a
    random k and re-extends the tail with the *randomised* greedy (top-K +
    rng), producing more diverse neighbours than the deterministic version
    used as a GA mutation."""
    if not chrom:
        return encoder.random_chromosome(rng)
    k = rng.randint(0, len(chrom))
    head = list(chrom[:k])
    start_time = head[-1].end if head else encoder.opening
    return encoder._greedy_extend(head, start_time, rng=rng)


@dataclass
class LSResult:
    best_chromosome: Chromosome
    best_score: int
    iterations: int
    time_seconds: float
    initial_score: int


class HillClimbingSolver:
    """Stochastic hill climbing using the Phase-2 mutation operators.

    First-improvement: pick ONE random move per iteration (remove or regenerate),
    accept the candidate iff its score is strictly better than the current best.
    Stops on either time cap or a no-improvement counter.
    """

    def __init__(
        self,
        encoder: ChromosomeEncoder,
        time_limit_seconds: float = 60.0,
        no_improve_limit: int = 200,
        accept_neutral: bool = True,
        seed: int = 0,
    ):
        self.encoder = encoder
        self.time_limit = time_limit_seconds
        self.no_improve_limit = no_improve_limit
        self.accept_neutral = accept_neutral
        self.rng = random.Random(seed)

    def run(
        self,
        initial: Chromosome,
        fitness_fn: Optional[Callable[[Chromosome], float]] = None,
    ) -> LSResult:
        fitness = fitness_fn if fitness_fn else self.encoder.fitness
        # Track current (used for next moves) and global-best (tracked by real fit).
        current = list(initial)
        current_score = fitness(current)
        best = list(current)
        best_score = current_score
        initial_score = best_score
        no_improve = 0
        iters = 0
        t0 = time.perf_counter()

        while (
            time.perf_counter() - t0 < self.time_limit
            and no_improve < self.no_improve_limit
        ):
            r = self.rng.random()
            if r < 0.25:
                candidate = remove_random_program_mutation(current, self.rng)
            elif r < 0.55:
                candidate = greedy_repair_regeneration_mutation(current, self.encoder, self.rng)
            elif r < 0.85:
                # Stochastic regenerate: cut + top-K-randomised greedy tail.
                # Produces neighbours that the deterministic regenerate cannot reach.
                candidate = _stochastic_regenerate(current, self.encoder, self.rng)
            else:
                # Compound move: drop one + stochastic regenerate to disrupt more.
                candidate = remove_random_program_mutation(current, self.rng)
                candidate = _stochastic_regenerate(candidate, self.encoder, self.rng)
            cand_score = fitness(candidate)
            if cand_score > best_score:
                best = candidate
                best_score = cand_score
                current = candidate
                current_score = cand_score
                no_improve = 0
            elif cand_score > current_score or (self.accept_neutral and cand_score == current_score):
                # Random walk: move sideways or on a non-best uphill — escapes
                # plateaus that strict greedy HC cannot leave.
                current = candidate
                current_score = cand_score
                no_improve += 1
            else:
                no_improve += 1
            iters += 1

        return LSResult(
            best_chromosome=best,
            best_score=best_score,
            iterations=iters,
            time_seconds=time.perf_counter() - t0,
            initial_score=initial_score,
        )


class GuidedLocalSearchSolver:
    """Guided Local Search (Voudouris & Tsang).

    Wraps an inner stochastic hill climber. When the inner HC plateaus, the
    feature with maximum utility in the current solution gets its penalty
    bumped; the next HC pass runs against an augmented fitness function that
    subtracts ``lambda * sum(penalty[f] for f in s)``. The best solution is
    always tracked by the *real* fitness.

    Features are scheduled (channel_id, unique_program_id, start) triples;
    cost(f) is the per-step fitness of that gene; utility(f) = cost(f)/(1+p[f]).
    """

    def __init__(
        self,
        encoder: ChromosomeEncoder,
        time_limit_seconds: float = 90.0,
        max_outer_iters: int = 50,
        inner_time_limit: float = 8.0,
        inner_no_improve_limit: int = 150,
        lambda_factor: float = 0.1,
        seed: int = 0,
    ):
        self.encoder = encoder
        self.time_limit = time_limit_seconds
        self.max_outer_iters = max_outer_iters
        self.inner_time_limit = inner_time_limit
        self.inner_no_improve_limit = inner_no_improve_limit
        self.lambda_factor = lambda_factor
        self.seed = seed
        self.penalty: dict[tuple, int] = {}
        self._lambda: float = 0.0

    @staticmethod
    def _feature(schedule) -> tuple:
        return (schedule.channel_id, schedule.unique_program_id, schedule.start)

    def _augmented_fitness(self, chrom: Chromosome) -> float:
        decoded = self.encoder.repair(chrom)
        base = sum(s.fitness for s in decoded)
        if not self.penalty:
            return float(base)
        pen_sum = sum(self.penalty.get(self._feature(s), 0) for s in decoded)
        return float(base) - self._lambda * pen_sum

    def _select_feature_to_penalise(self, chrom: Chromosome) -> Optional[tuple]:
        decoded = self.encoder.repair(chrom)
        if not decoded:
            return None
        best_f, best_u = None, -1.0
        for s in decoded:
            f = self._feature(s)
            cost = max(1, s.fitness)
            util = cost / (1 + self.penalty.get(f, 0))
            if util > best_u:
                best_u, best_f = util, f
        return best_f

    def run(self, initial: Chromosome) -> LSResult:
        init_score = self.encoder.fitness(initial)
        decoded = self.encoder.repair(initial)
        avg_gene_fit = (init_score / len(decoded)) if decoded else 1.0
        # Calibrate lambda to the instance: 10% of mean gene fitness.
        self._lambda = max(1.0, avg_gene_fit * self.lambda_factor)
        self.penalty.clear()

        hc = HillClimbingSolver(
            self.encoder,
            time_limit_seconds=self.inner_time_limit,
            no_improve_limit=self.inner_no_improve_limit,
            seed=self.seed,
        )
        # Initial HC pass against the real fitness.
        result = hc.run(initial)
        current = result.best_chromosome
        best = list(current)
        best_score = self.encoder.fitness(best)
        total_iters = result.iterations

        t0 = time.perf_counter()
        outer = 0
        while (
            time.perf_counter() - t0 < self.time_limit
            and outer < self.max_outer_iters
        ):
            feature = self._select_feature_to_penalise(current)
            if feature is not None:
                self.penalty[feature] = self.penalty.get(feature, 0) + 1

            hc.rng = random.Random(self.seed + outer + 1)
            result = hc.run(current, fitness_fn=self._augmented_fitness)
            current = result.best_chromosome
            total_iters += result.iterations

            real_score = self.encoder.fitness(current)
            if real_score > best_score:
                best = list(current)
                best_score = real_score
            outer += 1

        return LSResult(
            best_chromosome=best,
            best_score=best_score,
            iterations=total_iters,
            time_seconds=time.perf_counter() - t0,
            initial_score=init_score,
        )
