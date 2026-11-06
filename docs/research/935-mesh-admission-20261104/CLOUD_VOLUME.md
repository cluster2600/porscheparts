# Terminal Vast volume mesh and fixed-boundary quality limit

Date: 2026-11-04. The prepared retry completed on Vast and produced a
3,770,701-tetrahedron **study** mesh. All seven independent geometry checks pass.
The 22 recovered files match their manifest, and the exact task instance was
destroyed with absence independently observed by the controller and guard.
The mesh still has very poor cells. No head physics or metal release is granted.

This follows the [bounded-relocation surface/Kali checkpoint](BOUNDED_RELOCATION.md).
The terminal [cloud receipt](cloud-volume.json),
[fixed-face receipt](fixed-face-ceiling.json) and
[fixed-face audit source](source/audit_fixed_face_ceiling.py) retain the results.
Raw geometry, native fields and face/cell provenance remain private.

## Prepared task, execution and recovery

The input is the same coarse inferred assembly envelope, including attached
hardware and unsupported closures. It is admissible for this numerical study,
not as an accepted faithful bare head. The original OBJ was not uploaded.
The relocated NPZ hash is
`7b40f5eb3707fa0dfe80c154058f759135070c81a710df2b9dfa01c42043ee16`.

The private phase ledger C01–C07 precedes the rental: surface admission; local
benchmark; guarded creation/budget; runtime/transport; cube and head meshing;
independent verification; recovery and exact-resource closeout. Its executed
companion records each actual outcome. The broader
[H01–H14 ledger](../935-hypothesis-study-20261029/REPRODUCE.md) and
[completion requirements](../935-readiness-20261104/README.md) remain incomplete
for a functional head; this task does not declare the complete chain ready.

| Item | Actual outcome |
|---|---|
| Offer / instance | Validated offer 49416067; owned instance 59142713; 32 effective CPUs, 64 GB offered RAM; 120 GB reserved disk |
| Image | Existing mesh-CFD digest `a1db60cbf61bbcca52c171e50cab01ed0b6ec860b227e7c5fc50f7b809659b4f` |
| Runtime | Python 3.12.3, NumPy 2.5.2, Gmsh API 4.12.1; distribution metadata 4.12.1.dev1 |
| Native job | Algorithm 10, 1.5 mm interior size, 24 threads, 24 GiB child address-space limit, 1,800-second head deadline |
| Cube | Native unit-volume/positive-cell control passed before the head; actual recovered cube independently verified afterward |
| Head execution | Exit 0, no timeout; 273.454 s; peak child RSS 5,786,640 KiB |
| Mesh | 1,228,103 nodes; 3,770,701 tetrahedra; 2,099,584 boundary triangles |
| Native volume | 1,106,103.0255797368 mm³; zero nonpositive tetrahedra |
| Recovery | Archive 102,492,536 bytes; all 22 manifest files match; worker source and surface admission match the Mac originals |
| Closeout | Exact owned instance destroyed; provider inventory and the prearmed guard both verify absence |

The provider's instance RAM metadata reports host memory as well as GPU fraction;
it is not used to claim the entire host allocation. Runtime limits remain those
above. The SSH client used the existing approved identity without exporting it.
The provider-reported proxy endpoint was pinned on first connection in a private
task-specific known-hosts file; subsequent transfers used strict checking.
This is first-use host-key trust, not independent host attestation. Image READY,
runtime and every uploaded input digest were checked before execution.

The first offer lookup was refused by the wrapper before creation; a fresh
inventory contained zero instances. The subsequent offer created the single
paid resource. No uncertain creation request was blindly repeated. No credential,
external model request, manufacturer message or original-OBJ transfer was made.

## Independent geometry verdict

The actual recovered NPZ is checked separately from Gmsh's report. Coordinates
of the admitted relocated input surface are preserved exactly. Both the declared
oriented boundary and the boundary reconstructed from **every tetrahedral face**
match the admitted surface.
There are 6,491,610 interior face pairs, all with cancelling orientation. Every
node is used; every tetrahedron has positive signed volume. Independently summed
cell and surface volumes differ by 4.44 × 10⁻¹⁶ relatively, a numerical consistency
check rather than physical dimensional accuracy.

The verifier uses four analytic metric controls and six face-incidence controls.
The actual cloud cube also passes positive/unit-volume, interior-cancellation and
oriented-boundary checks. Success accepts the geometry of this discretised study
mesh only. Its inferred domain, source fidelity and physical interfaces remain
unaccepted for head engineering.

## Quality remains unresolved

The normalised tetrahedron mean ratio below is independently computed. It is
distinct from Gmsh minSICN. The 0.01 and 0.1 bins are diagnostic categories,
not material allowables or an approved solver-quality specification.

