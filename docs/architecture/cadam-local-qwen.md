# Local CADAM/Qwen proposal and calibration branch

Status: installed and software-tested on the Mac, 2026-11-04. Requirement:
owner-requested local AI generation with no scan or external-service transfer.
Decision: [ADR 0015](../decisions/0015-local-cadam-qwen-proposals.md).
Evidence: [aggregate receipt](../research/cadam-qwen-local-20261104.json).

## Position in the engineering chain

| Element | Role and authority |
|---|---|
| A-AI | Existing local Qwen/MLX proposes code from explicit requirements |
| A-CADAM | Local proposal UI, upstream OpenSCAD WASM preview and export |
| A-CHECK | Independent contract and STL measurement; model output cannot define expected dimensions |
| A-CAD | PicoGK remains the new engine geometry route; existing STEP/FreeCAD masters retain dimensional authority |
| A-CAE | Gmsh, OpenFOAM, CalculiX and Adamantine retain their own admission, convergence and calibration requirements |

```mermaid
sequenceDiagram
    participant U as Owner / dimensional contract
    participant C as CADAM local entry
    participant Q as Qwen MLX on loopback
    participant W as CADAM OpenSCAD WASM
    participant I as Independent STL verifier
    U->>C: Explicit synthetic specification
    C->>Q: Prompt only, fixed local endpoint
    Q-->>C: Proposed OpenSCAD and raw response
    C->>W: Exact returned source
    W-->>C: Preview and STL export
    C->>I: Exported STL and separately fixed contract
    I-->>C: Measurements, hashes, pass or reject
    alt Invalid source or failed measurements
        C->>C: Preserve rejection; revise specification in a new trial
    else Checks pass
        C-->>U: Digitally checked coupon, editable source and report
    end
```

CADAM/OpenSCAD output has no implemented automatic bridge to PicoGK, STEP,
Gmsh or a machine build file. Any future bridge needs its own units, topology,
interface and round-trip checks. The reference coupon shown on initial page load
is hand-authored; only Generate with Qwen creates an AI candidate.

## Installed runtime and commands

CADAM checkout: `~/Developer/CADAM`, upstream commit
`e339e3ad85601bb1e23a5ff9c7f33b51ddf602f5` (GPL-3.0).
The local entry lives in ignored `local-calibration/`; upstream tracked files
are unchanged. Its frozen source/configuration snapshot is in the private bundle.
Model: existing `lmstudio-community/Qwen3.6-35B-A3B-MLX-4bit`, no adapter,
non-thinking generation, temperature zero. Model upstream revision is unknown;
all 15 local model/config/tokenizer files are pinned by the private receipt.
MLX 0.32.3, MLX-LM 0.31.3, Transformers 5.17.0; Python 3.12; Node 26.12.1.

```sh
"$HOME/Developer/CADAM/local-calibration/start.command"
```

Open `http://127.0.0.1:4319/cadam/local-calibration/index.html`. Select
**Generate with Qwen**, then **Verify dimensions**, then export the accepted
candidate's STL/SCAD and report. STL coordinates are millimetres.

The launcher reuses only a matching dedicated local model on port 4320. Before
starting it, it checks model hashes; an occupied unexpected port stops startup.
The local CADAM server uses port 4319. Both bind to 127.0.0.1. Closing CADAM does
not terminate the separate model process. These are development services, not a
hardened multi-user deployment. Do not replace other services on these ports.

Backend routes under `/cadam/local-calibration/api/qwen/` are GET `status`,
POST `generate` (JSON with only `prompt`) and POST `verify` (binary STL).
The browser never chooses an endpoint or model. Host/origin checks, body limits,
model identity and the pinned independent contract are enforced. Failure has no
cloud fallback. Existing authenticated LM Studio services are untouched.

```sh
cd "$HOME/Developer/CADAM"
node --experimental-strip-types --test local-calibration/qwen/backend.test.ts
./node_modules/.bin/tsc -p local-calibration/tsconfig.json --noEmit
node local-calibration/qwen/test-ui.cjs
```

