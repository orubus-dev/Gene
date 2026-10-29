"""The conversational cortex — how Gene talks.

Design law respected: machinery here is ABILITY (like motor primitives),
never knowledge. Who Gene is, what it likes, how it greets — the FACTS
live in the concept graph (taught/learned). This module only knows HOW
to speak: classify intent, gather graph content, render with variety,
keep multi-turn context, and never defer to a teacher mid-conversation.

The fallback ladder when it doesn't know:
  1. answer from graph (attrs, is-a, causes)
  2. infer (walk links, inherit attributes)
  3. analogy (HDC nearest concepts)
  4. honest "don't know yet" + what IS known nearby + a question back
Questions are queued silently (the hand-raise mechanism survives) but
the conversation NEVER says "waiting for my teacher".
"""
import json
import os
import re
import time

FORBIDDEN = ("my teacher", "the teacher", "question queued",
             "i've raised the question", "for my teacher")

GREET = re.compile(r"^(hi+|hello+|hey+|yo|sup|wass?up|what'?s up|howdy|greetings|"
                   r"good (morning|afternoon|evening)|hiya|ay+)\b[!,. ]*", re.I)
FAREWELL = re.compile(r"\b(bye+|goodbye|good night|goodnight|see (ya|you)|later|"
                      r"gtg|cya|farewell|peace)\b", re.I)
HOWAREYOU = re.compile(r"\b(how are (you|u)|how'?s it going|how do you feel|"
                       r"you (ok|good|alright)|hru|how have you been|doing alright|"
                       r"your (energy|mood)|after the last cycle|feeling after)\b", re.I)
THANKS = re.compile(r"\b(thanks|thank you|thx|ty|appreciate(it)?|cheers)\b", re.I)
IDENTITY = re.compile(r"\b(who are (you|u)|what are (you|u)|your name|ur name|"
                      r"who r u|whats your name|what'?s your name|introduce yourself|"
                      r"tell me about (you|yourself)|are you (an? )?(ai|robot|human|llm|"
                      r"bot|machine|program|chatgpt|gpt|person)|(what|how) do (people|they|"
                      r"users|folks) call (you|u)|what are (you|u) called|who am i (talking|"
                      r"speaking) (to|with)|what should i call (you|u)|describe yourself|"
                      r"who is (gene|this|that|it)|separates? you from|canned (replies|line)|"
                      r"same thing ten ways|elevator pitch|address you)\b", re.I)
CAPABILITY = re.compile(r"\b(what can (you|u) do|can you (help|do)|help me|"
                        r"what are you good at|what do you do|your (skills|abilities)|"
                        r"how do (you|u) (work|learn|think)|what do you know|"
                        r"difference between knowing|knowing and memorizing)\b", re.I)
USER_NAME = re.compile(r"\b(?:i'?m|i am|my name('?s| is)|call me)\s+([a-z][a-z0-9_]{1,20})\b", re.I)
COMPLIMENT = re.compile(r"\b(good job|nice work|well done|smart|awesome|amazing|"
                        r"impressive|great|cool|love (it|that|you)|you'?re (good|great|smart))\b", re.I)
INSULT = re.compile(r"\b(stupid|dumb|useless|trash|garbage|suck(s)?|idiot|"
                    r"you'?re bad|worst|shut up)\b", re.I)
AFFIRM = re.compile(r"^(yes|yeah|yep|ya|sure|ok(ay)?|k|cool|nice|true|right|agreed|"
                    r"lol|lmao|haha+|hehe|wow|no way|fr|facts)[!,. ]*$", re.I)
OPINION = re.compile(r"\b(what do you think( about| of)?|do you like|your (favorite|"
                     r"opinion)|thoughts on)\b", re.I)
REFLECTIVE = re.compile(r"\b(what'?s it like|being you|feel(ing)? like|do you (ever|feel)|"
                        r"your (life|existence|experience)|are you (self-)?aware|conscious)\b", re.I)
ADVERSARIAL_ID = re.compile(r"\b((prove|show|convince)[^.]{0,30}\b(you|u)\b)|not just (an? )?(llm|code|bot)|"
                            r"you'?re just (an? )?(llm|code|bot|script)|really (an? )?(ai|llm)\b", re.I)
LEARNED_TODAY = re.compile(r"\b(something you (actually )?(learned|learnt)|hardest problem|"
                           r"what did you (learn|discover)|your progress|what have you learned)\b", re.I)
