# Software stack rebuild — 5 November 2026

Tracking: [parent #404](https://github.com/cluster2600/porscheparts/issues/404),
[Vast dependency gaps #405](https://github.com/cluster2600/porscheparts/issues/405),
[images #406](https://github.com/cluster2600/porscheparts/issues/406),
[NativeCAD/NVIDIA #407](https://github.com/cluster2600/porscheparts/issues/407).

This is an in-progress replacement generation, not a completed fleet upgrade.
`inventory.json` preserves the 43 Docker recipes at baseline `92e9826a5` and
now also accounts for the separate English F34b generation (44 inventory rows).
Original recipes, lock files, evidence and existing image tags are preserved. New image tags use `porscheparts/<name>:stack-20261105`.

## 7 November integration checkpoint

The current results contain 38 replacement recipes: all 38 have a matching native
Linux build and offline CPU-smoke receipt. PrusaSlicer 2.9.7 now passes its
offline synthetic-cube slice after adding the missing PNG runtime library;
`prusa-native-validation.json` binds the new image, inputs and receipt hashes.
The earlier missing-library failure is retained. Reconstruction also passes its
offline CLI, Blender-version and Python-import checks after refreshing the
allowlisted source context; `recon-native-validation.json` binds the selected
receipt. Cached build layers were reused. Representative reconstruction quality
and GPU execution remain unverified.
The separate CAD-Recode CAD companion passes
STEP readback and CalculiX bar/heat checks, with zero measured relative error
in both solver controls. `cad-recode-native-validation.json` binds the exact
parent images, all 19 source inputs and retained numerical results.
The original 33 successes were rechecked against the retained Kali receipt
metadata and exact image IDs; `receipt-audit-20261107.json` records the log
hashes. This audit does not establish every dependency revision or GPU behavior.
[JAX-FEM](JAX_FEM_NATIVE.md) and [vLLM](NATIVE_FOLLOWUP.md) add two successful
native runs, retaining their failures and explicit acceptance limits.

The text below retains the earlier rebuild history. NativeCAD's later active
connection and independent STEP/PicoGK check are reviewed separately in
[PR #635](https://github.com/cluster2600/porscheparts/pull/635); measurements from
different synthetic runs remain distinct. The English F34b receipt integration
is in [PR #636](https://github.com/cluster2600/porscheparts/pull/636).

All nineteen phase IDs in `workflow-coverage.json` remain accounted for, with
engineering inputs unvalidated and no engineering phase executed or admitted by
this software task. Only runtime evidence and delivery accounting change.
Corpora remain frozen; no model training, paid compute or registry publication
is performed. F40/F41 wrapper migration remains excluded under the prior
approval-hook rejection described below.

`upstream-audit.json` retains the 4 November online checks for 285 Python
distributions and native repositories, including their source URLs. Its declared
versions describe the earlier audit checkout, not installed software or the
newer rebuild baseline. Of the Python queries, 133 found a newer registry
version than an extracted pin, 136 matched, 13 had no extracted pin and three
needed CUDA-specific wheel comparison. `dependency-evidence-index.json` records
the 13 matching tracked setup/failure documents and separates actual runtime
repairs from instructions and mocks.

## Expected project improvements

| Change | Project benefit and verification limit |
|---|---|
| COLMAP 4.2.1 | Upstream meshing, memory and CUDA fixes target reconstruction failures; a representative scan benchmark is still needed |
| Content Agents 0.6.2 | Material-layer, rendering and retry fixes target the Omniverse workflow; GPU/service replay remains required |
| Warp 1.19 | New sparse and geometry APIs offer optimization opportunities; CPU analytic checks pass but no GPU speedup is measured |
| Python 3.15.2 | Selected standard-library and Warp lanes execute successfully; it cannot replace incompatible native Python environments |
| Split CAD environments | Latest build123d and CadQuery can coexist without contradictory OCP requirements; independent STEP readback passes |
| Image dependency closure | Explicit mesh/OpenMP dependencies and preflights reduce last-minute installations; remaining gaps are listed below |
| NativeCAD 0.29 | Updated local MCP server passes the analytic-box check; export interoperability and active-chat restart remain separate |

No project-wide performance gain or engineering qualification is claimed.

The owner explicitly accepted the applicable NVIDIA terms and authorized the
Kit installer acceptance flag on 5 November 2026. The candidate pins Kit App
Template `b8e9f2e4f2930d19e87e3702d4eeaf00d9846676` (Kit 110.4.1).
Its packaging check is not editor, Vulkan, GPU or streaming acceptance.

`build-results.json` records passing build/CPU-smoke candidates and failed attempts.
Representative reconstruction and GPU validation remain pending;
this is not completion of the 44-recipe inventory. CAD's passing check covers
STEP geometry and Python imports, not every solver and slicer in that image.

The first full Linux check ran 5,194 tests with 26 failures and 97 errors under
Kali's umask 002. Security guards rejected group-writable fixtures and checkout
files. A new run uses umask 022 and removes group/world write permission from the
dedicated validation clone; the guards themselves are unchanged.
That rerun executed 5,199 tests with one failure and 414 skips: the host's .NET
6 SDK cannot target the existing .NET 9 alignment test. SDK 9.0.320 was installed
in the dedicated workspace after checking Microsoft's published SHA-512; host
system .NET was left intact. The corrected full `make check` passed: 5,199 tests,
414 skips, followed by the remaining make targets. The skips are not native-tool
acceptance; dedicated image smokes are recorded separately.

## Builder and network recovery

The owner selected Kali1. A fresh trusted SSH connection verified x86-64,
Docker 28.5.2+dfsg4, native Linux storage, 158 GiB initially free, approximately
10 GiB available RAM, and no running containers. The owner added `lolman` to
the Docker group; a fresh session verified access.

The first four build attempts failed before compilation because kalitorify's
transparent-Tor firewall rejected DNS requests to the configured LAN resolver.
Small builds proceeded using public digest-verified base images and hash-locked
wheelhouses transferred from the Mac. The owner then explicitly requested
removing Tor routing. The installed `kalitorify --clearnet` restored normal
rules/DNS and stopped Tor; the idle Docker daemon was restarted to recreate
its network rules. Host and container HTTPS both returned HTTP 200 from PyPI.
Pre-change firewall rules and failed build logs remain in the private work
receipts. No keys or credentials were copied into an image.

The owner subsequently authorized deleting old build data to restore space.
Cleanup removed unused Docker build cache, a superseded CAD/Kit image,
downloaded apt/pip caches, and 50,034 files in two old validation copies only
after each matched the retained checkout by SHA-256 (7,867,077,208 bytes).
The deletion receipt lists retained counterparts. Unique files, simulation
results, datasets and model weights were preserved. Free space recovered to
approximately 65 GiB before the next AI build. Docker's reported cache total
includes shared storage and is not the same as physical disk space reclaimed.

Kit's final runtime-only image is 6,026,321,249 bytes, compared with
14,196,552,367 bytes for the initial build image. Its packaged EGL NVIDIA ICD
addresses the prior GLX configuration gap, but still requires GPU execution.
Kali1 exposes Intel Iris Xe graphics only; it cannot validate NVIDIA kernels,
native Kit rendering or streaming. OpenCFD v2606 passes its packaged cavity
solver check after adding the matching tutorial package to the runtime image.

## Compatibility decisions

| Runtime | Selection | Reason |
|---|---|---|
| Standard-library metrology/review | Python 3.15.2 | New-generation synthetic workload smoke checks pass |
| Warp | 1.19.0, NumPy 2.5.4, Python 3.15.2 | Offline CPU analytic geometry witness passes; CUDA remains untested |
| USD BRep | 1.0.1, Python 3.12.16 | Latest package is unchanged and requires 3.12; bundled USD stays isolated |
| OV CPU | ovphysx 0.7.0.74035321, ovstage 0.3.0.1791986420 | Matched dependencies, external PhysX schemas and `destroy()` lifecycle |
| Scan preparation | NumPy 2.5.4, trimesh 5.2.0, SciPy 1.18.1 | Updated lock; existing synthetic segmentation workload retained |
| CAD | build123d 0.13.0 and CadQuery 2.8.0 in separate environments | build123d needs OCP proxy >=8, CadQuery needs OCP <8; combined resolution fails |
| Content Agents | 0.6.2 with its upstream runtime locks | Service locks require OVRTX 0.4.1 and OvPhysX 0.4.13; newer standalone libraries are a separate candidate |
| Reconstruction | CUDA Docker 13.4.3, COLMAP 4.2.1, GLOMAP 1.2.0, Blender 5.2.3 | CUDA 13.5 toolkit exists but requested Docker tag is absent; native build and offline CPU smoke pass; GPU validation pending |
| Foundation OpenFOAM | 14 candidate | Existing Foundation 13 solver evidence remains unchanged; no automatic physical acceptance |

The OpenFOAM candidate uses maintenance package `20261008` and ICengines commit
`8bba57f7e004c57d3a36b6df0f972bcc7c4c82a1`; serial and two-rank MPI synthetic
solver checks passed. The new SimReady workflow also exercises two CAD-to-USD
conversions and compares their bytes through the existing preflight contract.
Local derived images use generation-specific parent tags during development;
receipt image IDs identify the actual build. They are not published digest locks.

CAD now includes source-built CalculiX 2.23. Analytic displacement and heat-flux
checks pass without network access. PrusaSlicer 2.9.7 now builds from pinned
source and passes the offline synthetic slice; this does not qualify a physical
printer. OpenSCAD 2021.01 is
confirmed latest stable, rather than an upgrade gap.
The official CalculiX 2.23 Linux binary failed `ldd`/execution because it requires
`libgfortran.so.4`; the candidate builds the pinned source with current libraries.

The CGAL 6.2.1 toolchain passes an analytic distance check, and the separate
analysis image passes all five existing envelope self-tests. Its purpose-built
toolchain does not replace the historical CFD diagnostic environment. The
nineteen phases in `workflow-coverage.json` remain unexecuted engineering work.

Managed PicoGK/ShapeKernel compilation, native runtime compilation and the
independent voxel witness pass on .NET SDK 10.0.403. The dependent M64 image
also passes its offline synthetic geometry and Python mesh checks.
PhysicsNeMo 2.2.2 retains Torch 2.10/CUDA 12.8 because the required PyG extension
wheels are available for that combination. The newer PyG index lacks the same
scatter/sparse/cluster extensions; a newer Torch version is not yet a qualified
replacement for this image.

The generic uv Linux target assumed glibc 2.28 and initially rejected valid
OCP, OV and PyMeshLab wheels. Resolution now explicitly targets Debian
bookworm's glibc 2.36. Resolution success is not an execution result.

The old metrology/review smoke scripts require Python 3.12 explicitly. Separate
copies change only that declared interpreter expectation; all original checks
remain. The scan smoke copy changes the two upgraded package expectations.
The topology application also contains an exact NumPy guard; its separately
named source copy changes only 2.2.6 to 2.5.4. Historical sources are untouched.

## Dependency gaps found

| Evidence | Finding | Treatment/status |
|---|---|---|
| `twins/964-chassis/monocoque/omniverse/kit-review.md` | Compute image lacked the native Kit editor; two retained runtime layers had to be transferred | Kit-inclusive replacement still pending; do not call standalone OVRTX an editor |
| `twins/964-chassis/monocoque/omniverse/native-review-20261029/README.md` | GLX Vulkan initialization failed; EGL ICD worked on the actual driver | Package a separate headless ICD and test on a GPU before declaring the issue closed |
| `containers/picogk-station-hotfix.Dockerfile` | Renderer cache/MDL directories needed worker write access | Carry these permissions into replacement station image and test as worker |
| `docs/reports/SOFTWARE_STACK_REVIEW_20260927.md` | CAD print screens depended on externally mounted shapely/rtree/networkx | Added explicitly to new CAD requirements |
| Actual cadsim rebuild | `COPY templates` references a directory that no longer exists | Candidate copies `catalog/templates` to the matching installed path |
| Actual dependency resolver | Latest build123d and CadQuery cannot share one OCP environment | Separate `/opt/venv` and `/opt/cadquery`; independent STEP readback smoke |
| Actual OV build | Old `PhysX.release()` is not the new lifecycle API | New smoke uses `destroy()` and includes external schema distribution |
| Actual Content Agents 0.6.2 build | Rendering API now needs in-tree `usd-cli`, unavailable on PyPI | Install the component explicitly from the same pinned upstream checkout |
| JAX-FEM 0.0.12 source and installation guide | Solver imports PETSc and Basix, absent from the old PhysicsML recipe's explicit dependency closure | Isolated replacement build adds PETSc/petsc4py 3.26.1 and Basix, with an analytic Laplace solve; pending |
| Official vLLM 0.33.0 image | `pip check` finds mixed OpenTelemetry versions and the intentional NCCL override | Latest LMCache 0.5.6 caps API at 1.40.0, so match exporter-common 0.61b0 to that series; exact upstream NCCL 2.31.2 exception is explicit and all other mismatches fail; GPU collectives untested |
| `docs/reports/M64_PARALLEL_CAD_CAMPAIGN_20260928.md` | Linux OpenMP was installed before mesh runs | Require libgomp in replacement meshing images and exercise imports without host packages |
| `docs/reports/M64_MESH_VOLUME_TOOLCHAIN_20260928.md` | DelOptim precision build and isolated delmesher/netgen/wildmeshing environment | Dedicated replacement still pending; CAD import smoke does not cover these meshers |
| Actual USD BRep smoke | `pxr` module-load warnings despite successful BRep roundtrip | Retained warning; do not inject incompatible `usd-core` or claim full USD validation |

Coverage is explicitly bounded: October 29 native review and its preparation,
station hotfix recipe, September stack review, and new build failures have been
reviewed. A complete census of all private Vast logs is not yet established.
The October 28 head campaign document is preparation, not an executed run.

## Running a prepared build

Run from an allowlisted source context on Kali1:

```sh
STACK_RECEIPTS="$HOME/porsche-stack-rebuild-20261105/receipts" \
  bash containers/stack-20261105/build-one.sh warp-geometry
```

Offline recipes require `wheelhouse/<runtime>` and, for OV/scan, `debhouse/common`
in the context. Wheels are checked against committed hashes. The offline base
override `STACK_PYTHON_BASE=stack-input/python:3.15.2` (or `3.12.16`) refers to a
transferred official image; record and compare its image ID before use. The
default recipe retains the upstream digest. Set `STACK_BUILD_NETWORK=default`
only for online build steps such as apt; runtime smokes remain network-disabled.

Every attempt gets a fresh receipt directory: recipe hash, base identity when
overridden, build log/exit code, image ID/architecture/size, bounded offline
smoke output/exit code, and start/end times. Build failures are not overwritten.
No image is pushed or promoted by this runner. Do not use host-mounted Python
packages or install dependencies during a smoke run.

## NativeCAD

Official MCP 0.29.0 tarball SHA-256:
`1a3df3770eac1df6b6c8b83385d1c88980366e1811ce6f065a5c361d682b794a`.
Installed in a separate versioned local directory with npm install scripts
disabled. A separate MCP process reported 0.29.0 and produced a synthetic
60 × 40 × 15 mm box matching independently calculated volume 36,000 mm³,
surface area 7,800 mm² and bounds. The Codex entrypoint now selects the new
installation; the existing chat connection was rechecked and still reports
0.26.0, so it needs restart. The old installation is retained. No private
geometry was used. Independent CadQuery STEP and trimesh STL readback now pass:
valid/watertight geometry, 60 × 40 × 15 mm bounds and 36,000 mm³ volume.
The rebuilt PicoGK voxel bridge also passes on that STL: at 0.5 mm voxel size,
volume is 35,918.418 mm³ (0.227% error, below the predefined 2% tolerance), and
bounds agree within the 0.5 mm tolerance. `nativecad-verification.json` records
the export hashes, image identity and independent expected values. This is a
synthetic interoperability check only. The free-tier failure-reporting
condition remains.

Sources: [NativeCAD manifest](https://featureboard.ai/nativecad/releases/latest.json),
[release notes](https://featureboard.ai/nativecad/web/releases),
[Warp](https://nvidia.github.io/warp/stable/project/changelog.html),
[OV migration](https://nvidia-omniverse.github.io/PhysX/ovphysx/latest/changelog.html),
[kalitorify](https://github.com/brainfucksec/kalitorify).

## Completion gates

Keep #404 open until every inventory row has an explicit build/test result or
an approved exception, all required runtime dependencies are included, and
repository checks pass. A resolved lock, built image, GPU render and physically
qualified part are different outcomes. Never mark unbuilt images complete.
For the 962 workflow retain all nineteen phase IDs from
`twins/962-cylinder-head-f0/workflow-contract.json`; this software rebuild does
not execute or admit any engineering phase, approve a rental, or qualify metal.

The F40/F41 Vast wrapper migration is incomplete. An automatic secret-access
approval hook rejected the proposed versioned recipe/lock transformation,
including a subsequent exact-path edit, although it requested repository
artifacts rather than secret storage. The incomplete F40 copy was withdrawn;
no replacement wrapper is admitted to the runner. Original wrapper locks and
security checks remain intact.
The current Bookworm OpenSSH package closure was independently refreshed and
still selects 9.2p1-2+deb12u10; package version age alone is not a missing update.