Replay writes new timestamped trials; do not run writers in a frozen bundle.
The retained browser runner uses the installed bundled Playwright runtime.

## Executed checks and provenance

The fixed coupon is 60 × 40 × 15 mm with a 4 mm base, three through-bores
(4/6/8 mm) and five fins (0.8/1/1.5/2/3 mm). Coordinates and tolerances belong
to its synthetic contract, not to Porsche specimen metrology.

Two consecutive complete UI generations passed all 70 independent checks with
identical source/STL hashes. Each test compiled the exact returned code and
confirmed that UI export matched the verified STL. No source was manually
corrected. Prompt refinement included a generic OpenSCAD grammar example.
Eight backend tests and nine API/negative controls passed, including deliberate
bore and scale errors. Local TypeScript checking passed. Initial invalid
outputs, invalid CSG syntax and an exhausted reasoning budget remain rejected.
Two successes establish only this tested case, not general text-to-CAD quality.

The browser recorded zero external attempts and no page errors. Both dedicated
servers use `sandbox-exec` with non-loopback outbound connections denied, plus
offline Hugging Face flags. A same-origin CSP limits browser requests. A TEST-NET
socket probe was denied by the OS before application data transmission.
No scan was input. Test URL logging removes query strings; an initially logged
ephemeral development token was rotated by restarting the dedicated server.

Private bundle:
`~/Developer/PorschePartsArtifacts/cadam-qwen-calibration-20261104/`.
It retains the manifest, model hashes, prompts/raw responses, failed trials,
editable SCAD, exported STL, independent contract, dimensional reports, actual
UI capture and orthographic views. Public documentation retains aggregate
results and hashes only. There is no scan, secret or raw mesh in this increment.

## Resumed 935 work and remaining gates

Resume from the [executed hypothesis study](../research/935-hypothesis-study-20261029.md),
not from the older unexecuted plan. Its independent closed-envelope, supported
3MF, CLI readback and exploratory numerical results remain valid for their
recorded assumptions. CADAM does not retroactively qualify or replace them.

| Next activity | Concrete input / output | Current admission |
|---|---|---|
| Reuse software branch | Frozen coupon contract, model/source receipt → new hashed SCAD/STL and checks | Accepted for this synthetic software case |
| Propose a head feature | Accepted scan mask, interface contract, source-derived dimensions → separate editable proposal and bidirectional deviations | Requires exact observed feature selection and independent inspection; no hidden gallery inference |
| Admit geometry to Gmsh/physics | Complete named domain, interfaces and surface audit → independently accepted mesh | Full bare-head geometry and attached-hardware separation unresolved |
| Revisit CFD/CHT/strength | Existing native study decks plus sourced/declared loads and properties → new convergence/balance reports | Prior exploratory cases retained; calibrated head result still lacks specimen/process data |
| Prepare metal build | Alloy, machine, powder, exposure, supports, calibration and inspection → machine-specific job | Manufacturer/process qualification missing; neutral contours are not a qualified job |

Continue independent ready work using local Mac/Kali resources. Preserve failed
PicoGK/Boolean candidates. CADAM cannot supply its own geometry approval or
close material, manufacturing or engine gates. For 962 work, the mandatory
19-phase workflow remains unchanged; this optional 935 coupon branch does not
advance any 962 phase or waive its input requirements. No compute was rented,
message sent or fabrication ordered for this integration.

Executed continuation: the [observed-wall CAD review](../research/935-observed-wall-cad-20261104/README.md)
uses registered acquired-face masks and unchanged baseline primitive parameters.
It produces private STEP/FreeCAD references with independent source-membership,
export and distance checks. CADAM/Qwen did not author or approve those faces;
the coupon branch and scan-derived reconstruction retain separate evidence.

The later [exact source-facet charts](../research/935-source-shells-20261104/README.md)
also preserve original triangle/edge adjacency after actual STEP reload and
native FreeCAD save/reopen. Vertex-only contacts in the selected masks are
explicitly separated with source-ID provenance. These remain open reference
surfaces; [native Kali verification](../research/935-kali-validation-20261104/README.md)
checks the repository software independently and does not grant head release.

