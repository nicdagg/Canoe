"""One call that runs every calculation for a design in a given condition."""
import math

import numpy as np

from . import hydrostatics as hs
from . import resistance as rs
from . import seakeeping as sk
from . import stability as st


def handling(H, up):
    """Turning and tracking proxies from the underwater profile (lateral plane)."""
    x = H.x
    d = np.clip(up['zw'] - H.keel, 0, None)
    A = float(np.sum((d[1:] + d[:-1]) * np.diff(x) / 2))
    xc = float(np.sum(((d * x)[1:] + (d * x)[:-1]) * np.diff(x) / 2)) / A
    I = float(np.sum(((d * (x - xc) ** 2)[1:] + (d * (x - xc) ** 2)[:-1]) * np.diff(x) / 2))
    lwl = up['lwl_in']
    ends = np.abs(x - (up['x_aft'] + up['x_fwd']) / 2) > 0.3 * lwl
    end_ratio = float(d[ends].mean() / d.max()) if ends.any() else 0.0
    return dict(
        lateral_area_ft2=A / 144,
        # radius of gyration of the lateral plane over waterline length: higher holds a line, lower spins
        turn_index=math.sqrt(I / A) / lwl,
        # mean immersion of the outer 40% of the waterline relative to the deepest point
        end_depth_ratio=end_ratio,
        rocker_total_in=H.p['b_rocker'] + H.p['s_rocker'],
    )


def _speed_at_power(H, up, off, depth, water, watts, curve=None):
    """Calm-water speed (mph) that the given effective power holds, by secant on P(v)."""
    if curve is not None:
        return rs.speed_at_power(curve, watts)
    P = lambda v: float(rs.calm_water(H, up, [v], depth, water, offsets=off)['power_w'][0]) - watts
    a, b = 3.0, 5.0
    fa, fb = P(a), P(b)
    for _ in range(12):
        if fb == fa:
            break
        c = float(np.clip(b - fb * (b - a) / (fb - fa), 0.5, 9.0))
        a, fa, b = b, fb, c
        fb = P(b)
        if abs(fb) < 0.02 * watts:
            break
    return b


def evaluate(params, cond, detail=False, angles=None):
    """Metrics for a design in a condition. detail=True also returns curves for plotting."""
    H = hs.SampledHull(params)
    lc = st.load_case(H.p, cond.get('load'))
    water = cond.get('water', 'fresh')
    rho = hs.LB_PER_IN3_SALT if water == 'salt' else hs.LB_PER_IN3_FRESH
    cap = hs.capacity(H, rho)
    out = dict(capacity_lb=cap, capacity_margin_lb=cap - lc['disp_lb'], disp_lb=lc['disp_lb'])
    if cap <= lc['disp_lb'] * 1.02:
        out['overloaded'] = True
        return out
    up = hs.upright(H, lc['disp_lb'], lc['lcg_in'], rho)
    stab = st.summarize(H, up, lc, angles if angles is not None else (None if detail else np.arange(0, 61, 5.0)))
    depth = cond.get('depth_m') or math.inf
    v0 = cond.get('speed_mph', 4.0)
    band = [v0 - 0.5, v0, v0 + 0.5]
    off = rs.centreplane_offsets(H, up)
    cw = rs.calm_water(H, up, band, depth, water, cond.get('wind_mph', 0.0), offsets=off)
    paddlers = cond.get('paddlers') or (2 if lc['crew_lb'] > 260 else 1)
    pw = cond.get('power_w_per_paddler', 40.0) * paddlers
    curve = rs.calm_water(H, up, np.arange(1.0, 8.01, 0.25), depth, water, 0.0, offsets=off) if detail else None
    fb_front, fb_side = rs.frontal_windage(H, up)
    out.update(
        draft_mid_in=up['draft_mid_in'], draft_max_in=up['draft_max_in'], freeboard_mid_in=up['freeboard_mid_in'],
        lwl_in=up['lwl_in'], bwl_in=up['bwl_in'], lwl_bwl=up['lwl_bwl'], cb=up['cb'], cp=up['cp'], cm=up['cm'],
        cwp=up['cwp'], lcb_pct=up['lcb_pct'], wetted_ft2=up['wetted_ft2'], ppi_lb=up['ppi_lb'], kmt_in=up['kmt_in'],
        bmt_in=up['bmt_in'], disp_length=up['disp_length'], half_angle_entrance=up['half_angle_entrance'],
        trim_in=up['trim_in'], vcg_in=stab['vcg_in'],
        gm_in=stab['gm_in'], gz_max_in=stab['gz_max_in'], angle_gz_max=stab['angle_gz_max'],
        rm_max_ftlb=stab['rm_max_ftlb'], flood_angle=stab['flood_angle'] or 90.0, rm10_ftlb=stab['rm10_ftlb'],
        secondary_ratio=stab['secondary_ratio'], dyn_area_inrad=stab['dyn_area_inrad'],
        calm_resistance_lbf=float(np.mean(cw['total_lbf'])), friction_lbf=float(np.mean(cw['friction_lbf'])),
        wave_lbf=float(np.mean(cw['wave_lbf'])), air_lbf=float(np.mean(cw['air_lbf'])),
        speed_at_power_mph=_speed_at_power(H, up, off, depth, water, pw, curve), power_w=pw, paddlers=paddlers,
        froude=float(cw['fn'][1]), depth_froude=float(cw['fh'][1]),
        front_windage_ft2=fb_front, side_windage_ft2=fb_side,
        gunwale_beam_in=params['beam'] - 2 * params.get('tumble', 0),   # width at the gunwales, midship: how far a paddler reaches out
        **handling(H, up),
    )
    waves = cond.get('waves')
    R = None
    if waves:
        R = sk.raos(H, up, lc, v0, water)
        sea = sk.in_sea(R, waves['hs_m'], waves['tp_s'], waves.get('gamma', 3.3))
        out.update(heave_sig_in=sea['heave_sig_in'], pitch_sig_deg=sea['pitch_sig_deg'],
                   bow_rel_sig_in=sea['bow_rel_sig_in'], bow_wet_prob=sea['bow_wet_prob'],
                   added_resistance_lbf=sea['added_resistance_lbf'], bow_freeboard_in=sea['bow_freeboard_in'])
    else:
        out.update(added_resistance_lbf=0.0)
    out['resistance_lbf'] = out['calm_resistance_lbf'] + out['added_resistance_lbf']
    out['effort_w'] = out['resistance_lbf'] * 4.4482216 * v0 * 0.44704
    out = {k: (float(v) if isinstance(v, (np.floating, np.integer)) else v) for k, v in out.items()}
    if detail:
        out['_curves'] = dict(gz=stab['curve'], resistance=curve, raos=R, upright=up, load=lc, hull=H)
    return out
