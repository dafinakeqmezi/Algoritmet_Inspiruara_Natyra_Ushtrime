"""
Genetic operators — problem-specific, applied to variable-length chromosomes.

Selection : tournament (k configurable)
Crossover : time-window crossover  -OR-  channel-based crossover
Mutation  : remove a random program  -OR-  greedy repair/regeneration

The Phase 1 / local-search operators (shift, replace, swap, insert) are NOT
provided. The mutations here either DROP a gene or RE-GENERATE a tail; they
never re-position a single gene by ±dt or rotate two genes (which would be
shift/swap by another name).

All operators take an explicit random.Random instance for reproducibility.
Every offspring is repaired by `ChromosomeEncoder.repair()` before fitness
evaluation; operators are free to produce mildly inconsistent chromosomes.
"""
from __future__ import annotations

import random
from typing import List, Tuple

from ga.chromosome import Chromosome, ChromosomeEncoder


# -------------- Selection --------------

def tournament_select(
    population: List[Chromosome],
    fitnesses: List[int],
    tournament_size: int,
    rng: random.Random,
) -> Chromosome:
    k = min(tournament_size, len(population))
    contenders = rng.sample(range(len(population)), k)
    winner = max(contenders, key=lambda i: fitnesses[i])
    return list(population[winner])


# -------------- Crossover --------------

def time_window_crossover(
    p1: Chromosome, p2: Chromosome, encoder: ChromosomeEncoder, rng: random.Random
) -> Tuple[Chromosome, Chromosome]:
    """Pick a split time t in (opening, closing). Each child concatenates
    one parent's schedules ending before t with the other parent's schedules
    starting at or after t. The encoder's repair pass cleans any seams."""
    opening, closing = encoder.opening, encoder.closing
    if closing - opening < 2:
        return list(p1), list(p2)
    t = rng.randint(opening + 1, closing - 1)
    head1 = [s for s in p1 if s.end <= t]
    tail1 = [s for s in p1 if s.start >= t]
    head2 = [s for s in p2 if s.end <= t]
    tail2 = [s for s in p2 if s.start >= t]
    return head1 + tail2, head2 + tail1


def channel_based_crossover(
    p1: Chromosome, p2: Chromosome, encoder: ChromosomeEncoder, rng: random.Random
) -> Tuple[Chromosome, Chromosome]:
    """Pick a random subset of channel ids. Child 1 = parent1's items on those
    channels + parent2's items on the rest; child 2 is the complement."""
    n_ch = encoder.n_channels
    if n_ch < 2:
        return list(p1), list(p2)
    take_from_p1: set[int] = set()
    for ch_idx in range(n_ch):
        if rng.random() < 0.5:
            ch_id = encoder.instance.channels[ch_idx].channel_id
            take_from_p1.add(ch_id)
    c1 = [s for s in p1 if s.channel_id in take_from_p1] + \
         [s for s in p2 if s.channel_id not in take_from_p1]
    c2 = [s for s in p2 if s.channel_id in take_from_p1] + \
         [s for s in p1 if s.channel_id not in take_from_p1]
    return c1, c2


def crossover(
    p1: Chromosome,
    p2: Chromosome,
    crossover_type: str,
    encoder: ChromosomeEncoder,
    rng: random.Random,
) -> Tuple[Chromosome, Chromosome]:
    if crossover_type == "time_window":
        return time_window_crossover(p1, p2, encoder, rng)
    if crossover_type == "channel":
        return channel_based_crossover(p1, p2, encoder, rng)
    raise ValueError(f"unknown crossover_type: {crossover_type!r}")


# -------------- Mutation --------------

def remove_random_program_mutation(
    chrom: Chromosome, rng: random.Random
) -> Chromosome:
    """Drop one randomly-chosen scheduled program from the chromosome."""
    if not chrom:
        return list(chrom)
    out = list(chrom)
    idx = rng.randrange(len(out))
    out.pop(idx)
    return out


def greedy_repair_regeneration_mutation(
    chrom: Chromosome, encoder: ChromosomeEncoder, rng: random.Random
) -> Chromosome:
    """Pick a random cut point k. Keep schedules[0:k] verbatim and re-generate
    the tail with the greedy from `schedules[k-1].end` (or the opening time
    if k == 0). This recovers structure after disruption."""
    if not chrom:
        return encoder.random_chromosome(rng)
    k = rng.randint(0, len(chrom))  # 0 ⇒ regenerate the whole thing
    head = list(chrom[:k])
    start_time = head[-1].end if head else encoder.opening
    return encoder._greedy_extend(head, start_time, rng=None)


def mutate(
    chrom: Chromosome, encoder: ChromosomeEncoder, rng: random.Random
) -> Chromosome:
    """Pick one of the two problem-specific mutations uniformly at random."""
    mtype = rng.choice(("remove", "regenerate"))
    if mtype == "remove":
        return remove_random_program_mutation(chrom, rng)
    return greedy_repair_regeneration_mutation(chrom, encoder, rng)
