# 4 L head: bounded Vast campaign preparation

The owner authorized moving the next engineering iterations to a larger Vast
machine on 28 October 2026. This supersedes the local-only allocation for this
campaign; it does not change numerical or physical acceptance criteria.
No rental has been created. The spending ceiling is still awaiting the owner,
and the approved Vast wrapper currently receives HTTP 403 from OpenBao.

The preceding [flow dossier](FLOW_RESTART_FOLLOWUP.md) is now in merged
[PR #301](https://github.com/cluster2600/porscheparts/pull/301). Its original
GitHub validation run completed successfully. Seven CFD trials remain rejected.
A larger machine provides more computational capacity, not convergence proof.

## Software suite and execution order

Use the repository's [toolchain](../../docs/TOOLCHAIN.md),
[compute environment](../../docs/COMPUTE_ENVIRONMENT.md), and
[head engineering program](ENGINEERING_PROGRAM.md). Execute each stage when
its inputs exist; installing a package does not count as executing or accepting it.

| Stage | Repository tools | Next campaign action and acceptance |
|---|---|---|
| Geometry and bionic changes | PicoGK, ShapeKernel, LatticeLibrary, Fasteners | Keep the current metal master frozen during hydraulic diagnosis; generate later variants in fresh directories, with explicit interface assumptions |
| Surface inspection and repair | pymeshlab, Open3D, CGAL/libigl, trimesh | Inspect each changed surface for intersections, topology and deviations against its bound reference; retain rejected candidates |
| Volume meshing | Gmsh, MMG, native OpenFOAM mesh checks | Replay the admitted 635,132-cell mesh first; screen new variants independently before solving |
| Hydraulic reference | OpenFOAM Foundation 13, MPI, existing independent Python audit | Benchmark 4/8/16/32 ranks, extend useful runs, retain first-solve global residuals and the unchanged 1e-5 target |
| Thermal coupling | OpenFOAM CHT | Requires conformal metal/water interfaces and declared heat loads, fluid and temperature-dependent material properties; no accepted head CHT case exists yet |
| Strength and thermomechanics | Gmsh, CalculiX; existing MOOSE witnesses | Requires measured donor interfaces, contacts, preload and justified loads; hypothetical cases remain studies |
| Additive process | Existing Adamantine and MOOSE workflows; AdditiveFOAM runtime where qualified | Separate calibrated process/coupon studies from whole-head distortion and fatigue claims |
| Twin and results | OpenVDB, PyVista/ParaView, OpenUSD, SimReady, OVRTX | Real field plots after audit; physical VDB imports retain their original convergence gate; RTX is for review/rendering |
| Assistance and surrogate | Qwen; PhysicsNeMo | Qwen proposes bounded alternatives; PhysicsNeMo waits for accepted reference data and independent evaluation |

No scan acquisition or photogrammetry is run without a suitable, licensed input
dataset. No synthetic datum becomes an OEM measurement through this campaign.

## Machine selection and useful iteration rate

Target one verified host with **64 effective CPU threads, 256 GB RAM and
500 GB disk**, consistent with the existing
[engine-twin compute profile](../../deploy/vast/engine-twin/README.md).
Actual availability and total prices must be read again through the approved
wrapper. A 48 GB or larger RTX GPU is useful for Qwen/RTX stages; the present
Foundation 13 solver uses CPU MPI and has no qualified GPU acceleration path.
Do not buy extra GPU count as a substitute for CPU throughput.

Run identical checkpoint cases at 4, 8, 16 and 32 ranks, sequentially, capped
at 150 additional global iterations or 300 solver seconds each. Compare completed
iterations per wall second, resource usage and early residual histories.
Incomplete and timed-out pilots stay visible. More ranks need not be faster.
The retained numerical settings are unchanged, including first-order upwind;
a scaling result does not establish hydraulic accuracy.

Choose the useful rank count from measured throughput, then prepare a separate
long run with at most 20,000 additional iterations and 7,200 solver seconds.
Use independent recipe/mesh comparisons when the global residuals stall.
Do not silently loosen residual, mesh, pressure-stability or conservation gates.
Classical SIMPLE and consistent SIMPLE are separate recipes, not combined labels.

The [new preparer](source/coolant_flow/prepare_cloud_restart.py) verifies the
original case, mesh, checkpoint, history and log hashes. It copies the audited
case-023 **iteration 2200** fields into a fresh case, changes only the time range
and MPI partition count, and retains all physical and solver settings.
The [runner](source/coolant_flow/run_cloud_restart.sh) requires an absolute
campaign deadline, rechecks all prepared bytes, runs native mesh admission,
captures the actual solver exit code and bounds reconstruction.
The existing [independent audit](source/coolant_flow/analyze_restart.py) remains
the flow acceptance check. These new runner sources have software tests and
real-input preparation checks, but no native execution qualification yet.

## Rental preflight, cost and collection

1. Restore the existing narrowly scoped OpenBao Vast identity; verify with
   `openbao-vastai --auth-check`. Never use Keychain or export tokens.
2. Record the owner's total spending ceiling. Read account inventory, balance,
   offers, allocated CPU/RAM, hourly disk and transfer charges. Do not affect
   another workload. No live offer or price is claimed in this preparation.
3. Qualify a digest-pinned **Foundation 13** runtime with all required tools
   before paying. The old engine-twin compute image is a candidate only;
   the profile name does not prove solver availability or version. The
   `openfoam-engine-f35` lock targets Foundation 14 and is not a drop-in replay.
   Do not reuse a different workload's launcher merely to satisfy a price filter.
4. Replay the native analytical benchmark and establish cross-host agreement
   before extending the head case. Record image, package/build and input hashes.
5. Arm a compatible controller deadline/cost guard before the paid launch.
   Reserve startup, transfer and collection time. Budget includes compute,
   reserved disk, ingress/egress and cleanup reserve; a stopped instance may
   still incur storage charges. The solver timeout alone does not end rental.
6. Send only the bound source/runtime bundle and selected cases. Keep purchased
   scans, proprietary documents, credentials and unrelated repository files out.
7. Collect checkpoint fields, complete logs, audits, manifests and figures at
   each milestone. Verify SHA-256 and archive readability on the Mac and kali1.
8. After verified collection, destroy the owned instance and verify its absence
   through the existing wrapper. Keep a cleanup receipt. If collection fails,
   report that failure and let the agreed hard cost/deadline policy apply.

The [prepared-case receipt](derived/vast-preparation-20261028/preparation.json)
records the real local pilot inputs. `CAMPAIGN_DEADLINE_EPOCH` is required at
execution; it does not itself authorize or create a rental.
The [pilot archive](derived/vast-preparation-20261028/bundle.json) is 511,549,491
bytes with 140 payloads. Full archive and per-payload hash, size and CRC checks
pass on [both Mac and kali1](derived/vast-preparation-20261028/replicas.json).
The raw archive remains outside Git, in the worktree's
`work/962-vast-20261028/` directory and the existing kali1 station directory.

The three new software tests cover unchanged checkpoint/physics bytes across
the four MPI partitions, tampering and bounds rejection, and refusal to run
without an unexpired campaign deadline. The full 264-test head suite passes
in the isolated Python 3.12 environment, with seven skips; the system Python
3.10 run encounters the pre-existing SciPy native-library import failure.

Measured donor dimensions, combustion/SP95 knock limits, CHT, strength,
manufacturing process qualification and dyno validation remain open.
Manufacturing remains unauthorized.

Primary references: [Foundation 13 parallel execution](https://doc.cfd.direct/openfoam/user-guide-v13/running-applications-parallel),
[Vast Docker environment](https://docs.vast.ai/guides/instances/docker-environment),
[Vast storage](https://docs.vast.ai/guides/instances/storage/volumes).
