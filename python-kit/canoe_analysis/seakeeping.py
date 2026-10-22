"""Heave and pitch in head seas by strip theory, and what they mean in a given sea.

Each station is a 2D strip with Lewis-form added mass and Grim's approximation for
wave damping. Motions come from the relative-motion (Gerritsma-Beukelman) form of
ordinary strip theory with forward speed, the Smith correction for wave pressure
decaying under the hull, and added resistance in waves from the radiated energy.
Irregular seas are a JONSWAP spectrum from significant height, peak period and
peak enhancement (gamma 1 is a fully developed sea, 3.3 a fetch-limited chop).

Results are linear and best used to rank shapes against each other. Roll in beam
seas is not modelled: it depends more on the paddlers than on the hull.
"""
import math

import numpy as np

from .resistance import G, IN, LBF, MPH, WATER


def strips(H, up, n=60):
    """Sectional properties at n stations along the waterline, SI units."""
    m = H.model
    xs = np.linspace(up['x_aft'], up['x_fwd'], n + 2)[1:-1]
    out = dict(x=[], b=[], area=[], draft=[])
    for x in xs:
        s = m.at(x, 61)
        zw = up['h0'] + (x - m.mid) * up['trim_slope']
        if zw <= s.keel:
            out['x'].append(x); out['b'].append(0); out['area'].append(0); out['draft'].append(0)
            continue
        zz = np.linspace(s.keel, min(zw, s.z[-1]), 80)
        yy = np.interp(zz, s.z, s.y)
        out['x'].append(x)
        out['b'].append(2 * yy[-1])
        out['area'].append(2 * float(np.sum((yy[1:] + yy[:-1]) * np.diff(zz) / 2)))
        out['draft'].append(zw - s.keel)
    return {k: np.array(v) * (IN if k != 'area' else IN * IN) for k, v in out.items()}


def lewis_heave_coeff(b, t, area):
    """Lewis-form high-frequency heave added-mass coefficient C (a33 = rho pi b^2 / 8 * C)."""
    C = np.ones_like(b)
    ok = (b > 1e-6) & (t > 1e-6)
    H0 = np.where(ok, b / (2 * np.where(ok, t, 1)), 1)
    sig = np.where(ok, area / np.where(ok, b * t, 1), np.pi / 4)
    # keep inside the range where a Lewis form exists
    sig = np.clip(sig, 0.3, 0.95)
    r = (H0 - 1) / (H0 + 1)
    c1 = (3 + 4 * sig / np.pi) + (1 - 4 * sig / np.pi) * r * r
    disc = np.maximum(9 - 2 * c1, 0)
    a3 = (-c1 + 3 + np.sqrt(disc)) / c1
    a1 = r * (a3 + 1)
    C = np.where(ok, ((1 + a1) ** 2 + 3 * a3 ** 2) / (1 + a1 + a3) ** 2, 1.0)
    return C


def jonswap(w, hs, tp, gamma=3.3):
    """JONSWAP spectrum S(w) in m^2 s, normalised to the given significant height."""
    wp = 2 * np.pi / tp
    sig = np.where(w <= wp, 0.07, 0.09)
    S = (5 / 16) * hs * hs * wp ** 4 / w ** 5 * np.exp(-1.25 * (wp / w) ** 4)
    S = S * gamma ** np.exp(-((w - wp) ** 2) / (2 * sig * sig * wp * wp))
    m0 = np.trapezoid(S, w)
    return S * (hs * hs / 16) / m0 if m0 > 0 else S


