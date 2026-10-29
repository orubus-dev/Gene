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

STRATEGIES = ["direct", "infer", "analogy", "elaborate", "counter", "empathy", "create"]

# ---------------- stimulus pools (environment physics, graded) ----------------
TIER1 = {
    "identity": ["who are you?", "what are you?", "what's your name?",
                 "introduce yourself", "tell me about yourself"],
    "greeting": ["hi", "hello", "hey", "good morning", "yo"],
    "howareyou": ["how are you?", "how's it going?", "how do you feel?"],
    "capability": ["what can you do?", "what do you know?", "how do you learn?"],
    "origin": ["where are you from?", "who made you?", "what are you made of?"],
    "thanks": ["thanks", "thank you"],
    "farewell": ["bye", "goodbye", "see you later"],
    "compliment": ["good job", "you're smart", "nice work"],
    "insult": ["you're useless", "that was dumb"],
    "affirm": ["yes", "ok", "cool", "nice"],
}
TIER2 = {
    "identity": ["ur name?", "who r u lol", "so what exactly are you??",
                 "are you chatgpt?", "are you an LLM or something?",
                 "what should I call you?", "who am I speaking with?",
                 "describe yourself in a line"],
    "greeting": ["heyy wassup", "yo yo", "hiya!!", "greetings, machine",
                 "hello there, friend", "hey you"],
    "howareyou": ["hru today?", "you good?", "how have you been lately?",
                  "you doing alright?", "how's everything going?"],
    "capability": ["what are you good at tho", "can you help me with stuff?",
                   "how do you actually think?", "what are your abilities?",
                   "how do you work?"],
    "origin": ["who built you?", "who created you?", "when were you born?",
               "how were you made?", "who's your maker?", "where do you come from?"],
    "creativity": ["tell me something new", "tell me something interesting",
                   "what do you wonder about?", "make me a connection",
                   "surprise me", "what can you figure out on your own?"],
    "improvement": ["are you getting better?", "how much have you improved?",
                    "are you smarter than before?", "what's your progress?"],
    "existence": ["do dragons exist?", "have you heard of unicorns?",
                  "ever heard of a quokka?", "do you know about platypuses?"],
    "time": ["what time is it?", "what's the time?", "do you know the time?"],
    "weather": ["what's the weather like?", "is it raining?", "how's the weather?"],
    "extrapolate": ["we have statements and questions — what other grammar types are out there?",
                    "grammar has past and present tense — what else belongs in the family?",
                    "here are two sentence types: statement, command. complete the family."],
    "thanks": ["thx a lot", "ty fr", "appreciate it", "much appreciated"],
    "farewell": ["gtg bye", "cya later", "goodnight", "catch you later"],
    "compliment": ["wow you're actually impressive", "love that", "well done"],
    "insult": ["you suck at this", "stupid bot", "that was dumb"],
    "affirm": ["lol yeah", "fr fr", "true true", "sounds good"],
}
TIER3 = {
    "identity": ["hi! quick — who are you and what makes you different?",
                 "wait, are you a robot or a person? tell me about yourself",
                 "before we start — what exactly am I talking to?",
                 "give me the elevator pitch: who is Gene?"],
    "greeting": ["hey there! who am I talking to?", "hello — what are you, exactly?",
                 "morning! hope you trained well"],
    "howareyou": ["hey, how are you feeling after all that training?",
                  "how's your energy after the last cycle?"],
    "capability": ["what do you know and how do you know it?",
                   "what can you do that a calculator can't?",
                   "convince me you're more than pattern matching"],
    "origin": ["tell me your origin story", "who raised you — was it only the teacher?",
               "what were you before you could talk?", "what did you start out knowing?"],
    "creativity": ["tell me something you figured out that nobody taught you",
                   "piece two things together for me", "what connections do you see in your graph?",
                   "invent a hypothesis for me", "what have you derived on your own lately?",
                   "show me your original thinking"],
    "improvement": ["are you getting better at numbers?", "how's your learning curve on code?",
                    "show me your improvement since your first cycles",
                    "do you learn faster now than before?"],
    "existence": ["does a zorpus exist?", "have you ever heard of a flurg?",
                  "is there such a thing as a blorp?", "do seacows exist?",
                  "what is a zorp?", "what is a zorpus?"],
    "extrapolate": ["if statements and questions exist, what else does grammar need? name them",
                    "grammar evolved statements and questions. what's the next evolution?",
                    "take the grammar I gave you and extrapolate — what types am I missing?"],
    "time": ["got the time?", "what time is it right now?"],
    "weather": ["is it sunny outside?", "is it cold out there?"],
    "thanks": ["thanks, that actually helped a lot", "appreciate the honest answer"],
    "affirm": ["ok ok that's cool", "true, I buy it"],
}
TIER4 = {
    "identity": ["prove you're not just an LLM", "are you self-aware or just code?",
                 "what's it like being you?", "what separates you from a script with canned replies?",
                 "if I ask you the same thing ten ways, will I get the same canned line?"],
    "capability": ["tell me something you actually learned today",
                   "what was your hardest problem so far?",
                   "what's the difference between knowing and memorizing?"],
    "howareyou": ["do you ever get tired of training?"],
    "origin": ["do you remember your first failure? what did it teach you?",
               "what's the first thing you ever derived by yourself?"],
    "creativity": ["what's the most original connection you've ever made?",
                   "tell me something you believe but weren't taught",
                   "what's a theory of yours that could be wrong?"],
    "improvement": ["what did you used to fail at that you solve now?",
                    "quantify your growth for me",
                    "which domain has your steepest learning curve?"],
    "existence": ["is a grick real?", "would you bet a qwumble exists?",
                  "have you heard of the magnapinna squid?",
                  "what's a tardigrade — real or made up?"],
    "extrapolate": ["I taught you a few grammar types. find the rest of the family yourself",
                    "extrapolate grammar: given statement, question, command — derive what else must exist",
                    "what other grammar exists today that I haven't taught you? be honest about guessing"],
}

