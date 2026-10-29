"""The sentence world — English syntax as environment physics.

The teacher's world owns real English transforms (it is the PHYSICS of
the task, like arithmetic owning a+b): statements become questions,
negatives, past tense, continuous, future, imperatives; questions become
statements. The ORGANISM never sees the rules or the expected output —
only the stimulus and a pass/fail bit.

The organism's side: sentences are handled with its sentence motor
cortex (dsl ops — list surgery + memory lookups into its own taught
tables). WHICH pipeline turns "she walks" into "does she walk?" is
discovered by trial here, then consolidated as genes and reflexes.
Generalization is structural: held-out regular verbs work through the
discovered route because inflection reads memory-then-orthography, and
agreement reads the taught aux tables — never a hard-coded pair list.
"""
import json
import os

from . import dsl, genome

# ---------------- environment tables (the physics) ---------------------------
PRONOUNS_SG = ["i", "you", "he", "she", "it"]
PRONOUNS_PL = ["we", "they"]
# the environment's own HELD-OUT regular verbs — never in any lesson pack
PROBE_VERBS = ["climb", "march", "glow", "sail", "jog", "greet", "paint",
               "warn", "type", "bolt", "sip", "hum", "stir", "trot", "peck"]
AUX_DO = {"i": "do", "you": "do", "we": "do", "they": "do",
          "he": "does", "she": "does", "it": "does"}
AUX_BE = {"i": "am", "you": "are", "we": "are", "they": "are",
          "he": "is", "she": "is", "it": "is"}
CONTR = {"do not": "don't", "does not": "doesn't", "is not": "isn't",
         "are not": "aren't", "am not": "am not"}
DETS = ("a", "an", "the")

_LESSON_CACHE = None


def _curriculum_dir():
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "curriculum")


def _load_packs():
    """PUBLIC lesson data: verbs/nouns/adjectives the organism was taught
    (same files digested through teach). The environment uses them to
    build stimuli and compute targets — never shipped to the learner."""
    global _LESSON_CACHE
    if _LESSON_CACHE is not None:
        return _LESSON_CACHE
    verbs, nouns, adjs = {}, [], []
    by_third, by_past, by_ing = {}, {}, {}
    cdir = _curriculum_dir()
    for fn in ("vocab-verbs.json", "vocab-nouns.json", "vocab-adj.json"):
        try:
            with open(os.path.join(cdir, fn)) as f:
                pack = json.load(f)
        except Exception:
            continue
        for c in pack.get("concepts", []):
            a = c.get("attrs", {})
            k = c.get("kind")
            w = (c.get("words") or [None])[0]
            if not w:
                continue
            if k == "verb_form" or str(c.get("id", "")).startswith("verb_"):
                verbs[w] = {"third": a.get("third"), "past": a.get("past"),
                            "ing": a.get("ing")}
                if a.get("third"):
                    by_third[a["third"]] = w
                if a.get("past"):
                    by_past[a["past"]] = w
                if a.get("ing"):
                    by_ing[a["ing"]] = w
            elif k == "noun_form":
                nouns.append((w, a.get("plural", w + "s")))
            elif k == "adj_form":
                adjs.append(w)
    _LESSON_CACHE = {"verbs": verbs, "nouns": nouns, "adjs": adjs,
                     "by_third": by_third, "by_past": by_past, "by_ing": by_ing}
    return _LESSON_CACHE


def _base_of(surface, pack):
    """Base form of a surface verb (walks->walk, went->go). Lesson forms
    come from the taught tables; unknown -s forms strip regularly."""
    v = surface.lower()
    if v in pack["by_third"]:
        return pack["by_third"][v]
    if v in pack["by_past"]:
        return pack["by_past"][v]
    if v in pack["by_ing"]:
        return pack["by_ing"][v]
    if v in pack["verbs"]:
        return v
    if v.endswith("ies"):
        return v[:-3] + "y"
    if v.endswith("oes"):
        return v[:-2]
    if v.endswith(("ches", "shes", "xes", "zes")):
        return v[:-2]
    if v.endswith("s"):
        return v[:-1]
    return v


def _third_of(base, pack):
    vi = pack["verbs"].get(base)
    if vi and vi.get("third"):
        return vi["third"]
    return dsl.reg_third(base)


def _past_of(base, pack):
    vi = pack["verbs"].get(base)
    if vi and vi.get("past"):
        return vi["past"]
    return dsl.reg_past(base)


