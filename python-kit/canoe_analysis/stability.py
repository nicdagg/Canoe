"""Transverse stability: load case, centre of gravity, righting-arm (GZ) curve.

The GZ curve is computed by direct integration at each heel angle with displacement
and trim held at their upright values. It is the static curve for a rigid load:
paddlers bracing or leaning are not modelled, and past gunwale immersion an open
canoe swamps, so the curve beyond that angle only describes a decked or covered hull.
"""
import math

import numpy as np

from . import hydrostatics as hs

# Height of a paddler's centre of gravity above the hull bottom (inches), by posture.
# Seated assumes a seat 3.5 in below the gunwale and a body CG 8 in above the seat (legs forward, low).
POSTURE_VCG = {'kneeling': lambda depth: 11.0, 'low_seat': lambda depth: 14.5, 'seated': lambda depth: depth - 3.5 + 8.0}


def load_case(p, load=None):
    """Weights and centre of gravity heights.

    load (all optional): crew_lb, crew_posture or crew_vcg_in, gear_lb, gear_vcg_in, hull_vcg_frac, lcg_in.
    By default the payload is 85% crew seated and 15% gear on the bottom, the hull's own
    centre of gravity is at 45% of depth, and the canoe floats level (lcg None).
    """
    load = dict(load or {})
    pay = p['payLb']
    crew = load.get('crew_lb', 0.85 * pay)
    gear = load.get('gear_lb', pay - crew)
    crew_vcg = load.get('crew_vcg_in', POSTURE_VCG[load.get('crew_posture', 'seated')](p['depth']))
    gear_vcg = load.get('gear_vcg_in', 4.0)
    hull_vcg = load.get('hull_vcg_frac', 0.45) * p['depth']
    W = p['hullLb'] + crew + gear
    vcg = (p['hullLb'] * hull_vcg + crew * crew_vcg + gear * gear_vcg) / W
    return dict(disp_lb=W, vcg_in=vcg, crew_lb=crew, gear_lb=gear, crew_vcg_in=crew_vcg,
                lcg_in=load.get('lcg_in'), kyy_frac=load.get('kyy_frac', 0.27))


def gz_curve(H, up, vcg, angles=None):
    """Righting arm GZ (inches) and righting moment (in-lb) against heel (degrees)."""
    if angles is None:
        angles = np.arange(0, 91, 5.0)
    vol, tau = up['vol_in3'], up['trim_slope']
    gz, clear = [], []
    for a in angles:
        h0, yb, zb = hs.heeled(H, vol, a, tau)
        s, c = math.sin(math.radians(a)), math.cos(math.radians(a))
        gz.append(yb * c + (zb - vcg) * s)
        clear.append(hs.gunwale_clearance(H, a, h0, tau))
    gz, clear = np.array(gz), np.array(clear)
    return dict(angle=np.asarray(angles, float), gz_in=gz, rm_inlb=gz * up['disp_lb'], gunwale_clear_in=clear)


def _first_root(x, y):
    for i in range(1, len(x)):
        if y[i - 1] > 0 >= y[i]:
            return float(x[i - 1] + (x[i] - x[i - 1]) * y[i - 1] / (y[i - 1] - y[i]))
    return None


def summarize(H, up, lc, angles=None):
    """Stability numbers used by the scoring: GM, gunwale-immersion angle, GZ peak, reserve."""
    vcg = lc['vcg_in']
    cur = gz_curve(H, up, vcg, angles)
    a, gz = cur['angle'], cur['gz_in']
    gm = up['kmt_in'] - vcg
    flood = _first_root(a, cur['gunwale_clear_in'])
    vanish = _first_root(a[1:], gz[1:])
    upto = flood if flood is not None else (vanish if vanish is not None else a[-1])
    m = a <= upto
    ai, gi = a[m], gz[m]
    if flood is not None and ai[-1] < flood:
        ai, gi = np.append(ai, flood), np.append(gi, np.interp(flood, a, gz))
    imax = int(np.argmax(gi))
    rad = np.radians(ai)
    area = float(np.sum((gi[1:] + gi[:-1]) * np.diff(rad) / 2))      # inch-radians, dynamic stability
    gz10 = float(np.interp(10, a, gz))
    gz20 = float(np.interp(20, a, gz))
    return dict(
        vcg_in=vcg, gm_in=gm, gz_max_in=float(gi[imax]), angle_gz_max=float(ai[imax]),
        rm_max_ftlb=float(gi[imax]) * up['disp_lb'] / 12,
        flood_angle=flood, vanish_angle=vanish,
        gz10_in=gz10, gz20_in=gz20, rm10_ftlb=gz10 * up['disp_lb'] / 12,
        # >1: righting arm grows faster than the initial GM predicts ("firm" secondary stability)
        secondary_ratio=gz20 / (gm * math.sin(math.radians(20))) if gm > 0 else 0.0,
        dyn_area_inrad=area, curve=cur,
    )
