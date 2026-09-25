# Compute environment

The project's heavy work — photogrammetric reconstruction, meshing, FE
computation, CFD and SimReady preparation — does not fit on an ordinary
workstation. It is described here as eight reproducible container images,
runnable locally or on a GPU machine rented by the hour.

No container is needed to contribute to the catalog. `make check`
remains a dependency-free Python command.

## Eight images, eight needs

| Image | Need | Contents | Scope |
|---|---|---|---|
| `3dprinting993-recon` | CUDA | COLMAP, GLOMAP, Blender, Open3D, pymeshlab, OpenCV | photos → scaled mesh |
| `3dprinting993-cadsim` | cores and memory | build123d, CadQuery, Gmsh, CalculiX, OpenFOAM, PrusaSlicer | code → STEP → computation → G-code |
| `3dprinting993-mesh-cfd` | cores and memory | Blender, pymeshlab, trimesh, build123d, Gmsh, OpenFOAM | OBJ scan → segmentation → STEP proxy → CFD domain |
| `3dprinting993-physicsml` | CUDA + GPU memory | contents of `cadsim`, JAX-FEM, PhysicsNeMo, DeepXDE | mesh → differentiable solver → physics model |
| `3dprinting993-simready` | RTX, 48 GB recommended | OVRTX, Material Agent, Physics Agent, OpenUSD, SimReady Validator | 3D source → enriched USD → validation → Omniverse render |
| `3dprinting993-simready-workflow` | RTX, 48 GB recommended | pinned SimReady image, CAD preflight and Vast.ai startup | reproducible validation before rental |
| `3dprinting993-simready-local-ai` | 48–80 GB GPU, 500 GB disk | SimReady contents, local Qwen2.5-VL 7B, vLLM, PhysicsNeMo | API-free chain: views → materials/physics → USD → physics models |
| `3dprinting993-ov-libraries-cpu` | `linux/amd64` CPU | NumPy 2.5.2, ovstage 0.1.1.355824, ovphysx 0.5.11 | physics USD → shared state → rigid contact/motion |

The split is deliberate. Reconstruction needs a GPU and a heavy CUDA image;
classical computation runs just as well on a machine without a GPU, often much
cheaper. `physicsml` is reserved for the steps that actually benefit from the
GPU: differentiable solvers and physics-informed learning.

`simready` groups the three NVIDIA services in a single container, because a
standard Vast.ai instance cannot run Docker Compose inside Docker.
The image must be built and tested in GitHub Actions before any rental. NVIDIA
secrets are never placed in a layer: they are injected after SSH login by the
OpenBao wrapper, then `simready-services start` validates the inference
authorization with a minimal request that displays neither secret nor
response, then starts the native services. An HTTP 401/403 error therefore
blocks the chain before batch preparation and rendering.

`ov-libraries-cpu` separately tracks the new embeddable NVIDIA architecture.
The application loads USD into `ovstage`, then `ovphysx` reads the same scene
and writes back its results. OVRTX stays in the RTX image: a render or a sensor
is not needed to verify a CPU rigid contact.

The `simready-local-ai` variant removes this dependency. It pins in the image
the Apache-2.0 snapshot of `Qwen/Qwen2.5-VL-7B-Instruct`, exposes its
OpenAI-compatible API only on `127.0.0.1:8000`, and routes Material Agent and
Physics Agent to that service. PhysicsNeMo 2.2.0 is installed in the same
isolated environment; it remains a physics-model engine distinct from the
Physics Agent that enriches the USD. This image needs no inference secret at
startup.

On September 1, 2026, the image published and tested for this chain is
`ghcr.io/cluster2600/3dprinting993-simready@sha256:3947ea34d5101065c97103cc2176f395cb9753cb1d7807acb3cfd095796a4e1a`.
On Vast.ai, the 917 and 935 scans were converted to direct USD and rendered by
OVRTX. The Material Agent prepared its views but the call to the public model
was refused with HTTP 403: conversion and rendering are proven, AI assignment
and Physics Agent are not. This split avoids confusing a ready service with a
valid API authorization.

The profile validator must receive the three specification directories.
Use the embedded launcher rather than the raw command:

```bash
simready-profile-validate scene.usd \
  --profile Prop-Robotics-Physx --version 2.1.0
```

