# M64-SHORTBLOCK-0001 — short-block parametric source (lane 2, wave 2)

PicoGK C# source geometry for the M64/60 short-block lane: piston envelope,
connecting-rod hypothesis envelope, parametric finned cylinder, and the
crankcase skeleton that acts as the layout master. One program
(`ShortBlock.cs`), four exported parts plus a machine-readable run report.

## Evidence class — read before using anything from this folder

**Concept only.** Nothing here is measured, fitted, tested, safe, or
manufacturing-ready. The output is parametric source geometry:

- `FACT_public`: bore 100.0 mm, stroke 76.4 mm, 6 cylinders, head-joint
  O-ring seat 102.0 mm (see provenance block in `ShortBlock.cs`).
- `SOURCED_B`: PAUTER aftermarket rod datum (declared, level B) — the rod
  contour is a HYPOTHESIS envelope around those sourced bores, and the
  aftermarket part is not the OEM baseline.
- `NOT public` (tracked by M64-ACQ-0004): cylinder pitch and crank-to-deck
  height are unknown; they reach the geometry only as parameters with
  PROVISIONAL assumption values, overridable via the environment
  (`M64_PITCH_MM`, `M64_DECK_MM`, `M64_BANK_X`). No value is baked as a guess.
- Everything else is an order-of-magnitude ASSUMPTION parameter, all
  configurable in `ShortBlockParams`.

The piston is a nominal-bore envelope, not piston geometry. No CFD/FEA is
implied by this folder.

## Build / run

```sh
dotnet build -c Release                                     # needs SDK >= 8
dotnet run -c Release -- [VOXEL_MM 0.5..5.0] [OUTPUT_DIR]    # prints M64_SHORTBLOCK_PASS on success
```

PicoGK resolves from a local checkout via `-p:UpstreamRoot=<path>` (default
`/upstream`), the same convention as the station's `HeadVoxels.csproj`. The
pinned API surface is PicoGK 2.3.0 commit `0e6cf6b6f4993ec16dbcd72d8f26b999980f3`
(image `picogk-station:qualified-final-20260928`); the calls used in
`ShortBlock.cs` are listed in its header comment and were limited to that
verified surface — no box primitive exists there, so slabs are flat-capped
beams.

## Build status — honest record (see validation/build-log.md)

**Compiled clean 2026-09-29** in the pinned station image
(`picogk-station:qualified-final-20260928`, dotnet build -c Release,
0 warnings / 0 errors, commit `c48b133`). The first attempt **failed**
(reserved-word parameter, `ref`-on-using arguments, one malformed
`Annulus` call); the fixes and both logs are in `validation/build-log.md`.

On the host directly, a build is still impossible: the only .NET SDK on
kali2 is 6.0.400 (net9.0 needs >= 8) and `/upstream/PicoGK` exists only
inside the station image — hence the container build. `bin/`/`obj/` here
are container by-products (root-owned), ignored via `.gitignore`.

## Verified vs unverified (as of this commit)

Verified on this host / image:
- Compiler type-check of `ShortBlock.cs` against PicoGK 2.3.0: **PASS**
  (0 warnings, 0 errors, see `validation/build-log.md`).
- The C# uses only .NET 9 / C# 12 language features and BCL APIs (no
  external packages beyond the PicoGK reference; `System.Text.Json` and
  `System.Numerics` ship with the SDK).
- Every PicoGK kernel call in the file is one of the header-listed,
  image-verified signatures (`Library(float)`, `Lattice.AddSphere`,
  `Lattice.AddBeam` in both overloads, `Voxels(Lattice)`, `BoolAdd`,
  `BoolSubtract`, `Offset`, `CalculateProperties(out float, out BBox3)`,
  `SaveToVdbFile`, `Mesh(Voxels)`, `Mesh.SaveToStlFile(string, Mesh.EStlUnit)`,
  `nTriangleCount()`); no API was invented. A naming shadow of the `base`
  keyword (valid C#, but a static-analysis smell) was removed.

Unverified — requires the station container (or SDK ≥ 8 + PicoGK checkout):
- Runtime execution, STL/vdb export, run-report contents, volume sanity.
- Any dimensional correctness (`dimensional_correctness_verified: false` is
  written into the run report itself).

## Known design limitations of the F1 scaffold

- `Slab()` approximates axis-aligned boxes by flat-capped beams: the two cap
  faces are exact planes (what the split-plane deck needs), but the four side
  corners are rounded to the smaller transverse half-extent — i.e. the slab
  under-fills its bounding box. Accepted for a layout scaffold; revisit if a
  boolean-exact box is required.
- Fin thickness 1.5 mm at voxel ≥ 1.5 mm aliases; the run report carries a
  warning whenever fin thickness < 2× voxel size.
