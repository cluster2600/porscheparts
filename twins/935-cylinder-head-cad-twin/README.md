# 935 cylinder head: CAD twin, rebuilt top-down

> **Study twin. Not measured, not functional, not released.** It reconstructs
> the Wolfe Classics 935 Xtreme head scan (SHA-256 `4623d5d3…c766486`,
> 1 OBJ unit = 1 mm by owner instruction, no physical calibration). Unobserved
> geometry is closed by declared hypotheses listed in
> [hypotheses.json](hypotheses.json); none is a measurement.

## Why this directory exists

The earlier line repaired the scan from the bottom up: about seventy studies
under `docs/research/935-*` tried to admit, one evidence class at a time,
surfaces for the scan's 928 open boundary loops. On 2026-11-06 the owner froze
that line ([notice](../reference-935-cylinder-head/README.md)). Two measured
facts motivated the change:

- 87 loops of 20 mm or more hold 67% of the 99,876 open edges. They sit at fin
  roots and deep in the ports, where the scanner never looked. They are
  occlusions, not defects; no local admission rule can fill them honestly.
- The machined faces of the scan are excellent: the deck plane fits at
  0.040 mm RMS over 3,573 mm². The head is mostly plates, cylinders and
  extrusions along its bore axis, so it fits naturally top-down.

The twin is therefore built from fitted datums and an inside/outside field,
and progress is measured by one number that can only rise: the share of the
acquired scan surface the twin explains within tolerance.

```mermaid
flowchart TB
  subgraph OLD["Frozen: bottom-up repair (about 70 studies)"]
    direction LR
    O1["928 open loops"] --> O2["admit a surface<br/>one evidence class at a time"]
    O2 --> O3["0 of 124 large loops admissible"]
    O3 --> O4["no closed solid,<br/>no twin"]
  end
  subgraph NEW["Top-down twin (this directory)"]
    direction LR
    N1["fitted datums<br/>deck 0.040 mm RMS"] --> N2["winding-number<br/>occupancy"]
    N2 --> N3["closed bare head<br/>+ tagged hypotheses"]
    N3 --> N4["scorecard:<br/>share of scan explained"]
  end
  OLD -. "owner decision 2026-11-06" .-> NEW
  classDef stop fill:#fde2e1,stroke:#c0392b,color:#1a1a1a;
  classDef ok fill:#e3f1e6,stroke:#2e7d32,color:#1a1a1a;
  class O3,O4 stop;
  class N3,N4 ok;
```

Every surface of the twin belongs to exactly one evidence class, and only one
class can count as observed:

```mermaid
flowchart LR
  SCAN["acquired scan facets"] --> OBS["observed<br/>within 0.2 mm of the scan<br/>(grey)"]
  GAP["regions the scanner never saw"] --> INF["inferred closure<br/>H01, H02, H04<br/>(orange)"]
  FIT["fitted rods"] --> HW["hardware: 10 studs<br/>separate bodies<br/>(blue)"]
  NONE["not observable from a surface"] --> HYP["analytic hypotheses<br/>H03, H05, H06<br/>(magenta, not yet modelled)"]
  INF -. "retired only by CT, rescan or drawing" .-> OBS
  HYP -. "retired only by specification" .-> OBS
  classDef ok fill:#e3f1e6,stroke:#2e7d32,color:#1a1a1a;
  classDef open fill:#fff4d6,stroke:#b7791f,color:#1a1a1a;
  class OBS ok;
  class INF,HYP open;
```

## Chain and selected tools

