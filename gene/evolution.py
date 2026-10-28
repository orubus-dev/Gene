"""Evolution — selection over procedure genomes.

Population = the gene pool. Fitness = behavioral (tasks solved, attempts
spent). Tournament selection, mutation, crossover. Each generation is
logged so growth is inspectable in git history.
"""
import json
import os
import random

from . import genome as G
from . import trainer


def fitness_of(gene, solve_events):
    """Fitness from lived performance, not opinion."""
    return gene.get("fitness", 0.0) * 1.0 + 0.1 * gene.get("uses", 0)


def evolve(genes, rng, gens=2, evaluate=None, pop_cap=60):
    """Run generations. evaluate(pool) -> dict gene_id -> fitness."""
    pool = list(genes)
    history = []
    for gen in range(gens):
        scores = evaluate(pool) if evaluate else {g["id"]: g.get("fitness", 0.0) for g in pool}
        pool.sort(key=lambda g: -scores.get(g["id"], g.get("fitness", 0.0)))
        survivors = pool[: max(4, len(pool) // 2)]
        children = []
        while len(survivors) + len(children) < min(pop_cap, max(len(pool), 8)):
            a = rng.choice(survivors)
            if rng.random() < 0.5 and len(survivors) > 1:
                b = rng.choice(survivors)
                child = G.crossover(a, b, rng)
            else:
                child = G.mutate_gene(a, rng, "string")
            children.append(child)
        pool = survivors + children
        pool = pool[:pop_cap]
        history.append({"gen": gen + 1, "size": len(pool),
                        "top": scores.get(pool[0]["id"], 0.0) if pool else 0.0})
    return pool, history


def prune_pool(genes, cap=400):
    return trainer.dedupe_genes(genes, cap=cap)
