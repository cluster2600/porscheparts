# 935 native mesh serialization and solver admission

## Scope and upstream verdict

This diagnostic consumes the independently inspected volume from the
[local convex-cavity study](../935-local-cavity-20261105/README.md), SHA-256
`233f7bd83072772fa0b92d0287f20cec3cf44c4988546be42addf5579630299e`.
Its 12,981,388 tetrahedra preserve every node and the complete boundary of a
hypothetical reconstruction. All stored-coordinate orientation signs pass
certified inspection, but the absolute shape-quality gate still fails.
Specimen scale, inferred closures, attachment identity and process/physical
qualification are not resolved. This admits serialization and conditioning
diagnostics; it does not admit an engine field calculation.

No geometry, source boundary, printing master or native image is modified.
The scan may be transferred to Vast under the user's permission, but this
increment needs only derived geometry. Private meshes, native outputs and
connection metadata remain outside Git. The eight executable sources and
aggregate results provide the replay trail.

## Native geometry and numerical conditioning

`export_native_mesh.py` checks labels before mapping, constructs the native
region and writes MSH 4.1 binary with Gmsh 4.12.1. After clearing the model and
reopening the actual file, all coordinates, tetrahedra and boundary rows are
exact. Positive and inverted analytic tetrahedron controls precede the head.
No optimizer is invoked. The complete head scan of native metrics reports:

| Metric | Minimum | Nonpositive or nonfinite cells |
|---|---:|---:|
| minDetJac | 1.5317399711e-19 | 0 |
| Volume | 2.5528999518e-20 | 0 |
| minSICN | -3.8590472543e-13 | 3,130 |

The last row contains 3,126 negative values and four zeros. It does not prove
3,130 geometrically inverted cells. `inspect_metric_disagreement.py` computes
exact rational edge matrices from the stored binary64 coordinates for every
flagged cell, verifies the adjugate identity and finds all determinants positive.
Its separate condition measure is
`kappa_F = norm_F(A) * norm_F(adj(A)) / abs(det(A))`; this is not Gmsh minSICN.

All 3,130 have kappa_F at least 1e12; 225 reach 1e15 and 46 reach 1e16.
Approximate minimum/median/maximum are 1.684e13 / 1.262e14 / 4.658e16.
The kappa_F times binary64 epsilon indicator reaches one on 64 cells;
the conservative spectral-condition lower bound kappa_F/3 times epsilon does
so on five. These indicate sensitivity, not measured PDE error or a proof
that the assembled operator is singular. Gmsh's internal cause of the SICN
disagreement is not established by this experiment.

Of these cells, 3,129 have all four vertices on the source boundary; one has
one interior vertex. This is a geometric classification, not an engine boundary
condition. Controls distinguish thin positive, inverted and singular matrices,
with exact uniform-scale invariance.

## Actual OpenFOAM interoperability

The existing isolated Kali image is pinned by its image content ID, with
OpenFOAM 14 and CalculiX 2.23 verified at execution. A registry/source-build
attestation is not supplied by that local image ID. Strict trusted-host SSH,
disabled agent forwarding and the existing native identity are used. No
credential or host configuration is changed.

The first two-cell synthetic control reaches the actual `gmshToFoam` reader
and is rejected with `Can only read ascii msh files.` It never reaches
`checkMesh`. The preserved first report's `converter_reports_ascii_only`
convenience flag is false because its search was case-sensitive; the retained
native log establishes the diagnosis. That executed source/report is kept
unchanged. This tests binary 4.1 rejection, not every possible Gmsh format.

`export_ascii_mesh.py` then serializes MSH 2.2 ASCII itself, with 17 significant
coordinate digits, and uses native Gmsh for complete readback verification.
This is not a native Gmsh ASCII writer. Its synthetic five-point, two-cell
precision fixture shifts x by 100 and places the apex at `nextafter(100,+inf)`.
Sixteen significant digits lose the extra bit; seventeen retain it. Exact
analytic volume is `2/3 * (1 + 2^-46)`. This is not Porsche calibration data.

The actual Kali ASCII import and `checkMesh` pass. Recovered OpenFOAM points,
faces, owner and neighbour files independently reproduce all five coordinates,
both tetrahedron vertex sets and all six boundary face sets exactly. OpenFOAM
write precision is explicitly 17. Native floating-point volume arithmetic is
not claimed exact. Full-head ASCII export also passes complete native Gmsh
coordinate/connectivity/boundary readback. No engine ports or loads are assigned.

## Bounded full-head admission

A fresh Kali capacity check finds sufficient disk under its home filesystem,
although `/tmp` alone is too small for the declared staging reserve. One head
diagnostic uses two CPUs, an 8 GiB container memory limit with no extra swap,
300-second conversion and 180-second mesh-check limits. Conversion returns 137
after reading all source cells; `checkMesh` is not run. This is an actual
SIGKILL exit under the declared bound, not a demonstrated invalid head mesh or
a confirmed kernel OOM diagnosis. Every generated file is recovered and hashed,
then the owned container and staging directory are verified absent.

