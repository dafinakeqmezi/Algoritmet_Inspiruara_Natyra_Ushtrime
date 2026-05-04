"""
Chromosome encoding (variable-length) and decode/repair for the GA.

Spec (from the assignment):
    Chromosome = one complete schedule (a list of accepted programs in time order).
    Gene       = one scheduled program/item (a Schedule).
    Fitness    = total score of the schedule (computed with the SAME components
                 the greedy uses; see scheduler/greedy_scheduler.py).

A chromosome is therefore `List[Schedule]` ordered by start time.

Construction:
    - `seed_with_greedy_solution()`     - one canonical greedy run
    - `random_chromosome(rng)`          - randomized greedy: at each step, pick
                                          uniformly at random among the top-K
                                          fitness-positive candidates (K=3 default)

Decode/repair:
    - `repair(schedules)`  - walks the list in time order, drops any item that
                             would violate constraints or overlap, recomputes
                             the per-step fitness with the greedy formula.
                             Output is a fully valid Solution.

The decode is intentionally lossless on already-valid chromosomes and acts as
the repair operator for offspring produced by crossover/mutation.
"""
from __future__ import annotations

import random
from typing import List

from models.instance_data import InstanceData
from models.program import Program
from models.schedule import Schedule
from models.solution import Solution
from scheduler.greedy_scheduler import GreedyScheduler
from utils.algorithm_utils import AlgorithmUtils
from utils.utils import Utils
from validator.exceptions.constraint_exception import ConstraintException
from validator.validator import Validator


Chromosome = List[Schedule]


class ChromosomeEncoder:
    """Variable-length encoding. Each chromosome is a list of valid Schedule
    items in time order. The encoder caches per-instance lookups used by the
    operators (which programs are airing at a given time, etc.)."""

    TOP_K_RANDOMIZED_INIT = 3

    def __init__(self, instance: InstanceData):
        self.instance = instance
        Utils.set_current_instance(instance)

        self.opening = instance.opening_time
        self.closing = instance.closing_time
        self.min_d = instance.min_duration
        self.n_channels = len(instance.channels)

        self.uid_to_program: dict[int, Program] = {}
        self.uid_to_channel_index: dict[int, int] = {}
        for ch_idx, channel in enumerate(instance.channels):
            for p in channel.programs:
                if p.unique_id is None:
                    continue
                self.uid_to_program[p.unique_id] = p
                self.uid_to_channel_index[p.unique_id] = ch_idx

    # ----------------- per-step fitness (matches greedy exactly) -----------------

    def step_fitness(self, prev: Chromosome, channel, program: Program) -> int:
        return (
            program.score
            + AlgorithmUtils.get_time_preference_bonus(self.instance, program, program.start)
            + AlgorithmUtils.get_switch_penalty(prev, self.instance, channel)
            + AlgorithmUtils.get_delay_penalty(prev, self.instance, program, program.start)
            + AlgorithmUtils.get_early_termination_penalty(prev, self.instance, program, program.start)
        )

    # ----------------- candidate generation -----------------

    def _candidates_at(self, schedules: Chromosome, time: int) -> List[tuple]:
        """All (channel_index, program, fitness) candidates whose program is
        broadcasting at `time` and which would be accepted by the greedy."""
        out = []
        if time >= self.closing:
            return out
        for ch_idx, channel in enumerate(self.instance.channels):
            program = Utils.get_channel_program_by_time(channel, time)
            if not program:
                continue
            if program.end > self.closing:
                continue
            if program.end - program.start < self.min_d:
                continue
            if schedules and schedules[-1].unique_program_id == program.unique_id:
                continue
            if schedules and program.start < schedules[-1].end:
                continue
            try:
                Validator.validate_schedule_time(self.instance, program.start)
                Validator.validate_min_duration(schedules, self.instance, program.start)
                Validator.validate_max_consecutive_genre(schedules, self.instance, ch_idx, program.start)
                Validator.validate_priority_time_block(self.instance, ch_idx, program.start)
            except ConstraintException:
                continue
            fit = self.step_fitness(schedules, channel, program)
            if fit <= 0:
                continue
            out.append((ch_idx, program, fit))
        return out

    def _greedy_extend(
        self, schedules: Chromosome, start_time: int, rng: random.Random | None = None
    ) -> Chromosome:
        """Extend `schedules` from `start_time` onward, greedy-picking each step.
        If `rng` is provided, choose uniformly at random among the top-K candidates
        by fitness; otherwise always pick the best (canonical greedy)."""
        out = list(schedules)
        time = start_time
        while time < self.closing:
            candidates = self._candidates_at(out, time)
            if not candidates:
                time += 1
                continue
            candidates.sort(key=lambda x: x[2], reverse=True)
            if rng is None:
                ch_idx, program, fit = candidates[0]
            else:
                top = candidates[: self.TOP_K_RANDOMIZED_INIT]
                ch_idx, program, fit = rng.choice(top)
            channel = self.instance.channels[ch_idx]
            out.append(Schedule(
                program_id=program.program_id,
                channel_id=channel.channel_id,
                start=program.start,
                end=program.end,
                fitness=fit,
                unique_program_id=program.unique_id,
            ))
            time = program.end
        return out

    # ----------------- initialization -----------------

    def seed_with_greedy_solution(self) -> Chromosome:
        """Canonical greedy result, used as one warm-start individual."""
        sol = GreedyScheduler(self.instance).generate_solution()
        return list(sol.scheduled_programs)

    def random_chromosome(self, rng: random.Random) -> Chromosome:
        """Randomized greedy: pick uniformly among the top-K candidates per step."""
        return self._greedy_extend([], self.opening, rng=rng)

    # ----------------- decode + repair -----------------

    def repair(self, schedules: Chromosome) -> Chromosome:
        """Drop any item that would violate constraints / overlap / be a same-uid
        repeat / fail step-fitness > 0, and recompute the per-step fitness for
        the survivors. The greedy never runs here; this is pure validation."""
        clean: Chromosome = []
        items = sorted(schedules, key=lambda s: (s.start, s.end))
        for s in items:
            program = self.uid_to_program.get(s.unique_program_id)
            if program is None:
                continue
            ch_idx = self.uid_to_channel_index.get(s.unique_program_id)
            if ch_idx is None:
                continue
            if program.end > self.closing:
                continue
            if program.end - program.start < self.min_d:
                continue
            if clean and clean[-1].unique_program_id == program.unique_id:
                continue
            if clean and program.start < clean[-1].end:
                continue
            try:
                Validator.validate_schedule_time(self.instance, program.start)
                Validator.validate_min_duration(clean, self.instance, program.start)
                Validator.validate_max_consecutive_genre(clean, self.instance, ch_idx, program.start)
                Validator.validate_priority_time_block(self.instance, ch_idx, program.start)
            except ConstraintException:
                continue
            channel = self.instance.channels[ch_idx]
            fit = self.step_fitness(clean, channel, program)
            if fit <= 0:
                continue
            clean.append(Schedule(
                program_id=program.program_id,
                channel_id=channel.channel_id,
                start=program.start,
                end=program.end,
                fitness=fit,
                unique_program_id=program.unique_id,
            ))
        return clean

    def decode(self, chromosome: Chromosome) -> Solution:
        clean = self.repair(chromosome)
        total = sum(s.fitness for s in clean)
        return Solution(scheduled_programs=clean, total_score=total)

    def fitness(self, chromosome: Chromosome) -> int:
        return self.decode(chromosome).total_score
