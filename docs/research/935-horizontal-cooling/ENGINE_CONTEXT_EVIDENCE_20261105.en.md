# Engine context and crankcase interference: evidence boundary

The engine in the current upright cooling-system scene is a PicoGK packaging
hypothesis, not a scan of a 935 engine. Its crankcase is a rectangular envelope;
its dimensions and relative placement are not measured 935 mounting data. The
scene uses one source unit as one millimetre only for display and calculations.

## Available geometry

The previously inventoried 917 engine-case scan is a flat-twelve reference and
cannot establish a 935 flat-six crankcase or fan mounting. A separate 935
cylinder-head scan is present, but its variant, scale and relationship to the
fan-drive scan have not been established. A complete, identified 935 crankcase
scan has not been found in the project inventory or the two Downloads folders
checked on 2026-11-05. This is a limited inventory, not proof that none exists.

## Historical context

Porsche's [Group C press kit, “Engines and gearboxes”](https://newsroom.porsche.com/dam/jcr%3Aa6f33b52-c47d-47b4-98c1-7e963661f587/40%2520Years%2520Group%2520C.pdf)
describes the **Type 935/76 engine used in the 956** as having a two-part
crankcase based on, and modified from, the 911 (930) Turbo unit. This is a
useful lead for sourcing a reference case. It does not identify the engine or
fan installation represented by our scans, prove compatibility with a
particular 935, or provide a dimensioned exterior or mounting interfaces.
Do not transfer its later 956/962 specifications to the scanned assembly.

## What the interference test shows

In one provisional upright pose, the existing CGAL screen detected 4,932 drive
triangles intersecting the engine proxy. The proxy's triangle coordinates were
verified against its 13 constituent PicoGK meshes. A second exact-predicate
screen attributed all 4,932 selected drive triangles to the crankcase box;
none intersected the six cylinder or six head envelopes in that static pose.
The private receipt, selected indices, per-part results and plot are in
`935-engine-proxy-part-attribution.tar.gz` on the
[private project release](https://github.com/cluster2600/porscheparts-935-private/releases/tag/935-rotor-parallel-20261104).

These are triangle-surface intersections against an artificial envelope. They
do not distinguish an oversimplified box, an incorrect pose, an intended
interface or actual interference. Translating the proxy until surfaces no
longer intersect is not a mounting solution.

## Evidence needed for a replacement

1. Identify the intended 935 engine variant and the physical provenance of the
   rotor, drive and any prospective engine reference.
2. Obtain a permissioned, dimensioned crankcase scan or CAD reference, and
   independently calibrate it with at least two dimensions on that same case.
3. Record mounting faces, hole patterns, axes and their uncertainty on both
   case and drive; register the geometry using those shared features.
4. Repeat the assembly interference and clearance checks against the measured
   case, including retention, tolerance and thermal conditions. Treat hidden
   gear, bearing and lubrication features as unknown until independently
   documented.

The current scene remains useful for visualization and method development; it
does not establish installation fit, mechanical performance or manufacturing
readiness.