def _ing_of(base, pack):
    vi = pack["verbs"].get(base)
    if vi and vi.get("ing"):
        return vi["ing"]
    return dsl.reg_ing(base)


def _noun_phrase(rng, nouns):
    """A taught noun phrase: 'the dog' / 'a cat' / 'the dogs'. Plurality is
    surface-visible (head ends in -s) so agreement stays discoverable —
    irregular plurals without -s (men, children) stay singular here; the
    organism still meets them through vocabulary."""
    base, plur = rng.choice(nouns)
    if rng.random() < 0.5:
        return "the %s" % (plur if plur.endswith("s") else base)
    return ("the %s" if base[0] in "aeiou" else "a %s") % base


def _head_of(words):
    for w in words:
        lw = w.lower().strip("'\".,?!")
        if lw in DETS:
            continue
        return lw
    return words[0].lower() if words else ""


def _is_plural(head):
    return head.endswith("s") and not head.endswith("ss")


def expected_transform(kind, sentence):
    """The environment's English. Computes the target of a transform.
    Lives HERE (physics), never in the organism."""
    s = sentence.strip().rstrip("?!. ")
    words = s.split()
    if not words:
        return sentence
    pack = _load_packs()
    verb = words[-1].lower()
    head = _head_of(words)

    if kind == "ynq":
        if len(words) >= 2 and words[1].lower() in ("is", "are", "am"):
            # she is happy -> is she happy? (move the copula to the front)
            return "%s %s %s?" % (words[1], words[0], " ".join(words[2:]))
        base = _base_of(verb, pack)
        aux = AUX_DO.get(head) or ("do" if _is_plural(head) else "does")
        return "%s %s %s?" % (aux, " ".join(words[:-1]), base)
    if kind == "neg":
        if len(words) >= 2 and words[1].lower() in ("is", "are", "am"):
            be = words[1].lower()
            mid = " ".join(words[2:])
            negd = CONTR.get("%s not" % be)
            if negd and negd != "%s not" % be:
                return "%s %s %s." % (words[0], negd, mid)
            return "%s %s not %s." % (words[0], be, mid)
        base = _base_of(verb, pack)
        aux = AUX_DO.get(head) or ("do" if _is_plural(head) else "does")
        negd = CONTR.get("%s not" % aux, "%s not" % aux)
        # the dog barks -> the dog doesn't bark. (whole subject phrase stays)
        return "%s %s %s." % (" ".join(words[:-1]), negd, base)
    if kind == "past":
        return "%s %s." % (" ".join(words[:-1]), _past_of(_base_of(verb, pack), pack))
    if kind == "cont":
        be = AUX_BE.get(head) or ("are" if _is_plural(head) else "is")
        return "%s %s %s." % (" ".join(words[:-1]), be, _ing_of(_base_of(verb, pack), pack))
    if kind == "fut":
        return "%s will %s." % (" ".join(words[:-1]), _base_of(verb, pack))
    if kind == "q2s":
        first = words[0].lower()
        rest = words[1:]
        if first in ("does", "do") and rest:
            base = _base_of(rest[-1], pack)
            head = _head_of(rest)
            # agreement: plural / i-you-we-they keep the base form
            if head in ("i", "you", "we", "they") or _is_plural(head):
                return "%s %s." % (" ".join(rest[:-1]), base)
            return "%s %s." % (" ".join(rest[:-1]), _third_of(base, pack))
        if first in ("is", "are", "am") and len(words) >= 2:
            return "%s %s." % (rest[0], " ".join([first] + words[2:]))
        return "%s." % s
    if kind == "imp":
        if words[0].lower() == "you":
            return "%s!" % " ".join(words[1:])
        return "%s!" % s
    if kind == "excl":
        return "%s!" % s
    return sentence


