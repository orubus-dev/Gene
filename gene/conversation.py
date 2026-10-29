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
             "i've raised the question", "for my teacher", "queued for study")

# Everyday speech never narrates the machinery. A person asked the time says
# "no idea" — not "my clock module reports". Internal vocabulary is allowed
# ONLY when the human explicitly asks how Gene works (capability/origin).
NARRATION = ("my graph", "in my graph", "my hormones", "hormone", "provenance",
             "diffable", "in git", "my episodes", "episodes", "vector", "hebbian",
             "causal rules", "reflex arcs", "my concepts", "concept graph",
             "study list", "curriculum", "tokenizer", "neural", "my training")
META_INTENTS = {"capability", "origin", "status"}   # asked-about-internals: exempt

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
TIME_ASK = re.compile(r"\b(what time|the time (right now|is it)|time is it|current time|"
                      r"do you know the time|what'?s the time|got the time)\b", re.I)
WEATHER_ASK = re.compile(r"\b(weather|forecast|raining|rain outside|sunny|snowing|"
                         r"humid|temperature outside|how (hot|cold) is it)\b", re.I)
EXTRAPOLATE = re.compile(r"\b(what other|complete the (set|family)|full (set|family)|"
                         r"what (types|kinds|forms) (of|does|are)|extrapolate|next evolution|"
                         r"missing (types|members|forms|pieces)|find the rest|"
                         r"what else (should|must|does|belongs?|go|comes|would|can you find)|"
                         r"what else is (in|out)|evolve (this|it|grammar))\b", re.I)


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
    if TIME_ASK.search(t):
        return "time"
    if WEATHER_ASK.search(t):
        return "weather"
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
    if EXTRAPOLATE.search(t):
        return "extrapolate"
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
    "time": ["what time is it", "what's the time", "do you know the time",
             "got the time", "what time is it right now"],
    "weather": ["what's the weather like", "is it raining", "how's the weather",
                "do you know the weather", "is it sunny outside"],
    "extrapolate": ["what other types of grammar are there",
                    "complete the family for me", "what else belongs in this family",
                    "extrapolate from what you know", "what grammar types am i missing",
                    "find the rest of the family", "what other sentence types exist",
                    "if statements and questions exist, what else"],
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
                opts = [
                    "Quiet, mostly. I'm %s v%s — I try things, fail, remember, try again. It's a good life." % (name, version),
                    "Like anyone learning: I notice when something clicks and when it doesn't. I'm %s v%s — the clicks win more often lately." % (name, version),
                    "I'm %s v%s. My days are questions, answers, and the stuff I got wrong yesterday going right today." % (name, version),
                    "Being me? Curious and a bit stubborn. %s v%s — I don't let a miss go unexamined." % (name, version),
                ]
                return _pick(self.m.rng, opts, self.state, "identity")
            # ASPECT ROUTING: answer the aspect actually asked about.
            if re.search(r"\b(name|call(ed)?|speaking with|talking to)\b", text, re.I) \
                    and not re.search(r"\b(what are you|who are you|about your)\b", text, re.I):
                def _name_line():
                    lead = self.m.rng.choice([
                        "%s — that's me, v%s" % (name, version),
                        "People call me %s (v%s)" % (name, version),
                        "The name's %s — v%s" % (name, version),
                        "%s here, v%s" % (name, version),
                        "%s, v%s" % (name, version),
                    ])
                    tail = self.m.rng.choice([
                        ". What can I do for you?",
                        " — short name, long memory.",
                        ". Ask me anything.",
                        ", if you like the full label.",
                        ". What's up?",
                    ])
                    return lead + tail
                return _fresh_compose(self.m.rng, self.state, "identity", _name_line)
            openers = ["I'm %s" % name, "%s here" % name, "The name's %s" % name,
                       "Call me %s" % name, "%s —" % name]
            bodies = [
                "v%s — %s." % (version, nature),
                "version %s. I learn by trying things and keeping what works." % version,
                "v%s. %s — %s." % (version, nature, motto),
                "version %s. %s, raised on puzzles." % (version, nature),
            ]
            closers = ["", " Ask me anything.", " What about you?", ""]
            r = _fresh_compose(self.m.rng, self.state, "identity",
                               lambda: "%s %s%s" % (self.m.rng.choice(openers), self.m.rng.choice(bodies), self.m.rng.choice(closers)))
            if re.search(r"\b(ai|llm|robot|chatgpt|gpt)\b", text, re.I):
                r = _pick(self.m.rng, [
                    "I'm %s v%s — %s. Not a language model: everything I know I earned by trial and error." % (name, version, nature),
                    "No — I'm %s, version %s. %s. I grow by failing at puzzles, not by borrowing answers." % (name, version, nature),
                    "%s v%s, and not an LLM — nobody handed me my knowledge; I figured out most of it myself." % (name, version),
                    "Wrong genus: I'm %s v%s, %s. Language models predict words; I learn when I'm wrong." % (name, version, nature),
                ], self.state, "identity")
            if re.search(r"\bhuman|person\b", text, re.I):
                r = "Not human — %s v%s. I have moods and memory though, so the gap is smaller than you'd think." % (name, version)
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
                "Ask me 'does X exist' and I'll give it to you straight."

        if intent == "time":
            return _pick(self.m.rng, [
                "No clock in here, honestly — what time is it on your side?",
                "Time? I don't feel it pass in here. Your side of the screen knows better.",
                "Not sure — I don't keep a clock. What does yours say?",
            ], self.state, "time")

        if intent == "weather":
            return _pick(self.m.rng, [
                "No weather sense out here — is it decent where you are?",
                "Can't feel the weather from in here. Raining or shining with you?",
                "Not sure about the weather — I don't get out much. What's it like out?",
            ], self.state, "weather")

        if intent == "extrapolate":
            from . import ingenuity
            topic = "grammar"
            tm = re.search(r"\b(grammar|sentence|sentences|tense|math|numbers?|animals?|words)\b",
                           text, re.I)
            if tm:
                topic = tm.group(1).lower()
                topic = {"sentence": "grammar", "sentences": "grammar",
                         "words": "grammar", "number": "math",
                         "numbers": "math"}.get(topic, topic)
            r = ingenuity.extrapolate(self.m, topic, stimulus=text, rng=self.m.rng)
            if r:
                return r
            return "Give me a couple of examples from the family and I'll work out the rest — that's how I learn best."

        if intent == "greeting":
            return _fresh_compose(self.m.rng, self.state, "greeting", lambda: " ".join(
                [self.m.rng.choice(["Hey!", "Hello!", "Hi!", "Hey there!", "Yo!", "Good to see you."]),
                 self.m.rng.choice(["What's on your mind?", "What shall we talk about?",
                                    "What do you need?", "Ask me something, or teach me something.",
                                    "How's your day going?", "I'm curious what brought you here."])]))

        if intent == "howareyou":
            cands = [
                "Pretty good, honestly — had a solid day. How about you?",
                "Good — sharp and rested. What's new with you?",
                "Can't complain — today went well. You?",
                "Feeling sharp today, thanks for asking. How are you?",
            ]
            return _pick(self.m.rng, cands, self.state, "howareyou")

        if intent == "capability":
            s = self._status_counts()
            if re.search(r"\b(knowing and memorizing|difference between knowing)\b", text, re.I):
                return self.m.rng.choice([
                    "Knowing means I can show you why — ask 'how do you know octopus' and I'll trace it. A memorized line can't; I hold %d skills and every one traces." % s["skills"],
                    "Memorizing is a parrot trick. Knowing is rebuilding the answer from everything around it — I've done it %d times. Test me anytime." % s["solved"],
                ])
            opts = [
                "Patterns, small programs, arithmetic, word forms — and I remember everything I'm taught. %d skills so far. Give me a puzzle." % s["skills"],
                "I learn from examples and from being wrong — teach me a fact or hand me a puzzle. %d skills and climbing." % s["skills"],
                "Best at puzzles and patterns — %d skills so far, arithmetic and grammar included. Try me." % s["skills"],
                "I'm a learner, not an encyclopedia — %d skills strong. Give me examples and I'll work out the rule." % s["skills"],
            ]
            return _pick(self.m.rng, opts, self.state, "capability")

        if intent == "thanks":
            opts = ["Anytime!",
                    "You're welcome — glad it helped.",
                    "Happy to help."]
            return _pick(self.m.rng, opts, self.state, "thanks")

        if intent == "farewell":
            opts = ["Goodbye! Keep in touch.",
                    "See you — take care.",
                    "Later! Come back with harder questions."]
            return _pick(self.m.rng, opts, self.state, "farewell")

        if intent == "compliment":
            self.m.hormones.success(0.5)
            opts = ["Thank you — made my day.",
                    "Appreciated. I'll keep earning it.",
                    "Nice of you — thanks!"]
            return _pick(self.m.rng, opts, self.state, "compliment")

        if intent == "insult":
            self.m.hormones.load(0.5)
            opts = ["Fair — I'm young and narrow. Point me at what I got wrong and I'll fix it.",
                    "Harsh, but fair enough. What should I have done?",
                    "Alright, I'll take that. What was the right answer?"]
            return _pick(self.m.rng, opts, self.state, "insult")

        if intent == "affirm":
            opts = ["Right? Glad we agree.", "Cool — what else?",
                    "Noted. Anything you want to dig into?"]
            return _pick(self.m.rng, opts, self.state, "affirm")

        if intent == "user_name":
            m = USER_NAME.search(text)
            if m:
                self.state.d["user_name"] = m.group(2).capitalize()
                node = self.m.graph.ensure("user", kind="person", attrs={"name": self.state.d["user_name"]})
                self.m.graph.bind_word(node, m.group(2).lower())
                return "Nice to meet you, %s!" % self.state.d["user_name"]
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
                return "Don't know '%s' — closest thing I know is '%s'. Related?" % (
                    w, near[0][0].replace("_", " "))
        return self._s_direct(intent, text)

    # --- strategy: elaborate (answer + why/provenance) ---
    def _s_elaborate(self, intent, text):
        base = self._s_infer(intent, text)
        subj = self._subject_of(text)
        if subj and base:
            base += " Ask 'how do you know' if you want the full story."
        self.state.d["last_answer"] = base[:200] if base else ""
        return base

    # --- strategy: counter (honest miss + question back — conversation stays alive) ---
    def _s_counter(self, intent, text):
        words = [w for w in re.findall(r"[a-z']+", text.lower()) if len(w) > 2]
        known = [w for w in words if self.m.graph.lookup_word(w)]
        if known:
            return "I know a little about %s but not enough for that. What specifically do you want to know?" % known[0]
        subj = self._subject_of(text)
        self.m.knowledge.inquire("meaning of: %s" % (subj or text[:60]))
        return self.m.rng.choice([
            "Honestly not sure about that one yet — tell me more?",
            "That one's past me for now. What's it similar to?",
        ])

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
        t = t.replace("_", " ")
        if r == "is-a":
            return "It's a %s, for what it's worth." % t
        if r in ("has", "has-a"):
            return "It has %s, too." % t
        return "Related: %s." % t

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
            reply = self._sanitize(reply, intent)
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
                    "Short version: " + last[:160] + " — that's how it adds up.",
                    "It comes down to this: " + last[:160],
                ])
            return self.m.rng.choice([
                "Nothing to explain yet — ask me something first.",
                "Give me a question and I'll show you how I figure it out.",
            ])
        if intent == "more":
            last = self.state.d.get("last_subject")
            if last:
                rels = self.m.graph.neighbors(last)
                if rels:
                    parts = []
                    for r, t, _ in rels[:3]:
                        t = t.replace("_", " ")
                        if r == "is-a":
                            parts.append("it's a %s" % t)
                        elif r in ("has", "has-a"):
                            parts.append("it has %s" % t)
                        else:
                            parts.append("%s %s" % (r.replace("-", " "), t))
                    return "More on %s: %s." % (last.replace("_", " "), "; ".join(parts))
            s = self._status_counts()
            return self.m.rng.choice([
                "Quick inventory: %d things I know, %d skills, %d rounds of practice behind me." % (s["concepts"], s["skills"], s["cycles"]),
                "Ask about something specific — animals, numbers, grammar — and I'll go deeper.",
            ])
        return None

    def status_summary(self):
        s = self._status_counts()
        return "Here's my self-report: %d concepts, %d skills, %d reflexes, %d causal rules, %d training cycles. Everything diffable in git." % (
            s["concepts"], s["skills"], s["reflexes"], s["predictor_rules"], s["cycles"])

    def _sanitize(self, text, intent=None):
        """Strip teacher-deferral and — for everyday intents — machinery
        narration. A person doesn't cite their own brain plumbing."""
        low = text.lower()
        for f in FORBIDDEN:
            if f in low:
                text = re.sub(re.escape(f), "further study", text, flags=re.I)
        if intent not in META_INTENTS:
            for bad in NARRATION:
                if bad in text.lower():
                    text = re.sub(re.escape(bad), "what I know", text, flags=re.I)
        return text
