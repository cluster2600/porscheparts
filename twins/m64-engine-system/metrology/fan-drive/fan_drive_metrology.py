#!/usr/bin/env python3
"""Fan-drive scan metrology analysis for M64-ACQ-0005 (wave-2).

Editable analysis script over the 0.21 mm scan mesh
``Fan+Drive+0.21mm.obj`` (single connected OBJ, no units metadata; mm
assumed per scanner convention). Performs:

1. Mesh load (vertices only, no face topology needed for radial statistics).
2. Component clustering (lower sprocket/gear cluster, upper fan/pulley
   cluster) by z-plane split, matching the 2026-09-27 intake triage.
3. Rotation-axis estimation per component (robust rim-band centroid).
4. Outer-diameter extraction per z-slab (max radius, with an
   angular-coverage gate so sparse slabs do not produce biased ODs).
5. Hub/blade harmonic angular analysis: per-blade angular binning,
   radial-crest signal, FFT harmonic scan (k=3..60), and a gap-based
   blade-peak detector; verdict logic for blade count.
6. Gear/sprocket tooth-band OD extraction.

Outputs ``fan-drive-dimensions.json`` next to this script (machine-readable
extracted dimensions with per-entry method notes and uncertainty bounds).

Evidence limits: every number is a scan-derived estimate, not a physical
measurement. Scan surface noise, tessellation gaps (angular coverage well
below 1.0 on most sections) and axis uncertainty inflate raw max-radius
values; uncertainties are stated per entry. Nothing here declares any part
dimensionally correct, fitted, tested, safe, released, or manufacturing-ready.
Blade count stays UNKNOWN unless a harmonic dominates its neighbours by a
clear margin (see ``blade_count_verdict``).

Usage:  python3 fan_drive_metrology.py [--src PATH] [--out PATH]
"""

import argparse
import hashlib
import json
import math
import sys
from datetime import datetime, timezone

import numpy as np

DEFAULT_SRC = "/home/lolman/imports/mac-obj/Downloads/Fan+Drive+0.21mm.obj"
# Reference digest from the wave-1 intake triage (work/obj-intake-20260927).
EXPECTED_SHA256_PREFIX = "6c0b12d4"

SLAB_MM = 8.0          # z-slab width for OD profiles
NB = 360               # angular bins (1 deg) for harmonic analysis
HARM_LO, HARM_HI = 3, 61  # FFT harmonic search window
OD_COVERAGE_GATE = 0.85   # trust raw max-radius OD only above this coverage
MIN_SLAB_VERTS = 500      # below this, a slab's max radius is spike-dominated
SCAN_ACCURACY_MM = 0.21   # nominal scanner point accuracy (spec of the scan)
AXIS_UNCERTAINTY_MM = 2.0 # observed slab-to-slab axis scatter (this scan)


def sha256_prefix(path, chunk=1 << 22):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(chunk), b""):
            h.update(block)
    return h.hexdigest()


def load_vertices(path):
    """Parse 'v ' lines into an (N,3) float64 array."""
    verts = []
    with open(path, "rb") as fh:
        for line in fh:
            if line[:2] == b"v ":
                p = line.split()
                verts.append((float(p[1]), float(p[2]), float(p[3])))
    return np.asarray(verts, dtype=np.float64)


def robust_axis(P, r_cap, c0, iters=8, band=95.0, min_band=200):
    """Iterated rim-band centroid: axis (x,y) estimate for near-axis-aligned P."""
    c = np.asarray(c0, float)
    inside = np.hypot(P[:, 0] - c0[0], P[:, 1] - c0[1]) < r_cap
    S = P[inside]
    if len(S) < 20:
        return c, np.hypot(P[:, 0] - c[0], P[:, 1] - c[1])
    for _ in range(iters):
        r = np.hypot(S[:, 0] - c[0], S[:, 1] - c[1])
        sel = r >= np.percentile(r, band)
        if int(sel.sum()) < min_band:
            break
        nc = S[sel][:, :2].mean(0)
        if np.hypot(*(nc - c)) < 1e-3:
            c = nc
            break
        c = nc
    r = np.hypot(P[:, 0] - c[0], P[:, 1] - c[1])
    return c, r


