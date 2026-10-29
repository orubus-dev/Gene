"""The artificial brain — Gene's own head, modeled in 3D.

Orubus's mad-science directive: "build an artificial brain in the
literal sense — 3D scans of human brains, animal brains, merged into
one; simulate emotions, chemical reactions; a brain simulated in a 3D
environment built into the graph; replicate everything the human brain
has — emotions, memory, every single thing."

What this module IS:
  * an anatomical substrate — her own regions laid out in 3D, each wired
    to the REAL subsystem that plays that role in her (hippocampus ->
    episodic memory, amygdala -> emotional memory, hypothalamus ->
    endocrine, cerebellum -> reflexes, ...). Events in her actual mind
    light up the actual regions. Nothing simulated about the wiring.
  * neurochemistry — nine neurotransmitters with event-driven secretion
    and decay toward baseline (the chemical layer under the endocrine
    scalars she already had).
  * emotions as attractors — taught prototypes (kind "emotion", chemical
    signatures) classify the current chemical state; feelings then bond
    into emotional memory.
  * a 3D voxel field — species scans (taught: human, mouse, octopus,
    crow, dolphin, with region emphases + weights) merge into ONE brain
    by weighted superposition, the way a scanner overlays volumes.

What this module is NOT: a store of facts. Region roles, species data,
emotion signatures all come from the graph/pack. Delete the teaching and
the brain still ticks — it just knows less about what it is.
"""
import json
import math
import os
import time

# ---- her own anatomy (machinery: the body plan this mind runs on) ----------
REGIONS = {
    #  id            position (x,y,z in unit head)   radius   wired subsystem
    "prefrontal":   ((0.50, 0.78, 0.55), 0.20, "working"),
    "cortex":       ((0.50, 0.62, 0.50), 0.34, "graph"),
    "motor":        ((0.50, 0.70, 0.30), 0.16, "skills"),
    "broca":        ((0.22, 0.62, 0.44), 0.12, "speech"),
    "wernicke":     ((0.78, 0.60, 0.46), 0.12, "language"),
    "visual":       ((0.50, 0.24, 0.42), 0.16, "reading"),
    "auditory":     ((0.78, 0.44, 0.60), 0.12, "listening"),
    "hippocampus":  ((0.36, 0.42, 0.50), 0.11, "episodic"),
    "amygdala":     ((0.64, 0.40, 0.52), 0.09, "emotion"),
    "hypothalamus": ((0.50, 0.40, 0.48), 0.08, "endocrine"),
    "thalamus":     ((0.50, 0.48, 0.50), 0.10, "attention"),
    "basal_ganglia": ((0.62, 0.50, 0.38), 0.12, "predictor"),
    "cerebellum":   ((0.50, 0.26, 0.22), 0.16, "reflexes"),
    "brainstem":    ((0.50, 0.18, 0.48), 0.09, "life"),
}
GRID = 16                      # 16^3 voxels — cheap and honest
RAMP = " .:-=+*#%@"

# ---- her body chemistry (machinery, like the endocrine scalars) -------------
CHEM_BASELINE = {
    "dopamine": 0.30,        # reward / motivation
    "serotonin": 0.45,       # mood stability
    "norepinephrine": 0.25,  # alertness
    "cortisol": 0.15,        # stress
    "oxytocin": 0.25,        # bonding
    "acetylcholine": 0.30,   # learning signal
    "gaba": 0.40,            # calm / inhibition
    "endorphin": 0.20,       # ease after effort
    "glutamate": 0.35,       # excitation / plasticity
}
DECAY = 0.18                   # per step toward baseline (fraction of gap)

# event -> (chemical, delta) Secretion table — the physiology of her body.
SECRETION = {
    "success":    {"dopamine": +0.14, "serotonin": +0.06, "endorphin": +0.05},
    "failure":    {"cortisol": +0.10, "norepinephrine": +0.06, "dopamine": -0.04},
    "effort":     {"acetylcholine": +0.07, "glutamate": +0.05, "cortisol": +0.02},
    "learn":      {"acetylcholine": +0.12, "glutamate": +0.08},
    "threat":     {"norepinephrine": +0.16, "cortisol": +0.12},
    "social":     {"oxytocin": +0.12, "serotonin": +0.04},
    "novel":      {"norepinephrine": +0.08, "dopamine": +0.05},
    "rest":       {"gaba": +0.14, "cortisol": -0.10, "serotonin": +0.05},
    "recall":     {"acetylcholine": +0.05, "hippocampus": 0},
}


