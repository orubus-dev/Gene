"""Hyperdimensional computing substrate — the organism's neurochemistry.

Bipolar HDC vectors of fixed dimension. Deterministic and seedable, so a
concept's vector is never stored — only its seed string is, and the vector
is recomputed identically every time. No training, no gradients: these are
the innate algebra of representation.

    bind(A, B)     -> association ("A and B together")
    bundle([...])  -> set membership / prototype
    permute(A, k)  -> order / sequence
    sim(A, B)      -> similarity in [-1, 1]
"""
import random

DIM = 2048
_cache = {}


def vec(seed: str):
    """Deterministic bipolar vector from a seed string (cached)."""
    v = _cache.get(seed)
    if v is None:
        r = random.Random("hdc:" + str(seed))
        v = tuple(1 if r.random() < 0.5 else -1 for _ in range(DIM))
        _cache[seed] = v
    return v


def bind(a, b):
    """Binding: XOR-like association. Commutative, dissimilar from both."""
    return tuple(x * y for x, y in zip(a, b))


def bundle(vs):
    """Bundling: majority vote — 'a set containing these'."""
    if not vs:
        raise ValueError("bundle of nothing")
    if len(vs) == 1:
        return vs[0]
    acc = [0] * DIM
    for v in vs:
        for i, x in enumerate(v):
            acc[i] += x
    return tuple(1 if x >= 0 else -1 for x in acc)


def permute(a, k=1):
    """Order marker: roll by k positions."""
    if not k:
        return a
    k %= DIM
    return a[-k:] + a[:-k]


def sim(a, b) -> float:
    """Cosine similarity of bipolar vectors."""
    dot = 0
    for x, y in zip(a, b):
        dot += x * y
    return dot / len(a)


def encode_sequence(items):
    """Encode an ordered sequence: sum of position-permuted role bindings."""
    if not items:
        return vec("empty")
    parts = [bind(permute(vec("pos:%d" % i), i), v) for i, v in enumerate(items)]
    return bundle(parts)


def probe(query_vec, candidates, topn=5):
    """Return [(key, similarity)] sorted best-first."""
    scored = [(k, sim(query_vec, v)) for k, v in candidates]
    scored.sort(key=lambda t: -t[1])
    return scored[:topn]
