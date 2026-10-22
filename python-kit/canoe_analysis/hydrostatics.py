"""Upright and heeled hydrostatics from closed section polygons.

Each station is a closed polygon: the starboard half section from keel to sheer, a
straight line across at the sheer (the hull is treated as closed at the gunwale, so
results past gunwale immersion describe a decked hull), and the port half back down.
The immersed part of every section under an arbitrary waterline is integrated
exactly with Green's theorem, vectorized over all stations, so heel and trim cost
the same as the upright case.

Units: inches, pounds, degrees. x is from midship of the overall length (bow +).
"""
import math

import numpy as np

from .geometry import HullModel

LB_PER_IN3_FRESH = 62.4 / 1728
LB_PER_IN3_SALT = 64.0 / 1728
_G = 1 / math.sqrt(3)


class SampledHull:
    """Stations and closed section polygons for one design."""

    def __init__(self, params, NE=45, NP=61):
        self.model = m = HullModel(params)
        self.p = m.p
        st = m.stations(NE, NP)
        self.st = st
        self.x = np.array([s.x for s in st])
        self.keel = np.array([s.keel for s in st])
        self.sheer = np.array([s.sheer for s in st])
        self.yr = np.array([s.y for s in st])          # starboard half, keel to sheer
        self.zr = np.array([s.z for s in st])
        self.Y = np.concatenate([self.yr, -self.yr[:, ::-1]], axis=1)
        self.Z = np.concatenate([self.zr, self.zr[:, ::-1]], axis=1)


def clip_sections(Y, Z, phi_deg, h):
    """Area and centroid (body y, z) of each polygon below the line z cos(phi) - y sin(phi) = h.

    Heel phi is positive with the +y (starboard) side going down. h is per section.
    """
    c, s = math.cos(math.radians(phi_deg)), math.sin(math.radians(phi_deg))
    eta = Y * c + Z * s
    w = Z * c - Y * s - np.asarray(h, float).reshape(-1, 1)
    e0, e1 = eta, np.roll(eta, -1, axis=1)
    w0, w1 = w, np.roll(w, -1, axis=1)
    de, dw = e1 - e0, w1 - w0
    with np.errstate(divide='ignore', invalid='ignore'):
        tc = np.where(dw != 0, -w0 / dw, 0.0)
    in0, in1 = w0 <= 0, w1 <= 0
    ta = np.where(in0, 0.0, np.where(in1, tc, 0.0))
    tb = np.where(in1, 1.0, np.where(in0, tc, 0.0))
    tb = np.where(~in0 & ~in1, 0.0, tb)
    ta, tb = np.clip(ta, 0, 1), np.clip(tb, 0, 1)
    tm, dt = (ta + tb) / 2, (tb - ta) / 2
    A = np.zeros(Y.shape[0])
    Me = np.zeros_like(A)
    Mw = np.zeros_like(A)
    for g in (-_G, _G):
        t = tm + g * dt
        et, wt = e0 + t * de, w0 + t * dw
        A -= np.sum(wt * de * dt, axis=1)
        Me -= np.sum(et * wt * de * dt, axis=1)
        Mw -= np.sum(0.5 * wt * wt * de * dt, axis=1)
    ok = A > 1e-12
    ec = np.where(ok, Me / np.where(ok, A, 1), 0)
    zc_rot = np.where(ok, Mw / np.where(ok, A, 1), 0) + np.asarray(h, float)
    yb = ec * c - zc_rot * s
    zb = ec * s + zc_rot * c
    return np.maximum(A, 0), yb, zb


def trapz(v, x):
    return float(np.sum((v[1:] + v[:-1]) * (x[1:] - x[:-1]) / 2))


def _volume(H, phi, h0, tau):
    h = h0 + (H.x - H.model.mid) * tau * math.cos(math.radians(phi))
    A, yb, zb = clip_sections(H.Y, H.Z, phi, h)
    V = trapz(A, H.x)
    if V <= 0:
        return 0.0, 0.0, 0.0, 0.0, A
    return V, trapz(A * H.x, H.x) / V, trapz(A * yb, H.x) / V, trapz(A * zb, H.x) / V, A


