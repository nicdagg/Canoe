"""Command line.

    python -m canoe_analysis conditions
    python -m canoe_analysis analyze designs/tripper.json designs/my-hull.json -c big-lake-chop
    python -m canoe_analysis matrix designs/*.json
    python -m canoe_analysis optimize designs/tripper.json -c big-lake-chop --vary beam,depth,rocker,fine
"""
import argparse
import csv
import json
import os
import sys

from . import config
from .report import run
from .scoring import load_conditions, score
from .analysis import evaluate

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _label(path):
    return os.path.splitext(os.path.basename(path))[0]


def cmd_conditions(a, C):
    for k, c in C.items():
        print('%-16s %s' % (k, c.get('description', '')))


def cmd_analyze(a, C):
    designs = [(_label(f), config.load(f)[1]) for f in a.designs]
    names = list(C) if a.condition == 'all' else a.condition.split(',')
    for n in names:
        out = os.path.join(a.out or os.path.join(HERE, 'results', '-'.join(d[0] for d in designs)), n)
        res = run(designs, n, C[n], out)
        print('%s -> %s' % (n, os.path.join(out, 'report.md')))
        for r in res:
            print('   %-20s score %6.1f %s' % (r['label'], r['score']['score'], '; '.join(r['score']['violations'])))


def cmd_matrix(a, C):
    designs = [(_label(f), config.load(f)[1]) for f in a.designs]
    rows = []
    for label, p in designs:
        row = [label]
        for n, c in C.items():
            s = score(evaluate(p, c), c)
            row.append('%.0f%s' % (s.get('raw_score', 0), '' if s['feasible'] else '*'))
        rows.append(row)
    w = max(len(r[0]) for r in rows) + 2
    print(' ' * w + ''.join('%15s' % n[:14] for n in C))
    for r in rows:
        print(r[0].ljust(w) + ''.join('%15s' % v for v in r[1:]))
    print('* breaks a hard limit of that condition (run analyze to see which)')
    if a.out:
        os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
        with open(a.out, 'w', newline='') as fh:
            wr = csv.writer(fh)
            wr.writerow(['design'] + list(C))
            wr.writerows(rows)


def cmd_optimize(a, C):
    from .optimize import optimize
    base_cfg, base = config.load(a.design)
    cond = C[a.condition]
    names = a.vary.split(',') if a.vary else None
    bounds = {}
    for b in a.bound or []:
        k, rng = b.split('=')
        lo, hi = rng.split(':')
        bounds[k] = (float(lo), float(hi))
    r = optimize(base, cond, names, link_ends=not a.unlink, bounds=bounds, pop=a.pop, gens=a.gens, seed=a.seed)
    out = a.out or os.path.join(HERE, 'results', 'opt-%s-%s' % (_label(a.design), a.condition))
    os.makedirs(out, exist_ok=True)
    best = os.path.join(out, 'best.json')
    config.save(best, r['params'], base_cfg)
    with open(os.path.join(out, 'history.csv'), 'w', newline='') as fh:
        wr = csv.DictWriter(fh, fieldnames=list(r['history'][0]))
        wr.writeheader()
        wr.writerows(r['history'])
    with open(os.path.join(out, 'search.json'), 'w') as fh:
        json.dump(dict(condition=a.condition, varied=r['names'], bounds=r['bounds'], score=r['score']), fh, indent=2)
    run([(_label(a.design), base), ('optimized', r['params'])], a.condition, cond, out)
    print('best score %.1f -> %s' % (r['score'], best))
    print('paste best.json into the designer (Paste settings) to see the shape')


def main(argv=None):
    ap = argparse.ArgumentParser(prog='canoe_analysis')
    ap.add_argument('--conditions', help='conditions file (default conditions.json)')
    sub = ap.add_subparsers(dest='cmd', required=True)
    sub.add_parser('conditions')
    s = sub.add_parser('analyze')
    s.add_argument('designs', nargs='+')
    s.add_argument('-c', '--condition', default='calm-lake', help="name, comma list, or 'all'")
    s.add_argument('-o', '--out')
    s = sub.add_parser('matrix')
    s.add_argument('designs', nargs='+')
    s.add_argument('-o', '--out', help='CSV path')
    s = sub.add_parser('optimize')
    s.add_argument('design')
    s.add_argument('-c', '--condition', required=True)
    s.add_argument('--vary', help='comma list of parameters (default beam,depth,rocker,secExp,planExp,fine,angle)')
    s.add_argument('--bound', action='append', help='name=lo:hi, repeatable')
    s.add_argument('--unlink', action='store_true', help='vary bow and stern separately (name b_x / s_x)')
    s.add_argument('--pop', type=int)
    s.add_argument('--gens', type=int, default=30)
    s.add_argument('--seed', type=int, default=1)
    s.add_argument('-o', '--out')
    a = ap.parse_args(argv)
    C = load_conditions(a.conditions)
    for k in ('condition',):
        v = getattr(a, k, None)
        if v and v != 'all' and any(n not in C for n in v.split(',')):
            sys.exit('unknown condition %s; try: %s' % (v, ', '.join(C)))
    dict(conditions=cmd_conditions, analyze=cmd_analyze, matrix=cmd_matrix, optimize=cmd_optimize)[a.cmd](a, C)


if __name__ == '__main__':
    main()
