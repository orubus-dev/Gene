import sys, os, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gene import concepts, memory, immune, development, endocrine


def test_sleep_consolidates_and_prunes():
    g = concepts.ConceptGraph()
    g.ensure("fire", words=["fire"]); g.ensure("smoke", words=["smoke"])
    ep_path = tempfile.mktemp(suffix=".jsonl")
    eps = memory.EpisodicMemory(ep_path)
    for _ in range(3):
        eps.record("observe", {"coactive": ["fire", "smoke"]})
    report = memory.sleep_cycle(g, eps, decay=0.01, replay_k=50)
    assert report["replayed"] == 3 and report["consolidated"] == 3
    assert g.neighbors("fire"), "sleep should wire co-active concepts"
    os.unlink(ep_path)


def test_immune_novel_then_habituates():
    im = Immune = immune.ImmuneSystem()
    ctx = {"domain": "gridworld", "door": 3}
    n1 = im.survey(0.9, fatigue=0.0, context=ctx)
    n2 = im.survey(0.9, fatigue=0.0, context=ctx)
    n3 = im.survey(0.9, fatigue=0.0, context=ctx)
    assert n1[0] and not n3[0], "first contact novel, repeats habituate"
    assert im.tolerant(ctx)


def test_development_gates():
    dev = development.Development()
    assert dev.allows("sensorimotor") and not dev.allows("skills")
    for _ in range(4):
        dev.record_win("number")
    promoted = dev.maybe_promote(concept_count=10)
    assert promoted == "skills"
    assert dev.allows("skills") and not dev.allows("language")


def test_endocrine_budget_widens():
    endo = endocrine.Endocrine()
    base = endo.search_budget(6)
    endo.load(1.0); endo.h["curiosity"] = 1.0
    assert endo.search_budget(6) > base