```mermaid
flowchart LR
  S["Scan OBJ<br/>(private, hash-checked)"] --> F["P1 fit_frame<br/>datums, studs"]
  F --> O["P1b occupancy<br/>libigl winding number"]
  O --> T1["T1 surface_mesh<br/>closed bare head"]
  O --> T2["T2 build_brep<br/>build123d/OCCT bands"]
  T1 --> SC["Scorecard<br/>NVIDIA Warp, independent"]
  T2 --> SC
  T1 --> D["decimate<br/>pymeshlab"]
  D --> TH["T3 sim_thermal<br/>Gmsh + CalculiX"]
  T1 --> U["T4 export_usd<br/>OpenUSD stage"]
  T1 --> P["T5 print study<br/>3MF, fit-check only"]
  H["hypotheses.json"] -.-> U
  classDef ok fill:#e3f1e6,stroke:#2e7d32,color:#1a1a1a;
  classDef open fill:#fff4d6,stroke:#b7791f,color:#1a1a1a;
  classDef stop fill:#fde2e1,stroke:#c0392b,color:#1a1a1a;
  class F,O,T1,SC ok;
  class D,TH,U,P open;
  class T2 stop;
```

| Role | Selected tool | Script |
|---|---|---|
| Datums, stud separation | NumPy/SciPy fits on acquired facets | [fit_frame.py](source/fit_frame.py) |
| Inside/outside of the open scan | libigl fast winding number (CGAL/MeshLib/libigl scan route) | [occupancy.py](source/occupancy.py) |
| Closed bare-head surface | scikit-image marching cubes, trimesh checks | [surface_mesh.py](source/surface_mesh.py) |
| Editable B-rep | build123d 0.13 / OCCT (OCP 8.0.1) | [build_brep.py](source/build_brep.py) |
| Fin faces, port sections | NumPy/SciPy fits on acquired facets and on the occupancy field | [fit_fins.py](source/fit_fins.py), [fit_ports.py](source/fit_ports.py) |
| Body stack, port lofts | build123d / OCCT, one process per band | [fin_stack.py](source/fin_stack.py), [port_loft.py](source/port_loft.py) |
| Independent scorecard | NVIDIA Warp BVH queries, trimesh oracle | [score_twin.py](source/score_twin.py) |
| Simulation surface | pymeshlab topology-preserving decimation (recon image) | [decimate.py](source/decimate.py) |
| Thermal FE screen | Gmsh HXT + CalculiX 2.21 (cadsim image) | [sim_thermal.py](source/sim_thermal.py) |
| OpenUSD stage | OpenUSD 26.11 (`usd-core`) + ComplianceChecker | [export_usd.py](source/export_usd.py) |

The private inputs and outputs live under `work/935-cad-twin/` (ignored by
Git). Only code, fitted scalar parameters and statistics are committed, as
the owner decided on 2026-11-06; the STEP, meshes and USD stay private and
rebuild from the code. [run_twin.sh](source/run_twin.sh) replays the chain.

## Results

### P1 datums ([frame.json](params/frame.json))

| Datum | Fit on acquired facets |
|---|---|
| Deck (combustion face), defines Z | plane, 3,573 mm², RMS 0.040 mm, p95 0.068 mm |
| Register recess | Ø113.88 mm, radial RMS 0.29 mm |
| Chamber shoulder | Ø92.80 mm, radial RMS 0.22 mm |
| High-B / low-B flange planes | RMS 0.33 / 0.14 mm; within 0.17° / 0.48° of the frame |
| Cam-housing side | not one plane: pads on several levels over about 4 mm |
| Studs (hardware) | 10 rods, Ø6.4–8.0 mm fits of threaded M8-class studs: 6 cam-side (4 × ≈51 mm, 2 × ≈20 mm proud), 2 per flange (≈21–23 mm) |

Two short rod-like features (Ø4.6 × 7 mm and Ø6.4 × 8.7 mm proud) fail the
stud test and stay in the body, flagged as H08.

### T1 closed bare-head surface

The libigl winding-number field at 0.25 mm gives 1,095,128 mm³ inside. Of
that, 239,664 mm³ of voxels have 0.2 < w < 0.8: the surface transition band
plus the unobserved regions. Marching cubes yields a single **watertight,
consistently wound** surface of 7.08 M triangles enclosing 1,095,597 mm³.
Its genus is 437, far above what a real head needs: closure handles in the
unobserved fin gaps and passages, part of the H01/H02/H04 footprint.

### Independent scorecard ([scorecard-t1.json](params/scorecard-t1.json))

