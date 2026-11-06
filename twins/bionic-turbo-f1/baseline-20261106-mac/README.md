# Mac runtime baseline revision — 6 November 2026

Additive revision for #394 and #579. The frozen
[parent baseline](../baseline-20261106/README.md) is unchanged. This revision
binds new observations and the precision-16 generator to the existing gate
validator; it preserves the full evidence inventory, comparison contract,
prohibitions and all downstream gates.

## Observed runtime

Both pinned images and the preserved source volume are present on the Mac.
All four previously missing executable hashes were read from the exact OpenCFD
image using an isolated read-only transient container. No mesh or solver ran;
no existing container or volume was changed. The recurring automation is paused.
Kali's hostname failed to resolve, but a connection to the documented direct
IPv4 endpoint succeeded with strict host-key checking: kali1, x86_64, Docker
28.5.2+dfsg4. Neither host had running containers or matching OpenFOAM processes.
Kali's ext4 filesystem reports 100% use with only 111,352 KiB available; no
checkout or build was started there.

The [runtime readback](runtime-readback.json) supplies these observations.
The new runtime matrix retains historical claims with their original receipts,
and adds current Mac availability and executable hashes. Unknown tools remain
unknown; this readback does not qualify a solver or a complete CFD case.

## Additive generator revision

[`prepare_case_v2.py`](../cfd/prepare_case_v2.py) retains the complete historical
source with exactly one change: field `writePrecision` is 16 instead of 12.
The old generator stays byte-for-byte frozen. The new execution-contract pin
names v2 explicitly; no existing caller is silently redirected. Time precision
and numerical formatting elsewhere remain unchanged. This is not binary64
conversion qualification under #397.

## Gate evaluation and verification

```sh
python3 twins/bionic-turbo-f1/baseline-20261106-mac/baseline.py check
python3 twins/bionic-turbo-f1/baseline-20261106-mac/baseline.py evaluate
python3 -m unittest discover -s tests -p 'test_bionic_turbo*baseline.py'
python3 -m unittest discover -s tests -p 'test_bionic_turbo_precision16_revision.py'
```

Both parent and revision pass `check`. The unchanged gate evaluator returns
`may_open: true` with no reasons for **G01-baseline-frozen** and
**G01-execution-contract** against the new attestations. This evaluates the
inventory and software identity contract only. The ledger deliberately does not
promote any gate to `engineering_passed`; formal gate acceptance and downstream
execution remain separate from this readback.

All 28 focused tests pass: 22 historical baseline tests, three Mac revision
tests and three generator tests. They verify frozen-source identity, every
generated dictionary across three mesh levels and both rotation signs,
publication hashes, matching attestations, rejection of substituted binaries
and generator hashes, and unchanged downstream/release states. The generator
publication test mocks surface admission and makes no claim about real geometry.

## Next action

Review and accept the two G01 evaluations, then prepare #395's bounded local
recovery plan. Resolve Kali capacity before substantial transfer/build work.
Do not run PR229, case 084 or a downstream solver study on the strength of this
readback. Physical correlation, fabrication and release remain closed.
