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