def solve_level(H, vol, phi=0.0, tau=0.0):
    """Waterline offset h0 that floats volume vol at heel phi and fixed trim slope tau."""
    c, s = math.cos(math.radians(phi)), math.sin(math.radians(phi))
    rot = H.Z * c - H.Y * s
    lo, hi = float(rot.min()) - abs(tau) * H.model.L, float(rot.max()) + abs(tau) * H.model.L
    # Illinois false position: converges in a handful of volume evaluations
    flo, fhi = -vol, _volume(H, phi, hi, tau)[0] - vol
    side = 0
    for _ in range(60):
        m = hi - fhi * (hi - lo) / (fhi - flo) if fhi != flo else (lo + hi) / 2
        fm = _volume(H, phi, m, tau)[0] - vol
        if abs(fm) < 1e-7 * vol or hi - lo < 1e-7:
            return m
        if fm < 0:
            lo, flo = m, fm
            if side == -1:
                fhi /= 2
            side = -1
        else:
            hi, fhi = m, fm
            if side == 1:
                flo /= 2
            side = 1
    return m


def capacity(H, rho=LB_PER_IN3_FRESH):
    """Displacement with the water at the lowest point of the sheer (level), as the artifact reports."""
    return _volume(H, 0, H.p['depth'], 0)[0] * rho


def equilibrium(H, disp_lb, lcg=None, rho=LB_PER_IN3_FRESH):
    """Upright float: midship waterline height h0 and trim slope tau (positive is bow down).

    With lcg=None the hull floats level, as in the artifact.
    """
    vol = disp_lb / rho
    if lcg is None:
        return solve_level(H, vol), 0.0
    t0, t1 = 0.0, 0.002
    f = lambda t: _volume(H, 0, solve_level(H, vol, 0, t), t)[1] - lcg
    f0, f1 = f(t0), f(t1)
    for _ in range(30):
        if abs(f1) < 1e-4 or f1 == f0:
            break
        t0, t1, f0 = t1, t1 - f1 * (t1 - t0) / (f1 - f0), f1
        t1 = float(np.clip(t1, -0.05, 0.05))
        f1 = f(t1)
    return solve_level(H, vol, 0, t1), t1


def _wetted_area(H, zw):
    """Wetted surface from a triangle mesh between stations, both sides, square inches."""
    N = 25
    pts = []
    for i in range(len(H.x)):
        y, z = H.yr[i], H.zr[i]
        if zw[i] <= z[0]:
            pts.append(np.column_stack([np.full(N, H.x[i]), np.zeros(N), np.full(N, z[0])]))
            continue
        k = int(np.searchsorted(z, zw[i]))
        if k >= len(z):
            yy, zz = y, z
        else:
            f = (zw[i] - z[k - 1]) / (z[k] - z[k - 1])
            yy = np.append(y[:k], y[k - 1] + f * (y[k] - y[k - 1]))
            zz = np.append(z[:k], zw[i])
        sarc = np.concatenate([[0], np.cumsum(np.hypot(np.diff(yy), np.diff(zz)))])
        if sarc[-1] <= 0:
            pts.append(np.column_stack([np.full(N, H.x[i]), np.zeros(N), np.full(N, z[0])]))
            continue
        t = np.linspace(0, sarc[-1], N)
        pts.append(np.column_stack([np.full(N, H.x[i]), np.interp(t, sarc, yy), np.interp(t, sarc, zz)]))
    P = np.array(pts)
    a, b, c, d = P[:-1, :-1], P[1:, :-1], P[:-1, 1:], P[1:, 1:]
    t1 = 0.5 * np.linalg.norm(np.cross(b - a, c - a), axis=2)
    t2 = 0.5 * np.linalg.norm(np.cross(b - d, c - d), axis=2)
    return 2 * float(np.sum(t1 + t2))