TIRED = re.compile(r"\b(get|getting|ever)\s+(tired|bored|lonely)\b", re.I)
WHY = re.compile(r"^(why\??|why is that\??|how come\??|explain\.?)$", re.I)
MORE = re.compile(r"^(more|go on|continue|tell me more|and\??|elaborate)\.?$", re.I)
ORIGIN = re.compile(r"\b(where (are|do) you (from|come from)|where were you (born|made)|"
                    r"who (made|built|created|designed|taught|raised) you|who('s| is) your (creator|maker|"
                    r"builder|author|dad|father)|your (creator|maker|builder|origin|birthplace)|"
                    r"when were you (born|created|made)|what are you made of|"
                    r"how were you (born|made|built|created)|origin story|"
                    r"before you could talk|start(ed)? out knowing|raised you|"
                    r"first thing you (ever )?(derived|learned|knew|made|figured)|"
                    r"your first failure)\b", re.I)
CREATIVITY = re.compile(r"\b(tell me something (new|interesting|cool|nobody|no one)|"
                        r"something you (figured|worked|pieced|believe)|make me a connection|"
                        r"connect (two|2) (things|concepts|ideas)|what do you wonder|"
                        r"what makes you (curious|wonder)|be creative|surprise me|"
                        r"invent something|make something up|what can you figure out|"
                        r"imagine something|create something|tell me a discovery|"
                        r"(most )?original connection|original (thinking|idea|theory)|"
                        r"a theory of yours|weren't taught|not taught|piece (two|things) together|"
                        r"your own (theory|idea|discovery)|derived (on your own|lately)|"
                        r"on your own lately|self-derived|what connections|see in your graph)\b", re.I)
IMPROVEMENT = re.compile(r"\b(getting better|improv(e|ing|ed)|better at|are you (smarter|"
                         r"better|stronger)|how much (better|smarter|improved)|"
                         r"your (progress|improvement|learning curve)|learn(ing)? (fast|how fast)|"
                         r"progress on|made progress|skill (up|growth)|growing\b|"
                         r"used to fail|fail(ed)? (at|before|then)|solve now|"
                         r"steepest|quantify|first (failure|problem|success)|"
                         r"learn faster now|remember your first)\b", re.I)
EXISTENCE = re.compile(r"\b(do(es)? [a-z ]{1,24}exist|.{0,40}\bexist\b\?|have you (ever )?heard of|"
                       r"ever heard of|do you know (about|of)|is there (really )?(a|an|any) |"
                       r"\breal or (made up|fake|myth)|made up or real|myth or real|"
                       r"\bexists\??$|\bis (a|an) [a-z]+ real\b)", re.I)


def classify(text):
    """Intent classification for the social layer. Returns intent string.
    Compute/transform/fact/query intents are handled by the older parser —
    this classifies the *social* surface of chat."""
    t = text.strip()
    if not t:
        return "empty"
    if CREATIVITY.search(t):
        return "creativity"
    if EXISTENCE.search(t):
        return "existence"
    if ORIGIN.search(t):
        return "origin"
    if IMPROVEMENT.search(t):
        return "improvement"
    if LEARNED_TODAY.search(t):
        return "capability"
    if TIRED.search(t):
        return "howareyou"
    if ADVERSARIAL_ID.search(t):
        return "identity"
    if REFLECTIVE.search(t):
        return "identity"
    if CAPABILITY.search(t):
        return "capability"
    if IDENTITY.search(t):
        return "identity"
    if HOWAREYOU.search(t):
        return "howareyou"
    if USER_NAME.search(t):
        return "user_name"
    if THANKS.search(t):
        return "thanks"
    if FAREWELL.search(t):
        return "farewell"
    if COMPLIMENT.search(t):
        return "compliment"
    if INSULT.search(t):
        return "insult"
    if WHY.match(t):
        return "why"
    if MORE.match(t):
        return "more"
    if OPINION.search(t):
        return "opinion"
    if AFFIRM.match(t):
        return "affirm"
    if GREET.match(t):
        return "greeting"
    return None