def gen_sentence_task(rng, tier=1):
    """Environment: build a stimulus sentence + a transform ask. Tier
    widens the world: copula -> do-support -> past/future/continuous ->
    held-out verbs + question-to-statement. The expected output never
    reaches the organism; only the sentence and the ask do."""
    pack = _load_packs()
    verbs = pack["verbs"] or {
        "walk": {"third": "walks", "past": "walked", "ing": "walking"},
        "bark": {"third": "barks", "past": "barked", "ing": "barking"},
        "sing": {"third": "sings", "past": "sang", "ing": "singing"},
        "jump": {"third": "jumps", "past": "jumped", "ing": "jumping"},
    }
    nouns = pack["nouns"] or [("dog", "dogs"), ("cat", "cats"), ("bird", "birds")]
    adjs = pack["adjs"] or ["happy", "sad", "fast", "slow"]
    kinds_by_tier = {
        1: ["ynq", "neg"],
        2: ["ynq", "neg", "imp"],
        3: ["ynq", "neg", "past", "cont", "fut", "imp"],
        4: ["ynq", "neg", "past", "cont", "fut", "q2s", "excl", "imp"],
    }
    kind = rng.choice(kinds_by_tier[min(tier, 4)])

    if kind in ("ynq", "neg") and rng.random() < 0.4:
        # copula sentence: she is happy
        subj = rng.choice(PRONOUNS_SG + PRONOUNS_PL)
        be = AUX_BE[subj]
        sentence = "%s %s %s" % (subj, be, rng.choice(adjs))
    else:
        if kind == "imp":
            subj, base = "you", rng.choice(list(verbs.keys()) + PROBE_VERBS)
        else:
            if kind in ("past", "cont", "fut") and rng.random() < 0.3:
                base = rng.choice(PROBE_VERBS)      # held-out regular verbs
            elif rng.random() < 0.15:
                base = rng.choice(PROBE_VERBS)
            else:
                base = rng.choice(list(verbs.keys()))
            subj = _noun_phrase(rng, nouns) if rng.random() < 0.4 else \
                rng.choice(PRONOUNS_SG + PRONOUNS_PL)
        if kind == "imp":
            sentence = "%s %s" % (subj, base)
        elif kind == "past":
            sentence = "%s %s" % (subj, _past_of(base, pack))
        else:
            tail_word = subj.split()[-1]
            bare = subj in ("i", "you", "we", "they") or \
                (tail_word.endswith("s") and not tail_word.endswith("ss"))
            sentence = "%s %s" % (subj, base if bare else _third_of(base, pack))
        if kind == "q2s":
            sentence = expected_transform("ynq", sentence)
    expected = " ".join(expected_transform(kind, sentence).split())
    return {"domain": "sentence", "kind": kind, "input": sentence,
            "expected": expected, "prompt": "%s: %s" % (kind, sentence[:36])}


# ---------------- the organism's hypothesis space -----------------------------
KIND_PUNCT = {"ynq": "?", "neg": ".", "past": ".", "cont": ".",
              "fut": ".", "q2s": ".", "imp": "!", "excl": "!"}


def _tail(kind):
    return [{"op": "join_words", "args": {}},
            {"op": "wrap", "args": {"pre": "", "suf": KIND_PUNCT.get(kind, ".")}}]


