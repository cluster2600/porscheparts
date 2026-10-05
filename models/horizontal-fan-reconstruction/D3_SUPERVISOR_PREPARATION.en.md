# D3: exact supervisor prepared and tested, without native execution

[Study home](README.en.md) · [D3 diagnosis and initial protocol](D3_ESTABLISHMENT_DIAGNOSTIC.en.md) · [Latest native D2 result](D2_COMPLETION_EXECUTION.en.md)

The supervisor is prepared for two sequential restarts of the same native
1020 checkpoint: `control015` with pressure relaxation 0.15, then
`candidate005` with 0.05. Each branch contains exactly twenty SIMPLE iterations,
1021–1040, on the four original partitions of the 680 596-cell mesh.
SIMPLE iterations do not represent twenty physical time steps. Mesh,
conditions, other parameters and initial criteria remain identical. The
current state is **prepared and tested without a solver**: no solver, container
or native 1040 result was created for this preparation. No resource is reserved
by this work.

## Executable capsule and independent checks

The [frozen capsule](parameters/D3-supervisor-reviewed-capsule/capsule-manifest.json)
contains thirteen original or already verified sources, configurations and
private-input hashes. Native fields remain private. Its SHA256, which must be
supplied to the launcher from an independently reviewed reference, is:

```text
e72db463f7f2feaec1ba7d53cfc2472b493e0ca9b89fe1ff01289246d094213f
```

The [actual copy check](results/runtime/D3-supervisor-input-copy-audit.json)
verified 179 prepared input files, 64 copies of MPI 1020 files and two sets of
eight serial 1020 files. The only differences between the branches' working
directories concern `system/fvSolution`. Derived protocols retain initial
criteria and require twenty consecutive native measurements, 1021–1040.
This check blocks all process creation; it is not an OpenFOAM execution.

The [19 supervisor tests](results/runtime/D3-supervisor-offline-tests.json)
check, among other things, refusal of an already active support or solver job,
actual container limits before gate opening, no restart after a partial branch,
evidence preservation and cleanup of only the owned container. Field fixtures
are synthetic; Docker and solver calls are simulated. The actual timeout test
uses a small owned Python process. Capsule imports and CLI help are also
actually executed. These tests qualify software controls, not their operation
with a new native solver or fan physics.

## Budget and launch admission

One overall **360 s** deadline covers both branches, preparation,
reconstructions, analysis, preservation and release. Each phase remains bounded
by its share and the reserve required by later phases:

| Phase | Maximum, s |
|---|---:|
| Preparation and admission | 30 |
| Control solver 0.15 | 90 |
| Candidate solver 0.05 | 90 |
| Two reconstructions, shared budget | 40 |
| Analysis | 45 |
| Preservation and archive verification | 60 |
| Release | 5 |

The ceiling is four CPU, with four verified distinct physical cores,
5 GiB combined RAM and swap, no networking and sources mounted read-only.
The Foundation OpenFOAM 13 image is the already available one, referenced by
digest; no download, installation or new access is planned. Admission requires
at least 7 GiB available memory and a verified CPU reserve at launch time.
An explicit coordination reference **after support work is released** is
mandatory. That reference does not bypass gates refusing concurrent calculation.

The read-only Kali1 check did not provide Docker access with the existing
account; no `foamRun` executable was found in its PATH. That runtime is
therefore unadmitted for this supervisor without resolving compatibility in a
newly coordinated scope. No privileged access or security change was attempted.
Kali2 remains the existing target to coordinate with the support-work owner and
other calculations.

## Reproduction

Local checks launch no solver:

```sh
python3 models/horizontal-fan-reconstruction/source/test_d3_supervisor.py
python3 models/horizontal-fan-reconstruction/source/verify_d3_supervisor.py
make fan-program-check
```

The [frozen launcher](parameters/D3-supervisor-reviewed-capsule/source/launch_d3.py)
is reserved for a compatible Linux amd64 runtime after explicit coordination.
The paths below denote the already verified private copies; the output
directory must be new. This is a future command,
**not executed in this preparation**:

```sh
python3 -B "$D3_CAPSULE/source/launch_d3.py" \
  "$D3_PREPARED" "$D3_PREVIOUS" "$D3_SELECTIONS" "$D3_CAPSULE" "$D3_OUTPUT" \
  --capsule-sha256 e72db463f7f2feaec1ba7d53cfc2472b493e0ca9b89fe1ff01289246d094213f \
  --coordinated-release "$D3_CONFIRMED_RESOURCE_RELEASE"
```

The capsule can be prepared again with the [builder](source/build_d3_capsule.py)
and checked with the [independent audit](source/audit_d3_input_copy.py).
A new capsule hash requires new review; previous evidence does not
automatically apply to it. Frozen sources and historical artifacts are not
rewritten.

## Interpretation and required evidence

Lower pressure variance under relaxation 0.05 could reflect slower numerical
establishment. Analysis requires the ten initial numerical checks and seven
additional steadiness checks for **both** branches. It also compares local
1020→1040 fields, backflow and the preceding native window. No threshold is
relaxed; declared admission in a report cannot replace the checks themselves.

Even an admitted pair would demonstrate neither physical unsteadiness,
domain independence nor an airflow or installed-cooling improvement.
A timeout or partial branch leads to preservation and termination, without
automatic extension or restart. New native execution, its verified archive
and release receipt remain the missing evidence.
