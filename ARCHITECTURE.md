# Gene — Architecture

## Overview

Gene is a cognitive organism built from twelve cooperating subsystems.
Everything is deterministic, seedable, zero-dependency Python. State is
JSON in `mind/`; the repository is the brain.

```
            text ──► LINGUISTICS (words→intents, no tokenizer)
                        │
        ┌───────────────▼────────────────┐
        │  REFLEXES (System 1, cached)   │──► response
        └───────────────┬────────────────┘
                        │ miss
        ┌───────────────▼───────────────┐
        │  MIND (System 2)              │
        │  concept graph ── reasoning   │
        │  skills (genes) ── execution  │
        │  predictor ── world model     │
        └───────┬──────────────┬────────┘
                │              │
       KNOWLEDGE (5 ways)   TRAINER (trial→fail→mutate→succeed)
                │              │
        EPISODES ── SLEEP ── consolidation, decay, apoptosis
                │
        EVOLUTION (selection over the gene pool)
```

## Subsystems

### 1. HDC substrate (`hdc.py`)
Bipolar vectors (dim 2048). `bind` = association, `bundle` = prototype,
`permute` = order, `sim` = similarity. Vectors are never stored — only
seed strings, recomputed deterministically. This is the innate algebra of
representation: no training happens here, ever.

### 2. Motor primitives (`dsl.py`)
~30 innate operations on strings, lists, numbers (reverse, upper, sumv,
diff, prod, sqr, map, ...). These are *abilities*, not knowledge — the
distinction is the core law of the system. A pipeline of primitives is a
hypothesis; executing it is acting.

### 3. Procedure genes (`genome.py`)
A gene = pipeline + fitness + usage. Mutation edits steps/args; crossover
splices two genes. Fitness is behavioral only.

### 4. Concept graph (`concepts.py`)
Nodes carry kind, attributes, word bindings, links (rel>target→strength).
Hebbian co-activation strengthens; decay weakens; apoptosis prunes the
weak and abandoned. This is semantic memory — structure, not content.

### 5. Predictor / world model (`world.py`)
Causal confidence per (domain, action-signature), born naive (p=0.35),
updated only by lived outcomes. Surprise = |Δp| feeds the endocrine
system. This is the smallest honest world-model loop.

### 6. Episodic memory + sleep (`memory.py`)
Append-only jsonl of everything that happens. Sleep replays recent
episodes: co-active concepts wire together (consolidation), all links
decay a little, and weak/abandoned concepts die (apoptosis). Episode
files rotate to keep the brain light.

### 7. Endocrine system (`endocrine.py`)
Four hormones (curiosity, urgency, energy, mood) modulate the whole mind:
curiosity raises exploration and widens trial budgets; urgency widens
search under load; energy depletes with effort and restores in sleep;
mood tracks how well life is going. Global, cheap, powerful.

### 8. Reflexes (`reflex.py`)
After repeated identical stimulus→successful-response pairs, the response
is cached and consulted first. System 1. Conflicts overwrite; disuse
decays.

### 9. Knowledge — the five ways (`knowledge.py`)
- **observe**: accept a fact from the environment
- **experiment**: act in a world, record the outcome
- **infer**: walk is-a/has/causes links, inherit attributes with provenance
- **inquire**: ask the teacher; if absent, queue the question (the organism raises its hand in `mind/questions.json`)
- **inherit**: specialize a parent concept

Teaching (`curriculum/*.json`) is structured data digested through these
same mechanisms. The organism's provenance report shows where every piece
of knowledge came from.

### 10. Trainer — the learning loop (`trainer.py`)
Task worlds: number, string, list, sequence, code (program synthesis from
I/O examples). For each task: reflex → fitted genes → generated
hypotheses, tried in order. **Only pass/fail feedback** — the expected
answer is never shown. Wrong → next hypothesis (hormone-modulated
budget). Right → consolidate: new gene, reflex reinforcement, causal
confidence, Hebbian wiring, success chemistry.

### 11. Evolution (`evolution.py`)
Tournament selection over the gene pool by behavioral fitness; mutation
and crossover fill the next generation. Generations are logged to
`mind/evolution.json` — growth you can diff.

### 12. Linguistics (`linguistics.py`)
Pattern-based parsing to intents (fact, query, compute, transform,
provenance, status). Words map to concepts; unknown words trigger
knowledge-seeking. Generation renders from internal structures. There is
deliberately **no tokenizer** — words are discrete keys, meaning lives in
the graph.

## Data flow of one training task

```
generate task (environment)          e.g. sum [3,9,4] = 16 (hidden)
  │
  ├─ reflex hit? ── yes ──► execute, check ──► done (1 try)
  └─ no
  │
  ├─ hypothesis 1: sumv([3,9,4]) → 16  ✓✓✓ solved, 1 try
  │     (if ✗: reconcile surprise, try next)
  ├─ hypothesis 2: maxv → 9 ✗ (surprise!)
  └─ ... until budget (hormones widen it)
  │
  on success: gene(fitness=1) + reflex + confidence + hebbian + dopamine
  on failure: failure episode, curiosity up → try harder next round
```

## Why no gradients?

Gradient descent rewrites billions of opaque numbers on a static corpus.
Gene's learning changes *explicit structure*: new genes, stronger links,
new reflexes, updated confidences — all inspectable, all diffable, all
committed to git. It is the architecture bet of this project: a mind you
can read.