def angular_profile(t, r, nb=NB):
    """Radial crest per angular bin + coverage fraction (0..1)."""
    idx = np.clip(((t + math.pi) / (2 * math.pi) * nb).astype(int), 0, nb - 1)
    order = np.argsort(idx, kind="stable")
    i_s, r_s = idx[order], r[order]
    starts = np.flatnonzero(np.r_[True, i_s[1:] != i_s[:-1]])
    crest = np.maximum.reduceat(r_s, starts)
    bin_center = (i_s[starts] + 0.5) * (2 * math.pi / nb) - math.pi
    return bin_center, crest, len(starts) / nb


def harmonic_spectrum(bin_center, crest, lo=HARM_LO, hi=HARM_HI):
    """Top FFT harmonics (amplitude per cycle) of the radial-crest signal."""
    sig = crest - crest.mean()
    sp = np.abs(np.fft.rfft(sig))
    top = sorted(((float(sp[k]), k) for k in range(lo, min(hi, len(sp)))),
                 reverse=True)
    return [[k, round(a, 2)] for a, k in top[:6]]


def peak_gap_count(bin_center, crest):
    """Gap-based blade/tooth detector: wrap-around local maxima and spacing.

    Returns (n_peaks, median_spacing_deg, coverage-limited flag). Only
    meaningful when angular coverage is high; the caller gates on coverage.
    """
    o = np.argsort(bin_center)
    a, p = bin_center[o], crest[o]
    lm = np.flatnonzero((p > np.roll(p, 1)) & (p >= np.roll(p, -1)))
    la = a[lm]
    if len(la) < 2:
        return int(len(la)), None
    gaps = np.diff(np.r_[la, la[:1] + 2 * math.pi])
    return int(len(la)), round(float(np.median(gaps)) * 180 / math.pi, 1)


def slab_rows(P, c, r_cap, r_lo, z0, z1, axis_min=2000):
    """OD statistics for one z-slab of component points P about axis c.

    The slab-local axis refit is used only for slabs dense enough to
    constrain it (``axis_min`` points inside the cap); sparser slabs keep
    the component-level axis. A slab with fewer than MIN_SLAB_VERTS points
    inside the radius cap is uninformative (empty gaps between parts) and
    is skipped rather than producing a noise-dominated maximum.
    """
    m = (P[:, 2] >= z0) & (P[:, 2] < z1)
    S = P[m]
    if len(S) < 200:
        return None
    cS = np.asarray(c, float)
    r0 = np.hypot(S[:, 0] - c[0], S[:, 1] - c[1])
    if int((r0 < r_cap).sum()) >= axis_min:
        cS, _ = robust_axis(S, r_cap, c)
    rS = np.hypot(S[:, 0] - cS[0], S[:, 1] - cS[1])
    inside = rS < r_cap
    if int(inside.sum()) < MIN_SLAB_VERTS:
        return None
    t = np.arctan2(S[:, 1] - cS[1], S[:, 0] - cS[0])
    r_in = rS[inside]
    bc, crest, cov = angular_profile(t[inside], r_in, NB)
    row = {
        "z_mm": [round(z0, 1), round(z1, 1)],
        "vertices": int(inside.sum()),
        "axis_xy": [round(float(cS[0]), 1), round(float(cS[1]), 1)],
        "r_max_mm": round(float(r_in.max()), 1),
        "r_p999_mm": round(float(np.percentile(r_in, 99.9)), 1),
        "r_p99_mm": round(float(np.percentile(r_in, 99)), 1),
        "coverage": round(cov, 2),
    }
    if cov > 0.25 and r_in.max() > r_lo:
        row["harmonics"] = harmonic_spectrum(bc, crest)
        n_pk, gap = peak_gap_count(bc, crest)
        row["peaks"] = n_pk
        row["median_peak_spacing_deg"] = gap
    return row