One actual Vast rental then uses the pinned mesh-CFD image and OpenFOAM 13,
repeating the precision control in that runtime before the full head. The
control imports, passes checkMesh and retains every coordinate and topology
entry. The head uses a 48 GiB child address-space limit and 720/240-second
import/check bounds. Conversion finishes successfully in 113.69 seconds and
writes the actual native head mesh. The native check reaches the correct
4,181,299 points, 30,072,005 faces and 12,981,388 tetrahedra, and passes its
first five topology checks, but reaches the 240-second deadline before
completion. Its SIGTERM exit is retained as **incomplete**, not as either a
passed or geometrically rejected mesh. No identical job is restarted.

The provider advertises 16 effective CPUs and 256,498 MB RAM; the worker's
larger host affinity is not a dedicated allocation. The instance rate including
120 GB storage is $0.112888889/hour. A live independent guard precedes creation
and limits ownership to the exact launch receipt. The initial launch-observation
timeout is reconciled against the actual worker PID and directory, without
launching a second worker. A slow relay input transfer is stopped and its exact
archive prefix retained; the verified direct endpoint completes the same input
transfer. This does not change the numerical trial or its budget.

The terminal outcome, verified recovery and owned-resource closeout are recorded
in [results.json](results.json). Neither successful import nor a future complete
`checkMesh` would establish case-specific field accuracy, physical loads or AM
qualification.

`inspect_foam_readback.py` independently reads the native ASCII points, faces,
owner and neighbour lists with a separate vectorized implementation. It checks
all face references, four faces per cell, four distinct vertices with the
tetrahedral incidence pattern, all source coordinate bits, every tetrahedron
vertex set and every boundary face set. Its precision control also checks a
single-coordinate corruption through the complete comparison path. Native
geometric face orientation and numerical volume accuracy are separate checks.
The complete head readback passes in 40.50 seconds: all 4,181,299 coordinate
triples, 12,981,388 tetrahedron vertex sets and 8,218,458 boundary face sets
are exact. All 30,072,005 native faces and 21,853,547 internal neighbours are
included. The corrupted control is rejected. This complete topology witness
does not complete the interrupted native geometric check or establish field
accuracy. A small control never stands in for the head.

All 36 retained remote result files match their recovered hashes. Five omitted
input copies are verified against the Mac inputs, including the stopped relay's
exact archive prefix. The worker is terminal before archiving. Only the actual
task-created instance is deleted; the controller and independent guard both
observe absence, and the guard process exits. Conservative elapsed-rate cost
including storage is $0.05402109; the 20 GB network planning upper estimate is
$0.10666667. These are estimates, not a provider invoice. Original scan,
conditioned volume input and printing-master 3MF are rehashed unchanged.

## Phase ledger and replay

| Phase | Concrete inputs/runtime/command | Outputs and checks | State |
|---|---|---|---|
| Upstream admission | Frozen conditioned NPZ and complete interval/exact report | Exact stored domain; absolute quality remains poor | Diagnostic only |
| Native serialization | `export_native_mesh.py`, Gmsh 4.12.1 | Actual binary file; full native readback and metrics | Complete |
| Exact conditioning | `inspect_metric_disagreement.py`, Fraction arithmetic | All 3,130 flagged cells, exact signs/adjugates/condition comparisons | Complete |
| Native format control | `probe_kali_control.py`, actual OpenFOAM 14 | Binary rejection retained | Complete negative witness |
| ASCII adaptation | `export_ascii_mesh.py`, native Gmsh reader | Precision control then complete head readback | Complete |
| Native precision witness | `probe_kali_ascii_control.py`, actual isolated Kali image | Import, check and independent full control readback | Passed |
| Local head benchmark | `probe_kali_head.py`, same image, 8 GiB | Exit 137; all generated files recovered, staging cleaned | Complete negative witness |
| Guarded cloud admission | `run_cloud_import.py`, pinned mesh-CFD image, existing scoped wrapper/guard | Fresh control passed; head import passed; native check timed out; verified recovery and owned closeout | Complete diagnostic |
| Independent native head readback | `inspect_foam_readback.py`, recovered points/faces/owner/neighbour, frozen NPZ | Every coordinate, tetrahedron and boundary face compared; control corruption refused | Passed |
| Head operator admission | Exact recovered mesh, explicit numerical problem | Native geometry check, conditioning, conservation, convergence and accuracy | Pending |
| Engine/process qualification | Specimen interfaces, operating data, material/machine/process calibration | Independent engineering and physical validation | Pending |

Each source provides its contract in code; command-line exporters/probes accept
`--help`, while the cloud worker consumes a private per-file input manifest
beside itself. Replay into new private directories. The existing scoped wrapper
and [receipt-bound rental guard](../935-local-conditioning-20261105/source/guard_conditioned_rental.py)
are retained; no raw OpenBao access is introduced. The cloud preparation ledger
and budget record precede creation. Prior $6.30 reservation ceilings are retained,
this attempt adds at most $1.50, and the original $35/$30/$5 allocation is not
reset. Account-wide balance changes are not task invoices.

The next engineering decision must use the actual importer outcome and the
documented condition distribution. No mesh-parameter sweep, engine field solve,
new analytic CAD master or functional-metal release follows automatically.