The checker shares no code with the producers. It re-reads the original OBJ,
re-derives the hardware exclusion and measures with its own Warp kernel; a
trimesh oracle re-measures a random sample:

```mermaid
sequenceDiagram
  participant P as producers (fit_frame, occupancy, surface_mesh)
  participant F as params/frame.json
  participant C as score_twin.py
  participant W as NVIDIA Warp BVH
  participant O as trimesh oracle
  P->>F: declared frame and stud rods
  P->>C: twin surface (private STL)
  C->>C: re-read original OBJ, verify SHA-256
  C->>C: re-derive hardware exclusion from F
  C->>W: scan facets to twin, twin facets to scan
  W-->>C: distances
  C->>O: 5,000 random scan facets
  O-->>C: distances, compared within 1e-3 mm
  C-->>F: scorecard JSON (scalars only)
```

![Cumulative share of acquired scan area against distance to the T1 twin](media/scorecard-t1-cdf.png)

| Metric | T1 |
|---|---|
| Acquired scan area within 0.1 mm of the twin | 89.5% |
| Acquired scan area within 0.2 mm of the twin | **99.4%** of 146,967 mm² (studs excluded) |
| Scan → twin distance | median 0.044, p95 0.118, p99 0.166 mm |
| Twin area supported by the scan (≤ 0.2 mm) | **87.9%** |
| Twin area inferred (hypotheses) | 12.1%, 21,450 mm² |
| Warp vs trimesh oracle on 5,000 samples | max difference 1.2e-5 mm |

The 0.1 mm residual of T1 is the 0.25 mm voxel pitch, not the scan. By
zone, the deck, fin and cam bands score alike (p95 0.114–0.130 mm).

### T1s: observed vertices snapped onto the scan ([summary](params/t1s-snap-summary.json), [scorecard](params/scorecard-t1s.json))

[snap_surface.py](source/snap_surface.py) moves each T1 vertex whose closest
scan point is within 0.3 mm onto that point (2.97 M of 3.54 M vertices),
rejecting any triangle that would turn by more than 60°. It runs until
rejection converges (34 rounds). Snapping both sides of the thinnest walls
folded 4,722 faces, so
[unsnap_intersections.py](source/unsnap_intersections.py) returns those
vertices and one ring around them to T1 until pymeshlab finds no
self-intersection (3 rounds, 6,363 vertices). Connectivity never changes.

| Metric | T1 | **T1s** |
|---|---|---|
| Scan area within 0.1 mm | 89.5% | **99.0%** |
| Scan → twin p95 | 0.118 mm | **0.015 mm** |
| Twin area supported by the scan | 87.9% | 87.4% |
| Watertight, consistent winding, self-intersections | yes, yes, 0 | yes, yes, 0 |

T1s is the reference twin surface.

### T3 steady thermal screen ([thermal-screen.json](params/thermal-screen.json))

Declared hypothesis case, uncorrelated with any engine: generic cast
aluminium (k = 150 W/m·K), chamber wall fixed at 220 °C, every other face
cooled by air at 40 °C with h = 80 W/m²·K. Mesh: Gmsh HXT inside the
marching-cubes surface of the occupancy field coarsened to 1.0 mm (400k
triangles, watertight, genus 9). Solver: CalculiX 2.21, iterative Cholesky.

| Quantity | 1.0 mm surface | 0.75 mm surface |
|---|---|---|
| Tetrahedra / nodes | 4,949,566 / 892,919 | 9,611,548 / 1,721,933 |
| Elements with minSICN < 0.1 (none inverted) | 0.41% | 0.37% |
| Temperature min / mean / p95 / max (°C) | 146.6 / 189.3 / 214.6 / 220.0 | 127.5 / 188.3 / 214.5 / 220.0 |
| Heat entering at the chamber | 1,643.4 W | 1,680.1 W |
| Convective loss recomputed independently | 1,648.0 W (0.28%) | 1,683.3 W (0.19%) |

Global quantities agree between the levels: mean within 0.5%, p95 within
0.04%, heat within 2.2%. The minimum moves by 19 °C. The finer surface
resolves thinner fin tips, so the coldest point depends on geometry
resolution and is **not converged**. Both the surface and the mesh change
between levels, so this is a resolution check rather than a pure mesh study.

