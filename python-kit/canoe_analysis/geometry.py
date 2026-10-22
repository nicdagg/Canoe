"""Hull surface model, ported line for line from the Canoe Hull Designer artifact.

Units are inches. x runs from -L/2 (stern) to +L/2 (bow), z is height above the
lowest point of the keel, y is the half-breadth. Parameters use the artifact's
internal keys (length, beam, depth, mid, tumble, tumbleAt, b_*, s_*); see
config.py for the mapping to and from config/default.json.
"""
import math

import numpy as np

DEF_SHARED = dict(length=193, beam=33.5, depth=13, mid=0, tumble=0, tumbleAt=60, hullLb=55, payLb=330)
DEF_END = dict(rocker=2.4, rise=3.5, sheerExp=2.5, angle=70, radius=18, secExp=2.4, planExp=2.0, fine=0.8, tlen=60)
END_KEYS = list(DEF_END)

# Slider ranges in the artifact: (min, max). Used to clamp and as optimizer bounds.
RANGES = dict(length=(72, 240), beam=(18, 44), depth=(6, 20), mid=(-30, 30), tumble=(0, 6), tumbleAt=(40, 90),
              hullLb=(8, 120), payLb=(30, 800))
END_RANGES = dict(rocker=(0, 8), rise=(0, 12), sheerExp=(1.2, 5), angle=(35, 88), radius=(1, 60), secExp=(1.6, 4),
                  planExp=(2, 4), fine=(0.5, 1), tlen=(6, 120))
for _k, _r in END_RANGES.items():
    RANGES['b_' + _k] = _r
    RANGES['s_' + _k] = _r


def default_params():
    p = dict(DEF_SHARED)
    for k, v in DEF_END.items():
        p['b_' + k] = v
        p['s_' + k] = v
    return p


def clamp(v, a, b):
    return min(b, max(a, v))


def smoother(t):
    t = np.clip(t, 0.0, 1.0)
    return t * t * t * (t * (6 * t - 15) + 10)


def _end_obj(p, pre):
    return dict(rocker=p[pre + 'rocker'], rise=p[pre + 'rise'], sx=p[pre + 'sheerExp'], angle=p[pre + 'angle'],
                radius=p[pre + 'radius'], n=p[pre + 'secExp'], pe=p[pre + 'planExp'], fine=p[pre + 'fine'],
                tlen=p[pre + 'tlen'])


class _End:
    """Keel profile of one end: rocker curve, stem fillet, straight stem line."""

    def __init__(self, p, e, Le):
        self.e, self.Le = e, Le
        zt = p['depth'] + e['rise']
        R = min(e['rocker'], zt - 1)
        MAXA = 88 * math.pi / 180
        # The stem line must be steeper than the sheer where they meet, and must reach the keel.
        minTh = max(math.atan((zt + 1) / Le), math.atan(1.2 * e['sx'] * e['rise'] / Le))
        th = min(max(min(e['angle'] * math.pi / 180, MAXA), minTh), MAXA)
        sn, cs, tn = math.sin(th), math.cos(th), math.tan(th)
        zb = lambda s: R * (max(s, 0) / Le) ** 2.5
        zbp = lambda s: 2.5 * R * (max(s, 0) / Le) ** 1.5 / Le
        lo, hi = 0.0, Le
        for _ in range(60):                        # sharp corner: keel curve meets stem line
            m = (lo + hi) / 2
            if zb(m) - (zt - (Le - m) * tn) > 0:
                lo = m
            else:
                hi = m
        sc = (lo + hi) / 2

        def fillet(r):
            # Circle of radius r tangent to the keel curve (from above) and to the stem line.
            def cen(s):
                sl = zbp(s)
                k = math.sqrt(1 + sl * sl)
                return s - r * sl / k, zb(s) + r / k

            def h(s):
                c = cen(s)
                return (Le - c[0]) * sn + (c[1] - zt) * cs - r

            if h(0) <= 0 or h(Le) >= 0:
                return None
            a0, b0 = 0.0, Le
            for _ in range(60):
                mm = (a0 + b0) / 2
                if h(mm) > 0:
                    a0 = mm
                else:
                    b0 = mm
            sa = (a0 + b0) / 2
            c = cen(sa)
            bx, bz = c[0] + r * sn, c[1] - r * cs
            room = (Le - bx) * cs + (zt - bz) * sn
            if sa < 0.02 * Le or bx <= sa or room < 0.5:
                return None
            return dict(ax=sa, ox=c[0], oz=c[1], bx=bx, r=r)

        f, r0 = None, max(e['radius'], 0)
        if r0 > 0.5:
            f = fillet(r0)
            if not f and fillet(0.5):              # largest radius that fits
                rl, rh = 0.5, r0
                for _ in range(40):
                    m = (rl + rh) / 2
                    if fillet(m):
                        rl = m
                    else:
                        rh = m
                f = fillet(rl)
        self.rEff = f['r'] if f else 0
        self.angleEff = th * 180 / math.pi
        self._f, self._sc, self._zb, self._zt, self._tn, self._R = f, sc, zb, zt, tn, R

    def keel(self, s):
        f, zt, tn, Le = self._f, self._zt, self._tn, self.Le
        if not f:
            return self._zb(s) if s <= self._sc else zt - (Le - s) * tn
        if s <= f['ax']:
            return self._zb(s)
        if s <= f['bx']:
            d = s - f['ox']
            return f['oz'] - math.sqrt(max(0, f['r'] ** 2 - d * d))
        return zt - (Le - s) * tn


