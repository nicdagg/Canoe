"""Read and write the settings JSON that the Canoe Hull Designer copies out.

The file layout matches the hull and hydro sections of config/default.json in the
PC project:

    {"hull": {"length", "beam", "depth", "mid_offset", "tumblehome", "tumble_start",
              "bow": {...}, "stern": {...}},
     "hydro": {"hull_mass_lb", "payload_lb"}}

Any other top-level sections (for example "analysis" or "load") are kept as they are.
"""
import json

from .geometry import RANGES, clamp, default_params

END_MAP = [('rocker', 'rocker'), ('stem_rise', 'rise'), ('sheer_exp', 'sheerExp'), ('stem_angle', 'angle'),
           ('stem_radius', 'radius'), ('section_exp', 'secExp'), ('plan_exp', 'planExp'), ('end_fine', 'fine'),
           ('tumble_len', 'tlen')]
HULL_MAP = [('length', 'length'), ('beam', 'beam'), ('depth', 'depth'), ('mid_offset', 'mid'),
            ('tumblehome', 'tumble')]


def params_from_config(cfg):
    """Artifact-style params from a config dict. Missing values fall back to the artifact defaults."""
    p = default_params()
    hull = cfg.get('hull', {})
    for ck, pk in HULL_MAP:
        if ck in hull:
            p[pk] = float(hull[ck])
    if 'tumble_start' in hull:
        p['tumbleAt'] = float(hull['tumble_start']) * 100
    for side, pre in (('bow', 'b_'), ('stern', 's_')):
        for ck, pk in END_MAP:
            if ck in hull.get(side, {}):
                p[pre + pk] = float(hull[side][ck])
    hydro = cfg.get('hydro', {})
    if 'hull_mass_lb' in hydro:
        p['hullLb'] = float(hydro['hull_mass_lb'])
    if 'payload_lb' in hydro:
        p['payLb'] = float(hydro['payload_lb'])
    for k, (a, b) in RANGES.items():
        p[k] = clamp(p[k], a, b)
    return p


def config_from_params(p, base=None):
    """Config dict in the artifact's export format, merged over base so other sections survive."""
    r2 = lambda v: round(float(v), 2)
    cfg = json.loads(json.dumps(base)) if base else {}
    end = lambda pre: {ck: r2(p[pre + pk]) for ck, pk in END_MAP}
    cfg['hull'] = dict(cfg.get('hull', {}))
    cfg['hull'].update({ck: r2(p[pk]) for ck, pk in HULL_MAP})
    cfg['hull']['tumble_start'] = r2(p['tumbleAt'] / 100)
    cfg['hull']['bow'] = end('b_')
    cfg['hull']['stern'] = end('s_')
    cfg['hydro'] = dict(cfg.get('hydro', {}))
    cfg['hydro'].update(hull_mass_lb=r2(p['hullLb']), payload_lb=r2(p['payLb']))
    return cfg


def load(path):
    with open(path) as fh:
        cfg = json.load(fh)
    return cfg, params_from_config(cfg)


def save(path, p, base=None):
    with open(path, 'w') as fh:
        json.dump(config_from_params(p, base), fh, indent=2)
        fh.write('\n')