The first attempt failed because the deck used node set `NALL` before
defining it ([attempt 1](params/thermal-attempt-1.json)). The deck writer now
defines it. fTetWild was stopped after 2 h 42 min of CPU without output.

### T4 OpenUSD stage ([usd-summary.json](params/usd-summary.json))

`/Head935` (Z-up, millimetres) holds:

- the T1s display surface (600k triangles) with per-face colour: grey is
  observed, orange inferred (12.8% of area);
- the 10 studs as hardware cylinders;
- the datums as customData.

All 30 OpenUSD 26 validators report no finding. The NVIDIA usd-convert-cad
and omni.asset_validator pass needs the SimReady image (10 GB compressed),
which does not fit on this host's disk yet.

### T5 print study ([print-summary.json](params/print-summary.json))

A single-object 3MF of T1s in millimetres: 7,081,318 triangles, watertight,
consistent winding. A streaming re-read gives exactly the same volume
(1,095,212.3 mm³). The file is labelled as a fit-check study object, never
an engine part or a metal build file.

### T2 editable B-rep: measured negative result

The band-stack B-rep was tried on a 10 mm slab (z 20–30 mm) and stopped
rather than tuned:

| Variant | Cost | Outcome |
|---|---|---|
| B-spline loops (approximation) | > 120 s for one band | stopped |
| B-spline loops (periodic interpolation, 0.5 mm) | 190 s for one band | invalid solid, 35% excess volume |
| Polygon loops (0.05 mm), glue fuse tree | 0.64 s per band, 230 s fuse for 90 prisms | 41 slices gave 41 bands; fused result invalid (13 solids, 55k faces) |

Sloped port and dome walls defeat band merging, and OCCT cannot glue
hundreds of dense prisms into one valid solid. A full-body editable B-rep
therefore needs a real feature tree: each fin as one extrusion of its
observed mid-plane outline, a revolved deck/register/chamber, and ports as
lofts through observed sections. That is the next milestone. T1 already
carries simulation, print and USD.

### v1 feature tree: deck-plate baseline ([features](params/deck-features.json), [score](params/deck-features-score.json))

[deck_features.py](source/deck_features.py) starts the editable feature tree
on the deck zone. It fits analytic features to acquired facets:

- the outer sides and corner radius (6.3 mm);
- the register recess Ø113.88 mm with its floor at z = 2.17 mm;
- the four stud passages (from iteration 2, Ø10.58–10.93 mm).

It builds them as a valid 16-face build123d solid (private STEP), and scores
that zone with the scorecard's Warp kernel. Progress is tracked per iteration:

| Iteration | Change | Median | p95 | Within 0.2 mm |
|---|---|---|---|---|
| 0 baseline | plate, register recess, 2 passages | 0.78 mm | 5.62 mm | 31% |
| 1 | chamber dome: sphere R 56.44 mm fitted to 48,013 facets (RMS 0.24 mm), cut inside the Ø92.80 shoulder | 0.43 mm | 4.00 mm | 41% |
| 2 | four stud passages found by seeding at the recorded pattern: Ø10.58–10.93 mm on about 86.2 × 85.6 mm. The two "passages" of iteration 0 were other features | **0.29 mm** | **3.05 mm** | **45%** |

| 3 (not adopted) | valve throats fitted: Ø47.94 and Ø46.48 mm, axes about 22° from Z, radial RMS 0.23 / 0.31 mm. Cutting them, with or without a coaxial "boss" (Ø≈30 mm, RMS 0.59 mm, not credible), lowered the score | 0.31 mm | 3.29 / 3.20 mm | 44% |

| 4 | two-level outline: deck face y −65.15…71.10 mm, body steps out at z = 2.75 mm (272 mm² of step faces) | **0.22 mm** | **2.72 mm** | **49%** (81% within 1 mm) |

Iteration 3 is kept as data in the features file, but not in the solid. The throat fits look right; the score drops because the port
interior beyond them (guide bosses, seat rings) is not modelled yet.

