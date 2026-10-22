"""Comparison plots and a Markdown report for one or more designs in a condition."""
import math
import os

import numpy as np

from .analysis import evaluate
from .scoring import score

COLORS = ['#2a6fdb', '#e0702a', '#2a9d6f', '#b23a8a', '#7a6a2a', '#555555']

ROWS = [
    ('Score', 'score', '%.1f'),
    ('Draft, deepest (in)', 'draft_max_in', '%.2f'),
    ('Freeboard at midship (in)', 'freeboard_mid_in', '%.2f'),
    ('Waterline length (in)', 'lwl_in', '%.1f'),
    ('Waterline beam (in)', 'bwl_in', '%.1f'),
    ('Prismatic coefficient Cp', 'cp', '%.3f'),
    ('Waterplane coefficient Cwp', 'cwp', '%.3f'),
    ('Wetted area (ft²)', 'wetted_ft2', '%.2f'),
    ('Load centre of gravity height (in)', 'vcg_in', '%.1f'),
    ('Initial stability GM (in)', 'gm_in', '%.2f'),
    ('Righting moment at 10° (ft·lb)', 'rm10_ftlb', '%.1f'),
    ('Peak righting moment (ft·lb)', 'rm_max_ftlb', '%.1f'),
    ('Angle of peak (°)', 'angle_gz_max', '%.0f'),
    ('Gunwale goes under at (°)', 'flood_angle', '%.1f'),
    ('Secondary stability ratio', 'secondary_ratio', '%.2f'),
    ('Calm-water drag at cruise (lbf)', 'calm_resistance_lbf', '%.2f'),
    ('  of which wave-making (lbf)', 'wave_lbf', '%.2f'),
    ('Added drag in waves (lbf)', 'added_resistance_lbf', '%.2f'),
    ('Total drag at cruise (lbf)', 'resistance_lbf', '%.2f'),
    ('Speed at the power budget (mph)', 'speed_at_power_mph', '%.2f'),
    ('Heave, significant (in)', 'heave_sig_in', '%.1f'),
    ('Pitch, significant (°)', 'pitch_sig_deg', '%.1f'),
    ('Bow wetness chance per wave', 'bow_wet_prob', '%.3f'),
    ('Turn index (lower turns easier)', 'turn_index', '%.3f'),
    ('End immersion ratio', 'end_depth_ratio', '%.2f'),
    ('Side windage (ft²)', 'side_windage_ft2', '%.1f'),
    ('Width at the gunwales (in)', 'gunwale_beam_in', '%.1f'),
    ('Capacity at the sheer (lb)', 'capacity_lb', '%.0f'),
]


def _plt():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.size': 9, 'axes.grid': True, 'grid.alpha': 0.3, 'axes.spines.top': False,
                         'axes.spines.right': False})
    return plt


def run(designs, cond_name, cond, out_dir):
    """designs: list of (label, params). Writes report.md and PNGs into out_dir; returns results."""
    os.makedirs(out_dir, exist_ok=True)
    res = []
    for label, p in designs:
        m = evaluate(p, cond, detail=True)
        s = score(m, cond)
        m['score'] = s['score']
        res.append(dict(label=label, params=p, metrics=m, score=s))
    figs = []
    ok = [r for r in res if '_curves' in r['metrics']]
    if ok:
        figs.append(_lines(ok, out_dir))
        figs.append(_stability(ok, out_dir))
        figs.append(_resistance(ok, cond, out_dir))
        if cond.get('waves'):
            figs.append(_seakeeping(ok, cond, out_dir))
        figs.append(_scores(res, cond, out_dir))
    _markdown(res, cond_name, cond, figs, out_dir)
    return res


