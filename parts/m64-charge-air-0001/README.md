# M64 charge-air path geometry study (concept, unvalidated)

Parametric PicoGK (C#) sources for the M64/60 charge-air path between the
compressor outlets and the throttle bodies: per-bank compressor-outlet tube,
charge-air coupling geometry, per-bank plenum form, and interconnect hose
routing expressed as centerlines plus SDF sweeps.

> [!CAUTION]
> **Concept geometry only.** The charge-air line has **no dimensions in the
> wave-1 master BOM**: every dimension in `ChargeAirParameters.cs` is tagged
> `ASSUMPTION` (vendor product envelopes are packaging bounds, not OEM
> interface dimensions). The 1.0 bar boost figure is a public FACT for the
> modified-engine brief but **does not size any geometry here**. Nothing in
> this folder may be called dimensionally correct, fitted, tested, safe,
> released, or manufacturing-ready.

## Layout

- `source/ChargeAirParameters.cs` — all physical inputs, configurable:
  wall thickness, clearances, voxel size, fin/interface sizes; each tagged
  `FACT_public`, `SOURCED_ENVELOPE`, `ASSUMPTION`, or `DERIVED`.
- `source/ChargeAirGeometry.cs` — PicoGK lattice/voxel construction: tubes,
  couplings, plenum, hose centerline sweeps. Only API calls verified against
  the pinned images in this repository (`Library`, `Lattice.AddSphere`,
  `Lattice.AddBeam`, `Voxels`, `Mesh.SaveToStlFile(..., Mesh.EStlUnit.MM)`,
  `Voxels.voxOffset`, boolean ops) — see `docs/` references in the provenance
  file. No invented API syntax.
- `source/Program.cs` — headless entry point; builds both banks at the
  configured voxel size and writes STL exports plus a `run-report.json`
  (repository-standard PicoGK export call, matching the pinned
  `containers/picogk-m64.Dockerfile` .NET SDK 9.0.317 / PicoGK 26.2 witness).
- `provenance.json` — per-dimension provenance and evidence tags.

## Coordinate system

Millimetres, right-handed, engine frame used by `twins/m64-engine-system`:
+X toward the rear of the car along the crankshaft, +Z up, banks mirrored
about Y=0. Centerlines are polylines through listed waypoints.

## Build & run (not verified locally)

The host dotnet SDK here is 6.0.400, which cannot build `net9.0`
(NETSDK1045). The build has **not** been verified; it targets the pinned
container image of this repository:

    dotnet build parts/m64-charge-air-0001/source/ChargeAir.csproj -c Release \
      -p:UpstreamRoot=/upstream -p:GeneratePackageOnBuild=false
    dotnet parts/m64-charge-air-0001/source/bin/Release/net9.0/ChargeAir.dll <NEW_OUTPUT_DIR>

## Status limits

Geometry research artifact only: no dimensional inspection, no fitment, no
flow/pressure testing, no engineering release. Vendor envelope values come
from third-party product pages (reference-only copyright) listed in
`provenance.json`.
