# 935 cylinder head: starting again from the raw scan

**Non-commercial** R&D with CAD-Recode v1.5 (code and weights CC-BY-NC-4.0).
No geometry, simplification, section, orientation, interface or material from
the old reconstruction is reused. The old work remains intact.
Only the generic tools are reusable. The part remains a 935
reference, with no 993 compatibility and no manufacturing authorisation.

## Status and boundaries

The preparation was executed on a dedicated Vast VM. See `verification.md`
for the checks actually executed and their limits. No public image.
`models.lock.json` fixes the public revisions; `fetch.py` writes the actual
digests of the downloaded files. The Docker bases are pinned by digest.
CAD-Recode GPU, Nemotron and the OpenClaw tools were executed; the
SimReady route is qualified separately.

A cylinder head with fins and galleries goes beyond the simple shapes of the
CAD-Recode benchmarks. The 256 input points can lose important details: the
first complete pass is a diagnostic, never evidence of a faithful
reconstruction. `face-components.npy` only proposes connected components; their
identity and any anatomical subdivision require a review of the raw scan.
No hole is filled automatically. No old result feeds the new reports.

## Local preparation

From the repository root (Python 3.11):

```bash
uv venv --python 3.11 work/cad-recode-tools-venv
uv pip install --python work/cad-recode-tools-venv/bin/python -r scripts/cad_recode/requirements.txt
uv pip install --python work/cad-recode-tools-venv/bin/python huggingface-hub==0.27.0
PY=work/cad-recode-tools-venv/bin/python
$PY -m unittest discover -s tests -p test_cad_recode_fresh.py -v
$PY scripts/cad_recode/fetch.py work/cad-recode-models --weights all
$PY scripts/cad_recode/pipeline.py prepare \
  raw-scans/wolfe-classics-935-cylinder-head/original/935-xtreme-cylinder-head.obj \
  work/cad-recode-935-fresh/intake
```

Each output requires a new directory, to preserve the attempts and their
failures. An interrupted download is kept; start again in another
directory, taking advantage of the HF cache. No HF token is used. The scans,
weights, STEP files and reports remain in folders ignored by Git.
The expected SHA-256 of the raw file is verified before analysis. The initial frame remains
raw XYZ: no PCA interpreted as a datum, no old frame imported.

Preprocessing samples 8192 points, then selects 256 distant points.
It keeps the centre, normalisation factor, seed and inverse transformation.
**The CAD-Recode code is at normalised scale ×100**: the worker applies
`xyz_brut = xyz_CAD / 100 / normalization_scale + center` (`xyz_brut` = raw XYZ).
The physical units remain unknown; the STEP uses the numerical OBJ units
for inspection, without claiming that its nominal units are measured.

## Machine and images

Target: Linux x86_64 Vast VM with Docker, NVIDIA Container Toolkit and GPU access,
RTX PRO 6000 Blackwell 96 GB, 32 vCPU, 128 GB RAM, 500 GB NVMe. A standard
container instance is not an automatic substitute for this VM.
Build on the VM; do not copy the Mac's credentials.

```bash
docker build --platform linux/amd64 --target cad -f containers/cad-recode.Dockerfile -t 3dprinting993-cad-recode-cad:dev .
docker build --platform linux/amd64 --target inference -f containers/cad-recode.Dockerfile -t 3dprinting993-cad-recode-inference:dev .
docker build --platform linux/amd64 -f containers/cad-recode-openclaw.Dockerfile -t 3dprinting993-cad-recode-openclaw:dev .
```

After testing, publish the authorised images separately and use their
`repository@sha256:…` references: no publication digest is invented here.
For a local Docker trial without publication, the immutable reference returned
by `docker image inspect --format '{{.Id}}' IMAGE` is also accepted.
Record `pip freeze`, driver version, `nvidia-smi`, GPU inventory, image and
smoke-test results. An emulated Mac build does not prove Blackwell inference.

## Inference and evaluation

