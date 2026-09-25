# Open-source suite for building the digital twin

## Decision

The project selects an open chain where the LLM assists the engineer but never
produces an authoritative dimension. The manufacturing geometry remains a
versioned parametric solid; scans and model answers are inputs to be verified.

| Function | Main choice | Role in the project |
|---|---|---|
| CAD/code agent | Qwen3-Coder-30B-A3B-Instruct + Qwen Code | write and fix the build123d masters, tests and JSON records |
| Multimodal reading | Qwen3-VL-8B-Instruct | sort photos and drawings, pick out candidates to verify |
| LLM server | vLLM | local OpenAI-compatible API on the GPU machine |
| Parametric CAD | build123d + FreeCAD | BREP solids, STEP and constrained assembly |
| Reconstruction | COLMAP/GLOMAP + Open3D | photos to point cloud/mesh, registration and deviations |
| Computation meshing | Gmsh | reproducible volume meshing |
| Structural/thermal | CalculiX | linear, nonlinear, static and thermal FE |
| Fluid/thermal | OpenFOAM | flow, convection and heat transfer |
| Visualization | FreeCAD, Blender, ParaView | CAD inspection, visual context and computation results |
| Data | Git + JSON + STEP | provenance, versions, interfaces and acceptance rules |

The Qwen models are published under Apache-2.0. The Coder model is a MoE of
30.5 billion parameters, of which about 3.3 billion are active per token, and
its official model card directly provides a `vllm serve` command. FreeCAD
uses Open CASCADE, includes a built-in Assembly workbench and imports/exports
STEP. build123d can build assembly trees and export the whole assembly
to STEP.

Primary sources:
[Qwen3-Coder](https://huggingface.co/Qwen/Qwen3-Coder-30B-A3B-Instruct),
[Qwen3-VL](https://huggingface.co/Qwen/Qwen3-VL-8B-Instruct),
[FreeCAD](https://www.freecad.org/features.php),
[build123d assemblies](https://build123d.readthedocs.io/en/latest/assemblies.html),
[COLMAP](https://colmap.github.io/tutorial.html),
[Gmsh](https://gmsh.info/),
[CalculiX](https://www.calculix.de/) and
[OpenFOAM](https://openfoam.org/version/13/).

## What each LLM does

`Qwen3-Coder-30B-A3B-Instruct` is the main model. It can turn a validated
measurement record into a build123d script, propose the assembly constraints
and write the tests. Its output must pass `make check`, be opened in FreeCAD
and be compared to the sources.

`Qwen3-VL-8B-Instruct` serves for the initial sorting of photos, screenshots
and drawings. It can spot a reference, a table or a useful view, but a
dimension read by vision stays `candidate` until a human reading and a second
piece of evidence.

Neural Concept is not part of the initial foundation: it is a commercial
surrogate-model product, useful only once a set of correlated simulations or
tests has been built. Before that stage, it adds cost without solving the
lack of geometry and boundary conditions.

## Vast.ai sizing

The sizes below are practical targets to be confirmed with the weight format
and context length at rental time.

| Offer | Recommended use | Limit |
|---|---|---|
| RTX 4090, 24 GB | Qwen3-VL-8B, COLMAP; quantized Coder 30B run alone | context and KV cache to be limited |
| RTX A6000 / RTX 6000 Ada, 48 GB | baseline choice: quantized or FP8 Coder 30B, then VL/reconstruction separately | avoid two large models at the same time |
| A100/H100, 80 GB or 2 × 48 GB | long contexts and heavier models | cost rarely justified for the first zone |

The best first choice is therefore **a 48 GB card**, 16 vCPUs, 64 GB of
RAM and 150 to 250 GB of disk. Photogrammetry and the LLM are run one after
the other. CAD/FE can then run with
`3dprinting993-cadsim` on a cheaper CPU offer.

Vast runs instances as Linux Docker containers and reserves the disk size at
creation. Its persistent volumes stay tied to the physical machine and are
therefore not a portable backup. See the
[Docker documentation](https://docs.vast.ai/guides/instances/docker-environment)
and the [volumes documentation](https://docs.vast.ai/guides/instances/storage/volumes).

## Launching the LLM on Vast.ai

Rental is paid: these commands are a launch template, not an authorization to
create the instance. After selecting a 48 GB offer and creating a volume,
start the official vLLM image with port 8000 exposed:

```bash
vastai create instance <offer_id> \
  --image vllm/vllm-openai:latest \
  --disk 80 --ssh --direct \
  --env '-p 8000:8000 -v <volume_name>:/data'
```

In the instance:

```bash
vllm serve Qwen/Qwen3-Coder-30B-A3B-Instruct \
  --host 0.0.0.0 --port 8000 \
  --enable-auto-tool-choice --tool-call-parser hermes
```

For a reproducible run, replace `latest` with the image version tested before
the first rental. Never put a token in the command, the repository or the
shell history; use the instance's own secret mechanism.

## Twin build flow

1. Record the source, its rights and what it proves.
2. Extract **candidate dimensions** with Qwen3-VL, then verify them.
3. Produce the build123d/FreeCAD master and export STEP.
4. Register scans and solid in Open3D, with a known metric reference.
5. Define datums, joints, contacts and clearances in the twin registry.
6. Assemble in FreeCAD and reproduce the assembly with a build123d script.
7. Run collisions and acceptance rules with the uncertainties.
8. Mesh with Gmsh then simulate with CalculiX or OpenFOAM if needed.
9. Correlate against physical measurements before any validation statement.

The first geometric batch is
`TWIN-993-WHEEL-HUB-INTERFACES-0001`. It contains four STEP wheel proxies,
but still awaits the hub and brake geometries before the first real spatial
check.

## Data and security

- Raw photos and scans stay in `/data` or private object storage,
  never in Git.
- A Vast volume is temporary and tied to its host; sync the results
  at the end of every session.
- STEP files and derived reports only enter the repository if their license
  and provenance allow redistribution.
- The LLM validates neither the fit, nor the material, nor the safety of a
  part.
- Wheel, braking, steering and suspension parts stay blocked for
  manufacturing without a professional engineering review.
