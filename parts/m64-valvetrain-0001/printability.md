# Printability screening — m64-valvetrain-0001 (honest, non-authorizing)

Screening note, not a process qualification. Per
[SAFETY.md](../../SAFETY.md), a calculation never authorizes manufacturing;
every component in this lane stays `prohibited_pending_engineering` (engine
risk class) until dimensional inspection, fitment and professional engineering
review exist.

## Scope

The five PicoGK meshes in `validation/run/` are voxelized (1.0 mm screen)
signed-distance fields, exported as STL (mm) with PicoGK 2.3.0 /
picogk.26.2. They are layout proxies of OHV-2V-lineage valve-ttrain forms
used for M64/60 digital-twin layout — not candidate LPBF parts.

## Observations against LPBF practice

- **Thin wall** — the bucket-follower cup wall defaults to 3.0 mm
  `[ASSUMPTION]`; printable in common stainless/aluminium LPBF windows,
  but the wall value itself is unsourced, so no build stress or
  supportstrategy claim applies.
- **Overhanging seat face** — the 45° valve seat face prints acceptably
  in LPBF without supports at that nominal angle, but the seat *width*
  (1.5 mm) is `[UNKNOWN]`; a real seat width must come from metrology
  before any geometry claim.
- **Voxel surface fidelity** — at 1.0 mm voxel size the exported STLs carry
  voxel-level facets (see bounds in `run-report.json`: valve head Ø
  resolves to ±0.5 mm of the nominal 49.0 mm). Finer voxels (0.2 mm) are
  supported by the CLI bounds but were not run in this verification.
- **Post-processing** — no support removal, HIP, machining stock or
  finishing allowances are modelled anywhere in this lane; nominal-as-printed
  dimensions of an actual build would not match the proxies anyway, because
  the proxies themselves are placeholder shapes.
- **Material** — no material is assigned to any component here; the
  repository safety policy requires documented functional testing for
  engine-loaded parts, which nothing in this lane has.

## Gate (binding)

Manufacturing of any component in this lane is **not authorized** by this
note, by the compile/run report, or by any calculation. Metrology of the
real M64/60 valvetrain components is the next evidence step (M64-ACQ-0002
blocks the cam profile in particular).