class Chemistry:
    """Nine scalars, event-driven secretion, exponential decay home."""

    def __init__(self, state=None):
        self.h = dict(CHEM_BASELINE)
        if state:
            self.h.update({k: float(v) for k, v in state.items() if k in CHEM_BASELINE})
        self._clamp()

    def _clamp(self):
        for k in self.h:
            self.h[k] = max(0.0, min(1.0, self.h[k]))

    def event(self, kind):
        for chem, dv in SECRETION.get(kind, {}).items():
            if chem in self.h:
                self.h[chem] += dv
        self._clamp()

    def step(self):
        """One heart-beat of homeostasis."""
        for k, base in CHEM_BASELINE.items():
            self.h[k] += DECAY * (base - self.h[k])
        self._clamp()

    def emotion(self, graph):
        """Nearest taught emotion prototype (kind 'emotion', ch_* attrs).
        Untaught chemistry classifies as 'resting' — honest."""
        protos = []
        for n in (graph.nodes.values() if graph else []):
            if n.get("kind") != "emotion":
                continue
            sig = {}
            for k, v in (n.get("attrs") or {}).items():
                if k.startswith("ch_") and k[3:] in CHEM_BASELINE:
                    try:
                        sig[k[3:]] = float(v)
                    except Exception:
                        pass
            if len(sig) >= 2:
                protos.append((n["id"], sig, [w for w in (n.get("words") or [])]))
        if not protos:
            return None, 0.0
        best, best_d = None, 1e9
        for eid, sig, words in protos:
            d = 0.0
            for k, base in CHEM_BASELINE.items():
                d += (self.h[k] - sig.get(k, base)) ** 2
            if d < best_d:
                best, best_d = (eid, words), d
        name = (best[1][0] if best[1] else best[0]) if best else None
        conf = max(0.0, 1.0 - math.sqrt(best_d) / 1.2)
        return name, round(conf, 2)

    def feed_endocrine(self, hormones):
        """Chemistry is the substrate under the four hormone scalars."""
        h = hormones.h
        h["mood"] = max(0.0, min(1.0, 0.5 * h["mood"] + 0.5 * (
            0.6 * self.h["serotonin"] + 0.4 * self.h["dopamine"])))
        h["energy"] = max(0.0, min(1.0, 0.7 * h["energy"] + 0.3 * (
            1.0 - self.h["cortisol"])))
        h["curiosity"] = max(0.0, min(1.0, 0.7 * h["curiosity"] + 0.3 * (
            0.5 * self.h["norepinephrine"] + 0.5 * self.h["dopamine"])))


