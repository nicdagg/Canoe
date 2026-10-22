"""Calm-water resistance: skin friction plus Michell thin-ship wave resistance.

Friction uses the ITTC-1957 line on the wetted surface with a small form factor.
Wave-making uses Michell's integral, which suits long slender hulls such as canoes
and kayaks, extended to finite water depth (Srettensky/Tuck form) so shallow rivers
and lake edges show their resistance hump near the critical speed sqrt(g h).

The integral is written over the longitudinal wavenumber kx:

    R_w = (4 rho U^2 / pi) * Int |F(kx)|^2  kx k / (ky D(k)) dkx
    F   = Int Int  df/dx  Z(k, z)  exp(-i kx x) dx dz
    k tanh(k h) = kx^2 / k0,   k0 = g / U^2,   ky = sqrt(k^2 - kx^2)
    D   = tanh(k h) + k h sech^2(k h),   Z = cosh(k (z + h)) / cosh(k h)

which reduces to the classical deep-water Michell integral as h -> infinity. The
offsets are treated as piecewise linear in x and z and the transforms are taken
exactly over each panel, so the high-wavenumber tail does not alias.

Limitations: the hull is held at its static waterline (no dynamic sinkage or trim),
and thin-ship theory tends to overstate the humps and hollows of the curve.
"""
import math

import numpy as np

G = 9.80665
IN = 0.0254
LBF = 4.4482216
MPH = 0.44704
WATER = {'fresh': dict(rho=999.1, nu=1.139e-6), 'salt': dict(rho=1025.9, nu=1.188e-6)}
RHO_AIR = 1.225


def centreplane_offsets(H, up, nx=401, nz=28):
    """Half-breadth f(x, depth below waterline) on a uniform grid, metres."""
    m = H.model
    xa, xf = up['x_aft'], up['x_fwd']
    xs = np.linspace(xa, xf, nx)
    tau, h0 = up['trim_slope'], up['h0']
    zw = h0 + (xs - m.mid) * tau
    T = up['draft_max_in'] * 1.0001
    zeta = np.linspace(0, T, nz)
    f = np.zeros((nx, nz))
    for i, x in enumerate(xs):
        s = m.at(x, 61)
        zabs = zw[i] - zeta
        ok = zabs >= s.keel
        f[i, ok] = np.interp(zabs[ok], s.z, s.y)
    f[0, :] = 0
    f[-1, :] = 0
    return xs * IN, zeta * IN, f * IN


def _phi_exp(t, c):
    """exp(c) * Int_0^1 (1 - u) exp(t u) du, evaluated without overflow when t + c stays moderate."""
    t, c = np.broadcast_arrays(np.asarray(t, float), np.asarray(c, float))
    out = np.empty(t.shape)
    small = np.abs(t) < 1e-3
    ts = t[small]
    out[small] = np.exp(c[small]) * (0.5 + ts / 6 + ts * ts / 24)
    tl, cl = t[~small], c[~small]
    with np.errstate(over='ignore', invalid='ignore'):   # end nodes overflow in a half hat that is discarded
        out[~small] = (np.exp(tl + cl) - np.exp(cl) * (1 + tl)) / (tl * tl)
    return out


def _z_weights(a, zeta, shift=0.0):
    """Weights w_j so that sum_j f_j w_j = Int f(zeta) exp(a zeta + shift) dzeta for piecewise linear f.

    a has shape (nk,), zeta is a uniform grid. Returns (nk, nz).
    """
    d = zeta[1] - zeta[0]
    ad = a[:, None] * d
    c = a[:, None] * zeta[None, :] + shift
    right = d * _phi_exp(ad, c)       # hat over [zeta_j, zeta_j + d]
    left = d * _phi_exp(-ad, c)       # hat over [zeta_j - d, zeta_j]
    w = right + left
    w[:, 0] = right[:, 0]
    w[:, -1] = left[:, -1]
    return w


def _wavenumber(kx, k0, h):
    c = kx * kx / k0
    if not np.isfinite(h):
        return c
    k = np.maximum(c, np.sqrt(c / h))
    for _ in range(40):
        th = np.tanh(k * h)
        g = k * th - c
        dg = th + k * h * (1 - th * th)
        k = np.maximum(k - g / dg, 1e-9)
    return k


def _kx_min(k0, h):
    if not np.isfinite(h):
        return k0
    if k0 * h <= 1:                 # supercritical depth Froude number: divergent waves only
        return 0.0
    lo, hi = 1e-9, k0 * 1.0000001
    for _ in range(100):            # root of tanh(kx h) = kx / k0
        m = (lo + hi) / 2
        if math.tanh(m * h) > m / k0:
            lo = m
        else:
            hi = m
    return (lo + hi) / 2


