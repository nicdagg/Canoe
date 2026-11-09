"""Copy python-kit/conditions.json into the designer page, so the website and the Python kit score with the same water profiles.

    python3 tools/sync_conditions.py          # rewrite the CONDS line in src/designer.html
    python3 tools/sync_conditions.py --check  # exit 1 if they differ
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HTML = os.path.join(ROOT, 'src', 'designer.html')
data = json.load(open(os.path.join(ROOT, 'python-kit', 'conditions.json')))
conds = {k: v for k, v in data.items() if not k.startswith('_')}
line = '  var CONDS = ' + json.dumps(conds, separators=(',', ':'), ensure_ascii=False) + ';'
src = open(HTML, encoding='utf-8').read()
m = re.search(r'^  var CONDS = \{.*\};$', src, re.M)
assert m, 'CONDS line not found'
if '--check' in sys.argv:
    sys.exit(0 if m.group(0) == line else 'designer.html CONDS differs from python-kit/conditions.json; run tools/sync_conditions.py')
open(HTML, 'w', encoding='utf-8').write(src[:m.start()] + line + src[m.end():])
print('synced', len(conds), 'profiles')