def _lines(res, out):
    plt = _plt()
    fig, ax = plt.subplots(3, 1, figsize=(8, 7.5), gridspec_kw=dict(height_ratios=[1, 1, 1.3]))
    for i, r in enumerate(res):
        c = COLORS[i % len(COLORS)]
        H, up = r['metrics']['_curves']['hull'], r['metrics']['_curves']['upright']
        ax[0].plot(H.x, H.sheer, c=c, label=r['label'])
        ax[0].plot(H.x, H.keel, c=c)
        ax[0].plot(H.x, up['zw'], c=c, ls=':', lw=1)
        ax[1].plot(H.x, [s.hb for s in H.st], c=c)
        ax[1].plot(H.x, up['hw'], c=c, ls=':', lw=1)
        m = H.model
        for f in (-0.75, -0.4, 0.0, 0.4, 0.75):
            x = m.mid + f * (m.Lb if f > 0 else m.Ls)
            s = m.at(x, 41)
            sgn = 1 if f >= 0 else -1
            ax[2].plot(sgn * s.y, s.z, c=c, lw=1.2 if f == 0 else 0.8)
        ax[2].axhline(up['draft_mid_in'], c=c, ls=':', lw=1)
    ax[0].set_title('Profile (stern left), dotted is the waterline', loc='left')
    ax[1].set_title('Half-breadth: widest (solid) and waterline (dotted)', loc='left')
    ax[2].set_title('Sections: stern half left, bow half right, at 0, 40 and 75% toward each end', loc='left')
    ax[2].set_aspect('equal')
    for a in ax[:2]:
        a.set_xlabel('inches from midship of length')
    ax[0].legend(frameon=False, fontsize=8)
    fig.tight_layout()
    path = os.path.join(out, 'lines.png')
    fig.savefig(path, dpi=130)
    plt.close(fig)
    return ('Lines', 'lines.png')


def _stability(res, out):
    plt = _plt()
    fig, ax = plt.subplots(figsize=(8, 4))
    for i, r in enumerate(res):
        c = COLORS[i % len(COLORS)]
        g = r['metrics']['_curves']['gz']
        rm = g['rm_inlb'] / 12
        fl = r['metrics']['flood_angle']
        rf = float(np.interp(fl, g['angle'], rm))
        m = g['angle'] < fl
        ax.plot(np.append(g['angle'][m], fl), np.append(rm[m], rf), c=c, label=r['label'])
        n = (g['angle'] > fl) & (g['angle'] <= 60)
        ax.plot(np.insert(g['angle'][n], 0, fl), np.insert(rm[n], 0, rf), c=c, ls='--', lw=0.8)
        ax.plot([fl], [rf], 'o', c=c, ms=5)
    ax.axhline(0, c='k', lw=0.6)
    ax.set_xlim(0, 60)
    ax.set_ylim(bottom=-20)
    ax.set_xlabel('heel (degrees)')
    ax.set_ylabel('righting moment (ft·lb)')
    ax.set_title('Righting moment. Dot is where the gunwale goes under; dashed beyond it assumes a covered hull',
                 loc='left')
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(os.path.join(out, 'stability.png'), dpi=130)
    plt.close(fig)
    return ('Stability', 'stability.png')


def _resistance(res, cond, out):
    plt = _plt()
    fig, ax = plt.subplots(1, 2, figsize=(9, 3.8))
    for i, r in enumerate(res):
        c = COLORS[i % len(COLORS)]
        cv = r['metrics']['_curves']['resistance']
        ax[0].plot(cv['speed_mph'], cv['total_lbf'], c=c, label=r['label'])
        ax[0].plot(cv['speed_mph'], cv['wave_lbf'], c=c, ls=':', lw=1)
        ax[1].plot(cv['speed_mph'], cv['power_w'], c=c)
    v = cond.get('speed_mph', 4)
    for a in ax:
        a.axvline(v, c='k', lw=0.6, ls='--')
        a.set_xlabel('speed (mph)')
    ax[0].set_ylabel('drag (lbf)')
    ax[1].set_ylabel('effective power (W)')
    d = cond.get('depth_m')
    ax[0].set_title('Calm-water drag%s, dotted is wave-making' % (' in %.1f m of water' % d if d else ''), loc='left')
    ax[1].set_title('Power to hold speed', loc='left')
    ax[1].axhline(res[0]['metrics']['power_w'], c='k', lw=0.6, ls=':')
    ax[0].set_ylim(0, max(np.max(r['metrics']['_curves']['resistance']['total_lbf'][:21]) for r in res) * 1.05)
    ax[1].set_ylim(0, max(np.max(r['metrics']['_curves']['resistance']['power_w'][:21]) for r in res) * 1.05)
    for a in ax:
        a.set_xlim(1, 6)
    ax[0].legend(frameon=False)
    fig.tight_layout()
    fig.savefig(os.path.join(out, 'resistance.png'), dpi=130)
    plt.close(fig)
    return ('Resistance', 'resistance.png')


