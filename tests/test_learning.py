import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gene import trainer, dsl, endocrine, world, reflex
import random


def _fresh_organs():
    return [], reflex.Reflexes(), world.Predictor(), endocrine.Endocrine(), random.Random(3)


def test_organism_learns_hidden_number_rule():
    """Acceptance: trial-and-error discovers the hidden op, no answers given."""
    genes, rx, pred, endo, rng = _fresh_organs()
    task = {"domain": "number", "input": [5, 3], "expected": 2, "prompt": "compute 5 - 3?"}
    solved = None
    for _ in range(3):  # a few lives; budget should find it within one
        r = trainer.train_task(task, genes, rx, pred, endo, rng, max_retries=14)
        if r["solved"]:
            solved = r
            break
        genes.append(r["gene"]) if r["gene"] else None
    assert solved, "organism failed to learn a subtraction task"
    assert dsl.execute_pipeline(solved["gene"]["steps"], [9, 4]) == 5  # it generalizes


def test_organism_learns_string_rule():
    genes, rx, pred, endo, rng = _fresh_organs()
    task = {"domain": "string", "input": "gene", "expected": "GENE!", "prompt": "shout"}
    r = trainer.train_task(task, genes, rx, pred, endo, rng, max_retries=14)
    assert r["solved"]
    assert dsl.execute_pipeline(r["gene"]["steps"], "mind") == "MIND!"


def test_code_synthesis_from_examples():
    genes, rx, pred, endo, rng = _fresh_organs()
    xs = [2, 5, 9]
    task = {"domain": "code", "input": xs[0], "expected": 4,
            "examples": [{"in": x, "out": x * 2} for x in xs],
            "prompt": "synthesize function from examples"}
    r = trainer.train_task(task, genes, rx, pred, endo, rng, max_retries=20)
    assert r["solved"], r["attempts"][-3:] if r["attempts"] else "no attempts"
    steps = r["gene"]["steps"]
    assert dsl.execute_pipeline(steps, 21) == 42  # synthesized function generalizes


def test_reflex_forms_after_success():
    genes, rx, pred, endo, rng = _fresh_organs()
    task = {"domain": "string", "input": "gene", "expected": "GENE", "prompt": "upper"}
    tags = []
    for _ in range(4):  # repetition wires the arc (strength crosses the gate)
        r = trainer.train_task(task, genes, rx, pred, endo, rng, max_retries=14)
        assert r["solved"]
        tags.append(r["attempts"][0]["tag"])
    assert tags[-1] == "reflex", tags  # System 1 eventually takes over
