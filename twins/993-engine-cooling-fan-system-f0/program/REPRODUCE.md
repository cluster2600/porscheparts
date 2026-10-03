# Reproducible commands

[Program](../README.md) · [Calculation status](EXECUTION_20261003.md)

Run from the repository root. Scripts refuse to overwrite their outputs;
choose fresh output directories. New scripts audit the scan privately and
existing receipts; they create no functional model from unknown dimensions.
CI uses Python 3.12, NumPy 2.2.6 and Matplotlib 3.10.8.

## Program checks

```sh
make fan-program-check
make check
python3 scripts/check_doc_links.py --strict
git diff --check
```

The first check needs neither solver nor GPU. `make check` includes historical
Docker audits of the 917 cylinder head; an absent runtime must be reported,
never counted as a passing test. Scan tests require NumPy.

## Private local scan

With Python and NumPy, reference the user's file without copying it into a
versioned path:

```sh
python3 twins/993-engine-cooling-fan-system-f0/source/audit_private_scan.py \
  "$PRIVATE_SCAN" work/fan-scan-audit-new/report.json
```

The report contains private coordinates: keep `work/` ignored and do not
publish previews. The script neither repairs nor rescales. Synthetic tests
need neither scan sources nor supporting purchase evidence.

For the reversible preparation copy, still private:

```sh
python3 twins/993-engine-cooling-fan-system-f0/source/prepare_private_scan.py \
  "$PRIVATE_SCAN" work/fan-private-preparation-new \
  --expected-sha256 244d4caeb2c4ac4a692b650ec9d766bee2a8124335a0236a55a1d30c1b2b98ba
```

This command only normalizes global pose and removes exactly zero-area faces.
It preserves holes and any relative alignment error; it rejects input that
does not match the intake digest.

## Models and variants

PicoGK commands/dependencies for the reconstruction and variants remain in
[REFERENCE_REBUILD](../REFERENCE_REBUILD.md) and
[ORGANIC_BLADE_STUDY](../ORGANIC_BLADE_STUDY.md). Use their editable parameters;
retain `generation.json`, source digest and mesh checks. Exporting STEP from a
surface would not establish missing datums. The 42° candidate and corrected
CFD workflow are at **ffe5ed00** in
[PR105](https://github.com/cluster2600/porscheparts/pull/105), with
[mesh evidence](https://github.com/cluster2600/porscheparts/releases/tag/fan-cfd-mesh-recovery-2026-10-02).
Do not run duplicate campaigns for the same variants.

## Audit completed CFD runs

```sh
mkdir -p work/fan-final-audit-new
tar -xzf twins/993-engine-cooling-fan-system-f0/results/program-20261003/cfd/native-receipts.tar.gz \
  -C work/fan-final-audit-new
python3 twins/993-engine-cooling-fan-system-f0/source/audit_completed_cfd.py \
  work/fan-final-audit-new/control-full-frame-flow work/fan-final-audit-new/control-audit.json
python3 twins/993-engine-cooling-fan-system-f0/source/audit_completed_cfd.py \
  work/fan-final-audit-new/pitch42-full-frame-flow work/fan-final-audit-new/pitch42-audit.json
```

Exit code zero means the receipt matches native data. Both flags
`integral_checks_passed` and `nonlinear_residual_checks_passed` remain false.
To rerun CFD, follow #105 commands and safeguards. This package holds final
evidence and conditions, not complete volume fields/meshes. Recovery from
campaign archives and a sufficiently sized runtime are still needed.
No threshold may be relaxed.

## Reproduce the modal calculation

```sh
mkdir -p work/fan-modal-new
gzip -dc twins/993-engine-cooling-fan-system-f0/results/program-20261003/modal/modal.inp.gz \
  > work/fan-modal-new/modal.inp
cp twins/993-engine-cooling-fan-system-f0/results/program-20261003/modal/preparation.json \
  work/fan-modal-new/preparation.json
cd work/fan-modal-new
OMP_NUM_THREADS=4 ccx modal > log.ccx 2>&1
cd ../..
python3 twins/993-engine-cooling-fan-system-f0/source/summarize_modal_screen.py \
  work/fan-modal-new work/fan-modal-new/summary.json
```

The original run used CalculiX 2.17 in the existing image
`sha256:1dc508c2bfab4d9911707fbfd9cacdf43faf84956a1502805194e3e70e18ae68`.
The exact deck suffices to reproduce this calculation without the scan.
To prepare another case from an **audited centrifugal deck of the same model**,
use `twins/993-engine-cooling-fan-system-f0/source/prepare_modal_screen.py SOURCE_INP NEW_DIRECTORY --modes 12`.
This produces unprestressed modes; do not call it Campbell analysis.

## LPBF and OpenUSD asset

Geometric, thermal and sensitivity commands are in
[ORGANIC_BLADE_STUDY](../ORGANIC_BLADE_STUDY.md). Supply
[zrapid-print-process.json](../zrapid-print-process.json); identify material,
machine, orientation, exact source and assumptions. These calculations are
not a machine program, do not predict qualified distortion and authorize no
manufacturing.

Open `program/fan-program.usda` in an OpenUSD-compatible application. With the
available `usd-core` 26.8 runtime, reproduce composition under a **new name in
the same directory** to retain relative references:

```sh
python3 twins/993-engine-cooling-fan-system-f0/source/build_program_asset.py \
  twins/993-engine-cooling-fan-system-f0/program/fan-program-reproduction.usda \
  work/fan-usd-reproduction-new.json
```

Solver outputs stay in their own directories with conditions/digests.
Opening the asset does not simulate mechanics or fluid flow. Kit-CAE and RTX
rendering are separate stages to verify in a compatible runtime when an
authorized GPU resource is available.