| Quantity | Historical 1.5 mm study mesh | New relocated-surface mesh |
|---|---:|---:|
| Tetrahedra | 3,771,342 | 3,770,701 |
| Mean ratio below 0.01 | 17,823 | 14,752 |
| Mean ratio below 0.1 | 199,048 | 199,928 |
| Minimum mean ratio | 1.38358 × 10⁻⁷ | 1.09610 × 10⁻⁷ |
| Median mean ratio | 0.484003 | 0.482040 |

The lowest bin contains fewer cells, while the wider bin and worst value do not
improve. The historical and current runs differ in runtime/parallelism and
regenerated interior cells. This is an artifact comparison, not a controlled
causal benchmark of relocation or a convergence result. All 14,752 cells in the
lowest bin touch at least one boundary node; node incidence alone does not
identify their cause. The new minimum Gmsh minSICN is 2.78438 × 10⁻⁶.
No stress, flow, heat-transfer or additive-manufacturing solve was run from this
mesh, and no physical result is inferred from its positive volumes.

## A fixed-face bound changes the next action

For one fixed triangular face, let S be the sum of its three squared edge
lengths and A₂ twice its area. Its normalised shape quality is
q_f = 2√3 A₂/S. Let the tetrahedron apex have normal height h and projected
distance r from the base centroid. Its six-edge squared-length sum is
4S/3 + 3r² + 3h², so its mean ratio is

`q_t = 12 (A₂ |h| / 2)^(2/3) / (4S/3 + 3r² + 3h²)`.

The maximum occurs at r = 0 and h² = 2S/9. Substitution gives
**q_t,max = q_f^(2/3)**. Thus no interior-node placement can give a tetrahedron
incident to a fixed face a higher mean ratio than that face-specific ceiling.
This is a necessary shape bound, independent of interior target size.

Nine controls check the regular case, equality at the optimal apex for four
different triangles and off-optimum sampled apices. The algebra above supplies
the bound; random samples are software controls, not its proof. The actual audit
rehashes the admitted surface, parent, mask and independently verified volume
mesh, then checks every predicted forced face against its actual adjacent cell.
It completes locally in 2.19 s under a 600-second controller.

- 213 boundary faces have ceilings below 0.01; they match exactly one low-quality
  tetrahedron each, covering 208 distinct cells in this actual mesh.
- 157 of these faces have all vertices locked, covering 155 current cells.
- 75 faces are directly protected, covering 75 current cells.
- The minimum face quality is 3.30357 × 10⁻⁶, so its incident tetrahedron's mean
  ratio cannot exceed 0.000221814 while that exact face remains.

The current distinct-cell counts are not universal lower bounds after changing
volume connectivity. A tetrahedron can have at most four boundary faces, so
retaining all 213 counted faces forces at least `ceil(213/4) = 54` subthreshold
cells in any such tetrahedralisation; retaining just the 75 directly protected
counted faces forces at least `ceil(75/4) = 19`. This loose combinatorial bound
does not assume that future cells keep their present identities.

The face ceiling identifies 208 current low-quality cells and does not explain
the remaining 14,544. It does prove that changing interior sizing alone cannot
eliminate the whole diagnostic category while the counted triangles remain
exact. It does not prove that the physical part is defective or unmanufacturable.
An alternative tessellation of an admissible geometric patch needs its own
geometry/feature-preservation proof. Acquired-surface CAD and geometry diagnosis
remain upstream work; another interior-size sweep is not an adequate response.

## Cost and remaining release requirements

The actual provider rate, including the 120 GB disk, was USD 0.2688889/hour.
From prelaunch intent through verified absence, 1,116.54 s elapsed. The
continuous rate-time estimate is **USD 0.08340**, excluding network. At the quoted
USD 0.00390625/GB in each direction, the conservative 13 GB network planning
allowance adds USD 0.05078; their planning total is USD 0.13418. These estimates
are not a finalised invoice or actual measured network charges. The separate
account-wide credit movement is also not attributed as an instance invoice.

The attempt allowance remains USD 1.50 inside the unchanged USD 35 program,
USD 30 compute allocation and USD 5 transfer/closeout reserve. Earlier charges
and reservation ceilings stay in the ledger. The guard was armed before the
paid call, limited time/rates, selected only the owned receipt ID and terminated
after independently observing absence. No unrelated resource was removed and
no automatic recharge was requested. The controller enforces time and rate
bounds; final charges still require provider reconciliation.

The complete-head objective remains active: bare-head reconstruction, all eight
accepted measured/toleranced interfaces, internal geometry, specimen material,
engine loads, calibrated manufacturing data and professional/physical validation
are still required. This successful mesh does not supply any of those missing
observations or constitute a functional-metal print file.
