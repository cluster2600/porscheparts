# 935 native geometry and finite-volume stencil diagnostics

## Upstream admission

The [native import/readback study](../935-native-solver-admission-20261105/README.md)
preserves every source coordinate, tetrahedron vertex set and boundary face in
the actual recovered OpenFOAM mesh. Its complete native check times out during
topology checking. This increment isolates native geometry/stencil diagnostics
after that independent complete incidence/readback witness. It does not replace
the incomplete native topology check or admit an engine field solution.

The inherited hypothetical reconstruction, physical scale, inferred closures,
unclassified interfaces and extreme cell conditioning remain unresolved. No
head geometry, threshold, boundary type or printing master is changed. The
geometry diagnostic is declared before execution, with a fixed time/memory
bound and no parameter sweep.

## Why the first extended control was refused

The actual OpenFOAM 14 help confirms `-noTopology` and `-allGeometry`. The
unchanged two-cell precision bipyramid passes the default check, but its
extended check reports two zero cell determinants and one failed mesh check.
The exact coordinate determinants remain positive. Its one-cell inverted copy
is correctly reported with a negative volume and seven failed checks. Both
failed native checks nevertheless return process exit code zero. A zero exit
therefore never supplies acceptance; terminal report content is required.
The first controller retains this result and refuses to execute the head.