def michell(offsets, U, depth=math.inf, rho=999.1, nk=1200):
    """Wave resistance in newtons at speed U (m/s) in water of the given depth (m)."""
    xs, zeta, f = offsets
    if U <= 0:
        return 0.0
    k0 = G / (U * U)
    dx = xs[1] - xs[0]
    kmax = 0.9 * math.pi / dx
    kmin = _kx_min(k0, depth)
    if kmin >= kmax:
        return 0.0
    # kx = kmin + s^2 removes the 1/ky singularity at the cusp-line wavenumber
    smax = math.sqrt(kmax - kmin)
    nodes, wts = np.polynomial.legendre.leggauss(8)
    edges = np.linspace(0, smax, nk // 8 + 1)
    s = ((edges[:-1, None] + edges[1:, None]) / 2 + (edges[1:, None] - edges[:-1, None]) / 2 * nodes).ravel()
    ws = ((edges[1:, None] - edges[:-1, None]) / 2 * wts).ravel()
    kx = kmin + s * s
    k = _wavenumber(kx, k0, depth)
    ky = np.sqrt(np.maximum(k * k - kx * kx, 1e-30))
    if np.isfinite(depth):
        th = np.tanh(k * depth)
        D = th + k * depth * (1 - th * th)
        # Z = cosh(k(h - zeta)) / cosh(k h) = (e^{-k zeta} + e^{k zeta - 2kh}) / (1 + e^{-2kh})
        e2 = np.exp(-2 * k * depth)
        Wz = (_z_weights(-k, zeta) + _z_weights(k, zeta, -2 * k[:, None] * depth)) / (1 + e2)[:, None]
    else:
        D = np.ones_like(k)
        Wz = _z_weights(-k, zeta)
    # x transform of piecewise linear f: dx * sinc^2(kx dx / 2) * sum f_n exp(-i kx x_n)
    sinc2 = np.sinc(kx * dx / (2 * math.pi)) ** 2
    E = np.exp(-1j * np.outer(kx, xs))
    Gx = (E @ f) * (dx * sinc2)[:, None]                 # (nk, nz)
    Fz = np.sum(Gx * Wz, axis=1)
    F2 = (kx * kx) * np.abs(Fz) ** 2                     # |i kx Int f Z e^{-i kx x}|^2
    integrand = F2 * kx * k / (ky * D) * 2 * s          # dkx = 2 s ds
    return 4 * rho * U * U / math.pi * float(np.sum(integrand * ws))


def form_factor(up):
    """Hoerner's streamlined-body form factor using the double-body equivalent diameter."""
    d = math.sqrt(4 * 2 * up['amax_in2'] / math.pi)
    r = d / up['lwl_in']
    return 1 + 1.5 * r ** 1.5 + 7 * r ** 3


def ittc57(Re):
    return 0.075 / (math.log10(Re) - 2) ** 2


def frontal_windage(H, up):
    """Hull area above the waterline seen head-on (ft^2) and side-on (ft^2)."""
    i = int(np.argmax(H.yr[:, -1] + H.yr.max(axis=1)))
    s = H.st[i]
    zw = float(up['zw'][i])
    m = s.z >= zw
    zz = np.concatenate([[zw], s.z[m]])
    yy = np.concatenate([[np.interp(zw, s.z, s.y)], s.y[m]])
    front = 2 * float(np.sum((yy[1:] + yy[:-1]) * np.diff(zz) / 2))
    above = np.clip(H.sheer - np.maximum(up['zw'], H.keel), 0, None)
    side = float(np.sum((above[1:] + above[:-1]) * np.diff(H.x) / 2))
    return front / 144, side / 144


def calm_water(H, up, speeds_mph, depth_m=math.inf, water='fresh', headwind_mph=0.0, offsets=None):
    """Resistance breakdown (lbf) at each speed. Returns a dict of arrays."""
    w = WATER[water]
    off = offsets or centreplane_offsets(H, up)
    S = up['wetted_ft2'] * 0.09290304
    L = up['lwl_in'] * IN
    k1 = form_factor(up)
    front_ft2, _ = frontal_windage(H, up)
    out = dict(speed_mph=np.asarray(speeds_mph, float), friction_lbf=[], wave_lbf=[], air_lbf=[], total_lbf=[],
               fn=[], fh=[], power_w=[])
    for v in speeds_mph:
        U = v * MPH
        Rf = 0.5 * w['rho'] * U * U * S * ittc57(U * L / w['nu']) * k1
        Rw = michell(off, U, depth_m, w['rho'])
        Ua = U + headwind_mph * MPH
        Ra = 0.5 * RHO_AIR * 0.9 * front_ft2 * 0.09290304 * Ua * abs(Ua)
        Rt = Rf + Rw + Ra
        out['friction_lbf'].append(Rf / LBF)
        out['wave_lbf'].append(Rw / LBF)
        out['air_lbf'].append(Ra / LBF)
        out['total_lbf'].append(Rt / LBF)
        out['fn'].append(U / math.sqrt(G * L))
        out['fh'].append(U / math.sqrt(G * depth_m) if np.isfinite(depth_m) else 0.0)
        out['power_w'].append(Rt * U)
    for k in list(out):
        out[k] = np.asarray(out[k], float)
    out['form_factor'] = k1
    return out


def speed_at_power(curve, watts):
    """Speed (mph) where the resistance curve needs the given effective power."""
    v, P = curve['speed_mph'], curve['power_w']
    if watts <= P[0]:
        return float(v[0] * (watts / P[0]) ** (1 / 3))
    if watts >= P[-1]:
        return float(v[-1])
    i = int(np.searchsorted(P, watts))
    return float(v[i - 1] + (v[i] - v[i - 1]) * (watts - P[i - 1]) / (P[i] - P[i - 1]))