The runtime uses PyTorch CUDA 12.8 and eager attention, without reusing
the old CUDA 12.4 FlashAttention build. Test the imports and one
inference before a long job. No silent fallback to CPU.

```bash
# MODEL_DIR et RUN_DIR : chemins absolus, hors Git ; images construites ci-dessus.
mkdir -p "$RUN_DIR/inference"
chmod 0777 "$RUN_DIR/inference"  # Seule cette sortie est inscriptible par UID 65534.
docker run --rm --gpus all --network=none --read-only --cap-drop=ALL \
  --security-opt=no-new-privileges --tmpfs /tmp --memory=24g \
  -v "$MODEL_DIR:/models:ro" -v "$RUN_DIR/intake:/input:ro" \
  -v "$RUN_DIR/inference:/output" \
  3dprinting993-cad-recode-inference:dev /input /models /output/proposals --attempts 3

$PY scripts/cad_recode/pipeline.py export \
  "$RUN_DIR/inference/proposals/candidate-1.py" "$RUN_DIR/intake" "$RUN_DIR/export-1" \
  --image "$CAD_IMAGE" --timeout 180
```

(The comments in the block read: "MODEL_DIR and RUN_DIR: absolute paths, outside
Git; images built above." and "Only this output is writable by UID 65534.")

The three proposals are distinct generations, not three successes.
The code must define `r`, a CadQuery Workplane. The worker is disposable, with no
network, no secret, unprivileged, with 4 GB RAM, 2 CPUs and a timeout.
The evaluation rereads the STEP separately and measures **surface-to-surface
distances, sampled in both directions**; sampled maximum ≠ exact
Hausdorff. No dimensional threshold is invented. For untrusted outputs,
use the dispatcher, which also isolates the STEP parser in a container.

## OpenClaw and Nemotron on Vast

`compose.yaml` keeps vLLM and OpenClaw on the VM's local loopback. The initial
context is 32K, a single sequence and 50 % of VRAM reserved for vLLM. Adjust this
reservation only after measurement. The gateway's no-authentication
configuration is limited to loopback: access only through SSH on a dedicated VM.
Do not change the bind to a public interface.

Define absolute paths for `CAD_MODELS`, `CAD_RUN`, `CAD_AGENT_STATE` and
`CAD_AGENT_WORKSPACE`. Create the state/workspace folders with UID/GID 1000,
then copy `AGENT.md` to `$CAD_AGENT_WORKSPACE/AGENTS.md` and create `requests/`.
Copy the generated proposals into the workspace, without old geometries.

```bash
docker compose -f deploy/vast/cad-recode/compose.yaml config --quiet
docker compose -f deploy/vast/cad-recode/compose.yaml build openclaw
docker compose -f deploy/vast/cad-recode/compose.yaml run --rm --no-deps openclaw config validate
docker compose -f deploy/vast/cad-recode/compose.yaml up -d nemotron
python3 deploy/vast/cad-recode/smoke-nemotron.py
docker compose -f deploy/vast/cad-recode/compose.yaml up -d openclaw
```

The FP8 model and its parser must be present in the pinned snapshot.
The smoke test requires a real JSON tool call; `/health` alone is not enough.
OpenClaw has only read/write/edit access to the workspace. **No
shell, Docker socket, Vast account, old memory or secret.** The operator
runs the dispatcher from the VM (repeat after each request from the agent):

```bash
$PY scripts/cad_recode/dispatch.py "$CAD_AGENT_WORKSPACE" "$CAD_RUN" --cad-image "$CAD_IMAGE"
```

Only `export` and `evaluate`, with attempts 1 to 3, are accepted. The results
folder is mounted read-only in OpenClaw. The requests allow
neither choosing an image, nor modifying a command, nor renting a machine.
The Compose profile `omniverse` adds the pinned local VLM Qwen2.5-VL-7B, on
127.0.0.1:8003 with 23 % of VRAM. Start it after Nemotron; together the two
reserve about 72 GB on this machine. Stop the models before
a heavy render if the available VRAM is insufficient. Save through SSH only the outputs,
requests and conversations needed; no authentication configuration.

## Local Content Agents on the qualified VM

The session uses Content Agents v0.5.2, the `usd-convert-cad` converter
0.2.0 in an isolated Python 3.12 venv, and the pinned SimReady runtime installed
by the preflight. See the saved manifest for the complete versions.
The VLM is started after Nemotron:

```bash
docker compose -f deploy/vast/cad-recode/compose.yaml --profile omniverse up -d vlm
python3 deploy/vast/cad-recode/smoke-vlm.py
```

In the Content Agents checkout created by the preflight, apply
`content-agents-local.patch`: ports published on loopback and the renderer reached
by its internal Docker name, recognised as local by the upstream services.
Start OVRTX with `OVRTX_HOST_PORT=127.0.0.1:8001`, create the
`content-agents-network` network, then connect the OVRTX container to it with the alias
`ovrtx-rendering-api` before the Material/Physics deployment.

The models stay on loopback. On this VM, `docker0` is 172.17.0.1;
the services reach them through two relays limited to that interface:

```bash
# socat doit être installé ; vérifier l'adresse docker0 avant réemploi.
for port in 8002 8003; do
  systemd-run --unit=cad-proxy-$port socat TCP-LISTEN:$port,bind=172.17.0.1,reuseaddr,fork TCP:127.0.0.1:$port
done
```

(The comment in the block reads: "socat must be installed; check the docker0
address before reuse.")

Configure the preflight with the `openai` backends, the VLM `cad-vlm` at
`http://host.docker.internal:8003/v1` and the LLM `nemotron-cad` at
`http://host.docker.internal:8002/v1`. The variables `LOCAL_VLM_API_KEY` and
`LOCAL_LLM_API_KEY` are literally `local-unused`: markers required
by the local client, with no external account or vendor secret.
In `deploy/collection/collection.yaml`, limit
`dependencies.vlm.max_tokens` to 2048 for the 8192-token VLM context.
Use `USD_CONVERT_CAD_PYTHON` for the converter venv, and run
the preflight with the Python of the SimReady venv (+ PyYAML 6.0.2).

The VM had a conflict after an automatic update of the NVIDIA
libraries; the driver was reloaded with no active GPU process. To reproduce,
check driver/NVML consistency before starting the models. Never
reload a driver during a calculation. The apt timers were suspended
only in this ephemeral guest during qualification.

## Physical calculations: a fresh dossier

`engineering-inputs.json` starts empty again. The following command lists what is missing
and returns 3 as long as an engineering review has not been carried out:

```bash
$PY scripts/cad_recode/pipeline.py readiness \
  deploy/vast/cad-recode/engineering-inputs.json "$RUN_DIR/physics-readiness"
```

Reuse the solvers of `containers/cadsim.Dockerfile`, but no old cylinder-head
case. For OpenFOAM: `benchmarks/openfoam-poiseuille-f25/run_local.sh` checks
an independent analytical problem. The script `scripts/cad_recode/ccx_smoke.py OUTPUT --ccx ccx` checks a
bar in tension (`u=FL/EA`) and 1D conduction (`q=kAΔT/L`) by actually running CalculiX. The properties and
loads of these synthetic fixtures never become those of the cylinder head.
PhysicsNeMo remains prepared by the existing isolated image, without training.

## Complete SimReady route, separate steps

Install the `omniverse-cad-to-simready` skill and its Python 3.12 environment.
`simready-stage.sh` calls its references directly, without a monolithic runner.
Define `SIMREADY_SKILL_ROOT`, `SIMREADY_PYTHON` and a new `OV` folder.

1. `bash deploy/vast/cad-recode/simready-stage.sh preflight --env-file "$OV/preflight.env" --report "$OV/preflight.json" --markdown-report "$OV/preflight.md"`, then source the env file.
2. Check the OVRTX, Material and Physics services before inspection/conversion. Use the Qwen2.5-VL-7B VLM already provided for by the SimReady tools, and stop Nemotron if VRAM requires it. Any secrets must come exclusively from the approved OpenBao wrapper; their absence blocks this route.
3. Call `identify-asset-context`, then `convert-to-usd` separately on the scan and the candidate STEP; keep the reported USD paths, without assuming their names.
4. Validate each USD with `validate-usd-minimum`. For the overlay, call `scripts/cad_recode/assemble.py SCAN_USD CAD_USD COMPARISON_USDA --scan-display-scale S --cad-display-scale C` in the USD environment. Determine S and C from the transformations reported by the converter: never from an assumed Porsche dimension. These scales are only visual; their values remain to be verified on the converter's first run.
5. On an experimental copy of the candidate, call `content-agents` with `--call material --call physics --convert-physics-output-to-usd`, then `simready-conform-profile --profile Prop-Robotics-Neutral`. Never modify the master scan or STEP.
6. Call in order `omni-asset-validate`, `omni-asset-validate-geometry`, `omni-asset-validate-physics`, `simready-validate`, then `ovrtx-render-service`. Each time, reuse the actual `output_usd_path` from the previous report.
7. Keep the FET correction requests and their evidence. Without justifiable properties/scale/grasps: `blocked` or `needs_rerun`, never forced conformance. Check that the images are neither empty nor uniform.

The detailed flags remain those of `references/commands.md` in the installed skill.
The SimReady profile describes a manipulable object, not a validated engine. The
experimental materials, densities and collisions are neither measurements nor a
validation of strength/fatigue. No texture or public publication.

## Sources

- https://github.com/filaPro/cad-recode — architecture, notebook and licence.
- https://huggingface.co/filapro/cad-recode-v1.5 — non-commercial weights.
- https://github.com/vllm-project/recipes/blob/main/NVIDIA/Nemotron-3-Nano-30B-A3B.md
- https://docs.openclaw.ai/gateway/config-tools/custom-providers
- https://vast.ai/article/announcing-virtual-machine-rental-on-vast-ai

### Restarting from the triangles: profiles and partial surfaces

After the visual rejection of the global 256-point reconstruction, the following
commands start again from the raw OBJ and its digest. No old frame or
old cylinder-head geometry is imported. Run in the qualified CAD runtime,
with the repository as the current directory:

```sh
python -m scripts.cad_recode.recover_sections SOURCE.obj OUTPUT/profiles --sha256 SHA256
python -m scripts.cad_recode.recover_planes SOURCE.obj OUTPUT/surfaces --sha256 SHA256
```

The outputs are analytical circles and trimmed planar faces, as STEP,
with their JSON parameters. They are not a complete cylinder head nor a solid.
Open contours are not closed; triangles forming pinches
are removed from the candidate zones only, without modifying the original scan.

The exploratory thresholds of 0.6 OBJ unit for profiles and 0.4 for planar
projection are adjustable with `--profile-tolerance` and `--projection-tolerance`.
They are not mechanical tolerances. The physical scale remains unknown.
An incomplete arc, a poor fit, a surface without support in the scan or
a STEP that fails to read back is rejected. The checks against the scan are
sampled; they prove neither global accuracy nor fitness for manufacture.

Targeted check: `python -m unittest tests.test_cad_recode_sections`.

To fill **small gaps in the scan**, on a copy that keeps exactly
the original vertices and triangles:

```sh
python -m scripts.cad_recode.repair_scan_gaps SOURCE.obj OUTPUT/profiles/profiles.json OUTPUT/repaired --sha256 SHA256
```

The script protects the detected circular openings, enforces a closed boundary,
continuity of normals with the neighbouring surface, a triangulation with no new
non-manifold edge and an exact OBJ read-back. The parameters `--max-gap` (3 OBJ
units by default) and `--max-planarity` (0.25) are exploratory repair limits.
Large contours, branched boundaries and ambiguous zones remain open.
The report explicitly distinguishes surfaces added by interpolation from measured
surfaces. This operation does not automatically make the mesh watertight.
