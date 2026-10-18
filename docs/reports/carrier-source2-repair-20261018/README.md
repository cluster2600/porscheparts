# STOCK source 2: repaired envelope with 22 unknown faces

On 18 October 2026, one bounded sealer-only invocation returned **RC0** and
packaged a separately versioned finite-distance geometric envelope. ROOT then
independently reconstructed the complete semantic proof and its serialized
bytes from all three immutable NPZ inputs. The result retains **22 unknown
faces**, with no positive parent or anchor assigned to them.

This report concerns the old **STOCK** process inputs: editable BREP
`42da92cc…` and surface STL `433c85bf…`. Their complete identities are in
[provenance.json](provenance.json). It supplies no admission for the later
`d64…` mechanical candidate, region/support geometry, scan vectors or build file.

| Actual result | Evidence |
|---|---|
| Sealer-only attempt: tool handle 89852, RC0, 115.882 s overall | [Actual tool terminal](evidence/actual-tool-terminal.json) |
| One owned seal scope: RC0, 109.376 s within its unchanged 120 s limit | [Independent ROOT closeout](evidence/root-final-seal-review.json) |
| V3 geometric/finite-distance scope, 22 semantic unknowns | [Seal assessment](evidence/seal-assessment.json) |
| Whole canonical identities, full lookup/map hashes and unknown roster rederived | [Semantic proof](evidence/semantic-overlay-proof.json) |
| 3,094 local and 3,098 remote pins; 100 retained outputs; owned scope and PID/PGID absent | [Independent ROOT closeout](evidence/root-final-seal-review.json) |

The invocation used the reviewed source and [explicit ROOT authorization](evidence/application-GO-ROOT.json).
Its original limits remained 2 CPU, 4 GiB, no swap and no network for the seal
scope; outer/controller limits were 3,600/3,200 s, CPU3,400–3,401 s and cleanup
10+10 s. Geometry, composed-distance and independent audits were closed
read-only dependencies. None was rerun during sealing.

## Why a separate semantic contract was needed

The original strict-12 reader refused the final mesh because exact oriented
triangle identity failed. Its acceptance remains false; the
[retained strict refusal](evidence/prior-strict12-refusal-ROOT.json) is unchanged.
Testing every final triangle found 12 mismatches, including one
repaired triangle that became five final children; none was merely a cyclic or
reversed corner order. See the [all-triangle diagnostic](evidence/triangle-diagnostic-ROOT.json).

Exact Fraction projection did not establish a full tiling for that five-child
group. Its positive residue in reference barycentric area was
`1122096682589 / 3202429639654286329984`. The
[projection diagnostic](evidence/exact-projection-diagnostic-ROOT.json) preserves
that result. No epsilon, continuous-coverage claim or primitive identity was
substituted for the failed proof.

The new contract rederives unknowns as the union of 15 original changed-parent
descendants and seven newly changed final faces. Every face asserted positive
still passes the original exact oriented-triangle test. All 22 unknowns expose
semantic raw/source/source-face `−1` and empty positive parent CSR. Native
geometry, native audits and native labels remain immutable; unsupported labels
are retained as history. Unknown faces receive no implicit plate-floor anchor.

All original repair, raw-CSR, native intersection, topology, positive-volume,
finite E/D, exact radical inequality, frozen-bound and contact gates remain.
The composed and independent audits had passed before sealing, including zero
remaining contacts. The accepted scope is explicitly
`prism-envelope-native-audit-v3-semantic-overlay22`;
`strict12_reader_passed`, continuous coverage and process-anchor admission
remain false. This is no physical, strength or manufacturing qualification.

## Verification and retained evidence

Run the compact evidence check from any working directory:

```sh
python3 /path/to/carrier-source2-repair-20261018/verify.py
```

It verifies the complete report inventory, nine byte-exact evidence copies and
their receipt joins. It performs no numerical reanalysis, geometry operation or
runtime import. [Source review](evidence/source-review-ROOT.json) and
[provenance](provenance.json) record the authorities. Full mesh arrays, work-job
outputs and installed runtimes remain external to this compact report.

A separately frozen cache correction would read the immutable patch changed
mask once before its per-face loop. It remains SOURCE-only and unapplied in
`work/carrier-stock-source2-semantic-overlay-preparation-002`. The successful
application above used the original reviewed reader. No repeat, default-library
change or further admission is implied by that optional future source change.
