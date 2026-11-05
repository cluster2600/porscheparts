# 935 horizontal system — preparing the reference

> **CFD input status: the rotor wall is recorded
> [`inadmissible_for_cfd_parameter_studies`](admissibility.json).** Nine of its 24
> worst facets project beyond the last registered section station of their nearest
> blade; this alone does not establish provenance or the cause of mesh failures.
> Mesh and solver parameter sweeps on that wall are refused until the facet
> provenance is settled; provenance audits, reacquisition and non-CFD work on this
> twin stay open. `make check` validates the record.

On 12 October, the [native 935 chain with a Qwen trial](../../docs/research/935-horizontal-cooling/NATIVE_935_PIPELINE.md)
reconstructs the nine blades separately in PicoGK, keeps the observed drive
and assembles an intake with six-cylinder engine envelopes.
The engine dimensions, poses and scale remain assumptions; this
result does not establish the historical installation. The 917 context of the
previous scene is excluded from this active chain.

Campaign of 5 October: the
[reconstruction coordinator](source/run_reconstruction.py) produces the
measured sections of nine blade regions, PicoGK lofts at three resolutions,
editable FreeCAD/STEP CAD and an independent deviation review. The sources,
transforms and derivatives remain private. The
[implementation report](../../docs/research/935-horizontal-cooling/IMPLEMENTATION.md)
gives the commands and the limits; the complete geometry and the reference
calculations remain to be finished. The proxies described below are historical.

Step of 3 October 2026: two scans prepared and passed through PicoGK, interface
requirements defined, dimensional research continued, then the
[executable baseline of the system twin](SYSTEM_TWIN.md): complete register of
functions, OpenUSD graph, six reduced-order models and comparison with measurements.
The functional
reference, the improvements and the calibrated twin remain to be built.

## Independent contract before reconstruction

The [contract](interface-contract.json) describes **17 interfaces**: rotor/hub,
shafts, belts, transmission, bearings, bracket, engine, housing, guides,
lubrication, coupling and alternator. It describes the load paths
to be verified and the evidence required. The axes, holes, faces, tolerances,
scales and the target engine variant are unknown. No plausible dimension
replaces them. The location of the coupling on the specimen must be
identified; the supplier data sheet is not enough to assign it.

See the [documentary dossier](../../docs/research/935-horizontal-cooling/DIMENSIONS_AND_DETAILS.md)
to distinguish the basic FIA form, Porsche 993 references and 935
reproductions. None of these commercial fields is a calibration of our scans.

## Scan processing performed

Preparation reuses the [existing program](../993-engine-cooling-fan-system-f0/source/prepare_private_scan.py):
rigid PCA transform, inverse matrix kept, vertex order
preserved, removal only of triangles with exactly zero area. The PCA provides
convenient views and defines neither a functional axis nor a rotor/bracket
positioning. The back of the rotor has not been realigned or filled.

| Result | Rotor | Drive/bracket |
|---|---:|---:|
| Vertices kept | 624,492 | 1,256,836 |
| Triangles after preparation | 1,240,439 | 2,484,656 |
| Zero-area triangles removed | 26 | 0 |
| Boundary edges after preparation and after PicoGK | 8,657 | 29,476 |
| Boundary loops after preparation | 58 | 200 |
| Surface components | 2 | 1 |
| Boundary circles passing the diagnostic filter | 0 | 0 |

[inspect_private_interfaces.py](source/inspect_private_interfaces.py) examines
the boundary loops, fits a plane/circle and requires sufficient angular
coverage. The thresholds are diagnostic filters, not machining
tolerances. The loops also correspond to coverage defects:
this filter does not detect all bores inside a continuous surface.
It does not segment all the mechanical parts. No measured datum is
established by this negative result.

## PicoGK actually run

