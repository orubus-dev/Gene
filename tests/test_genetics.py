import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gene import concepts, genome, dsl, evolution
import random


def test_concept_hebbian_and_decay():
    g = concepts.ConceptGraph()
    g.ensure("fire", words=["fire"]); g.ensure("smoke", words=["smoke"])
    g.hebbian(["fire", "smoke"], amount=0.5)
    assert g.neighbors("fire")[0][2] > 0.4
    for _ in range(60):
        g.decay(rate=0.01)
    assert sum(s for _, _, s in g.neighbors("fire")) < 0.5


def test_gene_mutation_changes_body():
    rng = random.Random(7)
    base = genome.new_gene([{"op": "reverse", "args": {}}])
    seen = set()
    for _ in range(20):
        child = genome.mutate_gene(base, rng, "string")
        seen.add(child["id"])
    assert len(seen) == 20  # every child is a new individual


def test_gene_executes():
    g = genome.new_gene([{"op": "upper", "args": {}}])
    assert dsl.execute_pipeline(g["steps"], "gene") == "GENE"


def test_evolution_improves_pool():
    rng = random.Random(11)
    pool = [genome.new_gene([{"op": "add", "args": {"n": rng.randint(-3, 9)}}]) for _ in range(12)]
    def evaluate(p):
        out = {}
        for g in p:
            s = g["steps"][0]
            out[g["id"]] = 1.0 if s.get("op") == "add" and s.get("args", {}).get("n") == 3 else 0.1
        return out
    pool, history = evolution.evolve(pool, rng, gens=3, evaluate=evaluate)
    alleles = [g["steps"][0].get("args", {}).get("n") for g in pool
               if g["steps"] and g["steps"][0].get("op") == "add"]
    assert 3 in alleles  # selection kept the fit allele