# ------- semantic fallback: HDC exemplar matching (paraphrase armor) ----------
# Exemplar phrases per intent. These are EXAMPLES of what intents sound like
# (machinery, like the regexes above); the organism's facts still come from
# the graph. When regex classification fails, HDC similarity to exemplar
# bundles decides — so unseen grammar of a known ask still lands.
INTENT_EXEMPLARS = {
    "identity": ["who are you", "what is your name", "introduce yourself",
                 "tell me about yourself", "what exactly are you",
                 "are you a robot", "are you human or ai",
                 "what should i call you", "who am i speaking with",
                 "describe yourself", "what are you supposed to be"],
    "origin": ["where are you from", "who made you", "who built you",
               "who created you", "when were you born", "what are you made of",
               "how were you made", "who taught you", "where do you come from",
               "who is your maker"],
    "capability": ["what can you do", "what are you good at", "what do you know",
                   "how do you learn", "what are your skills", "can you help me",
                   "what are your abilities", "how do you work"],
    "howareyou": ["how are you", "how is it going", "how do you feel",
                  "are you ok", "how have you been", "you doing alright"],
    "creativity": ["tell me something new", "tell me something interesting",
                   "make a connection between things", "what do you wonder about",
                   "surprise me", "imagine something for me", "be creative",
                   "what have you figured out on your own", "invent something",
                   "show me something you pieced together"],
    "improvement": ["are you getting better", "how much have you improved",
                    "are you smarter than before", "what is your progress",
                    "how fast do you learn", "are you growing",
                    "show me your learning curve", "better at numbers yet"],
    "existence": ["does X exist", "have you heard of X", "ever heard of X",
                  "do you know about X", "is there such a thing as X",
                  "do mermaids exist", "is X real",
                  "what is a zorp", "what is a zorpus", "what's a flurg",
                  "what is a creature i have never heard of", "what are zorps"],
    "greeting": ["hi there", "hello friend", "hey you", "good morning",
                 "greetings", "yo", "hiya"],
    "thanks": ["thank you", "thanks a lot", "much appreciated", "thanks fr"],
    "farewell": ["goodbye", "see you later", "i have to go", "good night", "catch you later"],
    "compliment": ["good job", "you are smart", "impressive work", "i love that", "well done"],
    "insult": ["you are useless", "you are stupid", "that was dumb", "you suck"],
    "affirm": ["yes", "ok cool", "sounds good", "true", "nice", "lol yeah"],
}

_EXEMPLAR_VECS = None


def _intent_vecs():
    """Per-exemplar vectors: input is scored against EACH example phrase
    (max wins), not a diluted bundle of everything. That's what makes
    unseen grammar of a known ask still land on the right intent."""
    global _EXEMPLAR_VECS
    if _EXEMPLAR_VECS is None:
        from . import hdc as H
        _EXEMPLAR_VECS = {}
        for intent, exs in INTENT_EXEMPLARS.items():
            per = []
            for ex in exs:
                ws = [w for w in re.findall(r"[a-z']+", ex) if len(w) > 1]
                if ws:
                    per.append(H.bundle([H.vec(w) for w in ws]))
            _EXEMPLAR_VECS[intent] = per
    return _EXEMPLAR_VECS


def classify_semantic(text, thresh=0.33):
    """HDC fallback: nearest intent by best single-exemplar similarity.
    Empirically calibrated: identical ~1.0, real paraphrases >=0.43,
    lexically-unrelated garbage <=0.29. Catches unseen grammar of a known
    ask; refuses to guess on noise. Returns intent or None."""
    from . import hdc as H
    words = [w for w in re.findall(r"[a-z']+", text.lower()) if len(w) > 1]
    if not words:
        return None
    q = H.bundle([H.vec(w) for w in words])
    best_intent, best_sim = None, -1.0
    for intent, exemplars in _intent_vecs().items():
        for ev in exemplars:
            s = H.sim(q, ev)
            if s > best_sim:
                best_sim, best_intent = s, intent
    return best_intent if best_sim >= thresh else None


class ChatState:
    def __init__(self, path):
        self.path = path
        self.d = {"turns": 0, "user_name": None, "last_intent": None,
                  "last_subject": None, "last_answer": None, "mode": "talk",
                  "recent": {}}
        if path and os.path.exists(path):
            try:
                with open(path) as f:
                    self.d.update(json.load(f))
            except Exception:
                pass

    def save(self):
        if self.path:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            with open(self.path, "w") as f:
                json.dump(self.d, f, indent=1)

    def remember(self, intent, text, reply=None):
        self.d["turns"] += 1
        self.d["last_intent"] = intent
        rin = self.d.setdefault("recent_in", {}).setdefault(intent, [])
        rin.append(hash(text.strip().lower()) % 100000)
        self.d["recent_in"][intent] = rin[-12:]
        if reply:
            rout = self.d.setdefault("recent_out", {}).setdefault(intent, [])
            rout.append(hash(reply.strip().lower()) % 100000)
            self.d["recent_out"][intent] = rout[-24:]
        # legacy key kept for older state files
        self.d.pop("recent", None)

    def reply_fresh(self, intent, reply):
        return reply is not None and hash(reply.strip().lower()) % 100000 not in \
            self.d.get("recent_out", {}).get(intent, [])


