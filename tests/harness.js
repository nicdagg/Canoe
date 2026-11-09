// Loads pieces of the designer page (src/designer.html) into Node so they can be tested without a browser.
'use strict';
var fs = require('fs'), path = require('path');
var SRC = fs.readFileSync(path.join(__dirname, '..', 'src', 'designer.html'), 'utf8');

// Text of a top-level `function NAME(` or `var NAME =` declaration inside the page script, found by brace matching.
function block(name) {
  var m = new RegExp('\\n  (function ' + name + '\\(|var ' + name + ' = )').exec(SRC);
  if (!m) throw new Error('not found in designer.html: ' + name);
  var i = m.index + 1, depth = 0, q = null, isFn = /^function/.test(m[1]);
  for (var k = i; k < SRC.length; k++) {
    var c = SRC[k];
    if (q) { if (c === '\\') k++; else if (c === q) q = null; continue; }
    if (c === '/' && SRC[k + 1] === '/') { k = SRC.indexOf('\n', k); continue; }
    if (c === '/' && SRC[k + 1] === '*') { k = SRC.indexOf('*/', k) + 1; continue; }
    if (c === "'" || c === '"' || c === '`') { q = c; continue; }
    if (c === '{' || c === '[' || c === '(') depth++;
    else if (c === '}' || c === ']' || c === ')') { depth--; if (isFn && c === '}' && depth === 0) return SRC.slice(i, k + 1); }
    else if (c === ';' && depth === 0) return SRC.slice(i, k + 1);
  }
  throw new Error('unterminated: ' + name);
}
function load(names, extra) {
  var code = names.map(block).join('\n') + '\n' + (extra || '') + '\nreturn {' + names.map(function (n) { return n + ':' + n; }).join(',') + '};';
  return new Function(code)();
}
var DEF_SHARED = { length: 193, beam: 33.5, depth: 13, mid: 0, tumble: 0, tumbleAt: 60, hullLb: 55, payLb: 330 };
var DEF_END = { rocker: 2.4, rise: 3.5, sheerExp: 2.5, angle: 70, radius: 18, secExp: 2.4, planExp: 2.0, fine: 0.8, tlen: 60 };
function design(shared, end) {
  var p = Object.assign({}, DEF_SHARED, shared || {});
  Object.keys(DEF_END).forEach(function (k) { p['b_' + k] = p['s_' + k] = (end && k in end) ? end[k] : DEF_END[k]; });
  return p;
}
var PRESETS = {
  default: design(),
  tripper: design({ length: 192, beam: 35, depth: 14, hullLb: 60, payLb: 400 }, { rocker: 2.5, rise: 4, angle: 68, radius: 20, secExp: 2.6, planExp: 2.0, fine: 0.8 }),
  'lake-cruiser': design({ length: 180, beam: 32, depth: 12.5, hullLb: 50, payLb: 330 }, { rocker: 1.5, rise: 3, angle: 72, radius: 16, secExp: 2.4, planExp: 2.2, fine: 0.85 }),
  solo: design({ length: 156, beam: 29, depth: 12, hullLb: 35, payLb: 220 }, { rocker: 2, rise: 3, angle: 70, radius: 14, secExp: 2.2, planExp: 2.0, fine: 0.85 }),
  'kids-pack-boat': design({ length: 84, beam: 24, depth: 8, hullLb: 12, payLb: 45 }, { rocker: 0.75, rise: 2.5, angle: 75, radius: 8, secExp: 3.0, planExp: 2.6, fine: 0.85, tlen: 30 }),
  'fast-tourer': design({ length: 204, beam: 30, depth: 12, hullLb: 45, payLb: 330 }, { rocker: 1, rise: 3, angle: 75, radius: 24, secExp: 2.0, planExp: 2.0, fine: 0.95 })
};
module.exports = { SRC: SRC, block: block, load: load, design: design, PRESETS: PRESETS };
