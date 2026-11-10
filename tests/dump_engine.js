// Prints the page engine's metrics for a list of [design, water] pairs, as JSON (used by compare_kit.py).
'use strict';
var h = require('./harness.js'), L = h.load(['ENGINE', 'CONDS']), E = L.ENGINE();
var out = JSON.parse(process.argv[2]).map(function (c) {
  var p = h.PRESETS[c[0]], m = E.evaluate(p, L.CONDS[c[1]], false), s = E.score(m, L.CONDS[c[1]]);
  return { p: p, m: m, score: s.score };
});
console.log(JSON.stringify(out));