The extended "cell determinant (wellposedness)" is different from the
coordinate Jacobian and from Gmsh minSICN. In the official source at the
runtime's reported revision, it forms a normalized tensor from outer products
of **internal or coupled** face-area vectors. In three dimensions, fewer than
three such vectors force its exact determinant to zero. The two-cell control
has only one internal face per cell. This explains the extended rejection
without changing its threshold. See the pinned official
[tensor calculation](https://github.com/OpenFOAM/OpenFOAM-14/blob/a4867fc914c10ee10c2f6f83c294c3d3160dd573/src/meshCheck/primitiveMeshCheck/primitiveMeshCheck.C#L424)
and [check and threshold](https://github.com/OpenFOAM/OpenFOAM-14/blob/a4867fc914c10ee10c2f6f83c294c3d3160dd573/src/meshCheck/polyMeshCheck/polyMeshCheck.C#L586).
Source bytes, hashes and acquisition metadata are retained privately. Matching
the reported revision does not provide a full native-image build attestation.

## Complete head stencil audit before another diagnostic

The frozen native-list reader inspects every owner/neighbour label. The single
boundary remains an uncoupled `patch`; no engine port or boundary condition is
assigned. All counts agree with the independently inspected 12,981,388 cells
and 21,853,547 internal faces:

| Internal faces per tetrahedron | Cells |
|---:|---:|
| 0 | 0 |
| 1 | 325 |
| 2 | 1,632,633 |
| 3 | 4,952,217 |
| 4 | 6,396,213 |

At least 1,632,958 exact internal-area tensors are therefore rank deficient.
The extended stencil gate is **known to fail before the head run**. This is a
neighbour-stencil criterion under the current uncoupled boundary classification,
not proof that those tetrahedra are geometrically inverted or that a specified
finite-element/boundary-value problem is singular. No field solve is admitted.
One bounded run is useful to measure the other native geometry diagnostics on
the unchanged domain, not to seek a pass by tuning thresholds.

## Independently known structured control

The replacement fixture is an analytic unit cube, divided into 2 x 2 x 2
hexahedra. Native `blockMesh` output must independently match all 27 grid points,
eight cell vertex sets, 36 face sets, 12 internal faces and 24 boundary faces.
Each cell has six faces and three orthogonal internal faces of equal area;
the exact normalized internal-area tensor is the identity, determinant one.
Each cell's exact volume is 1/8 and the total is one. This synthetic fixture
supplies no Porsche calibration, operating condition or material property.

`structured_control.py` checks the full analytic contract from native files,
then creates a separate reflected control with `R = diag(-1,1,1)`. Connectivity
and face orientation rows remain unchanged, so all eight signed volumes become
-1/8. The actual Kali OpenFOAM 14 default and extended positive checks pass,
including determinant one. The reflected control reports exactly eight negative
volumes and six failed checks. Both stdout content and exit/timeout state are
used for admission. Owned control staging/container cleanup follows complete
recovery and hash verification.

## Capacity and bounded head execution

The initial native-case controller uses a declared 8 GiB memory limit and
requires 10 GiB available on Kali. The structured head preparation finds only
7,454,150,656 bytes available, so it stops before remote head staging or
execution. That failed preparation and its complete stencil audit are retained.
The independent structured control is then executed under a separate 512 MiB
container bound. The head memory floor is not reduced.

One actual Vast worker repeats the structured control in its pinned OpenFOAM 13
runtime before executing the unchanged native head. Both controls pass their
positive/rejection contracts again. Its head command is
`checkMesh -noTopology -allGeometry -case head`, with native defaults, a 48 GiB
child address-space limit and a 600-second deadline. It finishes in 60.609
seconds without timeout, returns exit zero, but reports **10 failed mesh checks**.
The pipeline correctly rejects it. This completes the selected diagnostic,
not a passed geometry gate or the earlier incomplete full native topology check.

| Native diagnostic | Reported count / value |
|---|---:|
| High aspect-ratio cells | 39,913; maximum 1.05055e102 |
| Negative computed-volume cells | 4,070; minimum -1.56218e-15 |
| Severely nonorthogonal faces, over 70 degrees | 3,953,359 |
| Nonorthogonality errors | 1,009; maximum 90.000000000224475 degrees |
| Face-pyramid orientation warnings | 6,851 faces |
| Highly skew faces | 63,762; maximum skewness 1,112.965 |
| Low-quality/negative face decomposition-tet warnings | 288,815 faces |
| Small-edge warning | 224; minimum length 1.19209e-6 |
| Internal-area determinant below 0.001 | 4,319,287 cells |
| Native face-plane concavity warnings | 36,752 cells |
| Face interpolation weight below 0.05 | 4,151,434 faces |
| Face volume ratio below 0.01 | 2,022,190 faces |

These are native numerical diagnostics in the inherited hypothetical coordinate
frame, not specimen measurements. The edge row is a warning rather than an
eleventh failed category. The aspect-ratio formula clamps a nonpositive volume
before normalization, so its enormous value is not a measured physical aspect
ratio; see the pinned OpenFOAM 13
[formula](https://github.com/OpenFOAM/OpenFOAM-13/blob/18870c24d21c6b982e2cdec27b2f59738cca5f90/src/meshCheck/primitiveMeshCheck/primitiveMeshCheck.C#L224).
The internal-area tensor function is independently acquired at that revision
and is text-identical to the reviewed OpenFOAM 14 function. Source provenance,
actual reports and owned-resource closeout are in [results.json](results.json).

## Complete integer winding audit

The native negative volumes and face-pyramid warnings must not automatically
be interpreted as incorrectly imported face rows. `inspect_native_winding.py`
first builds a bijection from every native cell vertex set to the unique source
tetrahedron, whose stored-coordinate positivity was certified previously.
For each native face, integer permutation parity tests its orientation relative
to that positive reference cell. Owner faces must point outward; internal
neighbour faces must point inward. This uses no floating-point face areas,
cell centres or volume formulas.

The positive two-cell control passes; reversing its internal face is detected
for both incident cells. The complete head audit then passes in 38.46 seconds:
all 30,072,005 owner-face windings and 21,853,547 neighbour-face windings agree,
with **zero errors**, including the boundary. Every native cell maps uniquely
to the source, and actual native cell order also matches the source order.
No mesh coordinates, connectivity or face rows are changed.

Thus unchanged, certified positive source tetrahedra and correct imported
windings disagree with the native numerical geometry reports. The latter are
not proof of true inverted source tetrahedra. This audit excludes incorrect
face-row winding as the explanation; it does not identify which native
arithmetic, centre/area/volume evaluation or input-reading detail causes the
inconsistency. Its result supplies no native operator accuracy or engineering
approval. A source-relative conditioning audit must precede another mesh or
field trial; reversing these already-correct face rows is not a repair.

All 33 retained cloud result files and 14 omitted input copies are verified.
The worker is terminal before recovery; only owned instance 59285271 is deleted.
Controller and independent guard observe absence and the guard process exits.
Observed-rate times conservative elapsed estimate including storage is
$0.03550411; the 20 GB network planning upper estimate is $0.10666667, not a
provider invoice. The original scan and printing master are preserved.

## Phase ledger and replay

| Phase | Inputs, runtime and commands | Expected checks / state |
|---|---|---|
| Parent admission | Frozen native mesh and complete independent incidence/readback witness | Exact stored domain; diagnostic only |
| Native help | Existing isolated OpenFOAM 14 image, `checkMesh -help` | Actual selectors recorded |
| First control | `probe_native_geometry.py`, precision bipyramid and exact one-cell inversion | Extended positive rejected; head refused; evidence preserved |
| Head stencil audit | `probe_structured_geometry.py`, frozen native-list reader, every owner/neighbour | Complete histogram and rank lower bound; extended rejection expected |
| Local capacity | Fresh Kali memory/disk before remote staging | Head preparation refused under declared floor |
| Structured fixture | `structured_control.py`, analytic grid, actual native blockMesh files | Full independent contract and affine reflection |
| Native controls | `run_native_geometry.py`, default/extended positive and reflected negative | Actual Kali pass/rejection; report content required despite zero exit |
| Cloud controls/head | Manifest-bound worker/helper, pinned image and native head | Repeat controls; one bounded geometry/stencil diagnostic |
| Integer winding | `inspect_native_winding.py`, certified positive source, native arrays | All 51,925,552 incident face orientations checked; zero errors; corrupted control refused |
| Recovery/closeout | Terminal worker, per-file input/output hashes, exact launch receipt | Verify every retained result before owned deletion and independent absence proof |
| Numerical/engine/AM qualification | Explicit operator/loads/material/process and physical evidence | Remain separate pending gates |

The first two controller sources are preserved failed/admission recipes, not
successful head runs. The worker's input manifest, plan, helper hash and command
receipts permit replay in a fresh private directory; the case root contains
`run_native_geometry.py`, `structured_control.py`, `geometry-plan.json`,
`input-manifest.json`, `control/system/*` and the native `head/` when requested.
The retained scoped OpenBao wrapper and
[receipt-bound guard](../935-local-conditioning-20261105/source/guard_conditioned_rental.py)
are used for cloud execution. Prior reservation ceilings of $7.80 are retained;
this attempt adds a $1.50 cap, giving $9.30 within the original $35/$30/$5 budget.
Compute, storage and a conservative network provision are tracked separately
from any provider invoice. The supplier draft remains unsent.
