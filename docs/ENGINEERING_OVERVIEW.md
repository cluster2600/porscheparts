This is the full technical overview that used to be the README. The plain-language introduction is in [README.md](../README.md).

<div align="center">

![The 964 body shell traced from the workshop manual, turning, coloured by von Mises stress under a torsion load](media/diagrams/964-hero.gif)

# porscheparts

**Reverse engineering for the Porsche 911 964 and 993**<br>
*Sourced data, falsifiable calculations, no part manufactured.*

[![Validate catalogue](https://github.com/cluster2600/porscheparts/actions/workflows/validate.yml/badge.svg)](https://github.com/cluster2600/porscheparts/actions/workflows/validate.yml)
[![License: all rights reserved](https://img.shields.io/badge/license-all%20rights%20reserved-lightgrey)](../LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/)
[![Active phase](https://img.shields.io/badge/active%20phase-manufactures%20nothing-critical)](SAFETY.md)
[![Docs](https://img.shields.io/badge/docs-English-brightgreen)](TRANSLATION.md)

[**Our Porsche information catalogue**](https://porschefanatics.com/) ·
[**Our Qwen: qwen-picogk**](#our-qwen-qwen-picogk) ·
[**Software chain: Qwen and PicoGK**](#software-chain-qwen-and-picogk) ·
[**Parts**](#2-993-parts-for-additive-manufacturing) ·
[**964 structure and monocoque**](#1-the-964-body-shell-and-the-carbon-monocoque-programme) ·
[**Engine cooling**](#3-engine-cooling) ·
[**Gallery**](GALLERY.md) ·
[**993 carrier workflow**](manufacturing/993_CARRIER_PROJECT_EN.md) ·
[**Run the checks**](#quick-start) ·
[**Safety first**](SAFETY.md)

</div>

---

This repository does not publish a library of files to print. It publishes
**sourced data** and **falsifiable calculations**: every claim of fit, mass,
airflow or stiffness is tied to a measurement, a verifiable source or a
calculation anyone can rerun, and it is **withdrawn when it no longer holds**.
The repository has withdrawn several, listed
[further down this page](#what-the-repository-withdrew-from-its-own-results).

> [!IMPORTANT]
> **No part is validated.** All 43 part records are at status `concept`, and 25
> of them are `prohibited_pending_engineering`. Read [SAFETY.md](SAFETY.md).

## Software chain: Qwen and PicoGK

**[PorscheFanatics.com](https://porschefanatics.com/) is our Porsche information
catalogue.** It brings together [parts and suppliers](https://porschefanatics.com/parts/),
[factory references](https://porschefanatics.com/oem/), a
[research library](https://porschefanatics.com/library/) and
[technical guides](https://porschefanatics.com/knowledge/), with links to their
sources. We use it upstream to identify parts, applications and documentary
evidence. Each reused fact retains its source and evidence level; physical
interface measurements are recorded separately in this engineering repository.

**[qwen-picogk](https://github.com/cluster2600/qwen-picogk) is our locally trained
Qwen project.** We develop task-specific adapters, authored training data,
independent request checks and trusted native PicoGK hosts there. The released
planner is our MLX LoRA adaptation of **Qwen2.5-Coder-1.5B-Instruct**, used with
a 4-bit base on Apple Silicon. Its documented tasks cover English, French,
German, Japanese and Chinese. See [our Qwen's role and supported paths](#our-qwen-qwen-picogk).

**Our qwen-picogk adapter proposes a checked plan; PicoGK builds geometry;
OpenFOAM and CalculiX calculate its behaviour.** This repository, `porscheparts`,
holds the part records, design sources and engineering evidence. The
engineering order starts with the part's requirements,
measured interfaces, material/process assumptions and loads. Missing physical
inputs keep a result at study level. The diagram describes dependencies, not
an autonomous system or a claim that every step has run on every part.

```mermaid
flowchart TB
    CATALOG["PorscheFanatics.com<br/>our Porsche information catalogue"] -->|sourced part references and documentation| INPUT
    INPUT["Requirements, measurements and interfaces"] -->|manual authoring| CODE["Reviewed C# recipes and parameters"]
    INPUT -. optional assistance .-> QWEN["qwen-picogk<br/>our trained Qwen adapter; bounded JSON proposal"]
    QWEN --> CHECK["Independent schema, units and intent checks"]
    CHECK -->|accepted parameters| CODE
    CODE --> PICO["PicoGK + ShapeKernel / LatticeLibrary<br/>new M64 geometry; VDB and mesh exports"]
    INPUT --> EXISTING["Existing build123d / FreeCAD / STEP masters"]
    PICO --> GEO["Geometry and assembly checks<br/>dimensions, interfaces, topology and clearances"]
    PICO -. optional mesh queries .-> WARP["NVIDIA Warp<br/>batched point-to-surface queries; isolated synthetic pilot"]
    WARP -->|measurement report| GEO
    EXISTING --> GEO
    GEO --> CAE["Case preparation and meshing: Gmsh / OpenFOAM tools<br/>Solvers: OpenFOAM / CalculiX; Cantera when needed"]
    CAE --> REVIEW["Convergence, balances and comparison with measurements"]
    REVIEW -->|revise the design| CODE
    REVIEW --> PREP["Engineering and process review<br/>DfAM, supplier preparation; Adamantine if applicable"]
    PREP --> PHYSICAL["Authorised prototypes, metrology and physical tests"]
    PHYSICAL -->|measured discrepancies| INPUT
    GEO -. visual inspection .-> USD["OpenUSD / Omniverse<br/>assembly, contacts and rendering"]
    REVIEW -. optional reference dataset .-> PN["PhysicsNeMo<br/>train and validate a fast surrogate"]
```

| Tool or layer | What it does here | When it enters |
|---|---|---|
| **[PorscheFanatics.com](https://porschefanatics.com/)** | Our information catalogue: part listings, factory references, library and technical guides with sources. | Research and identification, before defining the engineering inputs. |
| **[Our qwen-picogk](https://github.com/cluster2600/qwen-picogk)** | Our trained Qwen adapters and guarded toolchains. The released planner proposes JSON parameters for trusted PicoGK recipes; the scan demonstration has a separate adapter. | After explicit requirements or independently extracted scan features; outputs are checked before native geometry. |
| **Codex** | Assist with authoring, repository changes and review. | Throughout development, alongside the local Qwen project. |
| **C# / PicoGK** | Generate new M64 geometry from reviewed rules; ShapeKernel and LatticeLibrary provide geometric building blocks. OpenVDB stores volumes and fields. | Before geometric inspection and simulation, then again when the design changes. Existing CAD masters remain authoritative for their own zones. |
| **[NVIDIA Warp](WARP_GEOMETRY_VAST_PILOT.md)** | Batched geometric queries after PicoGK. The synthetic pilot has an analytic oracle; the [935 continuation](research/935-horizontal-cooling/NATIVE_GPU_CONTINUATION_20261022.md) checks the complete private rotor on CUDA. | Optional geometry screening; numerical query agreement does not establish application speedup or physical performance. |
| **[Our cluster_compilot](WARP_GEOMETRY_VAST_PILOT.md#where-cluster_compilot-can-help)** | Optimize regular C/OpenMP CPU loops through model proposals, dependence checks and numerical verification. | Optional, after profiling identifies a costly CPU loop; a separate environment and experiment from Warp. |
| **Gmsh / OpenFOAM / CalculiX** | Prepare calculation meshes and solve fluid, thermal or structural cases; ParaView/PyVista inspect results. | After geometry, materials, loads and boundary conditions are sufficient for the declared study. |
| **Adamantine / AdditiveFOAM** | Study additive manufacturing: global thermomechanics or the local melt pool. | With a defined process case, including material, orientation and heat-source history. These are research tools, not a qualified machine job. |
| **OpenUSD / Omniverse** | Compose and inspect the assembly, contacts, motion and visual results. | A branch from checked geometry; rendering is not required to run CFD/FEA or prepare fabrication. |
| **PhysicsNeMo** | Learn a fast approximation of reference behaviour. | Optional, after suitable solver/measurement references exist, with separate validation. |
| **PrusaSlicer / supplier tools** | Prepare polymer prototypes or an industrial machine job. | After the relevant design and process review; an LPBF job requires the supplier's qualified workflow. |

### Our Qwen: qwen-picogk

The [qwen-picogk repository](https://github.com/cluster2600/qwen-picogk) contains
our adapters, training configuration, datasets, evaluation records and native
C# hosts. Its role is visible in three separately documented paths:

- **Published multilingual planner:** request → our pinned MLX LoRA adapter →
  JSON → independent unit and intent checks → trusted C# recipe → PicoGK →
  native geometry checks. It covers bounded synthetic cylinders, pipes,
  washers, BCC cells and thread cutters, plus missing-interface refusal.
  [Architecture and evidence](https://github.com/cluster2600/qwen-picogk/blob/main/docs/ARCHITECTURE.md).
- **Scan demonstration:** scan → independent feature extraction → our
  dedicated scan-demo adapter → checked tool plan → reconstruction tools and
  trusted PicoGK host → geometry checks. PyMesh cleanup and intersection
  auditing surround this path. The model plans from typed features; geometric
  tools process the actual vertices and triangles.
  [OBJ-to-STL demonstration](https://github.com/cluster2600/qwen-picogk/blob/main/docs/OBJ_TO_STL_DEMO.md)
  and [PyMesh integration](https://github.com/cluster2600/qwen-picogk/blob/main/docs/PYMESH_SCAN_RECONSTRUCTION.md).
- **Direct C# research:** our adapter produced six restricted C# beam statements,
  admitted into a trusted wrapper after code checks and run through native PicoGK.
  Broader AM program generation
  remains experimental, with rejected trials preserved and no qualified AM C#
  adapter. [Bounded C# probe](https://github.com/cluster2600/qwen-picogk/blob/main/docs/SCAN_TO_PICOGK.md)
  and [AM training study](https://github.com/cluster2600/qwen-picogk/blob/main/am-code/README.md).

The planner command itself neither writes C# nor executes geometry. Model
training, code generation, native geometry and physical validation have
separate evidence. The recorded Mac inference uses MLX; the generic
vLLM/CUDA serving route is documented separately. Training another adapter is
a parallel software activity, not a prerequisite for designing a part.
See [PicoGK and Qwen on the Mac](PICOGK_MAC_SETUP.md),
[local training evidence](QWEN_TRAINING.md) and
[our published model's training record](https://github.com/cluster2600/qwen-picogk/blob/main/docs/TRAINING.md).

### Execution and detailed contracts

**Where it runs.** Mac and Kali provide local authoring, Qwen assistance and
versioned geometry and solver runs. Docker packages runtimes; Git, Make and CI
preserve versions and check outputs. A final Vast/Omniverse review is a
separate, explicitly approved GPU job. These machines and containers are
execution environments, not additional design stages.

The [October 22 native 935 continuation](research/935-horizontal-cooling/NATIVE_GPU_CONTINUATION_20261022.md)
records complete-rotor CUDA checks, native OVRTX assembly views, a bounded analysis
surface and conditional material/speed comparisons. The rental is destroyed after
verified backups. Fan CFD, mechanical convergence and manufacturing remain open.

The [analysis-mesh correction](research/935-horizontal-cooling/ANALYSIS_MESH_CONTINUATION_20261022.md)
then preserves the full surface bound while preventing the simplifier from
creating very thin triangles. Geometric checks, native volume meshing and
mechanical acceptance remain separate stages.

The [quadratic-rotor continuation](research/935-horizontal-cooling/QUADRATIC_ROTOR_CONTINUATION_20261022.md)
then obtains a fully audited positive tetrahedral volume and completes matched
linear/quadratic calculations on the Mac and Kali. Their large formulation
difference keeps mechanical convergence open; results and rejected trials are
preserved privately, without another rental.

The [interior-star correction](research/935-horizontal-cooling/INTERIOR_STAR_CONTINUATION_20261022.md)
then preserves the boundary and exact volume while improving internal mesh
conditioning. Repeated quadratic fields retain stable global displacement but
show a 68% peak-stress change, keeping strength and spatial convergence open.

The [Foundation 13 rotor pilot](research/935-horizontal-cooling/FOUNDATION13_ROTOR_PILOT_20261022.md)
then verifies the rotating-wall velocity and viscous torque against circular
Couette flow before running MRF/SST on the private rotor. The first fluid mesh
fails the extended concavity check; its exploratory calculation cannot qualify
a fan curve, the historical assembly or manufacturing.

The [fluid-mesh correction](research/935-horizontal-cooling/FLUID_MESH_CORRECTION_20261022.md)
then obtains closed, positive, boundary-preserving tetrahedral fluid volumes
and independently verifies their native import. Full finite-volume quality still
rejects them; bounded skin simplification and local subdivision are retained as
failed alternatives, with no new accepted fan calculation.

The [fluid-topology continuation](research/935-horizontal-cooling/FLUID_TOPOLOGY_CONTINUATION_20261022.md)
then changes local tetrahedral connectivity while preserving all vertex coordinates
and boundary triangles. Exact cavity checks and complete native audits measure
the improvement; remaining full-quality failures still block CFD admission.

The [interior fluid-mesh continuation](research/935-horizontal-cooling/FLUID_KERNEL_CONTINUATION_20261022.md)
then adds guarded interior air-mesh points while retaining every physical boundary
and original coordinate. Failed determinants fall from 2,090 to 519; independent
native readback confirms the complete mesh, but four quality checks still fail.

The [finite-volume point-placement study](research/935-horizontal-cooling/FLUID_POINT_PLACEMENT_20261022.md)
then searches three-dimensional cavity point positions with bounded SciPy runs.
Failed determinants fall from 519 to 448 with exact boundaries retained; the
remaining native quality failures continue to block a new rotor CFD calculation.

The [convex fluid-cell agglomeration](research/935-horizontal-cooling/FLUID_AGGLOMERATION_20261022.md)
then joins 29 guarded tetrahedral pairs without moving any point or physical
boundary. Complete mixed-cell and native-field checks pass; failed determinants
fall to 419, while four full quality checks still block CFD admission.

The [reference-wall correction](research/935-horizontal-cooling/REFERENCE_FLUID_WALL_20261022.md)
then replaces the snapped rotor wall with every analysis-reference triangle.
Complete serialized and native readback preserves that surface in 3,685,053
positive fluid cells. Six native quality checks still reject this faithful
baseline; protected poor surface facets and near-wall meshing remain to repair.

The [bounded surface repair](research/935-horizontal-cooling/SURFACE_FACET_REPAIR_20261022.md)
then reduces poor input facets from 189 to 46 while retaining the complete
original/reference surface bounds. The new faithful fluid volume fails seven
native quality checks; a cube-qualified polyhedral alternative fails eleven on
the real rotor, including negative cells. Both refusals remain explicit.

The [local-relocation continuation](research/935-horizontal-cooling/LOCAL_RELOCATION_20261022.md)
then removes the remaining poor surface facets while preserving both complete
surface bounds and the PicoGK master. An adaptive fluid-mesh experiment adds
an explicit size field; its surface, volume and native-quality admissions remain
separate from the certified analysis geometry.

The [hex-mesh continuation](research/935-horizontal-cooling/HEX_MESH_CONTINUATION_20261022.md)
preserves the saved castellated mesh, qualified four-rank controls and a complete
wall-inspection view. Precise OBJ and rounded VTK exports have separate roles.
The user paused the real snapping run before completion; its processes are
stopped and its checkpoint is backed up. No new fan calculation is admitted.

The [25 October root and mesh continuation](research/935-horizontal-cooling/ROOT_MESH_RESUME_20261025.md)
then closes five inferred root passages directly in the PicoGK recipe while
preserving protected original triangles. It also replaces Foundation 13's
legacy reconstruction no-op with a moved-cube-qualified reconstruction. The
full native fluid-mesh check still rejects concave cells; airflow and
manufacturing remain unqualified.

The [corrected analysis surface](research/935-horizontal-cooling/CORRECTED_ANALYSIS_20261025.md)
then bounds a simplified rotor against the repaired PicoGK master in both
directions and prepares a new Foundation 13 case from that geometry. The case
has not yet been meshed or solved; the previous concavity failure still needs
a native diagnosis and correction.

Read the [engineering workflow](architecture/engineering-workflow.md),
[PicoGK decision](decisions/0004-picogk-new-geometry.md),
[software inventory and dated execution evidence](SOFTWARE_STACK.md), and
[per-part workflow](WORKFLOW.md) for the detailed contracts. Passing code,
mesh or USD checks does not close physical qualification.

<table>
<tr>
<td align="center"><h3>545</h3>qualified source records</td>
<td align="center"><h3>43</h3>part records<br><sub>25 prohibited as they stand</sub></td>
<td align="center"><h3>34</h3>993 design dossiers<br><sub>for additive manufacturing</sub></td>
</tr>
<tr>
<td align="center"><h3>10</h3>digital twin records<br><sub>none at <code>F2_interface</code></sub></td>
<td align="center"><h3>21</h3>LPBF geometric screens<br><sub>17 screened, 4 not</sub></td>
<td align="center"><h3>3,391</h3>tests run by<br><code>make check</code></td>
</tr>
</table>

## What changed recently

| date | change |
|---|---|
| 2026-10-16 | **The 964 monocoque redone in quadratic shells, and a buckling screen**: CalculiX's S3 triangle locks in bending (7-21% of the Scordelis-Lo reference deflection). In S6 the CFRP skin boxes give 19,900 N·m/deg on the finest mesh, still rising, not 35,500 "converged"; the windscreen frame joins the door rings at the head of the cabin members, and the shell-tube comparison is withdrawn. A linear buckling screen finds its first modes at ×2.4 to ×4 the assumed service loads: a screen, not a pass. [S6 correction](../twins/964-chassis/monocoque/README.md#s6-correction-2026-10-12-every-stiffness-redone) |
| 2026-10-11 | **917 quatre soupapes et biturbo sous hypothèses** : 119 définitions, 1 129 occurrences, culasses air + huile et deux turbos bioniques à 39 composants. Formes ramifiées ; incompatibilité d'enveloppe culasse/alésage détectée, interfaces et fabrication non qualifiées. [Assemblage de conception](../models/917-engine-reconstruction/assembly/README.md) |
| 2026-10-11 | **Cotes FIA du 917 appliquées à PicoGK** : calotte à 43 mm de l'axe, référence de maneton 52 mm et comparaison avec les masses documentées. L'implantation provisoire du cylindre est rejetée ; variante du scan et fabrication non qualifiées. [Réconciliation FIA](../models/917-engine-reconstruction/fia/README.md) |
| 2026-10-10 | **Reprise du moteur 917 avec PicoGK** : coques scannées, 48 instances paramétriques sous hypothèses et 18 scénarios de charges. Piston creux après rejet du piston plein ; interfaces et matériaux non qualifiés. [Reconstruction](../models/917-engine-reconstruction/README.md) |
| 2026-10-12 | **Monocoque in bending**: between the axles, the skin boxes stiffen the shell about four times (five to fifteen in torsion). Same cabin members, other weights: the sills lead (28-37% of the cabin's bending stiffness), the door rings follow; the members torsion would prune cost about 1%. Torsion decides the architecture. [Bending](../twins/964-chassis/monocoque/README.md#bending-the-same-members-other-weights) *Values superseded on 2026-10-12: S3 shells, see the S6 correction.* |
| 2026-10-12 | **Tubes meshed as shells**: bonded along their line of tangency, the tubes leave the skin between them open, and the model keeps softening with the mesh; the skin-formed boxes, stable, lead by ×1.18 per kg on the finest mesh. The direction holds: form the closed sections with the skin. [Comparison](../twins/964-chassis/monocoque/README.md#two-architectures-one-load-case) *Values superseded on 2026-10-12: S3 shells, see the S6 correction.* |
| 2026-10-11 | **Tubes against skin boxes: the joint decides**: tied to the skin over a bonded strip, the tube model converges, but its K follows the strip width (23,700 to 57,500 N·m/deg, the skin boxes 35,500 in between). The ranking is not settled with beam tubes; the tube-to-skin joint is the design point. [Comparison](../twins/964-chassis/monocoque/README.md#two-architectures-one-load-case) *Values superseded on 2026-10-12: S3 shells, see the S6 correction.* |
| 2026-10-11 | **Monocoque torsion corrected, and where the carbon pays**: the bulkheads were missing from every torsion model since 2026-10-08; with them the open shell is 3,209 N·m/deg and the CFRP monocoque about 35,500. The tube-versus-box ranking is not settled. A ply on the skin of a closed section returns 4-7 times more than on the floor or bulkheads; an F1 at the same mass gains 6%. [Corrections](../twins/964-chassis/monocoque/README.md#corrections-2026-10-11) *Values superseded on 2026-10-12: S3 shells, see the S6 correction.* |
| 2026-10-10 | **What each monocoque member is worth**: the cabin is carried by the door rings, the windscreen frame, the quarter-window rings and the sills; the engine-lid ring is worth nothing in torsion; the weak members removed together cost 12-15% of the cabin stiffness for 8-12 kg. [Members](../twins/964-chassis/monocoque/README.md#what-each-member-is-worth) *Values superseded on 2026-10-11.* |
| 2026-10-09 | **Two monocoque architectures in torsion**: on the same mesh and load, closed sections formed by the skin are 1.4 to 1.9 times stiffer per kilogram than tubes tangent to it, at all three meshes. A ranking of two hypotheses. [Comparison](../twins/964-chassis/monocoque/README.md#two-architectures-one-load-case) *Values superseded on 2026-10-11.* |
| 2026-10-09 | **Torsion of the monocoque architecture**: K about 29,500 N·m/deg in steel and 22,300 in CFRP (75 kg), stable within 7% over three meshes, more than five times the open shell; carbon gives ×1.15 to ×1.28 per kilogram. A model value, not a car's. [Torsion](../twins/964-chassis/monocoque/README.md#torsion-of-the-monocoque-architecture) *Values superseded on 2026-10-11.* |
| 2026-10-08 | **A ZESAD-type carbon monocoque in PicoGK**, inside the traced shell: closed sections around every aperture, boxed sills, tunnel and rails, sandwich floor and bulkheads; about 95 kg from assumed layups. A design envelope, not a part. [Monocoque](../twins/964-chassis/monocoque/picogk/README.md) |
| 2026-10-08 | **A 911-shaped monocoque shell**: outline traced from the workshop manual's plate 50-05a, sections modelled, a first whole-body torsion run; it replaces the box cell in the banner. [Shell](../twins/964-chassis/monocoque/README.md) |
| 2026-10-08 | **964 datum chain closed** from the workshop manual's own plates (50-02, 50-03, 50-05a): every suspension and power-unit mount of the monocoque interface contract now has a fore-aft position, checked against the underside scan. [Details](../twins/964-chassis/README.md#the-longitudinal-chain-closed-from-plate-50-05a) |
| 2026-10-08 | **LPBF geometry preview pictured**: layer-stack animations for the F1 cooling impeller and its stator. [Impeller dossier](993/993_COOLING_IMPELLER_WE43_F1.md#metal-lpbf-geometry-preview--hypothetical-supports) |
| 2026-10-08 | **PicoGK batch 01**: ten parametric concept parts from one voxel-kernel project. [Batch page](../parts/picogk-993-batch-01/README.md) |
| 2026-10-07 | **F1 cooling impeller redesigned from the original Turbo rotor**: same cup, windows and envelope, airfoil blades in WE43; the earlier generic shrouded design was withdrawn. [Dossier](993/993_COOLING_IMPELLER_WE43_F1.md) |

> [!TIP]
> **Printable today:**
> - 🖨️ the **[switch trim ring, F1](../parts/993-int-switch-trim-ring-f1-0001/print/README.md)**: a part the
>   repository designed, printed as designed, 17 minutes of PETG or ASA, no supports. Fit on the car not
>   checked yet ([decision 0010](decisions/0010-print-the-trim-ring-f1-in-polymer.md)).
> - a **[fit-test kit for the dashboard switch blank](../parts/993-int-switch-blank-0001/print/README.md)**: three
>   sizes to find the real opening ([decision 0009](decisions/0009-first-fit-test-print-switch-blank.md)).
> - 🧩 **display mock-ups** of two prohibited designs, engraved "MOCK-UP / NOT FOR USE":
>   [the F0 connecting rod](../parts/993-eng-connecting-rod-ti64-f0-0001/print/README.md) and
>   [the K16 wheel pair on a stand](../parts/993-eng-k16-compressor-wheel-al2139-f1-0001/print/README.md)
>   ([decision 0011](decisions/0011-printable-display-mockups-of-prohibited-parts.md)).
>
> None of them is validated.

## How the repository works

Every artifact climbs the same ladder, and every rung is checked by `make check`.
Nothing leaves the last rung: manufacturing is suspended by design.

```mermaid
flowchart LR
    S["Sources<br/><sub>catalog/sources/</sub>"] --> R["Part records<br/><sub>catalog/parts/</sub>"]
    R --> D["Design dossiers<br/><sub>docs/993/</sub>"]
    D --> T["Digital twins<br/><sub>twins/</sub>"]
    T --> C["FEA · CFD · LPBF geometry screening<br/><sub>CalculiX · OpenFOAM · LPBF</sub>"]
    C --> G{"Quality gates<br/><sub>docs/QUALITY_GATES.md</sub>"}
    G -- "claim fails" --> W["Withdrawn, and said so"]
    G -- "claim holds" --> E["Evidence<br/><sub>pinned by SHA-256</sub>"]
    E -. "suspended in the active phase" .-> M["Manufacturing"]
    classDef stop fill:#fde2e1,stroke:#c0392b,color:#1a1a1a;
    classDef ok fill:#e3f1e6,stroke:#2e7d32,color:#1a1a1a;
    class M,W stop
    class E ok
```

### Where to start

| I want to… | go to |
|---|---|
| print something today | [the F1 switch trim ring](../parts/993-int-switch-trim-ring-f1-0001/print/README.md) · [the switch blank fit-test kit](../parts/993-int-switch-blank-0001/print/README.md) |
| see which 993 parts exist and their status | [the parts table](#2-993-parts-for-additive-manufacturing) → one page per part in [`docs/pieces/`](pieces/) |
| follow the carbon monocoque programme | [section 1](#1-the-964-body-shell-and-the-carbon-monocoque-programme) → [the programme](MONOCOQUE_964_993_PROGRAMME.md) |
| see the engine cooling work | [section 3](#3-engine-cooling) → [the fan programmes](FAN_DEVELOPMENT_PROGRAMMES.md) |
| watch an LPBF geometry preview | [F1 impeller build-up](../parts/993-eng-cooling-impeller-we43-f1-0001/media/print-simulation/build.gif) · [all print screens](993/print-screen-status.json) |
| know what may and may not be built | [SAFETY.md](SAFETY.md) · [docs/QUALITY_GATES.md](QUALITY_GATES.md) |
| add a part or a source | [CONTRIBUTING.md](CONTRIBUTING.md) · [docs/WORKFLOW.md](WORKFLOW.md) · [docs/SOURCE_POLICY.md](SOURCE_POLICY.md) |
| find any document | [the documentation index](README.md) · [the gallery](GALLERY.md) · [dated reports](reports/README.md) |
| browse the digital twins | [twins/README.md](../twins/README.md) |
| run the checks locally | [Quick start](#quick-start) |

### Contents

1. [The 964 body shell and the carbon monocoque programme](#1-the-964-body-shell-and-the-carbon-monocoque-programme)
2. [993 parts for additive manufacturing](#2-993-parts-for-additive-manufacturing)
3. [Engine cooling](#3-engine-cooling)
4. [Engine and turbo research](#4-engine-and-turbo-research)
5. [Body and interior](#5-body-and-interior)
6. [The catalogue and its data contract](#6-the-catalogue-and-its-data-contract)
7. [The rules](#the-rules) · [What the repository withdrew](#what-the-repository-withdrew-from-its-own-results) · [What it does not claim](#what-the-project-does-not-claim)
8. [Quick start](#quick-start) · [Layout](#repository-layout) · [Status](#status)

---

## 1. The 964 body shell and the carbon monocoque programme

The main workstream. Its goal is a **replacement carbon monocoque for 964 and
993 restomods**, competing with the one existing offer on the axis where that
offer is bare: published data. The [programme](MONOCOQUE_964_993_PROGRAMME.md)
says what has to be established, in what order, and that it **contradicts the
written scope** of [ROADMAP.md](ROADMAP.md).

### The structure: what the shell model shows

A finite-element shell model of the floor pan, the box section and the full
cell answers **relative** questions: between changing the material and closing
the body shell, which pays off more? Where does the load go in torsion?

![The shell model, bare floor pan and full cell](media/diagrams/964-modele-coque.svg)

**Results that hold**, see [`twins/964-chassis/fea/`](../twins/964-chassis/fea/):

- the **side rail** carries torsion, not the floor pan, which agrees with plate
  50-013 of the workshop manual, which places high-strength steel there;
- **closing a ring does not just add stiffness, it changes the mechanism that
  carries it**: bending on the bare floor pan, shear on the closed cell;
- from bare floor pan to closed cell, **K × 3.77 for mass × 2.3**;
- roof and windshield frame together are worth **1.63 times** the sum of their
  separate contributions: the roof only works once the ring is closed;
- at equal mass, closing the body shell is worth more than switching to carbon.

![von Mises stress on the bare floor pan](media/diagrams/964-chemin-effort.svg)

A **corpus of 3,000 CalculiX cases** in quadratic shells is built to train a
design surrogate later, its validation set frozen before any model exists:
[docs/MONOCOQUE_964_993_CHAINE_CALCUL.md](MONOCOQUE_964_993_CHAINE_CALCUL.md).

### The shape: a 964 shell from the workshop manual

The box cell above has no 911 shape. The
[monocoque shell](../twins/964-chassis/monocoque/README.md) takes its outline
from plate 50-05a, which draws the body-in-white to scale from the side and
from above, with wings, doors and lids off. Side profile, plan width, door
aperture, quarter window and rear wheel house are traced from it; the sections
between them (tumblehome, barrel sides, 880 mm beltline) are modelled.

![The monocoque shell traced from plate 50-05a](../twins/964-chassis/monocoque/evidence/shell-views.png)

A first torsion run on it, uniform 0.8 mm steel with every aperture open,
puts the load around the windscreen frame, the A-pillars, the door corners and
the C-pillars: the open shell a monocoque has to close. Its K, 104 N·m/deg
in quadratic S6 shells (3,209 in the superseded S3), belongs to that surface
model, not to a 964.

Inside that shell, [a ZESAD-type carbon monocoque](../twins/964-chassis/monocoque/picogk/README.md)
is generated in voxels with PicoGK. Each aperture gets a closed section and
the sills, tunnel and rails are boxes, so the closures the box-cell study
ranked first are there by construction. Member sizes and layups are
hypotheses. In torsion, on the same mesh and load as the open shell, the
architecture is more than forty times stiffer. Its K, 19,900 N·m/deg in
CFRP on the finest mesh, still rises 8 to 10% on the last refinement: a
lower bound, not a converged value. Until 2026-10-12 it looked converged
within 2% at 35,500: the S3 element locked in bending
([S6 correction](../twins/964-chassis/monocoque/README.md#s6-correction-2026-10-12-every-stiffness-redone),
[torsion](../twins/964-chassis/monocoque/README.md#torsion-of-the-monocoque-architecture)).

![A ZESAD-type monocoque generated with PicoGK](../twins/964-chassis/monocoque/evidence/zesad-monocoque-turntable.gif)

### The interfaces: where a monocoque has to bolt up

A monocoque replaces the body shell, so it must carry every suspension,
power-unit and jacking interface in one frame. Until October 2026 the
fore-aft position of those points could not be established. It now is, from
Porsche's own repair plates: plate 50-05a dimensions three points from a 0 line
through the front strut mounts, plate 50-02 shows dimension P is longitudinal,
and the rear diagonals of plate 50-03 are read the way both drawings and the
scan confirm. Two independent published paths place the front jacking point
within 1.9 mm of each other.

![Published datum chain tied to the underside scan](../twins/964-chassis/evidence/scan-tie-50-05a.png)

*Blue: points placed from published dimensions. Green: rear mounts scaled off
the plate. Black: features measured on the scan. Red: the previous, wrong
network.*

The monocoque's governing span, front suspension mount to transmission
carrier, is **1535.6 mm**, both ends published. What is missing now is
tolerance, not data: the points carry ±2 to 9 mm where a tool needs ±1 mm.
[The full chain, its checks and its limits](../twins/964-chassis/README.md#the-longitudinal-chain-closed-from-plate-50-05a).

## 2. 993 parts for additive manufacturing

**34 design dossiers** in [`docs/993/`](993/) and **43 part records**,
from the headlamp spring hook to the K16 turbine wheel in Inconel 718, by way
of the Ti-6Al-4V connecting rod, the AlSi10Mg compressor wheel, the IN625
exhaust manifold and the WE43 cooling impeller. Each dossier starts from
dimensions published by a supplier, separates what is sourced from what is
assumed, and states what it does not contain.

**LPBF geometric screening.** Each STEP master is sliced over its full height
at a candidate layer thickness and checked against the EOS M 290 envelope.
The screen proposes a geometric orientation and a hypothetical support
envelope, and samples wall thickness and trapped powder. 17 screens completed;
3 failed closed and 1 hit the memory cap. None establishes printability.
No melt-pool, thermal, residual-stress or distortion simulation was run;
supports and orientation remain unqualified.

<div align="center">

![F1 cooling impeller geometry preview with hypothetical supports](../parts/993-eng-cooling-impeller-we43-f1-0001/media/print-simulation/build.gif)

*The F1 cooling impeller: the geometric report has 6,286 slices at 30 µm.
This animation uses coarse 0.5 mm slices and shows hypothetical support
regions in orange. No process physics or qualified support design; printing
is not authorized.*

</div>

**PicoGK batch 01.** [Ten parametric concept parts](../parts/picogk-993-batch-01/README.md)
generated from one C# voxel-kernel project, each parameter tagged
`published`, `community` or `assumption`. Their mounting interfaces are
assumptions, so none is functional.

The table below is generated from `catalog/parts/` on every `make check`. The
"status" column is the record's, not an intention: a part **prohibited pending
engineering** stays so until an engineering review lifts it.

<!-- parts:start - generated by scripts/render_parts_table.py -->

> [!CAUTION]
> These are concept models for studying parts in software, not validated parts. 🖨️ marks a printable design, 🧩 an engraved display mock-up (never for use).

<table>
<tr>
<td align="center" width="16%"><a href="../parts/993-body-front-impact-support-alsi10mg-f0-0001/"><img src="../parts/993-body-front-impact-support-alsi10mg-f0-0001/media/preview.png" alt="993 front impact support" width="130"><br><sub>993 front impact support</sub></a></td>
<td align="center" width="16%"><a href="../parts/993-body-front-lid-0001/"><img src="../parts/993-body-front-lid-0001/media/preview.png" alt="Front lid" width="130"><br><sub>Front lid</sub></a></td>
<td align="center" width="16%"><a href="../parts/993-ca-charge-pipe-set-pet-0001/"><img src="../parts/993-ca-charge-pipe-set-pet-0001/media/preview.png" alt="993 Turbo charge-air tract transc…" width="130"><br><sub>993 Turbo charge-air tract transc…</sub></a></td>
<td align="center" width="16%"><a href="../parts/993-ca-turbo-intake-manifold-pet-0001/"><img src="../parts/993-ca-turbo-intake-manifold-pet-0001/media/preview.png" alt="993 Turbo turbocharging intake tr…" width="130"><br><sub>993 Turbo turbocharging intake tr…</sub></a></td>
<td align="center" width="16%"><a href="../parts/993-elec-headlamp-spring-hook-f0-0001/"><img src="../parts/993-elec-headlamp-spring-hook-f0-0001/media/preview.png" alt="Headlamp spring hook repair" width="130"><br><sub>Headlamp spring hook repair</sub></a></td>
<td align="center" width="16%"><a href="../parts/993-eng-bracket-0001/"><img src="../parts/993-eng-bracket-0001/media/preview.png" alt="Console centrale moteur Turbo bio…" width="130"><br><sub>Console centrale moteur Turbo bio…</sub></a></td>
</tr>
<tr>
<td align="center" width="16%"><a href="../parts/993-eng-carrier-0001/"><img src="../parts/993-eng-carrier-0001/media/preview.png" alt="Turbo engine carrier (Motortraege…" width="130"><br><sub>Turbo engine carrier (Motortraege…</sub></a></td>
<td align="center" width="16%"><a href="../parts/993-eng-chain-case-0001/"><img src="../parts/993-eng-chain-case-0001/media/preview.png" alt="993 timing chain case and its lids" width="130"><br><sub>993 timing chain case and its lids</sub></a></td>
<td align="center" width="16%"><a href="../parts/993-eng-chain-case-lid-ti-f0-0001/"><img src="../parts/993-eng-chain-case-lid-ti-f0-0001/media/preview.png" alt="Left chain case lid 964 105 107 01" width="130"><br><sub>Left chain case lid 964 105 107 01</sub></a></td>
<td align="center" width="16%"><a href="../parts/993-eng-connecting-rod-ti64-f0-0001/"><img src="../parts/993-eng-connecting-rod-ti64-f0-0001/media/preview.png" alt="🧩 993/993 Turbo connecting rod" width="130"><br><sub>🧩 993/993 Turbo connecting rod</sub></a></td>
<td align="center" width="16%"><a href="../parts/993-eng-cooling-impeller-alsi10mg-f0-0001/"><img src="../parts/993-eng-cooling-impeller-alsi10mg-f0-0001/media/preview.png" alt="993 engine cooling fan — archived…" width="130"><br><sub>993 engine cooling fan — archived…</sub></a></td>
<td align="center" width="16%"><a href="../parts/993-eng-cooling-impeller-we43-f1-0001/"><img src="../parts/993-eng-cooling-impeller-we43-f1-0001/media/preview.png" alt="Engine cooling fan impeller" width="130"><br><sub>Engine cooling fan impeller</sub></a></td>
</tr>
<tr>
<td align="center" width="16%"><a href="../parts/993-eng-cylinder-head-4v-f0-0001/"><img src="../parts/993-eng-cylinder-head-4v-f0-0001/media/preview.png" alt="M64 four-valve water-cooled cylin…" width="130"><br><sub>M64 four-valve water-cooled cylin…</sub></a></td>
<td align="center" width="16%"><a href="../parts/993-eng-exhaust-manifold-in625-f0-0001/"><img src="../parts/993-eng-exhaust-manifold-in625-f0-0001/media/preview.png" alt="993 Turbo three-into-one exhaust…" width="130"><br><sub>993 Turbo three-into-one exhaust…</sub></a></td>
<td align="center" width="16%"><a href="../parts/993-eng-exhaust-valve-f1-0001/"><img src="../parts/993-eng-exhaust-valve-f1-0001/media/preview.png" alt="993 exhaust valves - F1 proxies" width="130"><br><sub>993 exhaust valves - F1 proxies</sub></a></td>
<td align="center" width="16%"><a href="../parts/993-eng-fan-housing-alsi10mg-f0-0001/"><img src="../parts/993-eng-fan-housing-alsi10mg-f0-0001/media/preview.png" alt="Stationary engine fan housing" width="130"><br><sub>Stationary engine fan housing</sub></a></td>
<td align="center" width="16%"><a href="../parts/993-eng-fan-stator-alsi10mg-f1-0001/"><img src="../parts/993-eng-fan-stator-alsi10mg-f1-0001/media/preview.png" alt="Engine cooling fan guide-vane rin…" width="130"><br><sub>Engine cooling fan guide-vane rin…</sub></a></td>
<td align="center" width="16%"><a href="../parts/993-eng-intake-valve-f1-0001/"><img src="../parts/993-eng-intake-valve-f1-0001/media/preview.png" alt="993 intake valve - F1 proxy and t…" width="130"><br><sub>993 intake valve - F1 proxy and t…</sub></a></td>
</tr>
<tr>
<td align="center" width="16%"><a href="../parts/993-eng-intake-valve-ti64-hollow-f0-0001/"><img src="../parts/993-eng-intake-valve-ti64-hollow-f0-0001/media/preview.png" alt="993 hollow Ti64 intake valve" width="130"><br><sub>993 hollow Ti64 intake valve</sub></a></td>
<td align="center" width="16%"><a href="../parts/993-eng-intercooler-bracket-ti-f0-0001/"><img src="../parts/993-eng-intercooler-bracket-ti-f0-0001/media/preview.png" alt="993 Turbo/GT2 intercooler bracket" width="130"><br><sub>993 Turbo/GT2 intercooler bracket</sub></a></td>
<td align="center" width="16%"><a href="../parts/993-eng-intercooler-end-tank-alsi10mg-f0-0001/"><img src="../parts/993-eng-intercooler-end-tank-alsi10mg-f0-0001/media/preview.png" alt="993 Turbo intercooler end tank" width="130"><br><sub>993 Turbo intercooler end tank</sub></a></td>
<td align="center" width="16%"><a href="../parts/993-eng-k16-compressor-wheel-al2139-f1-0001/"><img src="../parts/993-eng-k16-compressor-wheel-al2139-f1-0001/media/preview.png" alt="🧩 K16 compressor wheel" width="130"><br><sub>🧩 K16 compressor wheel</sub></a></td>
<td align="center" width="16%"><a href="../parts/993-eng-k16-compressor-wheel-alsi10mg-f0-0001/"><img src="../parts/993-eng-k16-compressor-wheel-alsi10mg-f0-0001/media/preview.png" alt="993 K16 compressor wheel" width="130"><br><sub>993 K16 compressor wheel</sub></a></td>
<td align="center" width="16%"><a href="../parts/993-eng-k16-turbine-wheel-in718-f0-0001/"><img src="../parts/993-eng-k16-turbine-wheel-in718-f0-0001/media/preview.png" alt="🧩 K16 turbine wheel" width="130"><br><sub>🧩 K16 turbine wheel</sub></a></td>
</tr>
<tr>
<td align="center" width="16%"><a href="../parts/993-eng-mounting-0001/"><img src="../parts/993-eng-mounting-0001/media/preview.png" alt="Support moteur Turbo bionique — c…" width="130"><br><sub>Support moteur Turbo bionique — c…</sub></a></td>
<td align="center" width="16%"><a href="../parts/993-eng-oil-filter-console-alsi10mg-f0-0001/"><img src="../parts/993-eng-oil-filter-console-alsi10mg-f0-0001/media/preview.png" alt="Engine oil filter console with in…" width="130"><br><sub>Engine oil filter console with in…</sub></a></td>
<td align="center" width="16%"><a href="../parts/993-eng-piston-cp1-gallery-f0-0001/"><img src="../parts/993-eng-piston-cp1-gallery-f0-0001/media/preview.png" alt="M64/60 piston with cooling gallery" width="130"><br><sub>M64/60 piston with cooling gallery</sub></a></td>
<td align="center" width="16%"><a href="../parts/993-eng-three-runner-intake-alsi10mg-f0-0001/"><img src="../parts/993-eng-three-runner-intake-alsi10mg-f0-0001/media/preview.png" alt="993 three-runner intake manifold" width="130"><br><sub>993 three-runner intake manifold</sub></a></td>
<td align="center" width="16%"><a href="../parts/993-eng-turbo-heat-shield-in625-f0-0001/"><img src="../parts/993-eng-turbo-heat-shield-in625-f0-0001/media/preview.png" alt="993 left turbo heat shield cover" width="130"><br><sub>993 left turbo heat shield cover</sub></a></td>
<td align="center" width="16%"><a href="../parts/993-eng-turbo-oil-return-line-in625-f0-0001/"><img src="../parts/993-eng-turbo-oil-return-line-in625-f0-0001/media/preview.png" alt="Turbo oil return line" width="130"><br><sub>Turbo oil return line</sub></a></td>
</tr>
<tr>
<td align="center" width="16%"><a href="../parts/993-eng-upper-valve-cover-alsi10mg-f0-0001/"><img src="../parts/993-eng-upper-valve-cover-alsi10mg-f0-0001/media/preview.png" alt="Upper valve cover with COP towers" width="130"><br><sub>Upper valve cover with COP towers</sub></a></td>
<td align="center" width="16%"><a href="../parts/993-exh-cat-converter-pair-pet-0001/"><img src="../parts/993-exh-cat-converter-pair-pet-0001/media/preview.png" alt="993 Turbo catalytic converters (f…" width="130"><br><sub>993 Turbo catalytic converters (f…</sub></a></td>
<td align="center" width="16%"><a href="../parts/993-exh-heat-exchanger-pair-pet-0001/"><img src="../parts/993-exh-heat-exchanger-pair-pet-0001/media/preview.png" alt="993 Turbo exhaust heat exchangers…" width="130"><br><sub>993 Turbo exhaust heat exchangers…</sub></a></td>
<td align="center" width="16%"><a href="../parts/993-exh-oval-tip-in625-f0-0001/"><img src="../parts/993-exh-oval-tip-in625-f0-0001/media/preview.png" alt="993 oval exhaust tip" width="130"><br><sub>993 oval exhaust tip</sub></a></td>
<td align="center" width="16%"><a href="../parts/993-exh-oval-tip-ti-f1-0001/"><img src="../parts/993-exh-oval-tip-ti-f1-0001/media/preview.png" alt="Oval exhaust tip" width="130"><br><sub>Oval exhaust tip</sub></a></td>
<td align="center" width="16%"><a href="../parts/993-int-dashboard-trim-0001/"><img src="../parts/993-int-dashboard-trim-0001/media/preview.png" alt="Dashboard trim" width="130"><br><sub>Dashboard trim</sub></a></td>
</tr>
<tr>
<td align="center" width="16%"><a href="../parts/993-int-door-opener-lever-f0-0001/"><img src="../parts/993-int-door-opener-lever-f0-0001/media/preview.png" alt="993 interior door opener lever" width="130"><br><sub>993 interior door opener lever</sub></a></td>
<td align="center" width="16%"><a href="../parts/993-int-door-pull-0001/"><img src="../parts/993-int-door-pull-0001/media/preview.png" alt="Interior door pull handle" width="130"><br><sub>Interior door pull handle</sub></a></td>
<td align="center" width="16%"><a href="../parts/993-int-seat-rail-cover-0001/"><img src="../parts/993-int-seat-rail-cover-0001/media/preview.png" alt="Seat rail cover" width="130"><br><sub>Seat rail cover</sub></a></td>
<td align="center" width="16%"><a href="../parts/993-int-switch-blank-0001/"><img src="../parts/993-int-switch-blank-0001/media/preview.png" alt="Switch blank" width="130"><br><sub>Switch blank</sub></a></td>
<td align="center" width="16%"><a href="../parts/993-int-switch-trim-ring-f1-0001/"><img src="../parts/993-int-switch-trim-ring-f1-0001/media/preview.png" alt="🖨️ Aluminum switch trim ring" width="130"><br><sub>🖨️ Aluminum switch trim ring</sub></a></td>
<td align="center" width="16%"><a href="../parts/993-turbocharger-k16-pair-0001/"><img src="../parts/993-turbocharger-k16-pair-0001/media/preview.png" alt="Pair of K16 turbochargers of the…" width="130"><br><sub>Pair of K16 turbochargers of the…</sub></a></td>
</tr>
<tr>
<td align="center" width="16%"><a href="../parts/993-whl-center-cap-alsi10mg-f0-0001/"><img src="../parts/993-whl-center-cap-alsi10mg-f0-0001/media/preview.png" alt="993 center cap" width="130"><br><sub>993 center cap</sub></a></td>
</tr>
</table>

*Concept models: 41 of 43 are PicoGK voxel models ([`parts/picogk-catalog/`](../parts/picogk-catalog/README.md)), the others concept CAD blocks. **None of these is the original part, and none is validated**: 43 of 43 records are at `concept`, and 0 of 43 have measured geometry. 🖨️ Printable as designed, fit unchecked: Aluminum switch trim ring. 🧩 Printable as an engraved display mock-up, never for use: 993/993 Turbo connecting rod, K16 compressor wheel, K16 turbine wheel. Click a part to see it next to the original.*

```mermaid
pie showData title 43 part records by safety class
    "prohibited pending engineering" : 25
    "safety-critical" : 1
    "functional" : 12
    "non-critical" : 5
```

```mermaid
flowchart LR
    L0["concept<br/><b>43</b> records"]
    L1["dimensionally_reviewed<br/><b>0</b> records"]
    L2["prototype_fitted<br/><b>0</b> records"]
    L3["functionally_tested<br/><b>0</b> records"]
    L4["engineering_reviewed<br/><b>0</b> records"]
    L5["released<br/><b>0</b> records"]
    L0 --> L1 --> L2 --> L3 --> L4 --> L5
    classDef here fill:#fff4d6,stroke:#b7791f,color:#1a1a1a;
    classDef empty fill:#f4f4f4,stroke:#9e9e9e,color:#6b6b6b;
    class L0 here
    class L1 empty
    class L2 empty
    class L3 empty
    class L4 empty
    class L5 empty
```

*The validation ladder of `catalog/schemas/part.schema.json`, with the number of records whose `validation.status` names each step. Both charts are computed from the records.*

**Engine, intake and cooling**

| part | candidate material | process | status |
|---|---|---|---|
| [Console centrale moteur Turbo bionique — étud…](pieces/993-eng-bracket-0001.md) | undetermined | undecided | **prohibited pending engineering** |
| [Turbo engine carrier (Motortraeger)](pieces/993-eng-carrier-0001.md) | unknown | undecided | **safety-critical** |
| [993 timing chain case and its lids](pieces/993-eng-chain-case-0001.md) | unidentified | undecided | **prohibited pending engineering** |
| [Left chain case lid 964 105 107 01](pieces/993-eng-chain-case-lid-ti-f0-0001.md) | Ti-6Al-4V Grade 5, plate — deliberate c… | CNC | functional |
| [993/993 Turbo connecting rod](pieces/993-eng-connecting-rod-ti64-f0-0001.md) | Ti-6Al-4V Grade 5 LPBF for screening | LPBF | **prohibited pending engineering** |
| [993 engine cooling fan — archived Carrera F0…](pieces/993-eng-cooling-impeller-alsi10mg-f0-0001.md) | EOS Aluminium AlSi10Mg T6 for comparison | undecided | **prohibited pending engineering** |
| [Engine cooling fan impeller](pieces/993-eng-cooling-impeller-we43-f1-0001.md) | WE43 LPBF, solutionized and aged, for c… | LPBF | **prohibited pending engineering** |
| [M64 four-valve water-cooled cylinder head — c…](pieces/993-eng-cylinder-head-4v-f0-0001.md) | not selected | undecided | **prohibited pending engineering** |
| [993 Turbo three-into-one exhaust manifold](pieces/993-eng-exhaust-manifold-in625-f0-0001.md) | EOS NickelAlloy IN625 / UNS N06625 for… | undecided | **prohibited pending engineering** |
| [993 exhaust valves - F1 proxies](pieces/993-eng-exhaust-valve-f1-0001.md) | INCONEL 751 / UNS N07751 candidate | CNC | **prohibited pending engineering** |
| [Stationary engine fan housing](pieces/993-eng-fan-housing-alsi10mg-f0-0001.md) | EOS Aluminium AlSi10Mg T6 for comparison | undecided | **prohibited pending engineering** |
| [Engine cooling fan guide-vane ring (stator)](pieces/993-eng-fan-stator-alsi10mg-f1-0001.md) | EOS Aluminium AlSi10Mg T6 for comparison | LPBF | **prohibited pending engineering** |
| [993 intake valve - F1 proxy and titanium vari…](pieces/993-eng-intake-valve-f1-0001.md) | Ti-6Al-4V Grade 5 | DMLS | **prohibited pending engineering** |
| [993 hollow Ti64 intake valve](pieces/993-eng-intake-valve-ti64-hollow-f0-0001.md) | Ti-6Al-4V Grade 5 LPBF, screening | LPBF | **prohibited pending engineering** |
| [993 Turbo/GT2 intercooler bracket](pieces/993-eng-intercooler-bracket-ti-f0-0001.md) | Ti-6Al-4V Grade 5 for screening | CNC | functional |
| [993 Turbo intercooler end tank](pieces/993-eng-intercooler-end-tank-alsi10mg-f0-0001.md) | EOS Aluminium AlSi10Mg for screening | LPBF | **prohibited pending engineering** |
| [K16 compressor wheel](pieces/993-eng-k16-compressor-wheel-al2139-f1-0001.md) | EOS Aluminium Al2139 AM, M290 60 µm, he… | LPBF | **prohibited pending engineering** |
| [993 K16 compressor wheel](pieces/993-eng-k16-compressor-wheel-alsi10mg-f0-0001.md) | EOS AlSi10Mg, screening | LPBF | **prohibited pending engineering** |
| [K16 turbine wheel](pieces/993-eng-k16-turbine-wheel-in718-f0-0001.md) | EOS NickelAlloy IN718 API, M290 40 µm… | undecided | **prohibited pending engineering** |
| [Support moteur Turbo bionique — cage et envel…](pieces/993-eng-mounting-0001.md) | undetermined | undecided | **prohibited pending engineering** |
| [Engine oil filter console with integrated gal…](pieces/993-eng-oil-filter-console-alsi10mg-f0-0001.md) | EOS Aluminium AlSi10Mg T6 for comparison | undecided | **prohibited pending engineering** |
| [M64/60 piston with cooling gallery](pieces/993-eng-piston-cp1-gallery-f0-0001.md) | Constellium Aheadd CP1, Velo3D Sapphire… | LPBF | **prohibited pending engineering** |
| [993 three-runner intake manifold](pieces/993-eng-three-runner-intake-alsi10mg-f0-0001.md) | generic AlSi10Mg for screening | undecided | functional |
| [993 left turbo heat shield cover](pieces/993-eng-turbo-heat-shield-in625-f0-0001.md) | EOS NickelAlloy IN625 / UNS N06625, scr… | undecided | functional |
| [Turbo oil return line](pieces/993-eng-turbo-oil-return-line-in625-f0-0001.md) | EOS NickelAlloy IN625 / UNS N06625 for… | undecided | **prohibited pending engineering** |
| [Upper valve cover with COP towers](pieces/993-eng-upper-valve-cover-alsi10mg-f0-0001.md) | EOS Aluminium AlSi10Mg T6, for comparis… | undecided | **prohibited pending engineering** |

**Charge air**

| part | candidate material | process | status |
|---|---|---|---|
| [993 Turbo charge-air tract transcribed parts…](pieces/993-ca-charge-pipe-set-pet-0001.md) | unknown per line item (hoses are rubber… | undecided | non-critical |
| [993 Turbo turbocharging intake tract (group 1…](pieces/993-ca-turbo-intake-manifold-pet-0001.md) | unknown | undecided | non-critical |

**Turbocharger**

| part | candidate material | process | status |
|---|---|---|---|
| [Pair of K16 turbochargers of the 993 Turbo](pieces/993-turbocharger-k16-pair-0001.md) | undetermined | undecided | **prohibited pending engineering** |

**Exhaust**

| part | candidate material | process | status |
|---|---|---|---|
| [993 Turbo catalytic converters (front muffler…](pieces/993-exh-cat-converter-pair-pet-0001.md) | unknown | undecided | **prohibited pending engineering** |
| [993 Turbo exhaust heat exchangers (manifolds)](pieces/993-exh-heat-exchanger-pair-pet-0001.md) | unknown (an IN625 aftermarket offer exi… | undecided | **prohibited pending engineering** |
| [993 oval exhaust tip](pieces/993-exh-oval-tip-in625-f0-0001.md) | EOS NickelAlloy IN625 / UNS N06625 for… | undecided | functional |
| [Oval exhaust tip](pieces/993-exh-oval-tip-ti-f1-0001.md) | Ti-6Al-4V if the actual temperature all… | LPBF | functional |

**Body**

| part | candidate material | process | status |
|---|---|---|---|
| [993 front impact support](pieces/993-body-front-impact-support-alsi10mg-f0-0001.md) | generic screening AlSi10Mg | undecided | **prohibited pending engineering** |
| [Front lid](pieces/993-body-front-lid-0001.md) | fiber and resin to be determined | undecided | functional |

**Interior**

| part | candidate material | process | status |
|---|---|---|---|
| [Dashboard trim](pieces/993-int-dashboard-trim-0001.md) | fiber and resin to be determined | undecided | functional |
| [993 interior door opener lever](pieces/993-int-door-opener-lever-f0-0001.md) | AlSi10Mg, screening | LPBF | functional |
| [Interior door pull handle](pieces/993-int-door-pull-0001.md) | to_be_determined_after_load_test | undecided | functional |
| [Seat rail cover](pieces/993-int-seat-rail-cover-0001.md) | to_be_determined_after_fit_test | FFF | non-critical |
| [Switch blank](pieces/993-int-switch-blank-0001.md) | to_be_determined_after_fit_test | FFF | non-critical |
| [Aluminum switch trim ring](pieces/993-int-switch-trim-ring-f1-0001.md) | EN AW-6063 T6 retained for bright anodi… | CNC | non-critical |

**Lighting**

| part | candidate material | process | status |
|---|---|---|---|
| [Headlamp spring hook repair](pieces/993-elec-headlamp-spring-hook-f0-0001.md) | EOS Aluminium AlSi10Mg / AlSi10Mg_FlexM… | LPBF | functional |

**Wheels**

| part | candidate material | process | status |
|---|---|---|---|
| [993 center cap](pieces/993-whl-center-cap-alsi10mg-f0-0001.md) | AlSi10Mg for screening | undecided | functional |

*43 records, 25 of them prohibited pending engineering, none released. Each link opens the part's description page in [`docs/pieces/`](pieces/), generated from its `catalog/parts/*.json` record; the design dossiers are in [`docs/993/`](993/). Table generated by `scripts/render_parts_table.py`, checked by `make check`.*

<!-- parts:end -->

## 3. Engine cooling

Two programmes, kept separate
([docs/FAN_DEVELOPMENT_PROGRAMMES.md](FAN_DEVELOPMENT_PROGRAMMES.md)):
the **upright 993 fan** behind the engine, and the **935-type horizontal fan**
lying on top of it.

| programme | where it stands | start here |
|---|---|---|
| 993 upright fan, F1 impeller | redesigned from the visual rebuild of the original Turbo rotor: same cup, windows and envelope, airfoil blades, WE43. On a duty inferred from the rebuild: +2 % air at equal power, +9 % with a matched stator. Geometric screening completed; metal process physics and supports remain unqualified. | [impeller dossier](993/993_COOLING_IMPELLER_WE43_F1.md) · [stator](993/993_FAN_STATOR_ALSI10MG_F1.md) |
| 993 fan system and CFD | reference rebuild, organic blade studies, mesh recovery and CFD campaigns, OpenUSD twin; no installed-airflow result yet | [system twin](../twins/993-engine-cooling-fan-system-f0/README.md) · [latest results and open gates](../twins/993-engine-cooling-fan-system-f0/program/ENGINEERING_RESULTS_20261003.md) |
| 935 horizontal fan | multilingual source research, CAD reconstruction, assembly S1, D2/D3 CFD diagnostics | [935 system](../twins/935-horizontal-cooling-system/README.md) · [reconstruction](../models/horizontal-fan-reconstruction/README.en.md) · [S1 assembly and manufacturing](../models/horizontal-fan-reconstruction/ASSEMBLY_MANUFACTURING_S1.en.md) |
| fan alloys | aluminium, WE43 and Ti64 compared on the same rotor: mass, inertia, centrifugal stress | [alloy comparison](../twins/fan-alloy-comparison-f0/README.en.md) |

No fan gain is claimed over the Porsche part: its performance is not
published, and every comparison here is against a rebuild or a synthetic
reference.

## 4. Engine and turbo research

- **M64/60 (993 Turbo)**: whole-engine bill of materials
  ([`m64-bom-v1.json`](../twins/m64-engine-system/bom/m64-bom-v1.json),
  [coverage](../twins/m64-engine-system/bom/coverage.md)) and a dated series of
  cylinder-head, valvetrain and meshing reports in
  [docs/reports/](reports/README.md).
- **Four-valve cylinder head**: [air + oil study](studies/993-air-oil-20261002/README.md).
- **K16 and hybrid turbos**: [2 October research](research/993-turbo-20261002/README.md),
  [Mezger variants and materials](research/mezger-turbo-materials-20261003/README.md),
  [German-source supplement](research/mezger-german-sources-20261003/README.md).
- **Local compute**: [architecture](architecture/README.md) and
  [local Qwen training](../training/m64-qwen/README.md). The
  [PicoGK library adaptation](../training/qwen-picogk-20261012/README.md) and
  [native proposal validation](../training/qwen-picogk-native-gate/README.md)
  add bounded training and independently checked STL/VDB exports.

## 5. Body and interior

**Bolt-on** panels (fenders, lids, spoiler, doors) are a legitimate target;
the load-bearing structure is not. The factory catalogue draws the line in part
numbers: [docs/research/993-964-panneaux-carbone.md](research/993-964-panneaux-carbone.md).

Those panels can already be ordered from several tuners, so the part chosen is
the one nobody sells: the **dashboard trim**, `993-INT-DASHBOARD-TRIM-0001`,
restricted to vehicles **without a passenger airbag**. On the others it
carries the deployment flap, which makes it an occupant-restraint part. Its
[measurement plan](../parts/993-int-dashboard-trim-0001/evidence/measurement-plan.md)
opens with an entry gate that can stop the project.

## 6. The catalogue and its data contract

**545 source records** qualified by provenance, rights and level of evidence;
43 part records, 10 twin records, 5 components, 3 assemblies, 3 workshop-manual
transcriptions and 2 records of declared community values. Everything is validated by a JSON schema and by the test suite.

A record keeps technical access, reading method and reuse rights separate. An
accessible page is not redistributable; a page read in a browser is neither an
authorized download nor a validation of accuracy.

```mermaid
flowchart TB
    subgraph catalog["catalog/ — source of truth, JSON-schema validated"]
      direction LR
      src["sources/<br/>545 records"] --- prt["parts/<br/>43 records"]
      prt --- tw["twins/<br/>10 records"]
      prt --- cmp["components/ · assemblies/"]
      prt --- mea["measurements/<br/>5 documentary records"]
    end
    prt -- "render_part_pages.py" --> pages["docs/pieces/<br/>one page per part"]
    prt -- "render_parts_table.py" --> table["parts table on this page"]
    prt -- "render_readme_gallery.py" --> gallery["README picture gallery"]
    tw --> twins["twins/&lt;zone&gt;/<br/>CAD · analysis · evidence"]
```

---

## The rules

| rule | what it requires |
|---|---|
| **Source before STL** | FreeCAD, OpenSCAD, build123d, PicoGK or STEP remain the master formats |
| **Evidence before publication** | every claim of fit or accuracy is tied to a measurement or a source |
| **Digital before prototype** | the active phase manufactures nothing |
| **Interface before appearance** | a measured zone that allows a clearance check beats a full scan of unknown accuracy |
| **Explicit safety** | when in doubt, the part is lowered to `prohibited_pending_engineering`; see [SAFETY.md](SAFETY.md) |
| **No vendor harvesting** | a site closed to robots is not queried; see [decision 0003](decisions/0003-no-vendor-harvesting.md) |
| **Accessible tools** | a free, open-source, local toolchain |

## What the repository withdrew from its own results

This is the most useful part of its history, and it is public.

![Stiffness by architecture in linear and quadratic shells](media/diagrams/964-echelle-architectures.svg)

| withdrawn claim | what defeated it |
|---|---|
| "the structure works in membrane shear" | a test decoupling `E` and `G`: the bare floor pan works in almost pure bending |
| "stiffness follows thickness exactly linearly" | the exponent is 1.00 with linear elements and **1.10** with quadratic ones: the exactness belonged to the element |
| "the windshield frame has the best return per kilogram" | in quadratic shells, it is the center tunnel |
| a cross member counted in the model's mass | a connectivity check: it was attached to nothing |
| eleven lost analysis cases, read as a near-singular system | a defect in the solver's partitioner, whose message went to `stderr` |
| the datum network's front cross-member mount P5 | plate 50-02 draws dimension P as longitudinal, not as a diagonal: P5 was 230 mm out, and the monocoque's governing span with it |
| the 964 monocoque's stiffness "converging from above" (35,500 N·m/deg in CFRP, two meshes within 2%) | the Scordelis-Lo roof: CalculiX's S3 triangle finds 7 to 21% of the reference deflection. In S6 the same model gives 19,900 and still rises with the mesh |
| a first F1 cooling impeller, generic and shrouded | next to a photo of the original it shared nothing, and it left no room for the alternator end the original cup wraps |
| +20 % fan airflow from that impeller | radial equilibrium, once modelled, put its hub section at de Haller 0.58 with a stalled station |

The figures on this page are regenerated from data kept in the repository:
`twins/964-chassis/fea/figures.py` for the charts and model views,
`twins/964-chassis/fea/hero.py` for the banner, from the torsion snapshot of
the monocoque shell kept in `twins/964-chassis/monocoque/derived/`. None of them is a rendering: they are the
calculation's data.

## What the project does not claim

- **No absolute stiffness value is a 964 stiffness.** The model's sections are
  `ASSUMED` and the mesh is not converged; only ratios and rankings are usable.
- **No part is validated.** The printable files above have not been checked on
  a car. All 43 records are at status `concept`, 25 of them
  `prohibited_pending_engineering`. No twin reaches the `F2_interface` level.
- **No physical measurement is recorded yet.** The five records in
  `catalog/measurements/` are documentary: three transcriptions from the
  workshop manuals and two of values declared in forum posts, not instrumented
  measurements.
- **No fan gain over the Porsche part.** Its performance is not published.
- **A rendering or a simulation is not evidence of physical behavior**:
  neither Omniverse, nor an image, nor a print simulation.

## What is archived

The **917 cylinder head** dossier, 891 files from iteration F1 to F50, is
retired as a product and kept as a numerical regression, along with the 935
cylinder-head scan. It was not moved into an archive folder:
[ARCHIVE.md](ARCHIVE.md) explains that it carries 2,014 SHA-256 digests that
moving it would invalidate. Evidence beats tidiness.

---

## Quick start

Requirements: Python 3.11 or newer and `make`. Clone onto a native Linux file
system (on WSL, not under `/mnt/c`; see [AGENTS.md](../AGENTS.md)).

```bash
git clone https://github.com/cluster2600/porscheparts.git
cd porscheparts
make help                 # active targets, grouped by theme
make check                # schemas, tests, generators and digests
```

To add a part:

```bash
cp catalog/templates/part-record.json catalog/parts/993-xxx-0001.json
# fill in the record, add licensed CAD files under parts/<part_id>/
make part-pages parts-table readme-gallery   # regenerate its page, this table and the README gallery
make check
```

Conventions in detail: [CONTRIBUTING.md](CONTRIBUTING.md). The `917-*` targets
drive the archived line and are listed by `make help-917`. Tests that need
`numpy`, `matplotlib` or CAD kernels are skipped or fail without them; the
compute images in [`containers/`](../containers/) carry the full stack, and the
CAD, print-simulation and rendering scripts run in the `cadsim` image.

## Repository layout

```text
catalog/            records: sources, parts, measurements, twins, components
  schemas/            the catalogue's data contract
  templates/          record, measurement and manufacturing-request templates
parts/              geometry, evidence, media and print files per part
components/         component geometry; assemblies/ holds their evidence
twins/              digital twins, one folder per zone; see twins/README.md
  964-chassis/        964 chassis: datum chain, CAD, FEA, corpus
  993-*/              993 functional zones
  m64-*/              M64 engine and cylinder-head twins
models/             reconstructions, e.g. the horizontal fan
docs/               plans, quality criteria, software chain; see docs/README.md
  993/                the 34 design dossiers of the 993 parts
  pieces/             one generated page per part record
  decisions/          numbered architecture decisions
  reports/            dated execution and audit reports, indexed by day
  research/           source research by topic
  media/              diagrams, banner and video projects
  GALLERY.md          every figure and render on one page
simulation/         CFD and forced-induction analysis cases
archive/917/docs/   the written dossiers of the 917 cylinder head
scripts/  tests/    automatic checks, generators and guardrails
containers/ deploy/ reproducible compute images and deployment
```

## Status

| phase | state |
|---|---|
| 0 — foundation | ✅ done |
| 1 — source inventory | 🟡 past its quantitative threshold; cross-qualification and direct measurements still open |
| 2 — physical inventory and twin assembly | 🟡 run in digital mode; physical prototypes suspended, except non-critical printable files (decisions 0009, 0010, 0011) |
| 3 — titanium engineering twin, no manufacturing | ⬜ open: candidate `993-ENG-CARRIER-0001` under study |
| 4 — public catalog | ⬜ open: only parts that clear their quality gates will be published |

Details and exit criteria: [ROADMAP.md](ROADMAP.md) ·
[docs/PROJECT_CHARTER.md](PROJECT_CHARTER.md) ·
[docs/DIGITAL_TWIN.md](DIGITAL_TWIN.md) ·
[docs/QUALITY_GATES.md](QUALITY_GATES.md).

![Sourced state of the 993 digital twin](media/diagrams/digital-twin-993-etat.svg)

*Sourced logical relationships of the 993 twin, not the actual position of
the components in the car.*

---

## Disclaimer

This repository provides research and manufacturing data without warranty.
Printing, fitting and road use remain the responsibility of whoever makes and
installs the part. Read [SAFETY.md](SAFETY.md) before any manufacturing.

Porsche and 911 are trademarks of their respective owners. This project is
independent and not affiliated with Porsche AG.

## License

**© 2026 Maxime Grenu. All rights reserved.** The repository is under a custom
[proprietary license](../LICENSE): you may view it, but copying, modifying,
printing or manufacturing parts, redistributing, commercial use and AI training
all need prior written permission; ask by opening an issue. Third-party
sources and models keep their own license; see [LICENSES.md](LICENSES.md).
Revisions published before 2026-09-25 were under the MIT License.
