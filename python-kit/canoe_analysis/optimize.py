"""Search the designer's parameters for the best score in a condition.

Differential evolution (rand/1/bin) over a chosen set of sliders, run in parallel.
Everything not varied stays at the starting design's value, so you can fix the
length, load and hull weight and let the shape move.
"""
import os
from multiprocessing import Pool

import numpy as np

from .analysis import evaluate
from .geometry import END_KEYS, RANGES
from .scoring import score

# Search ranges: narrower than the slider ranges, to stay in sensible canoe territory.
# Length, beam and depth widen around the starting design so short or small hulls search near themselves.
SEARCH = dict(beam=(28, 38), depth=(11, 15.5), length=(150, 222), mid=(-12, 12), tumble=(0, 3), tumbleAt=(50, 80),
              rocker=(0, 6), rise=(2, 8), sheerExp=(1.6, 4), angle=(55, 85), radius=(6, 40), secExp=(1.8, 3.4),
              planExp=(2, 3.2), fine=(0.6, 1.0), tlen=(30, 90))
DEFAULT_VARS = ['beam', 'depth', 'rocker', 'secExp', 'planExp', 'fine', 'angle']


def _apply(base, names, vec, link):
    p = dict(base)
    for n, v in zip(names, vec):
        if n in END_KEYS and link:
            p['b_' + n] = p['s_' + n] = float(v)
        elif n in END_KEYS:
            raise ValueError('with link_ends off, name the end: b_%s or s_%s' % (n, n))
        else:
            p[n] = float(v)
    return p


def _bounds(n, overrides, base=None):
    if n in overrides:
        return overrides[n]
    key = n[2:] if n[:2] in ('b_', 's_') else n
    rlo, rhi = RANGES[n if n in RANGES else 'b_' + n]
    lo, hi = SEARCH.get(key, (rlo, rhi))
    v = (base or {}).get(n)
    if v is not None and key == 'length':
        lo, hi = 0.85 * v, 1.15 * v
    elif v is not None and key in ('beam', 'depth'):
        pad = 3 if key == 'beam' else 2
        lo, hi = min(lo, v - pad), max(hi, v + pad)
    return max(lo, rlo), min(hi, rhi)


_JOB = {}


def _init(job):
    _JOB.update(job)
    try:                                   # one thread per worker; the pool supplies the parallelism
        from threadpoolctl import threadpool_limits
        threadpool_limits(1)
    except ImportError:
        pass


def _cost(vec):
    j = _JOB
    p = _apply(j['base'], j['names'], vec, j['link'])
    try:
        m = evaluate(p, j['cond'])
        s = score(m, j['cond'])
        return -s['score'], s['raw_score'] if 'raw_score' in s else 0.0
    except Exception:
        return 1e6, 0.0


def optimize(base, cond, names=None, link_ends=True, bounds=None, pop=None, gens=30, seed=1,
             workers=None, log=print):
    names = list(names or DEFAULT_VARS)
    bnds = np.array([_bounds(n, bounds or {}, base) for n in names], float)
    D = len(names)
    NP = pop or max(16, 4 * D)
    rng = np.random.default_rng(seed)
    lo, hi = bnds[:, 0], bnds[:, 1]
    X = lo + rng.random((NP, D)) * (hi - lo)
    start = []
    for n in names:
        k = 'b_' + n if (n in END_KEYS and link_ends) else n
        start.append(base[k])
    X[0] = np.clip(start, lo, hi)                   # keep the starting design in the population
    job = dict(base=base, names=names, link=link_ends, cond=cond)
    workers = workers or min(os.cpu_count() or 1, 8)
    os.environ.setdefault('OMP_NUM_THREADS', '1')
    os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')
    history = []
    with Pool(workers, initializer=_init, initargs=(job,)) as pool:
        f = np.array([c for c, _ in pool.map(_cost, list(X))])
        for g in range(gens):
            trial = np.empty_like(X)
            for i in range(NP):
                a, b, c = rng.choice([k for k in range(NP) if k != i], 3, replace=False)
                Fm = rng.uniform(0.5, 0.9)
                v = X[a] + Fm * (X[b] - X[c])
                cross = rng.random(D) < 0.8
                cross[rng.integers(D)] = True
                u = np.where(cross, v, X[i])
                # bounce back inside the box instead of sticking to the walls
                u = np.where(u < lo, lo + rng.random(D) * (X[i] - lo), u)
                u = np.where(u > hi, hi - rng.random(D) * (hi - X[i]), u)
                trial[i] = u
            ft = np.array([c for c, _ in pool.map(_cost, list(trial))])
            better = ft <= f
            X[better], f[better] = trial[better], ft[better]
            ib = int(np.argmin(f))
            history.append(dict(gen=g + 1, best=-f[ib], median=-float(np.median(f)),
                                **{n: float(X[ib, k]) for k, n in enumerate(names)}))
            if log:
                log('gen %3d  best %6.1f  median %6.1f  %s' % (g + 1, -f[ib], -np.median(f),
                    ' '.join('%s=%.2f' % (n, X[ib, k]) for k, n in enumerate(names))))
    ib = int(np.argmin(f))
    best = _apply(base, names, X[ib], link_ends)
    return dict(params=best, score=-f[ib], names=names, bounds=bnds.tolist(), history=history,
                population=[_apply(base, names, x, link_ends) for x in X[np.argsort(f)[:5]]])