Remaining gaps: port interiors behind the throats, the plug bores, the
flange bosses on the outline, and the plate-top level.
Each fix must raise this score; T1s (p95 0.015 mm) stays the reference
surface meanwhile.

### v1 body stack: fins, port lofts and chamber dome ([fin faces](params/fin-faces.json), [port fit](params/port-fit.json), [loft check](params/port-loft-check.json), [error breakdown](params/error-breakdown-v1-stack-f-shell.json))

[fin_stack.py](source/fin_stack.py) builds the whole body as one extrusion per
interval between measured horizontal faces. Each band's sketch is the
occupancy contour at its mid-level; fitted features are then cut from the
bands. The bands stay a compound of individually valid solids. Every run is
kept with its summary and scorecard (`params/v1-body-stack-<run>-summary.json`,
`params/scorecard-v1-stack-<run>[-shell].json`):

| Run | Change | Scored on | p50 | p95 | Within 0.2 mm | Within 0.5 mm | Within 1 mm | Twin area supported |
|---|---|---|---|---|---|---|---|---|
| a | levels from a 0.1 mm detector only | compound | 0.96 mm | 9.65 mm | 28.3% | 39.3% | 50.8% | n/a |
| b | fin faces fitted by [fit_fins.py](source/fit_fins.py) added as boundaries | compound | 0.26 mm | 1.62 mm | 44.1% | 66.9% | 85.6% | n/a |
| c | extrusion direction fixed (see below) | shell | 0.11 mm | 0.90 mm | 65.2% | 84.7% | 96.7% | 56.9% |
| d | 13 fin faces as tilted planes | shell | 0.11 mm | 0.90 mm | 64.8% | 85.7% | 96.6% | 58.1% |
| e | two port lofts cut in | shell | 0.10 mm | 0.87 mm | 67.9% | 87.1% | 96.8% | 57.8% |
| **f** | chamber dome cut, thick cam-side band split | shell | 0.10 mm | 0.85 mm | 69.9% | 88.3% | 96.9% | 59.9% |
| g | trial: interpolated sketches and dome ended at 42 mm | shell | 0.10 mm | 0.87 mm | 69.3% | 87.9% | 96.8% | 59.0% |
| h | trial: interpolated sketches only | shell | 0.10 mm | 0.86 mm | 69.7% | 88.1% | 96.8% | 59.7% |

The first five columns are scan → twin on the whole acquired surface
(146,967 mm², studs excluded). **Run f is the reference**; T1s (p95 0.015 mm)
remains the reference surface.

**Compound and shell.** The compound's tessellation contains the faces two
touching bands share, 1.2 to 1.4 million mm² of them. A scan facet lying on
such a hidden face scores as explained although the model has material on both
sides. From run c on, `fin_stack.py` also writes the outer shell: of each pair
of caps meeting on a boundary, only the parts the other band does not cover
are kept. Scored on the shell, run e reads p95 0.87 mm and 67.9% within
0.2 mm, against 0.74 mm and 69.8% on its compound. The compound scorecards of
runs c to e are kept beside the shell ones; runs a and b predate the shell and
their figures are optimistic by a similar margin.

What each step found:

- **Fins (a → b).** The fins are plates normal to the bore axis: 13 top and 15
  bottom faces, median top pitch 5.74 mm. Their faces are cast and spread over
  1 to 2 mm of Z, so the 0.1 mm detector of run a found levels near only 7 of
  the 28 and left single bands from z = 7.6 to 38.1 mm and from 50.0 to
  69.4 mm. `fit_fins.py` histograms up-facing and down-facing facets
  separately at 0.25 mm and fits every face as a level and as a plane.
- **A defect in `band_solid` (b → c).** `extrude()` followed the face normal,
  which the contour orientation decides, so every band of runs a and b sat one
  thickness below its interval (asked 41.80–44.12 mm, built 39.48–41.80 mm).
  The direction is now explicit, checked at build time and covered by a test.
  Runs a and b are kept as measured. The T2 slab trial above used the same
  function and has not been repeated.