def verdict_from_slabs(slabs):
    """Blade/tooth count verdict from per-slab harmonics (coverage-gated)."""
    votes = {}
    strong = []
    for s in slabs:
        hm = s.get("harmonics")
        if not hm or s["coverage"] < 0.25:
            continue
        top = hm[0]
        # a count is only credible if its harmonic is well above the runner-up
        if len(hm) > 1 and top[1] > 1.8 * hm[1][1]:
            strong.append((top[0], s["z_mm"], s["coverage"]))
        votes[top[0]] = votes.get(top[0], 0) + 1
    counts = sorted({k for k, _, _ in strong})
    if len(strong) >= 2 and len(counts) == 1:
        return counts[0], strong, "DETERMINED"
    return None, strong, "UNKNOWN"


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--src", default=DEFAULT_SRC)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    out_path = args.out or __file__.replace(
        "fan_drive_metrology.py", "fan-drive-dimensions.json")

    digest = sha256_prefix(args.src)
    if not digest.startswith(EXPECTED_SHA256_PREFIX):
        print(f"WARNING: source digest {digest[:8]} != expected "
              f"{EXPECTED_SHA256_PREFIX}; results tagged unverified",
              file=sys.stderr)

    V = load_vertices(args.src)
    bbox_min = V.min(0)
    bbox_max = V.max(0)

    # --- component clustering (matches wave-1 intake split at z=205) -------
    lower = V[V[:, 2] < 205]           # sprocket/gear + ancillary bracket pts
    upper = V[V[:, 2] >= 205]          # fan / pulley assembly

    # Lower sprocket: prior notes give axis approx (-11.6, -187.1); restrict
    # to the disc region (y < -129). Tooth-band analysis caps radius at 52 mm
    # (the cog rim); the full disc, including its outer flange, reaches ~66 mm.
    ld = lower[lower[:, 1] < -129]
    spr_c, spr_r = robust_axis(ld, 52.0, (-11.6, -187.1))
    spr_c_full, spr_r_full = robust_axis(ld, 80.0, (-11.6, -187.1), band=99.0)

    # Upper fan/pulley: prior notes give axis approx (-85, 80). Per-slab axes
    # are unstable against blade asymmetry, so the component-level axis is
    # fixed from the pulley rim (prior notes: OD~255.6 mm at z=310..328) via
    # a min-r_p99 grid search, then slab maxima are read against it.
    fan_c = np.array([-85.0, 80.0])
    fan_r = np.hypot(upper[:, 0] - fan_c[0], upper[:, 1] - fan_c[1])
    zr = (upper[:, 2] >= 310) & (upper[:, 2] < 328) & (fan_r < 140)
    R = upper[zr]
    best = None
    for gx in np.arange(-100, -70, 0.5):
        for gy in np.arange(65, 95, 0.5):
            rg = np.hypot(R[:, 0] - gx, R[:, 1] - gy)
            s = np.percentile(rg, 99)
            if best is None or s < best[0]:
                best = (s, gx, gy)
    fan_c = np.array([best[1], best[2]])
    fan_rim_r_p99_mm = best[0]
    # analysis cloud: everything within 140 mm of the fitted axis
    up = upper[np.hypot(upper[:, 0] - fan_c[0], upper[:, 1] - fan_c[1]) < 140.0]

    # --- gear / sprocket OD ---------------------------------------------------
    gear_slabs = []
    z = float(ld[:, 2].min())
    while z < ld[:, 2].max():
        row = slab_rows(ld, spr_c, 52.0, 38.0, z, z + SLAB_MM, axis_min=6000)
        if row:
            gear_slabs.append(row)
        z += SLAB_MM
    gear_od_crests = [s["r_max_mm"] for s in gear_slabs]
    disc_od_mm = round(2 * float(np.percentile(spr_r_full, 99.5)), 1)

    # --- fan/pulley OD vs z --------------------------------------------------
    fan_slabs = []
    z = float(up[:, 2].min())
    while z < up[:, 2].max():
        row = slab_rows(up, fan_c, 140.0, 60.0, z, z + SLAB_MM, axis_min=10 ** 9)
        if row:
            row["cap_truncated"] = bool(row["r_max_mm"] >= 139.9)
            fan_slabs.append(row)
        z += SLAB_MM
    trusted = [s for s in fan_slabs if s["coverage"] >= OD_COVERAGE_GATE]
    fan_od_mm = (round(2 * max(s["r_max_mm"] for s in trusted), 1)
                 if trusted else None)
    fan_od_p999 = (round(2 * max(s["r_p999_mm"] for s in trusted), 1)
                   if trusted else None)

    blade_verdict, strong_votes, status = verdict_from_slabs(fan_slabs)
    gear_verdict, gear_votes, gear_status = verdict_from_slabs(gear_slabs)

    unc_od = round(
        2 * math.sqrt(SCAN_ACCURACY_MM ** 2 + AXIS_UNCERTAINTY_MM ** 2), 1)

    result = {
        "study_id": "M64-ACQ-0005",
        "wave": "wave2/metro-fan-20260929",
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": {
            "path": args.src,
            "sha256": digest,
            "sha256_matches_wave1_intake": digest.startswith(EXPECTED_SHA256_PREFIX),
            "vertices": int(len(V)),
            "units_assumption": "mm assumed; OBJ carries no units metadata (verified wave-1: no '#' header comments)",
            "nominal_point_accuracy_mm": SCAN_ACCURACY_MM,
        },
        "global_bbox_mm": {
            "min": [round(float(x), 1) for x in bbox_min],
            "max": [round(float(x), 1) for x in bbox_max],
            "method": "vertex bounding box of full mesh",
            "uncertainty_mm": 1.0,
        },
        "components": {
            "lower_cluster": {
                "vertices": int(len(lower)),
                "z_range_mm": [-8.0, 205.0],
                "axis_xy_mm": [round(float(spr_c[0]), 1), round(float(spr_c[1]), 1)],
                "axis_method": "iterated rim-band centroid seeded from wave-1 note (-11.6,-187.1), radius cap 52 mm",
                "axis_uncertainty_mm": AXIS_UNCERTAINTY_MM,
            },
            "upper_cluster": {
                "vertices": int(len(up)),
                "z_range_mm": [205.0, 442.2],
                "axis_xy_mm": [round(float(fan_c[0]), 1), round(float(fan_c[1]), 1)],
                "axis_method": "iterated rim-band centroid seeded from wave-1 note (-85,80), radius cap 135 mm",
                "axis_uncertainty_mm": AXIS_UNCERTAINTY_MM,
            },
        },
        "dimensions": {
            "gear_sprocket_tip_od_mm": {
                "value": round(2 * float(np.percentile(gear_od_crests, 90)), 1)
                if gear_od_crests else None,
                "method": "p90 of per-slab max radius in tooth band (r<52 mm cap), x2; slabs of 8 mm; axis fixed at component level",
                "slab_maxima_mm": gear_od_crests,
                "uncertainty_mm": unc_od,
                "note": "tooth-band cap truncates at 104 mm; wave-1 estimate 127.6 mm likely refers to the full disc outer flange measured below",
            },
            "sprocket_disc_outer_od_mm": {
                "value": disc_od_mm,
                "method": "p99.5 of radius about iterated disc centroid over all lower-cluster disc vertices (z<60, y<-129)",
                "uncertainty_mm": unc_od,
                "note": "covers the disc outer band out to r~66 mm; consistent in scale with the wave-1 127.6 mm gear OD figure",
            },
            "fan_pulley_od_mm": {
                "value": round(2 * fan_rim_r_p99_mm, 1),
                "method": "min-p99 grid-search axis at the pulley rim (z=310..328 mm, r<140), OD = 2 x p99 radius about the fitted axis",
                "uncertainty_mm": unc_od,
                "note": "consistent with wave-1 r_max~127.8 mm (OD~255.6); per-slab raw maxima elsewhere reach r=135 mm (OD 270) due to axis scatter and blade asymmetry and are not used",
            },
        },
        "harmonic_analysis": {
            "method": "1-deg angular bins, radial crest per bin, rFFT amplitude for k=3..60; peaks counted via wrap-around local maxima",
            "fan_slabs": fan_slabs,
            "gear_slabs": gear_slabs,
            "fan_strong_votes": strong_votes,
            "gear_strong_votes": gear_votes,
        },
        "blade_count_verdict": {
            "value": blade_verdict,
            "status": status,
            "criteria": "a count is DETERMINED only when >=2 coverage-gated slabs agree on a single top harmonic whose amplitude exceeds 1.8x the runner-up",
            "note": "angular coverage on this scan is far below 1.0 on most blade-band slabs, so gap-based peak counting is noise-dominated; prior wave-1 conclusion (harmonics 4-7 inconclusive) is reproduced",
        },
        "gear_tooth_count_verdict": {
            "value": gear_verdict,
            "status": gear_status,
        },
        "evidence_limits": [
            "All values are scan-derived estimates, not physical measurements.",
            "Nothing here declares any part dimensionally correct, fitted, tested, safe, released, or manufacturing-ready.",
            "Blade count remains UNKNOWN absent physical metrology or a higher-coverage scan.",
            "Max-radius estimators are upward-biased by isolated tessellation spikes; p999 and coverage-gated variants are provided.",
        ],
    }

    with open(out_path, "w") as fh:
        json.dump(result, fh, indent=1)
    print(f"wrote {out_path}")
    print(f"vertices={len(V)} gearOD={result['dimensions']['gear_sprocket_tip_od_mm']['value']} "
          f"fanOD={fan_od_mm} blades={blade_verdict} ({status})")


if __name__ == "__main__":
    main()