def raos(H, up, lc, speed_mph, water='fresh', omegas=None):
    """Heave and pitch transfer functions in head seas, per metre of wave amplitude."""
    rho = WATER[water]['rho']
    if omegas is None:
        omegas = np.linspace(0.5, 9.0, 140)
    s = strips(H, up)
    x = s['x'] - up['lcb_in'] * IN          # about the centre of gravity, which sits over the LCB
    b, A, T = s['b'], s['area'], s['draft']
    Tm = np.where(b > 0, A / np.maximum(b, 1e-9), 0)
    U = speed_mph * MPH
    M = up['disp_lb'] * 0.45359237
    L = up['lwl_in'] * IN
    I55 = M * (lc.get('kyy_frac', 0.27) * L) ** 2
    a = rho * np.pi * b * b / 8 * lewis_heave_coeff(b, T, A)
    c = rho * G * b
    dx = np.gradient(x)
    da = np.gradient(a, x)
    out = dict(omega=omegas, omega_e=[], heave=[], pitch=[], rel_bow=[], raw=[], x=x)
    xb = x[int(0.85 * (len(x) - 1))]
    ib = int(0.85 * (len(x) - 1))
    for w in omegas:
        k = w * w / G
        we = w + k * U                      # head seas
        Abar = 2 * np.sin(np.clip(k * b / 2, 0, np.pi / 2)) * np.exp(-k * Tm)
        bb = rho * G * G * Abar ** 2 / we ** 3
        zeta_s = np.exp(-k * Tm) * np.exp(1j * k * x)          # effective wave per unit amplitude
        wst = 1j * w * zeta_s                                    # vertical orbital velocity

        def forces(e3, e5, za):
            Vr = 1j * we * e3 - x * 1j * we * e5 + U * e5 - za * wst
            zr = e3 - x * e5 - za * zeta_s
            f = -1j * we * a * Vr - bb * Vr - c * zr           # the U d(aVr)/dx term integrates to zero
            F3 = np.sum(f * dx)
            M5 = np.sum((x * (1j * we * a + bb) * Vr + x * c * zr) * dx) + U * np.sum(a * Vr * dx)
            return F3, M5, Vr, zr

        c3 = forces(1, 0, 0); c5 = forces(0, 1, 0); cw = forces(0, 0, 1)
        Amat = np.array([[-we * we * M - c3[0], -c5[0]], [-c3[1], -we * we * I55 - c5[1]]])
        rhs = np.array([cw[0], cw[1]])
        e3, e5 = np.linalg.solve(Amat, rhs)
        Vr = e3 * c3[2] + e5 * c5[2] + cw[2]
        zrel = e3 - xb * e5 - np.exp(1j * k * xb)               # bow motion relative to the actual wave
        bprime = bb - U * da
        raw = k / (2 * we) * np.sum(bprime * np.abs(Vr) ** 2 * dx)  # added resistance per amplitude^2
        out['omega_e'].append(we); out['heave'].append(e3); out['pitch'].append(e5)
        out['rel_bow'].append(zrel); out['raw'].append(max(raw, 0.0))
    for kk in ('omega_e', 'heave', 'pitch', 'rel_bow', 'raw'):
        out[kk] = np.array(out[kk])
    out['x_bow'] = xb
    out['bow_freeboard_m'] = _freeboard_at(H, up, xb / IN + up['lcb_in']) * IN
    return out


def _freeboard_at(H, up, x_in):
    m = H.model
    s = m.at(x_in, 31)
    return s.sheer - (up['h0'] + (x_in - m.mid) * up['trim_slope'])


def in_sea(R, hs_m, tp_s, gamma=3.3):
    """Significant motions, bow wetness chance per wave, and mean added resistance."""
    w = R['omega']
    S = jonswap(w, hs_m, tp_s, gamma)
    m0 = lambda tf: float(np.trapezoid(np.abs(tf) ** 2 * S, w))
    heave = 2 * math.sqrt(m0(R['heave']))
    pitch = 2 * math.sqrt(m0(R['pitch']))
    rel = m0(R['rel_bow'])
    f = R['bow_freeboard_m']
    wet = math.exp(-f * f / (2 * rel)) if rel > 0 else 0.0
    raw = 2 * float(np.trapezoid(R['raw'] * S, w))
    return dict(heave_sig_in=heave / IN, pitch_sig_deg=math.degrees(pitch), bow_rel_sig_in=2 * math.sqrt(rel) / IN,
                bow_wet_prob=wet, added_resistance_lbf=raw / LBF, bow_freeboard_in=f / IN)