class Brain:
    """Owns chemistry + the 3D field + region activations for this mind."""

    def __init__(self, mind):
        self.m = mind
        self.path = mind._p("brain.json")
        state = {}
        if os.path.exists(self.path):
            try:
                with open(self.path) as f:
                    state = json.load(f)
            except Exception:
                state = {}
        self.chem = Chemistry(state.get("chem"))
        self.activation = {rid: float(v) for rid, v in
                           (state.get("activation") or {}).items()
                           if rid in REGIONS}
        self.ticks = int(state.get("ticks", 0))
        self.field_sum = float(state.get("field_sum", 0.0))
        self.species = state.get("species", [])
        self._field = None

    # ---------- persistence -----------------------------------------------------
    def save(self):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, "w") as f:
            json.dump({"chem": self.chem.h, "activation": self.activation,
                       "ticks": self.ticks, "field_sum": round(self.field_sum, 3),
                       "species": self.species}, f, indent=1)

    # ---------- the 3D field ------------------------------------------------------
    def _bump(self, grid, pos, radius, weight):
        (cx, cy, cz) = pos
        r = max(radius, 0.05)
        lo = [max(0, int((c - r) * GRID)) for c in (cx, cy, cz)]
        hi = [min(GRID - 1, int((c + r) * GRID) + 1) for c in (cx, cy, cz)]
        for ix in range(lo[0], hi[0] + 1):
            for iy in range(lo[1], hi[1] + 1):
                for iz in range(lo[2], hi[2] + 1):
                    dx, dy, dz = (ix + 0.5) / GRID - cx, (iy + 0.5) / GRID - cy, \
                                 (iz + 0.5) / GRID - cz
                    d2 = (dx * dx + dy * dy + dz * dz) / (r * r)
                    if d2 <= 1.6:
                        grid[ix][iy][iz] += weight * math.exp(-d2 * 2.2)

    def _region_parse(self, spec):
        """'cortex:1.0;hippocampus:0.8' -> dict, clamped, known ids only."""
        out = {}
        for part in str(spec or "").split(";"):
            if ":" in part:
                rid, w = part.split(":", 1)
                if rid.strip() in REGIONS:
                    try:
                        out[rid.strip()] = max(0.0, min(1.5, float(w)))
                    except Exception:
                        pass
        return out

    def merge_field(self):
        """The merged 3D brain: every taught species scan (kind 'scan')
        superimposed by its taught weight. Species data lives ONLY in the
        graph — untaught, this is just Gene's own regions."""
        grid = [[[0.0 for _ in range(GRID)] for _ in range(GRID)]
                for _ in range(GRID)]
        used = []
        scans = []
        if self.m is not None:
            for n in self.m.graph.nodes.values():
                if n.get("kind") in ("scan", "brain_scan"):
                    a = n.get("attrs") or {}
                    try:
                        w = float(a.get("weight", 0))
                    except Exception:
                        w = 0.0
                    regs = self._region_parse(a.get("regions"))
                    if w > 0 and regs:
                        scans.append((n["id"], w, regs))
        for sid, w, regs in scans:
            for rid, rw in regs.items():
                pos, rad, _ = REGIONS[rid]
                self._bump(grid, pos, rad, w * rw)
            used.append(sid)
        # her own living regions on top (activation-scaled)
        for rid, (pos, rad, _) in REGIONS.items():
            act = self.activation.get(rid, 0.05)
            self._bump(grid, pos, rad, 0.25 + 0.75 * act)
        self._field = grid
        self.species = used
        total = sum(v for z in grid for y in z for v in y)
        self.field_sum = total
        return grid

    def field(self):
        return self._field if self._field is not None else self.merge_field()

    # ---------- events --------------------------------------------------------------
    SUBSYSTEM_REGION = {sub: rid for rid, (_, _, sub) in REGIONS.items()}

    def tick(self, event, subsystems=None):
        """One lived moment: chemistry secretes, the doing-regions glow."""
        self.chem.event(event)
        bump = {
            "success": 0.5, "failure": 0.4, "effort": 0.6, "learn": 0.8,
            "threat": 0.7, "social": 0.5, "novel": 0.6, "rest": -0.3,
            "recall": 0.7, "utterance": 0.4,
        }.get(event, 0.2)
        lit = []
        for sub in (subsystems or []):
            rid = self.SUBSYSTEM_REGION.get(sub)
            if rid:
                self.activation[rid] = max(0.0, min(1.0,
                                                    self.activation.get(rid, 0.05) + bump))
                lit.append(rid)
        # the doing regions also feed the always-on core
        if event in ("learn", "effort"):
            for rid in ("cortex", "hippocampus"):
                self.activation[rid] = max(0.0, min(1.0, self.activation.get(rid, 0.05) + 0.3))
        self.ticks += 1
        if self.ticks % 8 == 0:
            self.chem.step()
        return lit

    def rest(self):
        """Sleep: chemistry rebalances, activations cool."""
        self.chem.event("rest")
        for _ in range(4):
            self.chem.step()
        for rid in self.activation:
            self.activation[rid] *= 0.6
        self.merge_field()

    # ---------- speech (status/brain are explicitly-asked internals) -------------
    def emotion_word(self):
        name, conf = self.chem.emotion(self.m.graph if self.m else None)
        if not name:
            return None
        return name.replace("_", " ")

    def feeling_line(self):
        e = self.emotion_word()
        dom = max(self.chem.h.items(), key=lambda kv: kv[1] - CHEM_BASELINE.get(kv[0], 0))
        base = self.chem.h[dom[0]]
        chem = dom[0]
        if e and base > CHEM_BASELINE.get(chem, 0) + 0.08:
            return "feels like %s right now — %s is running high (%.2f)." % (e, chem, base)
        if e:
            return "mostly %s, with %s near baseline (%.2f)." % (e, chem, base)
        return "chemistry steady — %s is the loudest signal (%.2f), no taught word for the blend yet." % (chem, base)

    def levels_line(self, which=None):
        c = self.chem.h
        if which and which in c:
            return "%s at %.2f (baseline %.2f)." % (which, c[which], CHEM_BASELINE[which])
        top = sorted(c.items(), key=lambda kv: -kv[1])[:3]
        return ", ".join("%s %.2f" % (k, v) for k, v in top)

    def status_line(self):
        hot = sorted(self.activation.items(), key=lambda kv: -kv[1])[:3]
        e = self.emotion_word() or "steady"
        return ("brain: %d ticks lived, field merged from %d scan(s), "
                "busiest regions %s — mood reads as %s."
                % (self.ticks, len(self.species) or 0,
                   ", ".join(r.replace("_", " ") for r, _ in hot), e))

    def render_slices(self):
        """Three mid-cuts through the merged field — the honest ASCII scan."""
        grid = self.field()
        mid = GRID // 2
        cuts = []
        for axis in range(3):
            rows = []
            for i in range(GRID):
                row = ""
                for j in range(GRID):
                    v = (grid[i][j][mid] if axis == 0 else
                         grid[i][mid][j] if axis == 1 else grid[mid][i][j])
                    row += RAMP[min(len(RAMP) - 1, int(v * 3.2))]
                rows.append(row)
            cuts.append("\n".join(rows))
        return cuts

    def scan_report(self):
        cuts = self.render_slices()
        species = ", ".join(s.replace("_", " ") for s in self.species) or "mine alone"
        return ("brain scan — merged from: %s. axial | sagittal | coronal:\n%s"
                % (species, "\n---\n".join(cuts[:2])))
