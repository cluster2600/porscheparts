# Public thermal-birth software evidence

**Hypothetical numerical verification only. Whole-head LPBF remains open.**
No physical alloy or process is calibrated by this fixture. Manufacturing
qualification and authorization are false in the [receipt](receipt.json).

The [accepted contract](frozen-contract.json) is an exact copy of the contract
used by all three passing native MOOSE runs. Its SHA-256 is
`099ca030b523d43ca8a666c3e7f3a23cdc139077fe6d2e3531c051372d5a0ee2`.
Material laws, geometry, reference rules, time levels and tolerances were fixed
before those runs. The two earlier setup refusals and their superseded
contracts remain separately identified; neither executed a thermal step.

| Time step (s) | Native steps | Independent checks | Maximum continuous energy error |
| ---: | ---: | ---: | ---: |
| 0.0100 | 40 | 23 588 | 1.3048% |
| 0.0050 | 80 | 46 788 | 0.6794% |
| 0.0025 | 160 | 93 189 | 0.3481% |

The error ratios are 1.920 and 1.952, meeting the frozen minimum of 1.4; the
finest result meets its frozen 1% limit. Checks use full nodal histories,
cell-property/source values, finite-box Gaussian power and nonlinear enthalpy.
The corrected discrete energy identity errs by less than 9.3 × 10⁻¹² J;
existing-node history and new-node birth-temperature errors are zero.
The original verification passed eleven focused reference/rejection tests.
The [later guard-hardening addendum](POSTRUN_HARDENING_002.md) records the
current thirteen-test suite and a separately identified checker snapshot.

The [source snapshots](receipt.json) distinguish accepted inputs and the
pre-native frozen field checker from the refinement checker added afterward.
That later checker applies the refinement criterion already present in the
contract. The portable reproduction wrapper was also prepared later and did
not produce the original runs. A later documentation correction fixes the
contract-digest attribution without changing immutable numerical evidence.

The [native-output hash manifest](native-output-hashes.json) binds each run to
its original native receipt, log, input/output files and verified complete
capture hashes. This capsule contains no private host/user paths, access
commands, runtime binaries, raw transport captures or raw thermal fields.
It introduces no new native run. The original receipt records review as pending at its creation. The
[later hardening receipt](postrun-hardening-002.json) now records the separate
software/evidence review and current checker state. It introduces no physical
qualification and does not replace the original provenance.
