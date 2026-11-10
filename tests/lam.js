// Loads the laminate calculations out of the designer page for tests.
'use strict';
var h = require('./harness.js');
var NAMES = ['ENGINE', 'LAM_FIBERS', 'LAM_RESINS', 'LAM_PROCESS', 'LAM_FABRICS', 'LAM_FAB', 'LAM_CORES', 'LAM_CORE', 'lamPlies', 'lamQbar', 'lamInv', 'lamStack', 'lamSF',
  'LAM_NAV', 'lamNavier', 'lamPanel', 'lamRock', 'LAM_IN', 'lamZoneHas', 'lamPlan', 'lcHas', 'lamGrid', 'lamClip', 'lamRaster', 'lamGrow', 'lamCov', 'lamGap', 'lamLabel',
  'lamRibXs', 'lamRibsEven', 'lamAssess', 'LAM_ROCK_OK', 'lamGradeOf', 'lamGrade', 'lamGun', 'lamOuter', 'lamSection', 'lamGirder', 'lamMass', 'lamRun', 'lamRecs', 'lcOval', 'LAM_DEF', 'stlOf'];
module.exports = function () {
  return h.load(NAMES, 'var clamp = function (v, a, b) { return Math.min(b, Math.max(a, v)); }; var E = ENGINE(), makeModel = E.makeModel, interp = E.interp, trapz = E.trapz;' +
    'LAM_FABRICS.forEach(function (f) { LAM_FAB[f[0]] = { id: f[0], name: f[1], gsm: f[2], form: f[3], fibers: f[4] }; });' +
    'LAM_CORES.forEach(function (c) { LAM_CORE[c[0]] = { id: c[0], name: c[1], rho: c[2], E: c[3], G: c[4], tau: c[5], up0: c[6], up1: c[7], sc: c[8] }; });');
};