def sentence_pipeline_candidates(rng, task, known_genes):
    """Hypotheses for a sentence transform. Built from the sentence motor
    ops; the ask (`kind`) is visible — it is the instruction. Which
    skeleton fits WHICH sentence shape is what gets discovered."""
    kind = task.get("kind", "ynq")
    cands = []

    def add(steps):
        cands.append(steps)

    if kind == "ynq":
        add([{"op": "words", "args": {}},
             {"op": "aux_insert", "args": {"family": "do", "pos": 0}},
             {"op": "verb_last_to", "args": {"form": "base"}}] + _tail(kind))
        add([{"op": "words", "args": {}},
             {"op": "swap_first_two", "args": {}}] + _tail(kind))
        add([{"op": "words", "args": {}},
             {"op": "aux_insert", "args": {"family": "be", "pos": 0}}] + _tail(kind))
        add([{"op": "words", "args": {}},
             {"op": "aux_insert", "args": {"family": "will", "pos": 0}}] + _tail(kind))
    elif kind == "neg":
        # the general route: aux lands in the pre-verb slot (-1 works for
        # ANY subject — pronoun or noun phrase), verb drops to base form
        add([{"op": "words", "args": {}},
             {"op": "aux_insert", "args": {"family": "do", "pos": -1}},
             {"op": "insert_at", "args": {"pos": -1, "with": "not"}},
             {"op": "verb_last_to", "args": {"form": "base"}},
             {"op": "contract_not", "args": {}}] + _tail(kind))
        add([{"op": "words", "args": {}},
             {"op": "aux_insert", "args": {"family": "do", "pos": -1}},
             {"op": "insert_at", "args": {"pos": -1, "with": "not"}},
             {"op": "verb_last_to", "args": {"form": "base"}}] + _tail(kind))
        # decoys: pronoun-only routes and wrong slots — discovered wrong by trial
        add([{"op": "words", "args": {}},
             {"op": "aux_insert", "args": {"family": "do", "pos": 1}},
             {"op": "insert_at", "args": {"pos": 2, "with": "not"}},
             {"op": "verb_last_to", "args": {"form": "base"}},
             {"op": "contract_not", "args": {}}] + _tail(kind))
        add([{"op": "words", "args": {}},
             {"op": "insert_at", "args": {"pos": 2, "with": "not"}},
             {"op": "contract_not", "args": {}}] + _tail(kind))
        add([{"op": "words", "args": {}},
             {"op": "aux_insert", "args": {"family": "will", "pos": 1}},
             {"op": "insert_at", "args": {"pos": 2, "with": "not"}},
             {"op": "contract_not", "args": {}}] + _tail(kind))
    elif kind == "past":
        add([{"op": "words", "args": {}},
             {"op": "verb_last_to", "args": {"form": "past"}}] + _tail(kind))
        add([{"op": "words", "args": {}},
             {"op": "reg_past", "args": {}}] + _tail(kind))
        add([{"op": "words", "args": {}},
             {"op": "verb_last_to", "args": {"form": "ing"}}] + _tail(kind))
    elif kind == "cont":
        # general route: aux lands in the pre-verb slot (before the verb),
        # whatever the subject — pronoun or noun phrase
        add([{"op": "words", "args": {}},
             {"op": "verb_last_to", "args": {"form": "ing"}},
             {"op": "aux_insert", "args": {"family": "be", "pos": -1}}] + _tail(kind))
        add([{"op": "words", "args": {}},
             {"op": "verb_last_to", "args": {"form": "ing"}},
             {"op": "aux_insert", "args": {"family": "be", "pos": 1}}] + _tail(kind))
        add([{"op": "words", "args": {}},
             {"op": "aux_insert", "args": {"family": "be", "pos": 0}},
             {"op": "verb_last_to", "args": {"form": "ing"}}] + _tail(kind))
        add([{"op": "words", "args": {}},
             {"op": "verb_last_to", "args": {"form": "ing"}}] + _tail(kind))
    elif kind == "fut":
        # general route: base form + will in the pre-verb slot
        add([{"op": "words", "args": {}},
             {"op": "verb_last_to", "args": {"form": "base"}},
             {"op": "aux_insert", "args": {"family": "will", "pos": -1}}] + _tail(kind))
        add([{"op": "words", "args": {}},
             {"op": "verb_last_to", "args": {"form": "base"}},
             {"op": "aux_insert", "args": {"family": "will", "pos": 1}}] + _tail(kind))
        add([{"op": "words", "args": {}},
             {"op": "aux_insert", "args": {"family": "will", "pos": 1}},
             {"op": "verb_last_to", "args": {"form": "base"}}] + _tail(kind))
        add([{"op": "words", "args": {}},
             {"op": "aux_insert", "args": {"family": "do", "pos": 1}},
             {"op": "verb_last_to", "args": {"form": "base"}}] + _tail(kind))
    elif kind == "q2s":
        add([{"op": "strip_punct", "args": {}},
             {"op": "words", "args": {}},
             {"op": "drop_first", "args": {}},
             {"op": "verb_agree", "args": {}}] + _tail(kind))
        add([{"op": "strip_punct", "args": {}},
             {"op": "words", "args": {}},
             {"op": "drop_first", "args": {}},
             {"op": "verb_last_to", "args": {"form": "third"}}] + _tail(kind))
        add([{"op": "strip_punct", "args": {}},
             {"op": "words", "args": {}},
             {"op": "swap_first_two", "args": {}}] + _tail(kind))
        add([{"op": "words", "args": {}},
             {"op": "drop_first", "args": {}},
             {"op": "verb_last_to", "args": {"form": "third"}}] + _tail(kind))
    elif kind == "imp":
        add([{"op": "words", "args": {}},
             {"op": "drop_first", "args": {}}] + _tail(kind))
        add([{"op": "words", "args": {}}] + _tail(kind))
    elif kind == "excl":
        add([{"op": "words", "args": {}}] + _tail(kind))
        add([{"op": "strip_punct", "args": {}},
             {"op": "wrap", "args": {"pre": "", "suf": "!"}}])
    for g in known_genes:
        if g.get("domain") == "sentence" and g.get("steps"):
            add(g["steps"])
    for _ in range(2):
        add(genome.random_gene(rng, "string")["steps"])
    seen, out = set(), []
    for s in cands:
        k = json.dumps(s, sort_keys=True)
        if k not in seen:
            seen.add(k)
            out.append(s)
    return out
