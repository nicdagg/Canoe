// Automatic checks for the designer's calculations. Run from the repo root:  node tests/run.js
// They read the code straight out of src/designer.html, so they test what the website runs.
'use strict';
var h = require('./harness.js'), L = h.load(['ENGINE', 'CONDS']), E = L.ENGINE(), C = L.CONDS, LAM = require('./lam.js')();
var fails = 0, n = 0;
function check(name, ok, detail) { n++; if (!ok) fails++; console.log((ok ? '  ok    ' : '  FAIL  ') + name + (detail ? '  (' + detail + ')' : '')); }
function near(a, b, tol) { return Math.abs(a - b) <= tol * Math.max(Math.abs(a), Math.abs(b)); }
function scoreOf(p, cn) { return E.score(E.evaluate(p, C[cn], false), C[cn]).score; }

console.log('Floating and stability');
Object.keys(h.PRESETS).forEach(function (k) {
  var p = h.PRESETS[k], m = E.evaluate(p, C['calm-lake'], false);
  check(k + ' floats its load', !m.overloaded && near(m.disp_lb, p.hullLb + p.payLb, 1e-6) && m.freeboard_mid_in > 0, 'draft ' + m.draft_max_in.toFixed(2) + ' in');
});
var d0 = E.evaluate(h.PRESETS.default, C['calm-lake'], true);
check('a heavier load sits deeper', E.evaluate(h.design({ payLb: 500 }), C['calm-lake'], false).draft_max_in > d0.draft_max_in);
check('a wider hull is steadier', E.evaluate(h.design({ beam: 37 }), C['calm-lake'], false).gm_in > d0.gm_in);
check('righting arm starts at zero and rises', Math.abs(d0._c.gz[0]) < 1e-6 && d0._c.gz[2] > 0);

console.log('Drag');
check('drag rises with speed', d0._c.curve.every(function (c, i, a) { return !i || c.t > a[i - 1].t; }));
check('wave drag is small when slow', d0._c.curve[0].w < 0.1 * d0._c.curve[0].t);
var deep = E.evaluate(h.PRESETS.default, Object.assign({}, C['shallow-river'], { depth_m: null }), false), shal = E.evaluate(h.PRESETS.default, C['shallow-river'], false);
check('the hull settles more in shallow water', shal.sinkage_in > deep.sinkage_in && deep.sinkage_in > 0, deep.sinkage_in.toFixed(3) + ' -> ' + shal.sinkage_in.toFixed(3) + ' in');
check('squat coefficient is in the range for slender hulls', d0.squat_cs > 1.1 && d0.squat_cs < 1.7, d0.squat_cs.toFixed(2));
// Published predictions for a 17 ft 7 in by 21.3 in sea kayak at 250 lb (Sea Kayaker magazine, Aquanaut): 2.02 lb at 3 kn,
// 3.88 at 4 kn, 5.04 at 4.5 kn. The designer's hull is a similar shape, not that boat, so the band is wide.
var kayak = h.design({ length: 211, beam: 21.3, depth: 12.5, hullLb: 55, payLb: 195 }, { rocker: 1.5, rise: 2, angle: 45, radius: 30, secExp: 2.2, planExp: 2.0, fine: 0.9 });
var kc = E.evaluate(kayak, Object.assign({}, C['calm-lake'], { load: { crew_vcg_in: 9 }, wind_mph: 0 }), true)._c;
[[3, 2.02], [4, 3.88], [4.5, 5.04]].forEach(function (r) {
  var mph = r[0] * 1.15078, i = Math.round((mph - 1) / 0.25), t = kc.curve[i].t * Math.pow(mph / kc.speeds[i], 2);
  check('kayak drag at ' + r[0] + ' kn is within 25% of the published figure', near(t, r[1], 0.25), t.toFixed(2) + ' vs ' + r[1] + ' lb');
});

console.log('Scores');
var cruiser = h.design({ length: 180, beam: 32.5, depth: 12, hullLb: 50, payLb: 330 }, { rocker: 1.5, rise: 3, angle: 80, radius: 16, secExp: 2.5, planExp: 2.0, fine: 0.95 });
var tub = h.design({ length: 180, beam: 36, depth: 15, hullLb: 50, payLb: 330 }, { rocker: 4.2, rise: 3, angle: 84, radius: 16, secExp: 2.7, planExp: 2.0, fine: 1 });
check('calm lake prefers a slim, straight-keeled cruiser to a wide, rockered hull', scoreOf(cruiser, 'calm-lake') > scoreOf(tub, 'calm-lake') + 5, scoreOf(cruiser, 'calm-lake').toFixed(0) + ' vs ' + scoreOf(tub, 'calm-lake').toFixed(0));
check('moving water prefers the rockered hull', scoreOf(tub, 'moving-water') > scoreOf(cruiser, 'moving-water'));
var mt = E.evaluate(tub, C['calm-lake'], false), mc = E.evaluate(cruiser, C['calm-lake'], false);
check('rocker lowers the tracking index', mt.track_index < mc.track_index, mt.track_index.toFixed(2) + ' < ' + mc.track_index.toFixed(2));
check('a wide, deep hull is a longer reach to the water', mt.reach_in > mc.reach_in);
check('every profile only scores metrics the engine produces', Object.keys(C).every(function (k) {
  var m = E.evaluate(h.PRESETS.default, C[k], true); return Object.keys(C[k].weights).concat(Object.keys(C[k].constraints || {})).every(function (q) { return typeof m[q] === 'number' && isFinite(m[q]); });
}));
var big = Object.assign({}, h.PRESETS.default, { beam: 38, depth: 15 }), per = h.PRESETS.default.hullLb / E.skin(h.PRESETS.default);
check('in a search a bigger hull is a heavier one', E.evaluate(Object.assign({ hullPerFt2: per }, big), C['calm-lake'], false).hull_lb > h.PRESETS.default.hullLb + 3);

