"""The language trainer — conversation learned by trial, never by example.

Task worlds here produce STIMULI (what a human says) plus a CHECKER
(the physics of a good reply: must state name+version for identity, must
not contain cop-out phrases, must vary, must stay in length bounds).
The checker returns ONLY pass/fail — the expected reply text is never
shown to the organism, never written into it.

The organism's hypothesis space = response STRATEGIES of the
conversational cortex (direct/infer/analogy/elaborate/counter/empathy).
Winning strategies consolidate as genes in domain "chat" and reflex arcs,
so fluent replies become System 1.

Escalation law (per spec): on failure the environment gets HARDER
(tier up) — never easier, and the answer is never revealed.
"""
import re
import time

from . import conversation as C
from .reflex import stimulus_key

STRATEGIES = ["direct", "infer", "analogy", "elaborate", "counter", "empathy"]

# ---------------- stimulus pools (environment physics, graded) ----------------
TIER1 = {
    "identity": ["who are you?", "what are you?", "what's your name?",
                 "introduce yourself", "tell me about yourself"],
    "greeting": ["hi", "hello", "hey", "good morning", "yo"],
    "howareyou": ["how are you?", "how's it going?", "how do you feel?"],
    "capability": ["what can you do?", "what do you know?", "how do you learn?"],
    "thanks": ["thanks", "thank you"],
    "farewell": ["bye", "goodbye", "see you later"],
    "compliment": ["good job", "you're smart", "nice work"],
    "insult": ["you're useless", "that was dumb"],
    "affirm": ["yes", "ok", "cool", "nice"],
}
TIER2 = {
    "identity": ["ur name?", "who r u lol", "so what exactly are you??",
                 "are you chatgpt?", "are you an LLM or something?"],
    "greeting": ["heyy wassup", "yo yo", "hiya!!", "greetings, machine"],
    "howareyou": ["hru today?", "you good?", "how have you been lately?"],
    "capability": ["what are you good at tho", "can you help me with stuff?",
                   "how do you actually think?"],
    "thanks": ["thx a lot", "ty fr", "appreciate it"],
    "farewell": ["gtg bye", "cya later", "goodnight"],
    "compliment": ["wow you're actually impressive", "love that"],
    "insult": ["you suck at this", "stupid bot"],
    "affirm": ["lol yeah", "fr fr", "true true"],
}
TIER3 = {
    "identity": ["hi! quick — who are you and what makes you different?",
                 "wait, are you a robot or a person? tell me about yourself"],
    "greeting": ["hey there! who am I talking to?", "hello — what are you, exactly?"],
    "howareyou": ["hey, how are you feeling after all that training?"],
    "capability": ["what do you know and how do you know it?",
                   "what can you do that a calculator can't?"],
    "thanks": ["thanks, that actually helped a lot"],
    "affirm": ["ok ok that's cool"],
}
TIER4 = {
    "identity": ["prove you're not just an LLM", "are you self-aware or just code?",
                 "what's it like being you?"],
    "capability": ["tell me something you actually learned today",
                   "what was your hardest problem so far?"],
    "howareyou": ["do you ever get tired of training?"],
}

TIERS = [TIER1, TIER2, TIER3, TIER4]


def gen_chat_task(rng, tier=1):
    """Environment: pick a stimulus at this tier. The checker physics comes
    with it; the expected REPLY never does."""
    pool = TIERS[min(tier, 4) - 1]
    intent = rng.choice(list(pool.keys()))
    text = rng.choice(pool[intent])
    return {"domain": "chat", "tier": min(tier, 4), "intent": intent,
            "input": text, "prompt": "chat: " + text[:40]}