- **Tilt (c → d): neutral.** The top faces tilt by a median 0.53° towards
  azimuth ≈ 40° in XY, a steady ramp of about 1.8 mm across the head; the
  bottom faces are flat (median 0.10°). A face becomes a tilted plane when its
  plane fit has at most 0.8 of the level fit's RMS and tilts at least 0.3°;
  one candidate (z = 78.97 mm) is demoted because it would cross its
  neighbour. On the shell the tilt gains 1.0 point within 0.5 mm and loses
  0.4 point within 0.2 mm. It is kept because the ramp is measured, not
  because it scores.
- **Ports (d → e).** [fit_ports.py](source/fit_ports.py) finds the enclosed
  cavities of the occupancy field, follows the two that reach a flange face and
  measures a 48-ray section every 3 mm. [port_loft.py](source/port_loft.py)
  lofts them through periodic splines and adopts a loft only when it explains
  more of its own wall than the stack does. The ports are named by flange
  side; which one is intake is not established.
- **Chamber dome and cam side (e → f).** The fitted sphere (R 56.44 mm) is cut
  inside the fitted shoulder; each band first regains the dome footprint
  where the occupancy is material at the band's top, so valve pockets stay
  open. The 48 mm band above z = 87.2 mm is split at two occupancy steps
  (92.9 and 94.4 mm). The deck zone goes from 70.0% to 75.2% within 0.2 mm.
- **Two rejected trials (g, h).** Ending the dome at 42 mm, where a flat ring
  at the register floor starts to replace the sphere, restores that ring but
  gives up the sphere in rings where most facets still follow it. Taking each
  sketch from the occupancy interpolated at the exact mid-level, instead of
  the nearest 0.25 mm slice, also scores lower. Both stay available as options
  and neither is adopted.

| Port | Loft | Wall seen by the scanner | Port-wall scan within 0.2 mm: stack d → loft |
|---|---|---|---|
| `port_y_minus` | 18 sections, 51 mm, Ø 41–43 mm equivalent | 77% of wall points | 40.8% → 96.2% (5,591 mm²) |
| `port_y_plus` | 9 sections, 24 mm, Ø 38–41 mm equivalent | 92% of wall points | 43.4% → 90.0% (3,017 mm²) |

Each loft stops where its section stops being a tube, before the valve pocket.
The unseen share of each wall is winding-number closure, i.e. hypothesis H04.
The section profiles are geometry and stay private. The other 8 enclosed
cavities above 5,000 mm³ (two of them sit on stud passages) give no run
of closed sections and are not lofted: they are open pockets, not tubes, and
need a different feature.

The bands are built and tessellated in a process pool, and the STEP is written
only on request. The body of run b takes 58 s with 8 workers against 295 s
serially; run f, with its tilt, loft and dome cuts in 34 bands, takes about
5 minutes with 12 workers.

Where run f still misses, from [error_breakdown.py](source/error_breakdown.py)
on its shell, in points of the whole scan area:

| Surface class (facet normal) | Scan area | Within 0.2 mm | Points outside 0.2 mm | Points outside 0.5 mm |
|---|---|---|---|---|
| sloped, 0.17 ≤ \|n_z\| ≤ 0.94 | 39.1% | 60.9% | 15.3 | 5.4 |
| up-facing horizontal | 21.0% | 66.3% | 7.1 | 2.7 |
| down-facing horizontal | 15.1% | 68.6% | 4.7 | 2.4 |
| vertical walls | 24.8% | 88.1% | 3.0 | 1.1 |

- The sloped class is mostly the fin edges: about 15% of the scan area lies
  on the rounded or chamfered rims of the 12 fins, which the prisms leave
  square. The corner is roughly 1.3 mm wide by 0.6 mm high, the same size as
  the scatter of the cast faces it starts from, so a rim feature has to be
  fitted per fin and cannot be a single radius.
- The horizontal classes are the cast fin faces themselves: their plane fits
  leave 0.25 to 0.6 mm RMS, so a planar face cannot bring them all within
  0.2 mm. Within 0.5 mm the whole model stands at 88.3%.