The [current completion review](../research/935-readiness-20261104/README.md)
indexes the intact private deliverables, distinguishes the twelve incomplete
input packages from completed digital work, and retains the manufacturer-data
requests as unsent drafts. It also corrects the current original-scan location
without modifying historical evidence.

The [acquired axial-sheet increment](../research/935-observed-axial-sheet-20261104/README.md)
adds 13,895 exact acquired facets to the private native reference document.
It rejects a single-plane approximation and independently checks both the STEP
and the actual feature exported from the saved/reopened FreeCAD file. No hidden
geometry, physical tolerance, complete head or manufacturing job is inferred.

The [fourth-passage source audit](../research/935-fourth-passage-audit-20261104/README.md)
continues from fixed historical acquired-face selections. It preserves one
closed and three open section components, independently verifies their original
source edges and identifies all six open endpoints as original scan boundaries.
The circle diagnostic remains rejected; no fourth cylinder or stud pattern is
completed by symmetry.

The [fourth-region native CAD continuation](../research/935-fourth-region-cad-20261104/README.md)
then preserves 2,790 acquired facets around those fixed profiles as an exact
open reference. Independent STEP and actual saved-FreeCAD-feature checks pass;
140 acquired boundary edges and 144 selection cuts remain explicit. The five
combined reference objects contain 21,472 unique acquired faces, with zero
solids and no accepted complete-head domain.

The [chamber-mask surface admission study](../research/935-chamber-surface-admission-20261104/README.md)
then tests plane and quadratic graphs on all eight fixed historical masks.
All sixteen proposals fail the existing 0.01 mm digital screen at actual source
vertices. Independent training/score checks and complete-triangle Bernstein
bounds preserve these rejections; no smooth native surface or valve axis is
adopted from the fragmented masks.

The [source-connectivity follow-up](../research/935-chamber-connected-20261104/README.md)
selects the largest acquired-area component of each chamber mask before fitting,
with complete parent membership retained. Independent ranking and complete-face
checks pass; all sixteen proposals still fail the unchanged digital screen.
Neither the smaller fitting domain nor its lower residuals establish a valve
surface, hidden geometry or physical dimensional acceptance.

The [native Kali acquired-input receipt](../research/935-kali-acquired-inputs-20261104/README.md)
provides a new private input root and checksum-bound effective contract, avoiding
the absent historical catalogue path. Every original OBJ vertex and triangle is
checked directly against the exact arrays on ext4. Owner-confirmed millimetres
and the provider's cast/machined correction are explicit; historical records stay
unchanged. OCP is absent in the inspected Kali interpreter, so this source-reader
qualification does not claim that the complete CAD/solver chain is ready.

The [isolated native Kali CAD runtime](../research/935-kali-cad-runtime-20261104/README.md)
closes that OCP gap in a new venv with offline, hash-required wheel installation.
It constructs the registered acquired patch and passes actual STEP/source,
native fixture and cross-host Mac reinspection checks. The earlier scientific
interpreter remains unchanged; this runtime qualification adds no new source
coverage and does not admit a complete head or manufacturing job.

The [public process-reference and machine-envelope review](../research/935-public-process-data-20261104/README.md)
keeps three literature recipes separate and records the remaining manufacturer
input packages. An independently checked acquired-point distance excludes any
single rigid placement of the current unseparated scan in the optimistic FS121M
box. Larger nominal boxes remain candidates, without a printer/material choice
or manufacturing acceptance. No scan was transferred to an external service.

The [chamber projection and trim-domain audit](../research/935-chamber-chart-audit-20261104/README.md)
then independently classifies all 79,610 fixed-chart candidate pairs with exact
rational predicates. No projected positive-area overlap is found, but 296
original boundary vertices branch. A source-preserving contact/trim atlas is
required before more flexible fitting; neither the rejected smooth models nor
the existing exact native references are changed by this audit.