The software choices are justified in
[decisions/0002-scriptable-toolchain.md](decisions/0002-scriptable-toolchain.md):
every selected tool runs without a graphical interface.

General Coder/VL LLMs are not added to the CAD or solver images: vLLM is
normally started on a separate GPU instance. Only the explicitly named
`simready-local-ai` variant embeds Qwen2.5-VL for the Content Agents. The
selected model, the GPU sizing and the LLM's authority boundary are described
in [AI_DIGITAL_TWIN_STACK.md](AI_DIGITAL_TWIN_STACK.md).

## Build and verify

```bash
make container-recon      # GPU image
make container-cadsim     # CPU image
make container-mesh-cfd   # CPU image dedicated to large scans and CFD
make container-physicsml  # GPU image for JAX-FEM / PhysicsNeMo
make container-simready   # NVIDIA CAD-to-SimReady GPU image, linux/amd64
make container-simready-local-ai # SimReady + local VLM + PhysicsNeMo
make container-ov-libraries-cpu # current ovstage + ovphysx, CPU linux/amd64
make container-smoke-all  # runs smoke-test.sh in the five images
```

`containers/smoke-test.sh` fails if an advertised tool does not respond. An
image that does not pass this test does not go to a paid machine.

The GitHub workflow uses Docker Buildx. If the local workstation shows
"legacy builder is deprecated", install/enable Buildx or run the build
from the manual `Build compute images` action; the legacy builder can hang
while saving a very large CUDA layer.

The `physicsml` image pins JAX `0.11.1`, JAX-FEM `0.0.12`, PhysicsNeMo `2.2.0`
and DeepXDE `1.15.0`. PhysicsNeMo's `gnns` extra stays optional because it adds
architecture-dependent PyTorch extensions; it can be enabled at build time with
`PHYSICSNEMO_EXTRAS`.

This GPU image is large: plan at least 30 GB of disk for the image and more
for datasets, checkpoints and results. The smoke test checks the imports on a
CPU runner and also checks JAX/PyTorch on an instance that actually exposes an
NVIDIA card.

A version test does not, however, prove that a chain works.
`containers/examples/cad_to_fea.py` chains parametric solid, STEP export,
tetrahedral meshing and CalculiX computation in a single command:

```bash
docker run --rm -v "$PWD/work:/tmp/chain" \
    3dprinting993-cadsim:dev python /tmp/chain/cad_to_fea.py
```

## Deploy on a rented machine

The example uses vast.ai; the principle holds for any host that runs a
Docker image.

1. **Publish the image** to a reachable registry:

   ```bash
   make container-push REGISTRY=ghcr.io/<account> IMAGE_TAG=2026.08.28
   ```

   To publish only the dedicated GPU image, build and push its tags
   explicitly after authenticating to the registry:

   ```bash
   make container-physicsml IMAGE_TAG=2026.08.30
   docker tag 3dprinting993-physicsml:2026.08.30 \
     ghcr.io/<account>/3dprinting993-physicsml:2026.08.30
   docker push ghcr.io/<account>/3dprinting993-physicsml:2026.08.30
   ```

2. **Choose the machine.** For reconstruction, aim for an Ampere or Ada
   generation (RTX 3090, 4090, A100, L40S): CUDA 12 binaries are safe there.
   Also check the node's network throughput, because the image is downloaded
   on every rental, and the disk space, which is set at creation and cannot be
   changed afterwards.

3. **Fill in the instance template**: for the full CAD/FE/Physics ML chain,
   choose the image `…/3dprinting993-physicsml:<tag>` with a visible CUDA card.
   For photo reconstruction alone, use `…/3dprinting993-recon:<tag>`.
   Launch mode `Entrypoint`, and optionally `PROVISIONING_SCRIPT`
   pointing to the raw URL of `containers/provision-vastai.sh`.

   The `SSH` and `Jupyter` modes replace the image entrypoint: the container's
   environment variables and `PATH` are then not visible in the session. The
   provisioning script writes them back into `/etc/environment`.

   Recommended launch command in a Vast.ai terminal:

   ```bash
   nvidia-smi
   smoke-test.sh physicsml
   mkdir -p /workspace/project
   cd /workspace/project
   ```

   For an equivalent Docker launch with separate working directories:

   ```bash
   docker run --rm --gpus all --ipc=host --shm-size=16g \
       -v "$PWD:/workspace/project" -v "$PWD/work:/workspace/work" \
       ghcr.io/<account>/3dprinting993-physicsml:<tag> bash
   ```