def upright(H, disp_lb, lcg=None, rho=LB_PER_IN3_FRESH):
    """Full upright hydrostatics at a displacement. Returns a dict, inches and pounds."""
    h0, tau = equilibrium(H, disp_lb, lcg, rho)
    x, mid = H.x, H.model.mid
    zw = h0 + (x - mid) * tau
    V, lcb, _, kb, A = _volume(H, 0, h0, tau)
    hw = np.array([np.interp(min(zw[i], H.zr[i, -1]), H.zr[i], H.yr[i]) if zw[i] > H.keel[i] else 0.0
                   for i in range(len(x))])
    wet = np.where(hw > 1e-6)[0]
    if len(wet) == 0:
        raise ValueError('hull does not float at this load')
    xa = _wl_end(H, wet[0], wet[0] - 1, zw)
    xf = _wl_end(H, wet[-1], wet[-1] + 1, zw)
    lwl = xf - xa
    bwl = 2 * hw.max()
    awp = trapz(2 * hw, x)
    lcf = trapz(2 * hw * x, x) / awp
    it = trapz(2 / 3 * hw ** 3, x)
    il = trapz(2 * hw * (x - lcf) ** 2, x)
    imax = int(np.argmax(A))
    tmax = float(np.max(np.where(hw > 0, zw - H.keel, 0)))
    tx = zw[imax] - H.keel[imax]
    bx = 2 * hw[imax]
    draft_mid = float(np.interp(mid, x, zw))
    fb = H.sheer - zw
    disp = V * rho
    bmt, bml = it / V, il / V
    return dict(
        disp_lb=disp, vol_in3=V, h0=h0, trim_slope=tau,
        trim_in=tau * lwl, draft_mid_in=draft_mid, draft_max_in=tmax,
        freeboard_mid_in=float(np.interp(mid, x, fb)), freeboard_min_in=float(fb.min()),
        lwl_in=lwl, bwl_in=bwl, lwl_bwl=lwl / bwl, x_aft=xa, x_fwd=xf,
        amax_in2=float(A[imax]), x_amax=float(x[imax]),
        cb=V / (lwl * bwl * draft_mid) if draft_mid > 0 else 0.0,
        cb_true=V / (lwl * bwl * tmax), cp=V / (A[imax] * lwl), cm=A[imax] / (bx * tx),
        cwp=awp / (lwl * bwl),
        lcb_in=lcb, lcb_pct=100 * (lcb - (xa + xf) / 2) / lwl, lcf_in=lcf,
        kb_in=kb, bmt_in=bmt, kmt_in=kb + bmt, bml_in=bml, kml_in=kb + bml,
        awp_ft2=awp / 144, ppi_lb=awp * rho, wetted_ft2=_wetted_area(H, zw) / 144,
        mct_inlb=disp * bml / lwl, half_angle_entrance=_half_angle(H, hw, xf, 1),
        half_angle_run=_half_angle(H, hw, xa, -1), x=x, area=A, hw=hw, zw=zw,
        disp_length=(disp / 2240) / (lwl / 12 * 0.01) ** 3 if lwl > 0 else 0.0,
    )


def _wl_end(H, wet, dry, zw):
    """x where the keel crosses the waterline between a wet station and its dry neighbour."""
    if dry < 0 or dry >= len(H.x):
        return float(H.x[wet])
    kw, kd = H.keel[wet] - zw[wet], H.keel[dry] - zw[dry]
    f = float(np.clip(-kw / (kd - kw), 0, 1)) if kd > kw else 0.0
    return float(H.x[wet] + f * (H.x[dry] - H.x[wet]))


def _half_angle(H, hw, xe, sgn):
    """Waterline half angle at the end (degrees), from the slope over the last 5% of the waterline."""
    x = H.x
    wet = hw > 0
    xs, ys = x[wet], hw[wet]
    if len(xs) < 3:
        return 0.0
    span = 0.05 * (xs[-1] - xs[0])
    xi = xe - sgn * span
    yi = np.interp(xi, xs, ys)
    return math.degrees(math.atan2(yi, span))


def heeled(H, vol, phi, tau=0.0):
    """Centre of buoyancy (y, z) at heel phi with the volume and trim held."""
    h0 = solve_level(H, vol, phi, tau)
    V, _, yb, zb, _ = _volume(H, phi, h0, tau)
    return h0, yb, zb


def gunwale_clearance(H, phi, h0, tau):
    """Smallest height of the starboard gunwale above the heeled waterline (inches, + is dry)."""
    c, s = math.cos(math.radians(phi)), math.sin(math.radians(phi))
    yg, zg = H.yr[:, -1], H.zr[:, -1]
    h = h0 + (H.x - H.model.mid) * tau * c
    return float(np.min(zg * c - yg * s - h))
