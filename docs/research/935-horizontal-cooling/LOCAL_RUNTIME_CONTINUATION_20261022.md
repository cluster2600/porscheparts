# 935 local solver continuation: quadratic limits and OpenFOAM

This supplements the [conforming-rotor report](CONFORMING_ROTOR_20261022.md).
The [receipt](local-runtime-20261022.json) records the terminal quadratic attempt,
the separate OpenFOAM numerical witness and the source-commit CI results.
The entire 935 system remains unfinished; no result is a manufacturing release.

The [private delta archive](https://github.com/cluster2600/porscheparts-935-private/releases/tag/conforming-rotor-20261022-delta)
contains 287 new or changed entries, including the exact OCI blobs, and pins the
previous core archive as its dependency. Its 1,403,817,576 bytes were streamed
and checked against the manifest, mirrored and hash-verified on Kali1, and all
three GitHub asset digests were verified. Both bounded rotor attempts are
terminal; no paid instance was created by this continuation.

## Quadratic direct solve: both bounded attempts stopped

The unchanged C3D10 deck contains 4,100,825 nodes and 2,116,345 elements.
The isolated Mac CalculiX binary that reproduced the complete C3D4 solution
was retained. After the first 32 GiB stop, the second direct attempt received
48 GiB and a 1,800-second deadline. Its owned process group was terminated when
the measured physical footprint reached **48.1108 GiB**, after **1,088.31 seconds**.
RSS alone remained much smaller because macOS compressed memory. The private
native `proc_pid_rusage` monitor and the runner's separate RSS/time guard are
both retained. The supplementary monitor explains the SIGTERM; the runner's
`stop_reason: null` is not silently rewritten to suggest it made this decision.

Neither attempt produced accepted displacement/stress fields. There is no
quadratic convergence result and no reason to increase the local memory limit
again on this 64 GiB Mac. The next structural experiment needs a better analysis
mesh with measured approximation errors and thin-cell diagnostics, or a suitably
qualified larger host within the existing budget/lifecycle policy. No blade
thickness or validation threshold is changed to obtain a pass.

## OpenFOAM without the privileged Docker daemon

Kali1's Docker socket is unavailable to the task user, but unprivileged user
namespaces and Bubblewrap 0.12.0 work. Skopeo 1.22.0 and umoci 0.6.0 were downloaded
as pinned Kali packages and extracted into the private study folder; system
packages, daemon permissions and user groups were not modified.

The exact image from the existing F25 benchmark is fetched anonymously:
`ghcr.io/cluster2600/3dprinting993-mesh-cfd@sha256:a1db60cbf61bbcca52c171e50cab01ed0b6ec860b227e7c5fc50f7b809659b4f`.
The registry index hash matches and all twelve selected OCI blobs are verified
independently on Kali1 and after transfer to the Mac. No account credential is
read. A task-local signature policy limits the unsigned pull to this repository;
TLS and content-digest checks remain enabled.

[Skopeo](https://github.com/podman-container-tools/skopeo) transfers the image
without a running Docker daemon. [umoci's rootless extraction](https://umo.ci/quick-start/rootless/)
changes ownership/device metadata where an unprivileged user cannot reproduce
the privileged filesystem. That distinction is recorded. No claim of an
identical Docker runtime is made.

[Bubblewrap](https://github.com/containers/bubblewrap) executes the extracted
root filesystem read-only, with one writable case mount, an isolated network,
PID/user namespaces, cleared environment, a 64 MiB temporary filesystem and
all capabilities dropped. The live preflight observes OpenFOAM 13, host-matching
UID, `CapEff=0`, `NoNewPrivs=1` and only an unused loopback interface. The original
Docker cgroup PID limit and complete mount profile are not credited to this
different backend. The first preflight fails on a missing read-only mount point;
the second uses the image's existing `/workspace` directory. Both are preserved.

## Six independent numerical controls

The existing F25 generator, nine input decks, contract and analyzer are reused
unchanged. They define laminar planar Poiseuille flow with an analytical solution.
Three meshes (8, 16 and 32 cells) are each run twice through native OpenFOAM 13:
`blockMesh`, `checkMesh`, `simpleFoam` delegating to `foamRun`, and cell-centre
postprocessing. Each job has memory, CPU and wall-time bounds.

All six solves and both independent analyses pass the existing numerical
criteria. On the fine mesh:

- flow error against the analytical solution: **0.1953125%**;
- relative velocity L2 error: **0.1337213%**;
- observed spatial order: approximately **2.000000**;
- local continuity measure: **6.62e-19**;
- both repetitions have identical canonical metrics.

The initial controller finishes all six jobs but its final receipt writer uses
the wrong repeatability key. A separate recovery program rechecks every result
with the unchanged analyzer and constructs the receipt without rerunning solvers
or relaxing criteria. The failed controller, recovery source and outputs are
preserved. This qualifies this laminar numerical witness on the new backend.
It establishes no fan flow, rotor/casing interaction or 935 performance.

## Checks and next engineering work

The complete `make check` passed in [Linux CI on source commit da1462a1](https://github.com/cluster2600/porscheparts/actions/runs/39699757247),
including 4,771 unit tests (373 optional skips) and subsequent container checks.
The [Warp image build](https://github.com/cluster2600/porscheparts/actions/runs/39699757360)
also passed; publication was skipped. These results are distinct from the native
Docker permission failure and from the numerical solver results.

The next fluid step is a Foundation 13 case for the retained PicoGK rotor and
its explicitly provisional casing, with documented MRF region, stations,
operating assumptions and mesh/continuity/stationarity checks. Existing R0/V2/S1
curves do not transfer. Structural mesh convergence, real scale, interfaces,
transmission, engine installation and material/process qualification remain open.
There is still no accepted dataset for PhysicsNeMo or an optimized fabrication
package. No new Vast rental was created in this continuation.
