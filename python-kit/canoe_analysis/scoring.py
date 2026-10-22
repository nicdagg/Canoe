"""Turn metrics into a 0-100 score for a condition profile (see conditions.json)."""
import json
import os

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_conditions(path=None):
    with open(path or os.path.join(HERE, 'conditions.json')) as fh:
        data = json.load(fh)
    return {k: v for k, v in data.items() if not k.startswith('_')}


def desirability(v, poor, good):
    """1 at or past good, 0 at poor, and negative past poor (down to -1) so worse keeps counting."""
    if v is None:
        return 0.0
    t = (v - poor) / (good - poor)
    return min(1.0, max(-1.0, t))


def score(metrics, cond):
    """Score, per-metric desirability, and constraint violations."""
    if metrics.get('overloaded'):
        return dict(score=0.0, parts={}, violations=['overloaded: capacity %.0f lb' % metrics['capacity_lb']],
                    feasible=False)
    parts, tot, wsum = {}, 0.0, 0.0
    for k, w in cond.get('weights', {}).items():
        poor, good = cond['targets'][k]
        d = desirability(metrics.get(k), poor, good)
        parts[k] = d
        tot += w * d
        wsum += w
    s = 100 * tot / wsum if wsum else 0.0
    viol, pen = [], 0.0
    for k, (lo, hi) in cond.get('constraints', {}).items():
        v = metrics.get(k)
        if v is None:
            continue
        if lo is not None and v < lo:
            viol.append('%s %.3g < %.3g' % (k, v, lo))
            pen += 25 + 100 * (lo - v) / max(abs(lo), 1e-6)
        if hi is not None and v > hi:
            viol.append('%s %.3g > %.3g' % (k, v, hi))
            pen += 25 + 100 * (v - hi) / max(abs(hi), 1e-6)
    return dict(score=s - pen, raw_score=s, parts=parts, violations=viol, feasible=not viol)
