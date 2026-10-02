# Fan-drive metrology — wave-2 findings (M64-ACQ-0005)

Scan: `SCAN-FAN-DRIVE-0P21MM` (`Fan+Drive+0.21mm.obj`, sha256 `6c0b12d4…`,
1.26 M vertices, nominal 0.21 mm point accuracy, units undeclared).
Machine-readable results: `metrology-report.json` (built from
`fan-drive-dimensions.json` by `fan_drive_metrology.py`).
Status of every number: **scan-derived estimate, F1_envelope at best.**

## What this pass proves (honestly)

- **Two components, cleanly separated.** A lower sprocket/disc cluster
  (z −8…205, fitted axis (−2.9, −226.6) ± 2 mm) and an upper fan/pulley
  cluster (z 205…442, fitted axis (−83.5, 68.5) ± 2 mm). The z≈205 split
  from the wave-1 intake triage is reproduced with iterated rim-band
  centroids.
- **Outer-diameter estimates with stated uncertainty**: sprocket tooth-band
  tip OD ≥ 104 mm (search-cap truncated — a lower bound), lower disc outer
  flange OD 214.2 ± 4 mm, fan pulley rim OD 229.5 ± 4 mm.
- **Blade count is NOT determinable from this scan in this orientation.**
  The angular coverage of the blade-band slabs is 0.10–0.79 (most well below
  the gate); rFFT top harmonics scatter over k=3–5 between slabs with no
  slab pair agreeing under the dominance criterion (≥2 coverage-gated slabs,
  top harmonic > 1.8× runner-up). Verdict: **UNKNOWN**. This reproduces and
  extends the wave-1 conclusion ("harmonics 4–7 inconclusive").
- **Gear tooth count is NOT determinable either.** Tooth features are
  ~1–3 mm at 0.21 mm sampling; gear-slab coverage is 0.05–0.95 with peak
  counts up to 97 per slab and no agreement. Verdict: **UNKNOWN**.
- **Scale (mm) is consistent but NOT anchored.** See below.

## What this pass contradicts or corrects

Compared against `docs/research/obj-scan-intake-2026-09-27.md` (wave-1 note)
and the BOM cooling lines (`twins/m64-engine-system/bom/m64-bom-v1.json`):

1. **Wave-1 "pinion OD ≈ 127.6 mm" is reframed, not confirmed.** This pass
   measures the tooth-band tip OD truncated at the 52 mm search cap
   (≥ 104 mm) and the full disc outer flange at 214.2 mm. The wave-1 figure
   most likely refers to the outer flange measured differently; the two
   figures describe different features. Cite the wave-1 number with that
   caveat.
2. **Wave-1 "pulley r_max ≈ 127.8 mm (OD ≈ 255.6)" is superseded** by the
   axis-fitted rim measurement OD 229.5 ± 4 mm (z 310–328). Raw per-slab
   maxima reach r = 135 mm (OD 270) but are axis-scatter/blade-asymmetry
   artefacts, not used.
3. **Stage-ratio check stays open.** The only public geometry anchor — drive
   ratio ≈ 1:1.6 (FACT_public, 1996 OBD supplement) — cannot be verified
   from this scan: the tooth-band OD is capped and the scan includes the
   loose/idler pulley and elastic belt. Neither confirmed nor refuted.
4. **BOM M64B-CL-001** ("11-blade study target; blade count to confirm per
   M64-ACQ-0005"): this pass does **not** confirm 11 (or any) blade count.
   The 11-blade label remains a study target, not evidence.
5. **BOM M64B-CL-003** ("scan suggests r_max ~127.8 mm, unconfirmed"):
   update pointer — the best current scan value is pulley OD 229.5 ± 4 mm;
   still unconfirmed as a physical measurement.
6. **Scale hypothesis:** the observed bbox 325.2 × 398.7 × 450.1 mm cannot
   be compared against a published 993 fan-drive envelope — none exists in
   the repo or the public survey (fan pulley/blade dims are explicitly
   *non publiés*). The fastener-bore sanity check (upper pulley shaft bore
   ≈ 17.3 mm, plausible for a shaft seat at mm scale; lower pilot hole
   5.3 mm weak/artefact-prone) is *consistent* with mm but does not anchor
   it. **Scale verdict: UNRESOLVED — consistent, not anchored.**

## Link to the virtual bench

The 0D bench (`simulation/m64-virtual-bench/inputs-gap.md`, main repo) names
**cooling airflow as its bottleneck**: fan flow is a single FACT_public
point (1010 l/s @ 6100 rpm) with a linear-affinity HYPOTHESIS slope and a
60 %-effective-fraction ASSUMPTION — ask **M64-ACQ-BENCH-06**. Geometry from
this scan can narrow the CFD route (pulley/disc ODs, blade-band extents) but
cannot produce the flow-vs-rpm law; geometry alone does not close
BENCH-06.

## Next acquisition asks

1. **Rescan (re-scoped M64-ACQ-0005):** calibrated scale reference in frame;
   one cut plane perpendicular to each rotation axis; full 360° angular
   coverage of tooth band and blade band; idler pulley and elastic belt
   removed or masked. Unblocks blade count, tooth count, ratio check, scale.
2. **M64-ACQ-BENCH-06:** fan flow at 3 rpm points (Pitot/bellmouth) or a
   parametric disc-pressure CFD sweep in `simulation/993-fan-baseline`,
   plus shroud bypass estimate.
3. **Physical check on any 993 Turbo fan drive:** photo + caliper (blade
   count, both pulley ODs). Anchors scale and settles counts in one pass —
   cheapest path out of UNKNOWN.

## Standing evidence limits

Nothing here declares any part dimensionally correct, fitted, tested, safe,
released, or manufacturing-ready. Max-radius estimators are upward-biased by
tessellation spikes (p999/coverage-gated variants provided). Scan provenance
and licence remain unknown (see catalog record); do not publish or
redistribute.
