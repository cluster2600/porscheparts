# Software chain: capabilities and evidence

[Repository home](../../README.md) · [Studies and results](ENGINEERING.en.md) ·
[BLT manufacturer dossier, in English](MANUFACTURING_REVIEW.md)

State on October 4, 2026. The executed numerical chain is not a physically
qualified manufacturing chain. “Available,” “executed” and “verified” are
distinguished below. Versions/runtimes come from this study's receipts;
no new tool was installed for this audit. Cylinder-head and titanium-support
results are not reused as evidence for this rotor.

| Stage and runtime | Actually executed input → output | Evidence and state | Limits / next verification |
| --- | --- | --- | --- |
| CAD: build123d 0.13 / OCP 8, native Kali2 amd64 | Original R0/V2/V5 parameters → BRep, STEP and tessellation; renders of the same geometry | [Geometry receipts](results/geometry/): valid BRep, positive volume, connected rotor, verified STEP reread | Unmeasured scale, 935/993 identity, interfaces and tolerances; define the functional part independently |
| Meshing: Gmsh 4.15.2, native Kali2 | Rotor STEP → structural C3D10 or fluid tetrahedra | [FEM reports](results/mechanics/): positive Gauss4 Jacobian, volume compared to CAD, verified C3D10 permutation; [CFD](results/cfd/): retained geometry | No metrological evidence; wall layers absent; local stress convergence not established |
| CFD QA: OpenFOAM Foundation 13, existing frozen image | `volume.msh` → `polyMesh`, standard checks and `-allGeometry -allTopology` | Independent gates, historical failures retained, R0 and V2 meshes admitted after refinement without lowering thresholds | Mesh gate essential but insufficient to validate the turbulence model or physical regime |
| Flow: same OpenFOAM 13, bounded Kali2 Docker | Admitted domain, frozen conditions/protocol → U/p/k/omega/nut/phi, flow and torque | Common-grid R0/V2 admitted at 600 iterations. Audit of 39 original tables: 11 fine phases have only two measurements, fine R0 admission withdrawn; fine V2 also fails pressure at 600/750/900. D1: control 960 unadmitted on p, relTol 0 branch stopped after 29 iterations; [bounded result](D1_EXECUTION.en.md). Instantaneous fields and residuals retained; complete window now mandatory. [Cadence correction](results/cfd/measurement-cadence-audit.json) | Isolated flow with inlet total pressure 0 / outlet static pressure 0, 6000 rpm; first-order convection, steady MRF; simplified energy balance not closed and compressible sensitivity required |
| Rotation/modal: CalculiX 2.23, native Kali2 | C3D10 + assumed elastic aluminum + fixed bore → U/S and 12 frequencies | Twelve R0/V5/V2 jobs, two mesh sizes; [comparison](results/mechanics/three-variant-comparison.json) and actual [R0 fields](results/mechanics/R0-fields.png) | R0/V5 modes without prestress, gyroscopic effects or bearings/contact; blade-root stresses mesh-sensitive; no qualified safe speed/fatigue |
| LPBF screening: NumPy and original script, Kali2/Mac CPU | Actual R0 STL → envelopes, overhangs, layer sections and support proxy | [Report](results/lpbf/lpbf-screen.json), volume check by section integration | Geometric screening at 50 µm and hypothetical envelope; simulates neither physical supports, laser path nor heat |
| Shrinkage/unclamping: native CalculiX 2.23, adapted original scripts | Same R0/V5 CAD/mesh, declared contraction field, ideal attachments → two U/S states, shrinkage and release | Native analytical benchmark and comparative cases under assumptions; zero/amplitude/orientation/support/mesh checks | Generic elasticity, unmeasured amplitude, no layer activation, plastic/thermal card or machine calibration; point-attachment peaks are not admissible manufacturing stresses |
| Qualified LPBF process simulation | Recipe, paths, temperature/plasticity material data, supports/plate and calibration → qualified distortion/defects | **Not demonstrated on R0/V5**; a tool's presence in an old inventory does not establish its execution/validation on this case | Obtain workshop data and select a suitable method; calibrate and validate on an independent build |
| Post-processing | Actual build + thermal/cutting/machining route → final condition and before/after measurements | **No actual treatment or qualified R0/V5 thermal simulation executed** | BLT is a review target; sequence and possible HIP need justification, furnace/route/material approval |
| CT / metrology / NDT | Actual specimen and inspection drawing → measurements, defects and acceptance decision | **No specimen/inspection report available**; private-scan audit and CAD QA executed, without replacing industrial inspection | Request CT resolution/detectability/covered volume, measurement plan and approved defect/tolerance criteria |
| OpenUSD 25.11, library already available on Mac | Analytical tessellation and metadata → USD assets/scene, parsing/composition/topology/units/materials | [Assets](omniverse/), 24 generic validators without findings; meters per unit and axes verified | Missing `shaderDefs.usda` resource: Sdr shader check unvalidated; visual asset and linked evidence, not physical solver |
| NVIDIA Omniverse / SimReady / RTX | NVIDIA profile, compatible runtime and correlated data → validated twin | **No NVIDIA end-to-end (e2e) validation or RTX render executed for this mission**; no NVIDIA GPU available on authorized resources | Runtime/profile and physical correlation remain to be established; generic OpenUSD alone demonstrates neither SimReady nor a validated twin |
| Repository software QA: GitHub Actions | Exact commit → `make check` | PR129 merged, main `8283155cb2b1275b0bf3e22d4d7459d4ac76b059`, [green post-merge CI](https://github.com/cluster2600/porscheparts/actions/runs/37208996692) | Historical incompatible local checks retained in [runtime report](results/runtime/repository-checks.json); these additions require CI at their exact commit; physics remains separate from CI |

OpenFOAM image used:
`ghcr.io/cluster2600/3dprinting993-mesh-cfd@sha256:a1db60cbf61bbcca52c171e50cab01ed0b6ec860b227e7c5fc50f7b809659b4f`.
This mission's Kali2 jobs remain sequential, at most four CPU and six GiB;
deadlines are frozen per job and third-party services preserved. Measured
Docker-client memory is not the container's memory peak: the explicit
container ceiling is the relevant limit.

The [manufacturer dossier](MANUFACTURING_REVIEW.md) identifies workshop
decisions and necessary physical tests. No manufacturing validation, material
certification, service qualification or catalogue release is declared.