class Section:
    __slots__ = ('x', 'hb', 'T', 'keel', 'sheer', 'y', 'z')

    def __init__(self, x, hb, T, keel, sheer, y, z):
        self.x, self.hb, self.T, self.keel, self.sheer, self.y, self.z = x, hb, T, keel, sheer, y, z


class HullModel:
    """Same as makeModel() in the artifact. Bow and stern settings are blended across midship."""

    def __init__(self, params):
        p = default_params()
        p.update(params)
        self.p = p
        L = p['length']
        mid = clamp(p['mid'], -0.25 * L, 0.25 * L)
        self.L, self.mid = L, mid
        self.Lb, self.Ls = L / 2 - mid, L / 2 + mid
        self.B = _End(p, _end_obj(p, 'b_'), self.Lb)
        self.S = _End(p, _end_obj(p, 's_'), self.Ls)
        self.zmax = max(p['depth'] + p['b_rise'], p['depth'] + p['s_rise'])

    def at(self, x, NP=31):
        p, mid, Lb, Ls = self.p, self.mid, self.Lb, self.Ls
        eb, es = self.B.e, self.S.e
        Z = 0.18 * self.L
        T0, tm0 = max(p['tumble'], 0), p['tumbleAt'] / 100
        u = x - mid
        au = abs(u)
        w = float(smoother((u + Z) / (2 * Z)))
        mx = lambda a, b: a + (b - a) * w
        xi = min(au / (Ls + (Lb - Ls) * w), 1)
        hb = (p['beam'] / 2) * max(0.0, 1 - xi ** mx(es['pe'], eb['pe'])) ** mx(es['fine'], eb['fine'])
        sheer = p['depth'] + mx(es['rise'], eb['rise']) * xi ** mx(es['sx'], eb['sx'])
        keel = min(self.B.keel(au) if u >= 0 else self.S.keel(au), sheer - 0.02)
        n = mx(es['n'], eb['n'])
        lam = 1 - float(smoother(au / (eb['tlen'] if u >= 0 else es['tlen']))) if T0 > 0 else 0
        T = min(T0 * lam, 0.5 * hb)
        tm = 1 - (1 - tm0) * lam
        den = max(1 - tm, 1e-6)
        j = np.arange(NP)
        t = 1 - np.cos(0.5 * np.pi * j / (NP - 1))
        a = np.minimum(t / tm, 1)
        f = np.clip((t - tm) / den, 0, 1)
        y = hb * np.maximum(0, 1 - (1 - a) ** n) ** (1 / n) - T * f * f
        z = keel + (sheer - keel) * t
        return Section(x, hb, T, keel, sheer, y, z)

    def stations(self, NE=45, NP=31):
        """The artifact's station list: cosine spaced, dense toward the ends."""
        out = []
        for i in range(NE - 1, -1, -1):
            out.append(self.at(self.mid - self.Ls * math.sin(math.pi / 2 * i / (NE - 1)), NP))
        for i in range(1, NE):
            out.append(self.at(self.mid + self.Lb * math.sin(math.pi / 2 * i / (NE - 1)), NP))
        return out