[ScanReview](source/picogk-scan-review/Program.cs) uses a `Library` instance
without a viewer. The local kernel is **PicoGK Core 26.2.0**, native build
`2026-06-05 21:50:16`. The digests of the C# and native libraries are
kept in the summary. The local source of the
[LEAP 71 project](https://github.com/leap71/PicoGK) is at commit
`0e6cf6b6f4993ec16dbcd72d8f27f26b999980f3`; this marker does not constitute
an attestation of the build of the reused binaries.

The synthetic annular witness, with chosen dimensions known in mm,
tests the voxel operations, the volume and three inside/outside probes.
At 0.5 mm/voxel, the volume deviation from the analytical formula is **0.0556 %**.
This is a check of the runtime on this witness, without validation of a
fan nor a general guarantee of geometric convergence.

The two prepared OBJ files were then loaded as `PicoGK.Mesh`, without
voxelisation. All triangle indices were read back in the kernel before
export; the new audit of the exported OBJ files keeps the boundary counts,
with no new zero area, non-manifold edge or orientation inconsistency.
PicoGK stores positions in float32: the maximum deviation of each scan is
measured in its private receipt, in unknown source units. It cannot be
interpreted in mm or compared with a functional tolerance at this stage.
Surface intersections are not qualified by this audit.

## Local reproduction

Outputs must go in a new private directory, outside Git or under
an ignored `work/`. The input files are not modified. NumPy, SciPy and
Matplotlib are required for the Python diagnostic; .NET 9 and an already
qualified official PicoGK installation are required for the C# program.

```sh
python3 twins/993-engine-cooling-fan-system-f0/source/prepare_private_scan.py PRIVATE.obj work/NEW/prepared --expected-sha256 RAW_SHA256
python3 twins/935-horizontal-cooling-system-f0/source/inspect_private_interfaces.py work/NEW/prepared/pose-normalized-open-scan.obj work/NEW/inspection --expected-sha256 PREPARED_SHA256
dotnet build twins/935-horizontal-cooling-system-f0/source/picogk-scan-review/ScanReview.csproj -p:PicoGKAssembly=/PRIVATE/PicoGK.dll -p:BaseIntermediateOutputPath=/PRIVATE/obj/ -o /PRIVATE/bin
# Installer les bibliotheques natives officielles compatibles a cote du binaire.
dotnet /PRIVATE/bin/ScanReview.dll witness work/NEW/witness
dotnet /PRIVATE/bin/ScanReview.dll mesh work/NEW/prepared/pose-normalized-open-scan.obj PREPARED_SHA256 work/NEW/picogk
```

(The comment in the block reads: install the compatible official native
libraries next to the binary.)

The [limited public receipt](../../docs/research/935-horizontal-cooling/preparation-summary.json)
keeps the digests of the inputs/exports/tools and the counts.
Coordinates, transforms, geometries and derived parameters remain
in the private reports. Eight synthetic Python tests cover inclined
circles, incomplete arcs, non-planar rings, degeneracies, pinched edges,
distinct surfaces and input/output protections. Six native CLI cases
verified open export, rejection of non-finite values/invalid indices/
unknown records, SHA check and refusal to overwrite.

## Visual repair of the rotor

The Screened Poisson closure produced by
[photo_guided_surface_repair.py](source/photo_guided_surface_repair.py) is
rejected after multi-view review: its topological closure invents volumes
at the hub and between the blades. It is kept private as an attempt, never
as a reference, interface or computational mesh.

The program
[picogk-rotor-visual-proxy](source/picogk-rotor-visual-proxy/Program.cs)
had produced an explicit visual topology with a disc, a hub
and ten curved blades. PicoGK aligns it to the PCA envelope of the scan, without
converting the source unit to millimetres or deducing an interface. The
[proxy documentation](../../docs/research/935-horizontal-cooling/PICOGK_ROTOR_VISUAL_PROXY.md)
records its audit and its limits. The count of ten blades was a
visual assumption; it is not carried over by the generator based on the observed
sections, which detects nine regions. This proxy remains excluded from reference calculations.

## Next evidence to obtain

The variant must be identified, the scale established on two independent dimensions
and the contract interfaces verified to reconstruct a functional
reference. The transmission internals and the missing guides
also require suitable documents or inspections. The calculations of mass,
inertia, stresses, drive, flow/pressure and cooling of the
specimen will use these qualified inputs; no real characteristic
or quantified improvement is announced on the basis of a pass through PicoGK alone.