def rubric_ok(task, reply, state_recent=None):
    """The physics of a good conversational reply. BOOLEAN ONLY.
    No expected answer is compared — only structural requirements."""
    if not reply or not isinstance(reply, str):
        return False
    r = reply.strip()
    low = r.lower()
    # length sanity
    if len(r) < 6 or len(r) > 420:
        return False
    # no cop-outs, ever
    for f in C.FORBIDDEN:
        if f in low:
            return False
    # no meta-leak: never mention strategies/trainer internals
    for bad in ("strategy", "direct mode", "tier up", "rubric"):
        if bad in low:
            return False
    intent = task["intent"]
    if intent == "identity":
        name = task.get("env_facts", {}).get("name", "gene")
        if name.lower() not in low:
            return False
        if not any(ch.isdigit() for ch in r):   # must state a version
            return False
        if re.search(r"\b(human|person)\b", low) and "not" not in low:
            return False
    if intent == "greeting" and len(r) < 10:
        return False
    if intent == "howareyou" and not re.search(r"\b(mood|energy|good|great|fine|tired|fresh|off|feeling|hormone)\b", low):
        return False
    if intent == "capability" and not re.search(r"\d", r):
        return False
    if intent == "thanks" and ("welcome" in low or "anytime" in low or "happy" in low or "gift" in low or "episodes" in low):
        return True
    if intent == "farewell" and not re.search(r"\b(bye|goodbye|see|later|night|away|sleep)\b", low):
        return False
    if intent == "insult" and re.search(r"\b(you suck|stupid|idiot)\b", low):
        return False
    if intent == "compliment" and not re.search(r"\b(thank|appreciate|nice|keep|earning)\b", low):
        return False
    if task["tier"] >= 3 and len(r) < 24:    # harder tiers need substance
        return False
    # variety: identical recent response for same intent fails
    if state_recent is not None:
        h = hash(r) % 100000
        if h in state_recent.get(intent, []):
            return False
    return True


def _wrap(strat):
    """Strategy as a pipeline step, same shape as every other gene."""
    return [{"op": strat, "args": {}}]


def chat_candidates(rng, task, known_genes):
    """Hypothesis space: all strategies, best-fitting genes first."""
    cands = []
    for g in sorted(known_genes, key=lambda g: -g.get("fitness", 0)):
        if g.get("domain") == "chat" and g.get("steps"):
            cands.append(g["steps"][0].get("op", "direct"))
    cands.extend(STRATEGIES)
    seen, out = set(), []
    for s in cands:
        if s not in seen:
            seen.add(s)
            out.append(s)
    return out


def train_chat_task(task, conv, genome_genes, reflexes, predictor, endocrine,
                    rng, max_retries=6, now=0.0):
    """One chat task: try strategies, ONLY pass/fail, escalate on failure."""
    intent = task["intent"]
    attempts = []
    cands = chat_candidates(rng, task, genome_genes)
    budget = min(len(cands), endocrine.search_budget(max_retries))
    winner = None
    for i, strat in enumerate(cands[:budget]):
        steps = _wrap(strat)
        predicted = predictor.predict("chat", steps)
        try:
            reply = conv.respond(task["input"], strat)
        except Exception:
            reply = None
        ok = rubric_ok(task, reply, conv.state.d.get("recent_out", {}))
        surprise = predictor.reconcile("chat", steps, ok)
        endocrine.surprise(min(1.0, surprise))
        attempts.append({"tag": strat, "ok": ok, "pred": round(predicted, 2),
                         "reply_len": len(reply or "")})
        if ok:
            winner = strat
            break
        endocrine.effort(0.5)
    if winner:
        endocrine.success(1.0)
        reflexes.reinforce("chat", intent + "|" + task["input"][:48].lower(), _wrap(winner))
        gene = {"id": None, "domain": "chat", "steps": _wrap(winner), "fitness": 1.0,
                "uses": 1, "born": now, "name": "chat:%s:%s" % (intent, winner)}
        return {"solved": True, "attempts": attempts, "gene": gene,
                "coactive": ["chat", intent, "success"], "tier": task["tier"]}
    endocrine.load(1.0)
    # ESCALATION LAW: failure makes the world harder — tier up, never reveal.
    return {"solved": False, "attempts": attempts, "gene": None,
            "coactive": ["chat", intent, "failure"], "tier": min(4, task["tier"] + 1)}
