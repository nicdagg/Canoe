"""Check that the designer page (JavaScript) and the Python kit give the same numbers for the same canoe.

Run from the repo root:  python3 tests/compare_kit.py
"""
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'python-kit'))
from canoe_analysis.analysis import evaluate            # noqa: E402
from canoe_analysis.scoring import load_conditions, score  # noqa: E402

KEYS = ['disp_lb', 'draft_max_in', 'freeboard_mid_in', 'lwl_in', 'bwl_in', 'wetted_ft2', 'gm_in', 'rm_max_ftlb', 'flood_angle',
        'resistance_lbf', 'wave_lbf', 'speed_at_power_mph', 'track_index', 'reach_in', 'windage_ratio', 'sinkage_in', 'skin_ft2',
        'side_windage_ft2', 'pitch_sig_deg', 'bow_wet_prob']
TOL = {'wave_lbf': 0.02, 'flood_angle': 0.02, 'bow_wet_prob': 0.05}
CASES = [('default', 'calm-lake'), ('tripper', 'big-lake-chop'), ('lake-cruiser', 'shallow-river'), ('solo', 'fast-flatwater'),
         ('kids-pack-boat', 'kids-pack-boat'), ('tripper', 'moving-water'), ('fast-tourer', 'coastal-swell')]


def main():
    js = json.loads(subprocess.check_output(['node', os.path.join(ROOT, 'tests', 'dump_engine.js'), json.dumps(CASES)]))
    C = load_conditions()
    bad = 0
    for (design, cond), row in zip(CASES, js):
        m = evaluate(row['p'], C[cond])
        s = score(m, C[cond])
        worst = ('', 0.0)
        for k in KEYS:
            a, b = row['m'].get(k), m.get(k)
            if a is None or b is None:
                continue
            err = abs(a - b) / max(abs(a), abs(b), 0.05)
            if err > TOL.get(k, 0.01):
                bad += 1
                print('  MISMATCH %s: page %.5g, kit %.5g' % (k, a, b))
            worst = max(worst, (k, err), key=lambda t: t[1])
        if abs(row['score'] - s['score']) > 0.7:
            bad += 1
            print('  MISMATCH score: page %.2f, kit %.2f' % (row['score'], s['score']))
        print('%-15s %-15s score page %6.1f kit %6.1f  worst %s %.2f%%' % (design, cond, row['score'], s['score'], worst[0], 100 * worst[1]))
    print('FAILED: %d mismatches' % bad if bad else 'OK: page and kit agree')
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