def _seakeeping(res, cond, out):
    from .seakeeping import jonswap
    plt = _plt()
    fig, ax = plt.subplots(1, 3, figsize=(10, 3.4))
    w0 = cond['waves']
    for i, r in enumerate(res):
        c = COLORS[i % len(COLORS)]
        R = r['metrics']['_curves']['raos']
        T = 2 * np.pi / R['omega']
        ax[0].plot(T, np.abs(R['heave']), c=c, label=r['label'])
        k = R['omega'] ** 2 / 9.80665
        ax[1].plot(T, np.abs(R['pitch']) / k, c=c)
        ax[2].plot(T, R['raw'] / 4.448, c=c)
    S = jonswap(R['omega'], w0['hs_m'], w0['tp_s'], w0.get('gamma', 3.3))
    for a in ax:
        a2 = a.twinx()
        a2.fill_between(2 * np.pi / R['omega'], S, color='#999', alpha=0.2, lw=0)
        a2.set_yticks([])
        a2.grid(False)
        a.set_xlabel('wave period (s)')
        a.set_xlim(1, 10)
    ax[0].set_title('Heave per wave amplitude', loc='left')
    ax[1].set_title('Pitch per wave slope', loc='left')
    ax[2].set_title('Added drag (lbf per m²)', loc='left')
    ax[0].legend(frameon=False, fontsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(out, 'seakeeping.png'), dpi=130)
    plt.close(fig)
    return ('Head seas (grey is the sea spectrum)', 'seakeeping.png')


def _scores(res, cond, out):
    plt = _plt()
    keys = list(cond.get('weights', {}))
    fig, ax = plt.subplots(figsize=(8, 0.5 + 0.35 * len(keys) * max(1, len(res)) / 1.5))
    h = 0.8 / max(len(res), 1)
    for i, r in enumerate(res):
        vals = [r['score']['parts'].get(k, 0) for k in keys]
        ax.barh(np.arange(len(keys)) + i * h, vals, height=h, color=COLORS[i % len(COLORS)], label=r['label'])
    ax.set_yticks(np.arange(len(keys)) + h * (len(res) - 1) / 2)
    ax.set_yticklabels(['%s (x%g)' % (k, cond['weights'][k]) for k in keys])
    lo = min([0.0] + [v for r in res for v in r['score']['parts'].values()])
    ax.set_xlim(lo - 0.05 if lo < 0 else 0, 1)
    ax.axvline(0, c='k', lw=0.6)
    ax.invert_yaxis()
    ax.set_title('How each criterion scored (1 at the good target, 0 at poor, below 0 past poor)', loc='left')
    ax.legend(frameon=False, fontsize=8, loc='upper left', bbox_to_anchor=(1.0, 1.0))
    fig.tight_layout()
    fig.savefig(os.path.join(out, 'scores.png'), dpi=130)
    plt.close(fig)
    return ('Score breakdown', 'scores.png')


def _fmt(v, f):
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return '–'
    return f % v


def _markdown(res, cond_name, cond, figs, out):
    L = ['# %s' % cond_name, '', cond.get('description', ''), '']
    bits = ['speed %.1f mph' % cond.get('speed_mph', 4)]
    if cond.get('depth_m'):
        bits.append('water %.1f m deep' % cond['depth_m'])
    if cond.get('waves'):
        w = cond['waves']
        bits.append('waves Hs %.2f m (%.0f in), Tp %.1f s, gamma %g' % (w['hs_m'], w['hs_m'] / 0.0254, w['tp_s'],
                                                                       w.get('gamma', 3.3)))
    if cond.get('wind_mph'):
        bits.append('headwind %g mph' % cond['wind_mph'])
    ld = cond.get('load', {})
    bits.append('crew centre of gravity %s in' % ld['crew_vcg_in'] if 'crew_vcg_in' in ld and 'crew_posture' not in ld
                else 'crew %s' % ld.get('crew_posture', 'seated'))
    L += ['Condition: ' + ', '.join(bits) + '.', '']
    L += ['| | ' + ' | '.join(r['label'] for r in res) + ' |', '|---|' + '---|' * len(res)]
    for name, key, f in ROWS:
        vals = [_fmt(r['metrics'].get(key), f) for r in res]
        if all(v == '–' for v in vals):
            continue
        L.append('| %s | %s |' % (name, ' | '.join(vals)))
    L.append('')
    for r in res:
        if r['score']['violations']:
            L.append('- **%s** breaks: %s' % (r['label'], '; '.join(r['score']['violations'])))
    L.append('')
    for title, fn in figs:
        L += ['## ' + title, '', '![%s](%s)' % (title, fn), '']
    with open(os.path.join(out, 'report.md'), 'w') as fh:
        fh.write('\n'.join(L))