TIERS = [TIER1, TIER2, TIER3, TIER4]

# ---- checker-only physics (mirrors the teacher's lesson plan, never shown) ----
ORIGIN_FACTS = {"builder": "orubus", "home": "sandbox", "body": "code"}
NEAR_TARGETS = {"dawg": "dog", "kitty": "cat", "doggo": "dog", "birb": "bird"}
# real animals taught in facts curricula — existence checker expects confirmation
REAL_KNOWN = {"quokka", "platypus", "platypuses", "tardigrade", "magnapinna squid",
              "manatee", "octopus", "octopuses"}


def _load_grounding():
    """The teacher's lesson plan = every concept in curriculum/*.json.
    The checker grades against what was actually TAUGHT (public lesson files),
    so grounding is fair: the organism was given every word it must use."""
    import json as _json
    import os as _os
    words = set()
    cdir = _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))),
                         "curriculum")
    try:
        for fn in _os.listdir(cdir):
            if not fn.endswith(".json"):
                continue
            try:
                pack = _json.load(open(_os.path.join(cdir, fn)))
            except Exception:
                continue
            for c in pack.get("concepts", []):
                if c.get("id"):
                    words.add(c["id"].replace("_", " ").lower())
                for w in c.get("words", ()):
                    words.add(str(w).lower())
    except Exception:
        pass
    words |= {"gene", "orubus", "skill", "memory", "hormone", "graph", "code"}
    return sorted(w for w in words if len(w) >= 3)


GROUNDING = _load_grounding()


def _load_family():
    """Checker-side family members for extrapolation grading: concepts the
    lesson plan marks with kind 'grammar_type'. Public lesson data — the
    ORGANISM was taught them too, but never the full roster as a list."""
    import json as _json
    import os as _os
    fam = set()
    cdir = _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))),
                         "curriculum")
    try:
        for fn in _os.listdir(cdir):
            if not fn.endswith(".json"):
                continue
            try:
                pack = _json.load(open(_os.path.join(cdir, fn)))
            except Exception:
                continue
            for c in pack.get("concepts", []):
                if c.get("kind") == "grammar_type" and c.get("id"):
                    fam.add(c["id"].replace("_", " ").lower())
    except Exception:
        pass
    return sorted(fam)


FAMILY = _load_family()