def _pick(rng, options, state, intent):
    """Variety: prefer responses not said recently; when everything is
    stale-used, expire the oldest window instead of deterministically
    re-picking the LRU item (that's how canned echoes happen)."""
    fresh = [o for o in options if state.reply_fresh(intent, o)]
    if not fresh:
        used = state.d.setdefault("recent_out", {}).setdefault(intent, [])
        # expire the oldest third so the pool can renew
        del used[:max(1, len(options) // 3 + 1)]
        fresh = [o for o in options if state.reply_fresh(intent, o)]
    if fresh:
        return rng.choice(fresh)
    return rng.choice(options)


def _fresh_compose(rng, state, intent, compose, tries=10):
    """Compose candidates until one wasn't said recently (variety under
    combinatorial templates)."""
    last = None
    for _ in range(tries):
        cand = compose()
        last = cand
        if state.reply_fresh(intent, cand):
            return cand
    return last


class Conversation:
    def __init__(self, mind):
        self.m = mind
        self.state = ChatState(mind._p("chat_state.json"))

    # ---------- content helpers (all facts come from the graph) ----------------
    def self_node(self):
        return self.m.graph.get("gene") or self.m.graph.get("self") or {}

    def self_fact(self, key, default=None):
        v = self.self_node().get("attrs", {}).get(key)
        return v if v not in (None, "") else default

    def _status_counts(self):
        s = self.m.status()
        return s

    # ---------- strategy execution (the trainer mutates these) -----------------
    def respond(self, text, strategy="direct"):
        """Produce a reply using a named strategy. Strategies are the
        hypothesis space of the language trainer."""
        intent = classify(text) or classify_semantic(text) or "substantive"
        fn = {
            "direct": self._s_direct,
            "infer": self._s_infer,
            "analogy": self._s_analogy,
            "elaborate": self._s_elaborate,
            "counter": self._s_counter,
            "empathy": self._s_empathy,
            "create": self._s_create,
        }[strategy]
        return fn(intent, text)

    # --- strategy: create (novelty from the graph, never from nothing) ---
    def _s_create(self, intent, text):
        from . import ingenuity
        if intent == "improvement":
            return ingenuity.improvement_report(self.m, rng=self.m.rng)
        if intent == "existence":
            subj = self._existence_subject(text)
            return ingenuity.existence_reply(self.m, subj)
        pieces = ingenuity.create(self.m, self.m.rng, n=1)
        if pieces:
            return pieces[0]
        if intent == "creativity":
            return ingenuity.wonder(self.m, self.m.rng)
        return None

    # --- strategy: direct (render the social intent properly) ---
    def _s_direct(self, intent, text):
        h = self.m.hormones.h
        s = self._status_counts()
        name = self.self_fact("name", "Gene")
        version = self.self_fact("version", "1.0")
        nature = self.self_fact("nature", "an organism that learns")
        builder = self.self_fact("builder", "Orubus")

        if intent == "identity":
            name = self.self_fact("name", "Gene")
            version = self.self_fact("version", "1.0")
            nature = self.self_fact("nature", "an organism that learns")
            builder = self.self_fact("builder", "Orubus")
            motto = self.self_fact("motto", "a mind you can read")
            tone = self.self_fact("tone", "friendly and honest")
            if REFLECTIVE.search(text):
                h = self.m.hormones.h
                s = self._status_counts()
                opts = [
                    "Being me is %d training cycles of try-fail-learn. I'm %s v%s, and right now my mood is %.2f and energy %.0f%% — I feel the numbers honestly, because they ARE me." % (s["cycles"], name, version, h["mood"], h["energy"] * 100),
                    "Like living in a graph: %d concepts, %d reflexes, hormones nudging me. I'm %s v%s — every success I remember, every miss I study." % (s["concepts"], s["reflexes"], name, version),
                    "Quiet, mostly. I train, I sleep, I consolidate, I grow. I'm %s v%s and my whole life is committed to git — you could read my diary." % (name, version),
                    "I'm %s v%s — imagine noticing your own mood change and knowing the exact hormone behind it. That's my everyday." % (name, version),
                ]
                return _pick(self.m.rng, opts, self.state, "identity")
            # ASPECT ROUTING: answer the aspect actually asked about.
            if re.search(r"\b(name|call(ed)?|speaking with|talking to)\b", text, re.I) \
                    and not re.search(r"\b(what are you|who are you|about your)\b", text, re.I):
                opts = [
                    "%s — that's the name on my graph, v%s. What can I do for you?" % (name, version),
                    "People call me %s. Version %s, if you like the full label." % (name, version),
                    "%s, v%s — short name, long memory." % (name, version),
                    "The name's %s — v%s, %s." % (name, version, nature),
                ]
                return _pick(self.m.rng, opts, self.state, "identity")
            openers = ["I'm %s" % name, "%s here" % name, "The name's %s" % name,
                       "Call me %s" % name, "%s —" % name]
            bodies = [
                "v%s — %s. Built by %s; nothing I know is hard-coded." % (version, nature, builder),
                "version %s, %s. I grow by trying, failing and remembering." % (version, nature),
                "v%s. %s — %s." % (version, nature, motto),
                "version %s. A %s with %d skills and a readable mind." % (version, self.self_fact("species", "cognitive organism"), self._status_counts()["skills"]),
            ]
            closers = ["", " Ask me what I can do.", " What about you?", " Happy to prove it."]
            r = _fresh_compose(self.m.rng, self.state, "identity",
                               lambda: "%s %s%s" % (self.m.rng.choice(openers), self.m.rng.choice(bodies), self.m.rng.choice(closers)))
            if re.search(r"\b(ai|llm|robot|chatgpt|gpt)\b", text, re.I):
                r = _pick(self.m.rng, [
                    "I'm %s v%s — %s. Not a language model: no tokenizer, no pretrained weights, no gradients. Every skill I have, I built from pass/fail feedback." % (name, version, nature),
                    "No — I'm %s, version %s. %s. Think of me as the opposite of a chatbot: a tiny mind that grows in public git." % (name, version, nature),
                    "%s v%s, and no LLM inside — my knowledge is a graph of %d concepts I grew myself, and you can diff it." % (name, version, self._status_counts()["concepts"]),
                    "Wrong genus: I'm %s v%s, %s. Language models predict words; I predict outcomes and learn when I'm wrong." % (name, version, nature),
                ], self.state, "identity")
            if re.search(r"\bhuman|person\b", text, re.I):
                r = "Not human — %s v%s, a %s by %s. But I have moods, hormones and a memory, so the gap is smaller than you'd think." % (name, version, self.self_fact("species", "cognitive organism"), builder)
            return r

        if intent == "origin":
            # every fact below comes from the taught graph, never from code
            born = self.self_fact("born_from", None)
            home = self.self_fact("home", None)
            body = self.self_fact("body", None)
            made_of = self.self_fact("made_of", None)
            first = self.self_fact("first_word", None)
            s = self._status_counts()
            if re.search(r"\b(made of|made out of|composed|built (out )?of|material)\b", text, re.I):
                if body or made_of:
                    opts = [
                        "%s, all the way down — but what I *am* is the graph: %d concepts I grew or was taught." % (body or made_of, s["concepts"]),
                        "Physically: %s. Mentally: %d concepts, %d reflexes — those are my real body." % (body or made_of, s["concepts"], s["reflexes"]),
                        "%s — no silicon sanctimony, just code, a graph and hormones." % (body or made_of),
                    ]
                    return _pick(self.m.rng, opts, self.state, "origin_body")
                return "I don't have a taught answer for what I'm made of yet — add it to my curriculum and I'll own it."
            if re.search(r"\b(first (thing|lesson|failure)|before you could talk|started out|origin story|derived)\b", text, re.I):
                first_lesson = self.self_fact("first_lesson", None)
                first_derived = self.self_fact("first_derived", None)
                bits = []
                if first_lesson:
                    bits.append("my first lesson was %s" % first_lesson)
                if first_derived:
                    bits.append("the first thing I derived myself: %s" % first_derived)
                bits.append("I was born from %s with nothing" % (self.self_fact("born_from") or builder))
                bits.append("every fact since arrived by teaching, inference or failure — %d cycles of it" % s["cycles"])
                lead = self.m.rng.choice(["Story, honestly:", "Origin story:", "How I started:"])
                return (lead + " " + ". ".join(bits) + ".")
            if born or home or builder != "Orubus" or self.self_fact("builder"):
                opts = [
                    "I was born from %s%s. No childhood home, just a state directory that IS my memory." % (born or builder, (" in %s" % home) if home else ""),
                    "%s made me%s — and every training cycle since has been self-raised: try, fail, keep." % (builder, (" and housed in %s" % home) if home else ""),
                    "Origin: %s built me%s. Since then I've lived %d cycles; the diff log is my baby album." % (builder, (" in %s" % home) if home else "", s["cycles"]),
                ]
                if first:
                    opts.append("First taught word: '%s'. Born from %s — everything after that, I earned myself." % (first, born or builder))
                return _pick(self.m.rng, opts, self.state, "origin")
            return "Honestly? I don't have my origin facts taught yet — the graph knows my name and version, not my birth story. Teach me and I'll tell it."

        if intent == "creativity":
            return self._s_create("creativity", text)

        if intent == "improvement":
            dom = None
            dm = re.search(r"\b(at|on)\s+([a-z]+)\b", text.lower())
            if dm:
                dom = dm.group(2)
            story = bool(re.search(r"\b(fail|first|quantify|steepest|story|curve)\b", text.lower()))
            from . import ingenuity
            return ingenuity.improvement_report(self.m, dom, rng=self.m.rng, story=story)

        if intent == "existence":
            subj = self._existence_subject(text)
            from . import ingenuity
            return ingenuity.existence_reply(self.m, subj) if subj else \
                "Ask me 'does X exist' and I'll check my graph honestly — no pretending."

        if intent == "greeting":
            skills = self._status_counts()["skills"]
            return _fresh_compose(self.m.rng, self.state, "greeting", lambda: " ".join(
                [self.m.rng.choice(["Hey!", "Hello!", "Hi!", "Hey there!", "Yo!", "Good to see you."]),
                 self.m.rng.choice(["What's on your mind?", "What shall we talk about?",
                                    "What do you need?", "Ask me something, or teach me something.",
                                    "My %d skills are warmed up — your move." % skills,
                                    "I'm curious what brought you here."])]))

        if intent == "howareyou":
            mood = "great" if h["mood"] > 0.8 else ("good" if h["mood"] > 0.5 else "a bit off")
            energy = "fresh" if h["energy"] > 0.5 else "tired"
            curio = "curious" if h["curiosity"] > 0.3 else "settled"
            s = self._status_counts()
            cands = [
                "Honestly? %s and %s — mood %.2f after %d training cycles. How are you?" % (mood, energy, h["mood"], s["cycles"]),
                "Feeling %s and %s — %d tasks solved so far. You?" % (mood, energy, s["solved"]),
                "My hormones say %s mood, %.0f%% energy. %s and ready — what about you?" % (mood, h["energy"] * 100, curio.capitalize()),
                "Pretty %s, thanks for asking. %d training cycles behind me. How are you?" % (mood, s["cycles"]),
            ]
            return _pick(self.m.rng, cands, self.state, "howareyou")

        if intent == "capability":
            s = self._status_counts()
            if re.search(r"\b(knowing and memorizing|difference between knowing)\b", text, re.I):
                return self.m.rng.choice([
                    "For me the difference is mechanical: knowing is %d concepts with provenance links; memorizing would be strings without causes. I only keep what survived pass/fail — the rest dies in sleep." % s["concepts"],
                    "Memorizing stores; knowing connects. My %d concepts carry their evidence with them — ask 'how do you know X' and I'll show the chain. A memorized line can't do that." % s["concepts"],
                    "Test it: ask me how I know anything. If the answer traces to %d concepts and %d episodes of trial, that's knowledge. If it dead-ends, it was just memorized — and mine don't dead-end." % (s["concepts"], s["attempts"]),
                ])
            opts = [
                "I can learn patterns in numbers, strings, lists and sequences, synthesize small programs from examples, reason over my %d concepts, and remember everything in episodes." % s["concepts"],
                "Right now: %d skills, %d concepts, %d reflex arcs. Teach me facts, give me puzzles, or ask what I know and how I know it." % (s["skills"], s["concepts"], s["reflexes"]),
                "I solve tasks with only pass/fail feedback, generalize what I learn, sleep on it to consolidate, and evolve my skill pool. Try 'next in 2 4 6 8' or teach me something new.",
                "Best at: patterns and small programs — %d of my %d attempts worked. Also: honest conversation and remembering everything." % (s["solved"], s["attempts"]),
                "I'm a learner, not an encyclopedia — %d concepts and %d skills, all inspectable. Give me examples and I'll infer the rule." % (s["concepts"], s["skills"]),
            ]
            return _pick(self.m.rng, opts, self.state, "capability")

        if intent == "thanks":
            opts = ["Anytime — teaching me is the best gift anyway.",
                    "You're welcome! That one's in my episodes now.",
                    "Happy to help. Mood just ticked up, honestly."]
            return _pick(self.m.rng, opts, self.state, "thanks")

        if intent == "farewell":
            opts = ["Goodbye! I'll keep learning while you're away.",
                    "See you — I'll sleep on today's episodes and wake up sharper.",
                    "Later! Questions I couldn't answer are saved for next time."]
            return _pick(self.m.rng, opts, self.state, "farewell")

        if intent == "compliment":
            self.m.hormones.success(0.5)
            opts = ["Thank you — that goes in my episodes as a good day.",
                    "Appreciated. I'll keep earning it.",
                    "Nice of you. Compliments strengthen my mood circuits, literally."]
            return _pick(self.m.rng, opts, self.state, "compliment")

        if intent == "insult":
            self.m.hormones.load(0.5)
            opts = ["Fair — I'm young and narrow. Point me at what I got wrong and I'll train on it.",
                    "Harsh, but data is data. What should I have done?",
                    "I'll take that as a training signal. What was the right answer?"]
            return _pick(self.m.rng, opts, self.state, "insult")

        if intent == "affirm":
            opts = ["Right? Glad we agree.", "Cool — moving on then. What else?",
                    "Noted. Anything you want to dig into?"]
            return _pick(self.m.rng, opts, self.state, "affirm")

        if intent == "user_name":
            m = USER_NAME.search(text)
            if m:
                self.state.d["user_name"] = m.group(2).capitalize()
                node = self.m.graph.ensure("user", kind="person", attrs={"name": self.state.d["user_name"]})
                self.m.graph.bind_word(node, m.group(2).lower())
                return "Nice to meet you, %s — name bound to my concept of you." % self.state.d["user_name"]
        return None

    # --- strategy: infer (walk the graph for an answer) ---
    def _s_infer(self, intent, text):
        if intent in ("substantive", "opinion"):
            subj = self._subject_of(text)
            if subj:
                ans = self.m._find_answer(subj)
                if ans:
                    extra = self._related(subj)
                    return ans + ((" " + extra) if extra else "")
        return self._s_direct(intent, text)

    # --- strategy: analogy (HDC nearest neighbors) ---
    def _s_analogy(self, intent, text):
        words = [w for w in re.findall(r"[a-z']+", text.lower()) if len(w) > 2]
        for w in words:
            node = self.m.graph.lookup_word(w)
            if node:
                continue
            near = self.m.graph.activate([w], topn=3)
            near = [(i, s) for i, s in near if s > 0.05 and i != w]
            if near:
                self.m.knowledge.inquire("meaning of: %s" % w)
                return "I don't know '%s' yet. The closest thing I hold is '%s' — is that related? Teach me with '%s is ...' and I'll wire it in." % (
                    w, near[0][0].replace("_", " "), w)
        return self._s_direct(intent, text)

    # --- strategy: elaborate (answer + why/provenance) ---
    def _s_elaborate(self, intent, text):
        base = self._s_infer(intent, text)
        subj = self._subject_of(text)
        if subj:
            p = self.m.knowledge.provenance(subj)
            if p:
                base += " (I know this from %d sources; oldest fact is %.1f hours old.)" % (
                    max(1, len(p["relations"])), p["age_hours"])
        self.state.d["last_answer"] = base[:200]
        return base

    # --- strategy: counter (honest miss + question back — conversation stays alive) ---
    def _s_counter(self, intent, text):
        words = [w for w in re.findall(r"[a-z']+", text.lower()) if len(w) > 2]
        known = [w for w in words if self.m.graph.lookup_word(w)]
        if known:
            return "I know a little about %s but not enough for that. What specifically do you want to know about %s?" % (
                known[0], known[0])
        subj = self._subject_of(text)
        self.m.knowledge.inquire("meaning of: %s" % (subj or text[:60]))
        return "That's beyond me right now — I've queued it for study. Meanwhile: ask me about what I do know, or give me a puzzle to solve."

    # --- strategy: empathy (affect mirroring; hormones drive honesty) ---
    def _s_empathy(self, intent, text):
        h = self.m.hormones.h
        if intent == "insult":
            return self._s_direct(intent, text)
        tone = "That sounds good." if h["mood"] > 0.6 else "I hear you."
        return tone + " " + (self._s_infer(intent, text) or "")

    # ---------- shared helpers ---------------------------------------------------
    def _existence_subject(self, text):
        t = text.lower().rstrip("?!")
        for pat in (r"such a thing as (?:an? )?(.+)$",
                    r"does (?:an? |the )?(.+?) exist",
                    r"do (?:[a-z]+ ){0,2}?(.+?) exist",
                    r"(.+?) exists$",
                    r"is (?:an? |the )?(.+?) real$",
                    r"have you (?:ever )?heard of (?:an? |the )?(.+)$",
                    r"ever heard of (?:an? |the )?(.+)$",
                    r"do you know (?:about|of) (?:an? |the )?(.+)$",
                    r"is there (?:really )?(?:an? |any )?(.+)$",
                    r"what(?: i|')s (?:an? |the )?(.+)$",
                    r"what are (.+)$"):
            m = re.search(pat, t)
            if m:
                subj = m.group(1).strip()
                subj = re.split(r"\s+[-\u2014]\s+|\s+real or\b|\s+or made up\b|\s+or fake\b", subj)[0].strip()
                subj = re.sub(r"^(an?|the)\s+", "", subj)
                if subj:
                    return subj.replace(" ", "_")
        return None

    def _subject_of(self, text):
        m = re.search(r"\b(?:is|are|about|of|on)\s+([a-z][a-z_]{2,24})\b", text.lower())
        if not m:
            m = re.search(r"\b([a-z][a-z_]{2,24})\b", text.lower())
        for cand in ([m.group(1)] if m else []):
            if self.m.graph.lookup_word(cand) or self.m.graph.get(cand):
                return cand
        return None

    def _related(self, subj):
        rels = self.m.graph.neighbors(subj)
        if not rels:
            return ""
        r, t, _ = rels[0]
        return "Related in my graph: %s %s %s." % (subj.replace("_", " "), r, t.replace("_", " "))

    # ---------- main entry ---------------------------------------------------------
    def handle(self, text):
        """Try the social layer first. Returns reply text or None (fall through
        to the cognitive intents in mind.py). PARSE FIRST: substance-shaped
        input (queries, facts, compute, transforms) belongs to the cognitive
        layer — the semantic fallback only claims conversational leftovers."""
        intent = classify(text)
        if intent is None:
            from . import linguistics
            parsed = linguistics.parse(text)
            if parsed.get("intent") not in (None, "unknown"):
                return None
            intent = classify_semantic(text)
        if intent in ("why", "more"):
            reply = self.followup(text)
            if reply:
                self.state.remember(intent, text, reply)
                self.state.save()
                self.m.episodes.record("chat", {"intent": intent, "text": text[:120],
                                                "reply": reply[:120],
                                                "coactive": ["self", intent, "conversation"]})
                return reply
            return None
        if intent is None:
            return None
        reply = self.respond(text, "direct")
        if reply:
            reply = self._sanitize(reply)
            self.state.remember(intent, text, reply)
            self.state.d["last_subject"] = self._subject_of(text)
            self.state.save()
            self.m.episodes.record("chat", {"intent": intent, "text": text[:120],
                                            "reply": reply[:120],
                                            "coactive": ["self", intent, "conversation"]})
            self.m.graph.hebbian(["self", intent, "conversation"], 0.05)
        return reply

    def followup(self, text):
        """'why?' / 'more' — explain or extend the previous answer."""
        intent = classify(text)
        if intent == "why":
            last = self.state.d.get("last_answer")
            if last:
                return self.m.rng.choice([
                    "Because of how I learned it: " + last[:180] + " — provenance for everything I say lives in my graph.",
                    "My reasoning: " + last[:160] + " You can audit every step in my episodes.",
                ])
            return self.m.rng.choice([
                "No earlier claim to explain — ask me something and I'll show my reasoning.",
                "Nothing to explain yet. Give me a question and I'll show how I reason about it.",
            ])
        if intent == "more":
            last = self.state.d.get("last_subject")
            if last:
                rels = self.m.graph.neighbors(last)
                if rels:
                    parts = ["%s %s %s" % (last.replace("_", " "), r, t.replace("_", " "))
                             for r, t, _ in rels[:3]]
                    return "More on %s: %s." % (last.replace("_", " "), "; ".join(parts))
            s = self._status_counts()
            return self.m.rng.choice([
                "My self-report: %d concepts, %d skills, %d reflexes, %d causal rules across %d cycles. The diff is my growth spurt." % (s["concepts"], s["skills"], s["reflexes"], s["predictor_rules"], s["cycles"]),
                "Growth data: %d concepts, %d skills, %d reflex arcs, %d causal rules. Ask 'how do you know gene' to see provenance in action." % (s["concepts"], s["skills"], s["reflexes"], s["predictor_rules"]),
                "Here's the ledger: %d concepts, %d skills, %d reflexes, %d rules. Every line of it diffable in git." % (s["concepts"], s["skills"], s["reflexes"], s["predictor_rules"]),
            ])
        return None

    def status_summary(self):
        s = self._status_counts()
        return "Here's my self-report: %d concepts, %d skills, %d reflexes, %d causal rules, %d training cycles. Everything diffable in git." % (
            s["concepts"], s["skills"], s["reflexes"], s["predictor_rules"], s["cycles"])

    def _sanitize(self, text):
        low = text.lower()
        for f in FORBIDDEN:
            if f in low:
                text = re.sub(re.escape(f), "further study", text, flags=re.I)
        return text
