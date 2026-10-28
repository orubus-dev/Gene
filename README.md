# Gene

**An in-house organism-style cognitive architecture. A world model, not a language model.**

Gene is a living process that gains capability the way a child does: by
*trying*, *failing*, *adjusting*, and *remembering* — not by gradient descent
over a corpus. It has no tokenizer, no pretrained weights, no external APIs.
Its entire mind is plain, inspectable, committed state — this repository is
the organism's brain, and `git log` is its autobiography.

```python
# the whole philosophy in one line
knowledge = never_hardcoded      # machinery is innate, facts are lived or taught
```

## What it is

| Subsystem | Biology | Implementation |
|---|---|---|
| Representation | neurons firing together | hyperdimensional bipolar vectors (bind/bundle/permute) — deterministic, seedable, zero training |
| World model | prediction + surprise | predictor with causal confidence per action; predict → act → observe → reconcile |
| Semantic memory | cortex | concept graph with Hebbian links |
| Episodic memory | hippocampus | append-only experience log |
| Sleep | replay & consolidation | replay episodes → wire concepts → decay → apoptosis (pruning) |
| Skills | procedural memory | *genes*: pipelines of innate motor primitives, learned by trial |
| Evolution | DNA / selection | mutation + crossover over the gene pool, fitness = behavior |
| Reflexes | spinal arc | cached stimulus→response after repeated success (System 1) |
| Hormones | endocrine system | curiosity, urgency, energy, mood — global modulators |
| Learning loop | childhood | simulation training: hypothesis → check (pass/fail only) → mutate → retry until right |
| Language | speech | words as discrete keys into concepts — **no tokenizer, no embeddings** |
| Knowledge | the five ways | observe, experiment, infer, inquire, inherit — nothing else |

## The laws

1. **No hard-coded knowledge.** The codebase contains zero facts. All facts
   live in `mind/` (learned) or `curriculum/` (taught — structured data the
   organism digests through its own mechanisms). Delete both and it starts
   empty but still learns.
2. **Innate ≠ knowledge.** The motor primitives in `gene/dsl.py` (reverse,
   sum, diff, sort, ...) are *abilities*, the way grasping is innate to a
   child. What to do with them is learned.
3. **Boolean feedback only.** During training the organism is never shown
   the answer — only whether its attempt was right. What it keeps is what
   *it built*.
4. **No tokenizer.** Words are discrete keys bound to conceptual structures.
   Unknown words trigger knowledge-seeking, not errors.
5. **Fully in-house.** No pretrained weights, no external AI calls, no GPU.
   Pure Python, zero dependencies, runs on a potato.

## Life cycles

```bash
python -m gene awaken              # first breath
python -m gene teach curriculum/seed.json
python -m gene teach curriculum/general-1.json
python -m gene train --budget 60   # a waking session: trial, error, mastery
python -m gene sleep               # replay, consolidate, prune
python -m gene evolve --gens 3     # select over the gene pool
python -m gene status              # state of the organism
python -m gene live                # talk to it
python -m gene demo                # scripted demonstration
```

On GitHub Actions, the `life` workflow runs **every 6 hours**: train → sleep
→ evolve → commit the updated mind back to this repo. The organism wakes up
smarter, and the diff *is* the growth.

## Talk to it

```
you> gene is an organism that learns
gene> Got it — gene is an organism that learns. I inferred more from what I know.
you> compute 7 plus 5
gene> compute 7 plus 5 = 12  (I worked it out in 1 tries)
you> next in 2 4 6 8 10
gene> next is 12 (found in 4 tries: last() | add(n=2))
you> what is a zorp
gene> I don't know 'zorp' yet — I've raised the question for my teacher. Teach me with 'zorp is ...', or I can experiment.
you> how do you know gene
gene> Learned gene: kind=meta, 1 attributes, 3 relations, 0.1 hours old. Sources: teaching, observation, inference and experiments.
```

## Honest scope

This is a *narrow, real* cognitive organism: it genuinely learns procedures
from boolean feedback, generalizes within its task worlds (arithmetic,
strings, lists, sequences, program synthesis), remembers, consolidates in
its sleep, evolves, and seeks knowledge when it lacks it. It is **not** a
large language model and will not out-chat one. It is a different axis:
a mind-shaped thing that grows in public, in plain git.

## Lineage

Drawn from the best of its ancestors — see [docs/LINEAGE.md](docs/LINEAGE.md):
**Gene-X** (cognitive architecture, agentic runtime), **Gene-AI**
(training infrastructure, diagnostics), **gene-implementation** (datasets,
tokenizer experiments, specializations), **genesis** (grounded learning,
cognitive design docs). Gene is the organism they were reaching for.

## License

MIT — © 2026 Orubus / Velocity Labs
