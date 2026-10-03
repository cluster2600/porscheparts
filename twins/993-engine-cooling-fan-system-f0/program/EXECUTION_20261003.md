# Audit and execution record — October 3, 2026

[Program](../README.md) · [SHA-256 manifests](../results/program-20261003/manifest.json) · [Reproduction](REPRODUCE.md)

## Resuming without overwriting work

The mission used a dedicated branch from `origin/main` commit `807588d5`.
Uncommitted changes in the primary checkout and `codex/fan-qwen-local-chain`
were preserved. Neither checkout had `.agents/skills`; root instructions and
the installed NVIDIA skill were consulted. No private session journal was read.

[PR103](https://github.com/cluster2600/porscheparts/pull/103) is merged and
records rejected meshing attempts. [PR105](https://github.com/cluster2600/porscheparts/pull/105),
audited at `ffe5ed00`, remains a separate recovery effort: its repairs and mesh
checks progressed beyond this mission's initial context. Its uncommitted local
changes are not included here. The PR106 cylinder head is outside this program.

## Scan

The [intake record](SCAN_INTAKE.md) details the checks. The additional audit
preserved original OBJ indices, without vertex welding, repair, scaling or
export. It confirmed two components, 8,611 open edges and 26 zero-area
triangles. Missing units, calibration and identity block physics calculations
on this scan. Detailed results and previews remain private; provenance
supporting documents are not published.

## Completed CFD outputs from #105

Both cases already existed on their worker. At the October 3 inspection,
no `foamRun` or impeller monitor was running. Both logs end with `End` and
`Finalising parallel run`, at **2,000 iterations**. No solver is restarted
in this mission and no acceptance threshold is relaxed.

The [native receipts](../results/program-20261003/cfd/native-receipts.tar.gz)
retain logs, dictionaries, input manifests, MRF audits and integral outputs.
The [independent auditor](../source/audit_completed_cfd.py) recalculates the two
flow/torque windows and residuals from those logs, reproducing the
[control](../results/program-20261003/cfd/control-summary.json) and
[candidate](../results/program-20261003/cfd/pitch42-summary.json) summaries.

| #105 criterion | 36° control | 42° candidate | Unchanged threshold |
|---|---:|---:|---|
| Accepted mesh cells | 8,182,775 | 8,170,973 | Standard + extended geometry/topology |
| Maximum relative mass imbalance | 8.23e-6 | 4.80e-6 | < 1e-3 |
| Flow drift between windows | 4.37e-4 | 8.51e-4 | < 1e-3 |
| Relative flow amplitude | 5.89e-4 | 1.05e-3 | < 2e-3 |
| Relative torque amplitude | **3.36e-3** | **2.37e-3** | < 2e-3: **failed** |
| Maximum initial U residual | **3.64e-3** | **3.23e-3** | <= 1e-4: **failed** |
| Maximum initial p residual | **2.30e-2** | **2.14e-2** | <= 1e-3: **failed** |

Exploratory mean outlet flows are 0.387227 and 0.429768 m³/s, with 137.04
and 182.43 W transferred to the fluid. These are rejected numerical diagnostics,
**not a validated performance comparison**. They demonstrate neither improved
cooling nor installed engine airflow. Audits of the
[control](../results/program-20261003/cfd/control-audit.json) and
[candidate](../results/program-20261003/cfd/pitch42-audit.json) show that good
mass conservation alone does not establish convergence.

The model is an isolated impeller in an axisymmetric duct, whole-domain MRF,
**-3,000 rpm about +Z**, OpenFOAM **Foundation 14**. The alternator and engine
cooling circuit are absent. The steady field predicts neither noise nor
resolved vibratory loads. Wall resolution and mesh independence are unqualified.
No new CFD field rendering is fabricated from these mean values.

### Final field backup

Backup of both complete case directories to the Mac was authorized. Another
task deleted the worker before the transfer finished. The original interrupted
compressed stream is preserved locally; it is not a complete archive.
Recoverable files were checked individually against the worker's SHA-256
manifest, generated before deletion.

Of 913 control files, **897 files** were recovered and verified, including
**all 256 files from the 32 partitions at iteration 2000**, plus meshes and
dictionaries. Sixteen files are absent, including reconstructed global fields
at 2000. One incomplete file is retained separately without verified status.
None of the candidate's 913 files was recovered in this stream. Its final logs,
integrals, dictionaries and results had already been saved in the receipts above.

Reconstructing the control's global field from its native partitions could
be attempted without restarting its solver; this is not claimed as performed.
Check other backups before any new execution. Volume data and integrity
reports stay local and contain no private scan data. Losing worker access
changes neither convergence failure documented in the two native logs.

## Structure, rotation and modal analysis

The [existing centrifugal results](../results/organic/structure/reference-structure-50k/summary.json)
use a parametric reconstruction and assumed 10,000 rpm. They report a maximum
von Mises stress of 248.21 MPa and maximum displacement of 0.243 mm, with
`mesh_independence=false`. Organic comparisons retain their convergence failures
and bore peaks; no material/fatigue margin is inferred. Earlier
[Newton/PhysX rigid-rotation tests](../OMNIVERSE_DIGITAL_TWIN.md) check simplified
dynamics, not blade elasticity.

A new **unprestressed modal calculation** reuses the exact reference deck of
86,640 quadratic tetrahedra, with the digest in the published centrifugal
report. The preprocessor keeps mesh, material and bore restraint, replacing
only the centrifugal step with `*FREQUENCY` and requesting twelve modes.
CalculiX **2.17** finishes in **49.65 s** on Kali2 Linux amd64, in the existing
CAE image identified by SHA-256, with no network and limits of 4 CPU / 6 GiB.

[Modal report](../results/program-20261003/modal/summary.json) ·
[Compressed native frequencies](../results/program-20261003/modal/modal.dat.gz) ·
[Log](../results/program-20261003/modal/log.ccx) ·
[Compressed exact deck](../results/program-20261003/modal/modal.inp.gz)

The first two modes are **348.259 and 348.450 Hz**; the twelfth is
**1,870.084 Hz**. Values are positive, with no imaginary part, and the rad/s-to-Hz
check reproduces the output. This calculation has no centrifugal prestress,
gyroscopic term, bearing, belt, contact, measured temperature or damping.
It is not a rotating Campbell analysis. No safe/forbidden speed or fatigue
life is claimed.

## LPBF

The [ZRapid iSLM420DN / AlSi10Mg card](../zrapid-print-process.json),
[geometric screening](../PRINT_RELEASE.md) and thermal calculations at
[2 mm](../results/organic/e/thermal-2/thermal-summary.json) /
[1.5 mm](../results/organic/e/thermal-15/thermal-summary.json) are retained and
linked from the entry page. They belong to their own organic models.
Homogenized energy and sensitivities do not constitute a qualified industrial
stress/distortion simulation. None uses the private scan. No physical printing.

## Organized OpenUSD asset

[fan-program.usda](fan-program.usda) references the existing Turbo reconstruction
package. Its hierarchy separates reference, candidate material and results;
unknown components remain identified scopes. It declares `metersPerUnit=1`,
`upAxis=Z`, time in seconds, explicit rotation conversions, scan/field status,
reference digest and false physical-validation flags. The AlSi10Mg shader
presents a candidate material. No CFD or thermal field from a different
geometry is overlaid.

The [OpenUSD 0.26.8 audit](../results/program-20261003/usd-validation.json)
opens the composition and reopens it after export, comparing extents in meters
against existing geometric checks after mm-to-m conversion. It finds no
unresolved dependency or OpenUSD validator issue. The maximum extremum
difference is 8.24 µm **between two model representations**, below the 10 µm
numerical tolerance; this is not physical-part accuracy.

This is neither a new RTX calculation, SimReady-profile validation nor a
physically validated digital twin. Earlier renders and their conditions remain
in the [Omniverse record](../OMNIVERSE_DIGITAL_TWIN.md). Initial Mac Docker access
was blocked by confinement; a check outside confinement found **Docker 29.8.1**.
The historical F33 CAE image was absent locally. The initial result therefore
was not evidence that the daemon was absent. Kali1 has no authorized Docker
access; Kali2 does. Neither Kali host has an NVIDIA GPU. No new rental or
access/security change is made.

## Repository verification

`make check`, entry-page/link checks, diff and CI results are recorded in the
[verification report](VERIFICATION.md). They do not close the physical gates
still open in the [validation plan](VALIDATION_PLAN.md).