The [source-preserving chamber disk atlas](../research/935-chamber-disk-atlas-20261104/README.md)
then retains all 14,023 selected faces in 405 independently verified disk domains.
A new private native BREP/FreeCAD reference preserves source point/edge sharing
after actual saved-feature reinspection. The STEP shared-topology round-trip is
explicitly rejected and retained; it is not repaired by coordinate welding.
Across separate source-reference documents, 35,495 distinct acquired faces are
represented. These remain open observation references, without a complete head,
accepted smooth surface, qualified physics domain or manufacturing job.

The [fixed disk-domain primitive trial](../research/935-chamber-disk-fit-20261104/README.md)
then retains all 405 domains and fits only the nine meeting unchanged support
requirements. All eighteen plane/quadratic proposals fail the digital screen.
Independent full-triangle, boundary-curve, cut-seam and shared-vertex checks
preserve these rejections; 396 short-support domains retain exact references.
Point contacts without a cut at that vertex expose additional diagnostic gaps.
No smooth surface is adopted, and the exact native references remain unchanged.

The [whole-source separation audit](../research/935-source-separation-20261104/README.md)
then reparses every original OBJ face on Kali1 with independent Python and C++
implementations and reinspects the recovered partitions on the Mac. There are
four edge-connected components, but no named objects, groups or materials; all
eight fixed chamber masks belong to the largest component. Connectivity and
component size do not identify the bare head or attached hardware. The original
scan, native atlas/reference capsule and CADAM coupon capsule remain unchanged.
The full engineering goal remains active; this local increment accepts no new
head solid, physics domain or manufacturing job and rents no paid compute.

The [opaque component review](../research/935-component-visual-review-20261104/README.md)
localises the second component as a tubular surface fragment while threaded
protrusions remain connected to the main surfaces. All original triangles and
the independent partitions are retained. Removing small components cannot
supply an accepted bare-head domain; missing interfaces and hidden surfaces
remain separate acquisition requirements. The review images stay private.

The owner then explicitly resumed work with declared hypotheses. The
[local bare-head reconstruction](../research/935-bare-head-hypothesis-20261105/README.md)
now produces a digitally checked closed mesh, exact-coordinate head and
supported 3MF exports, and complete 50 micrometre neutral contours. Eleven
provisional protrusions are cut locally while all other parent triangles,
including fins, remain. A global cut that removed fins and an actual PicoGK
candidate with 29 shells are retained as rejected trials. The admitted local
construction uses exact CGAL post-processing of the frozen envelope; neither
CADAM/Qwen nor PicoGK is credited with authoring or approving that output.
Independent full geometry, all-layer readback/union and native Kali topology
checks pass. New-geometry physics, wall/support-removal and calibrated metal
process checks remain pending; no functional or manufacturing release follows.

The [revision-specific thin-feature screen](../research/935-local-wall-screen-20261105/README.md)
then measures 5,000 inward normal chords on the actual delivered mesh. Sixteen
distances, including the eight shortest, agree with an independent full-triangle
search. All 354 samples below 2 mm lie on retained envelope skin, away from
the new cut caps. These are diagnostic material paths, not global minimum-wall
metrology. Process-wall and simulation-feature admission remain open; the
existing 3MFs are unchanged and no mesh sweep or automatic thickening follows.

The [exact-boundary physics preparation](../research/935-local-physics-20261105/README.md)
then qualifies a fresh native Gmsh 4.12.1 runtime and independent tetrahedral
inspector on the actual analytic cube. Its one bounded attempt on the complete
delivered surface reaches the 900-second limit; no final head volume mesh is
accepted. A separate all-face bound finds 3,269 boundary triangles that force
incident tetrahedra below diagnostic mean ratio 0.01. Surface conditioning with
a preservation proof must precede another interior-size sweep. Kali version
probes confirm CalculiX 2.23 and an updated OpenFOAM 14 image, requiring fresh
OpenFOAM case controls. These software/preparation results do not qualify head
physics or manufacturing and do not replace the frozen 3MF files.