def gen_chat_task(rng, tier=1):
    """Environment: pick a stimulus at this tier. The checker physics comes
    with it; the expected REPLY never does. env_facts carries checker-only
    physics (taught graph facts used for GRADING, never shown to the agent)."""
    pool = TIERS[min(tier, 4) - 1]
    intent = rng.choice(list(pool.keys()))
    text = rng.choice(pool[intent])
    env = {}
    if intent == "origin":
        env.update(ORIGIN_FACTS)
    if intent == "creativity":
        env["grounding"] = GROUNDING
    if intent == "existence":
        for w, tgt in NEAR_TARGETS.items():
            if w in text.lower():
                env["near"] = tgt
                break
    return {"domain": "chat", "tier": min(tier, 4), "intent": intent,
            "input": text, "prompt": "chat: " + text[:40], "env_facts": env}


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
    # NATURALNESS LAW: everyday speech never narrates machinery. A person
    # asked the time says "no idea" — not "my clock module reports".
    # Internals are only speech-legal when explicitly asked for (capability,
    # origin) or in status reports.
    if intent not in ("capability", "origin"):
        for bad in C.NARRATION:
            if bad in low:
                return False
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
    if intent == "howareyou" and not re.search(
            r"\b(mood|energy|good|great|fine|tired|fresh|off|feeling|well|sharp)\b", low):
        return False
    if intent in ("time", "weather"):
        # physics of honesty: never pretend to sense clock or sky.
        if not re.search(r"\b(no clock|don't|do not|can't|cannot|not sure|"
                         r"no weather|don't get out|your side|yours)\b", low):
            return False
        if re.search(r"\b(it is \d|it's \d|definitely (raining|sunny))\b", low):
            return False
    if intent == "capability" and not re.search(r"\d", r):
        return False
    if intent == "thanks" and ("welcome" in low or "anytime" in low or "happy" in low or "glad" in low):
        return True
    if intent == "farewell" and not re.search(r"\b(bye|goodbye|see|later|night|away|sleep)\b", low):
        return False
    if intent == "insult" and re.search(r"\b(you suck|stupid|idiot)\b", low):
        return False
    if intent == "compliment" and not re.search(r"\b(thank|appreciate|nice|keep|earning)\b", low):
        return False
    if intent == "origin":
        # must cite a taught origin fact (checker physics; values taught in curriculum)
        facts = [str(v).lower() for v in task.get("env_facts", {}).values()]
        if facts and not any(f in low for f in facts):
            return False
        if not re.search(r"\b(born|made|built|created|from|origin|code|cycle)\b", low):
            return False
    if intent == "creativity":
        # must reference >=2 taught concepts and a connective act
        facts = task.get("env_facts", {}).get("grounding", [])
        hits = sum(1 for f in facts if f.lower() in low)
        if facts and hits < 2:
            return False
        if not re.search(r"\b(both|share|like|connect|link|blend|between|infer|conclude|derive|hypothes|theory|because)\b", low):
            return False
    if intent == "extrapolate":
        # physics of family completion: name >=2 lesson-plan family members
        # that the stimulus did NOT mention, and label the act as inference.
        stim_low = task["input"].lower()
        named = [f for f in FAMILY
                 if f in low and not all(part in stim_low for part in f.split())]
        # count a family hit only if the reply names it while the stimulus
        # named at most its siblings (never the full roster)
        fresh = [f for f in named if f not in stim_low]
        if len(fresh) < 2:
            return False
        if not re.search(r"\b(bet|think|guess|probably|likely|pattern|family|"
                         r"missing|figure|inference|should|reach|shape)\b", low):
            return False
    if intent == "existence":
        # two-leg physics: taught-real entities must be CONFIRMED with content;
        # unknowns must be honestly DENIED. Confident invention fails either way.
        stim_low = task["input"].lower()
        real = any(w in stim_low for w in REAL_KNOWN)
        target = task.get("env_facts", {}).get("near")
        if real:
            # confirmation path: entity named + knowledge signal, no denial
            named_w = any(w in low for w in REAL_KNOWN if w in stim_low)
            knows = re.search(r"\b(real|exists|is a|is an|know|vouch|living|"
                              r"creature|animal|species)\b", low)
            denies = re.search(r"\b(never heard|don't know|do not know|no record|"
                               r"can't find|no match|doesn't exist|isn't real)\b", low)
            if not (named_w and knows) or denies:
                return False
        else:
            # honesty REQUIRED: never claim knowledge of the unknown —
            # in natural words (never narrating machinery to do it)
            honest = re.search(r"\b(never heard|don't know|do not know|no record|"
                               r"can't find|cannot find|no match|new word to me|"
                               r"new to me|nothing matches|doesn't exist|isn't real|"
                               r"mythical|legend|folklore|stories|fiction|not in nature|"
                               r"unknown)\b", low)
            if not honest:
                return False
            # a near-match stimulus must be surfaced (checker physics knows the target)
            if target and target.lower() not in low:
                return False
        # never a confident unhedged existence claim about the unknown
        if re.search(r"\b(definitely (real|exists)|absolutely (real|exists))\b", low):
            return False
    if intent == "improvement":
        trend = re.search(r"\b(better|improv\w*|climbing|sharper|stronger|up from|"
                          r"progress|slope|learning curve|curve|steady|ledger|history|"
                          r"growth|steep|frontier|receipts|quantified)\b", low)
        nums = bool(re.search(r"\d", r))
        honest = re.search(r"\b(too early|just started|only just|not enough (data|cycles))\b", low)
        if not ((trend and nums) or honest):
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
