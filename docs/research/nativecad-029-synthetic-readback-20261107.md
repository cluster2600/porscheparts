# NativeCAD 0.29 synthetic interoperability readback

Date: 2026-11-07. Requirement: [issue #407](https://github.com/cluster2600/porscheparts/issues/407).
Architecture: [optional geometry routes](../architecture/usd-brep-lpbf.md) and
[local-compute authority](../architecture/README.md).

Verdict: live version readback, synthetic STEP export and a bounded PicoGK
bridge execution pass their checks below. The reported voxel volume and the
exported STL volume disagree and remain separate measurements. This does not
close the stack rebuild, qualify real geometry or change PicoGK's authority.

## Runtime and disclosure boundary

`cad_server_info` identifies `cadsolver` / NativeCAD **0.29.0**, Node
`v26.12.1`, stdio transport and `nativeDependencies: false`. Its staged kernel
metadata reports git revision `87549fc4cfead21fff8da15fde5d000c13e3b675`,
1,277 files and tree hash
`95256ca41c39273fe60cb3ccc6b2822938ee7da99eaa69d5f897d2d4887e27bd`.
The kernel version field is null. These are server-reported identifiers, not
an independently rebuilt kernel attestation.

The server was already at 0.29.0 when queried. No installer was run here and
neither the update route nor rollback was exercised. Its update configuration
is `notify-only`, with no completed latest-release check. This receipt does
not claim that 0.29.0 is the newest available release.

The server reports a licensed free tier with mandatory failure reporting.
Only a synthetic rectangular block was supplied; no scan, customer geometry,
vehicle dimensions or private part was imported. No failure packet was shared.
This observation is not approval for sending private geometry through that
runtime, nor a new determination of licence rights.

## Independent fixture contract and execution

The fixture was specified before construction: an axis-aligned **60 × 40 ×
15 mm** block, minimum corner `(0, 0, 0)`, expected volume **36,000 mm³**,
surface area **7,800 mm²**, six planar faces and twelve edges. These dimensions
are synthetic and have no Porsche meaning. A new document was used, preserving
all other sessions.

1. `cad_box` with `document: "new"`, `dx: 60`, `dy: 40`, `dz: 15` returned the
   expected envelope, volume, area and topology counts.
2. `cad_export_body` wrote STEP with `schema: "ap242e2"` and `strict: true`.
   NativeCAD's own re-import passed. The exporter explicitly warned that its
   OCP oracle did not run because that server could not find an OCP Python.
3. An independent read in the repository's isolated Python 3.12.13 environment
   used `cadquery-ocp-novtk` / proxy 7.9.3.1.1: `STEPControl_Reader` returned
   `IFSelect_RetDone` and transferred one root; `BRepCheck_Analyzer.IsValid()`
   returned true. `BRepGProp.VolumeProperties_s` returned **36,000 mm³** and
   `BRepBndLib.AddOptimal_s` returned bounds **(0, 0, 0, 60, 40, 15) mm**.
   Assertions required volume error below `1e-7 mm³` and each bound within
   `1e-6 mm`. This separate check resolves the export-oracle gap for this
   fixture only; it does not configure NativeCAD's oracle discovery.
4. `cad_picogk` voxelized that body with `voxel_size_mm: 1`, `import: false`
   and `timeoutSec: 60`. The real job completed using **Picopie 0.7.0** in
   702 ms reported total time, producing a 16,532-triangle STL. This was not
   a dry run and no paid compute was used.
5. Trimesh 5.1.0 independently loaded that STL: `is_watertight` and `is_volume`
   were true, the face count was 16,532, and bounds were within `1e-5 mm` of
   the specified block. Measured mesh volume was **36,000.0004580915 mm³**,
   relative error **1.272476381725735e-8**, below the explicit 1% smoke-check
   ceiling. This coarse ceiling is not a part tolerance.

The bridge's `results.json` reports **35,909.6015625 mm³**, about 0.2511% below
the analytic block. The exported mesh readback above reports a different
quantity. This run did not establish why they differ; do not substitute the
bridge's volume for independently measured exported geometry or interpret
the near-exact box envelope as general sub-voxel accuracy. Only voxelization
was exercised, not offsets, shells, lattices, CEM execution or convergence.

## Retained artifacts

Local root: `$HOME/Developer/PorschePartsArtifacts/nativecad-029-synthetic-20261107/`.
Geometry remains outside Git. SHA-256 identifies the actual bytes inspected.

| Artifact | SHA-256 |
|---|---|
| `box-60x40x15.step` (6,638 bytes) | `3afbe83a10f0c9ae20ef9af8b6ff012009e62356978b10a8ab32343f3b44d49e` |
| `picogk/result.stl` | `55aa4cc56419dceb29e12113a9bd278cc4483096b95ecd3562d25ace702f0c08` |

The same root retains `ocp-readback.json`, `trimesh-readback.json`,
`picogk/case.json` and `picogk/results.json`. The STEP sidecar records six named
faces. No generated geometry has been promoted into the part catalogue.

## Remaining issue #407 gates

- Supported update and rollback evidence are not established by finding an
  already-updated server.
- NVIDIA API migrations, Kit/WebRTC packaging and GPU/render/stream witnesses
  are outside this synthetic run and remain unresolved here.
- This Mac run does not satisfy the requested full native-Linux verification.
- Private geometry admission, functional interfaces, materials and physical
  or manufacturing qualification remain closed.