4. **Send the data**, never through Git:

   ```bash
   rsync -avP ./photos/ root@<host>:<port>:/workspace/images/
   ```

5. **Retrieve the results** then **destroy the instance**. The rented disk is
   not a backup.

## Known version constraints

- COLMAP is compiled from source: neither the Ubuntu packages nor conda-forge
  provide CUDA, so dense reconstruction is missing there.
- GLOMAP 1.2.0 does not compile against COLMAP 4.1.1: the `Rigid3d` API changed.
  It is therefore built against the COLMAP it pins, under its own prefix. The
  two coexist, `colmap` remaining the current version.
- Meshroom 2025.1 is compiled with CUDA 12 and requires compute capability ≥ 5.0.
  For a recent Blackwell card, check compatibility before renting.
- Code_Aster is not copied into `physicsml`: its official reproducible
  distribution relies on the Salome-Meca/Singularity environment. CalculiX is
  included for the immediately available containerized FE path; Code_Aster
  will be consumed in its dedicated container once we have frozen a
  Vast.ai-compatible image and smoke test.

Upstream references used to choose the versions:
[PhysicsNeMo](https://github.com/NVIDIA/physicsnemo),
[JAX](https://docs.jax.dev/en/latest/installation.html),
[JAX-FEM](https://github.com/deepmodeling/jax-fem) and
[code_aster](https://code-aster.org/en).

## Typical reconstruction chain

```bash
colmap feature_extractor   --database_path sfm/db.db --image_path images \
                           --ImageReader.single_camera 1
colmap exhaustive_matcher  --database_path sfm/db.db
glomap mapper              --database_path sfm/db.db --image_path images --output_path sfm
colmap image_undistorter   --image_path images --input_path sfm/0 --output_path dense
colmap patch_match_stereo  --workspace_path dense          # CUDA required
colmap stereo_fusion       --workspace_path dense --output_path dense/fused.ply
```

Scaling is not automatic: a photogrammetric reconstruction is only correct up
to a scale factor. Place a reference of known length in the scene and register
afterwards (`colmap model_aligner`), otherwise the mesh is not a measurement.
See [SOURCE_POLICY.md](SOURCE_POLICY.md).

## Reading a JavaScript-rendered page

Several sources in the registry respond but deliver nothing: their content
only exists after the page script runs. This is a rendering problem, not a
refusal, and it is solved by a server-side browser.

**Cloudflare Browser Run** provides one, with two engines: Chromium by default,
and **Kitesurf**, a stateless engine designed for agents, released on
August 6, 2026, free in beta, announced at 3 to 7 times less CPU and memory
than Chromium for HTML capture and extraction.

Two access paths, and they are not equivalent:

| Path | Kitesurf | What is needed |
|---|---|---|
| Worker binding, `env.BROWSER.quickAction()` | **not documented** | a deployed Worker, no token |
| REST API, `?browser=kitesurf` | **yes** | a `Browser Rendering - Edit` token |

The Kitesurf engine can therefore, to date, only be selected through the REST
API.

Pitfall to know: `quickAction()` returns a `Response` object, not a bare
object. Serializing it directly produces `{}` and suggests an empty page. The
useful body is `{ success, result }`.

What Browser Run does not solve: a host that returns 403, and a site that
refuses named agents. The documentation also states that Kitesurf cannot
negotiate a TLS-fingerprinting anti-bot challenge. Changing infrastructure does
not change a permission.

## Data hygiene

A rented machine belongs to someone else.

- No private key, no token, no vehicle identifier on the instance.
- Raw photos and scans stay out of the Git repository, in line with
  [AGENTS.md](../AGENTS.md).
- Do not process personal data there: license plates, faces, registration
  documents.
- What comes back into the repository is the processed result and its
  traceability, not the raw content.

## Cost

Rental is paid by the hour, image included. Three habits:

- build and test the image locally before renting;
- prepare the photo set and the complete script before starting the instance;
- run the chain under `tmux`, since a disconnection must not kill the
  computation.