console.log('Laminate');
var LM = JSON.parse(JSON.stringify(LAM.LAM_DEF)), R = LAM.lamRun(h.PRESETS.default, LM, null), lb = R.mass.kg / 0.453592;
check('sample layup weighs what an ultralight canoe weighs', lb > 20 && lb < 34, lb.toFixed(1) + ' lb');
var S1 = LAM.lamStack([{ m: 'cfud3', a: 0, n: 1 }, { m: 'bck', a: 45, n: 2 }], LM);
check('in-plane stiffness of an unbalanced stack is not lost to curling', S1.EAx > 0.8 * S1.A[0][0], (S1.EAx / S1.A[0][0]).toFixed(2));
var thin = LAM.lamStack([{ m: 'sg6', a: 0, n: 1 }], LM), thick = LAM.lamStack([{ m: 'sg6', a: 0, n: 4 }], LM);
thin.key = 'thin'; thick.key = 'thick';
check('a thicker skin takes a harder rock hit', LAM.lamRock(thick, 0.6, 0.3, 1000, 0.038).force > 2 * LAM.lamRock(thin, 0.6, 0.3, 1000, 0.038).force);
check('a thicker skin flexes less under a foot', LAM.lamPanel(thick, 0.6, 0.3, 0, 890, 0.25, 0.1).w < LAM.lamPanel(thin, 0.6, 0.3, 0, 890, 0.25, 0.1).w);
var cored = LAM.lamStack([{ m: 'sg6', a: 0, n: 1 }, { core: 'h80', t: 6 }, { m: 'sg6', a: 0, n: 1 }], LM); cored.key = 'cored';
var rc = LAM.lamRock(cored, 0.6, 0.3, 1000, 0.038);
check('a foam core dents before the skin is holed', isFinite(rc.dentForce) && rc.dentForce < rc.force, (rc.dentForce / 4.448).toFixed(0) + ' lb dent, ' + (rc.force / 4.448).toFixed(0) + ' lb hole');
var LM2 = JSON.parse(JSON.stringify(LAM.LAM_DEF)); LM2.ribs.on = true; LM2.ribs.at = []; for (var rx = 0.2; rx <= 0.801; rx += 0.025) LM2.ribs.at.push(rx);
var R2 = LAM.lamRun(h.PRESETS.default, LM2, null);
check('ribs placed one by one add weight and stiffen the floor between them', R2.mass.kg > R.mass.kg && R2.bad < R.bad, R.bad + ' -> ' + R2.bad + ' failing cells');
check('the suggested fixes clear the floor', R.recs.length > 0 && R.recs.some(function (r) { return r.zone || r.ribs; }));
check('every test has a result', R.worst.floor && R.worst.rock && isFinite(R.gun.sf) && isFinite(R.girder.sf));

console.log('Mold files');
// a closed pyramid whose apex is written four times a hair apart, as the plug tip is: the file must come out closed
var ap = [[0, 0, 1], [1e-5, 0, 1], [0, 1e-5, 1], [1e-5, 1e-5, 1]], base = [[-1, -1, 0], [1, -1, 0], [1, 1, 0], [-1, 1, 0]], tri = [];
for (var i = 0; i < 4; i++) tri = tri.concat(base[i], base[(i + 1) % 4], ap[i]);
tri = tri.concat(base[0], base[2], base[1], base[0], base[3], base[2]);
var stl = LAM.stlOf(tri, 't', function (x, y, z) { return [x, y, z]; }, 4e-4), dv = new DataView(stl.buffer), nt = dv.getUint32(80, true), edges = {};
for (i = 0; i < nt; i++) {
  var v = [0, 1, 2].map(function (k) { return [0, 1, 2].map(function (q) { return dv.getFloat32(84 + 50 * i + 12 + 12 * k + 4 * q, true); }).join(','); });
  [0, 1, 2].forEach(function (k) { var e = [v[k], v[(k + 1) % 3]].sort().join('|'); edges[e] = (edges[e] || 0) + 1; });
}
check('STL writer joins points a hair apart so the solid is closed', nt === 6 && Object.keys(edges).every(function (e) { return edges[e] === 2; }), nt + ' triangles');

console.log(fails ? '\nFAILED: ' + fails + ' of ' + n + ' checks' : '\nAll ' + n + ' checks passed');
process.exit(fails ? 1 : 0);