- Still staircase: the port bends and valve pockets beyond the lofts, and
  the other enclosed pockets.
- A few hundred mm² above z = 94 mm (the largest errors, up to 48 mm) belong
  to thin features the mid-level sketch of that band misses.

```mermaid
flowchart LR
  F["fitted features<br/>(numbers in Git)"] --> B["build123d solid<br/>(private STEP)"]
  B --> S["zone scorecard<br/>Warp kernel"]
  S -->|"gap found"| F
  S -->|"zone within tolerance"| N["next zone:<br/>fins, cam pads, ports"]
  classDef ok fill:#e3f1e6,stroke:#2e7d32,color:#1a1a1a;
  classDef open fill:#fff4d6,stroke:#b7791f,color:#1a1a1a;
  class F,B ok;
  class S,N open;
```

## Phase ledger

| Phase | Inputs | Output | Check | State |
|---|---|---|---|---|
| P0 freeze | owner decision | notices in the old twin README and `docs/ARCHIVE.md` | — | done |
| P1 datums | scan | [params/frame.json](params/frame.json) | plane/circle residuals recorded | done |
| P1b occupancy | scan, frame | private winding-number grid; [summary](params/occupancy-summary.json) | ambiguous volume reported | done |
| T1 surface | occupancy | private closed surface; [summary](params/t1-surface-summary.json) | watertight, winding, genus | done |
| Scorecard T1 | scan, frame, T1 | [scorecard-t1.json](params/scorecard-t1.json) | Warp vs trimesh oracle | done: 99.4% within 0.2 mm |
| T1s snap | T1, scan | private snapped surface; [summary](params/t1s-snap-summary.json) | connectivity unchanged, watertight, 0 self-intersections | done: p95 0.015 mm ([scorecard](params/scorecard-t1s.json)) |
| T2 B-rep v0 | occupancy | none | BRepCheck | measured negative result (see above) |
| Simulation surface | occupancy at 0.75 mm | private; [summary](params/sim-surface-mc075-summary.json) | watertight, genus 21 | done |
| T3 thermal | 1.0 mm surface | private deck and fields; [result](params/thermal-screen.json) | mesh quality, solver return, energy balance 0.28% | done at two levels; means agree, fin-tip minimum not converged |
| Screenshots | T1, scan, thermal | private renders (observed/inferred, scan deviation, thermal field); public [scorecard chart](media/scorecard-t1-cdf.png) | visual review | done |
| T4 USD | T1s, frame, hypotheses | private `.usdc`; [summary](params/usd-summary.json) | 30 OpenUSD validators | done, 0 findings |
| T5 print | T1s | private 3MF; [summary](params/print-summary.json) | streaming round trip | done, exact volume |
| v1 features | frame, scan | deck plate first: [features](params/deck-features.json) | zone scorecard | iteration 4: p95 2.72 mm (chamber, four passages, two-level outline) |
| v1 body stack | occupancy, scan, fin faces, port sections, deck features | private compound of band solids and its outer shell; [run f summary](params/v1-body-stack-f-summary.json) | whole-scan scorecard on the shell, per run | run f: p95 0.85 mm, 69.9% within 0.2 mm, 88.3% within 0.5 mm; next: per-fin rim feature, port bends and valve pockets, the other enclosed pockets as pocket features |
| Port CFD | v1 ports | OpenFOAM steady port flow | mesh/flux convergence | blocked by v1 ports |
| SimReady | T2 STEP | NVIDIA usd-convert-cad + omni.asset_validator | validator report | needs the 10 GB image on X1/Kali |
| AM study | T1/T2 | PicoGK supports, Adamantine cooldown | as in the earlier study | after v1 |

## Limits

- Distances are to the acquired surface. They say nothing about unobserved
  geometry, the specimen's true dimensions, its material or its function.
- The studs are hardware fitted as cylinders; their threads and tapped holes
  are hypotheses (H03).
- The thermal case is a declared hypothesis set, uncorrelated with an engine.
- Engine use, metal manufacture and any interface claim remain prohibited
  without the evidence named in the repository rules.
