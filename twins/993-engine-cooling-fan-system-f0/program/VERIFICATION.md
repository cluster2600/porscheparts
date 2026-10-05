# Publication verification

[Program](../README.md) · [Verification receipt](../results/program-20261003/verification.json) · [PR118 checks](https://github.com/cluster2600/porscheparts/pull/118/checks)

After complete research integration, `make check` finishes with **exit code 0**,
using Python 3.12.11, NumPy 2.2.6 and Matplotlib 3.10.8. The main suite runs
**3,375 tests**, with **193 optional skips**. All additional Makefile checks pass,
including the historical Docker LPBF audit and checks of program references,
digests and validation boundaries. Full logs remain private; the receipt records
the latest log's SHA-256. Tests requiring temporary Git repositories, loopback
or Docker ran with the necessary local permissions.

The **five scan/preparation/contour tests** and **six research tests** also pass
separately without skips. SHA-256 checks cover the twenty original research
texts; references and the index of 140 source records / 130 URL groups are
verified. A Git whitespace exception limited to one CSV's final blank line
preserves its original bytes. Strict links/anchors checks pass across
**687 Markdown files**, as does `git diff --check`.

Native integrals and residuals from both CFD runs were recalculated and confirm
rejected criteria. OpenUSD composition was generated twice with identical
reports and digests, without using the scan. Recovered files from the interrupted
CFD transfer were compared with the remote manifest: all 32 final control
partitions are present, not the candidate's complete fields. See the
[execution record](EXECUTION_20261003.md).

Public archives contain no scan, scan derivative, purchase evidence, private
host identifier or billing data. User metadata was removed from published
solver archives. Private originals/derivatives and recovery reports remain on
the Mac.

CI passed for [0ddd2238](https://github.com/cluster2600/porscheparts/actions/runs/37110927353)
and [ebd13b93](https://github.com/cluster2600/porscheparts/actions/runs/37111701807).
The [PR118 checks](https://github.com/cluster2600/porscheparts/pull/118/checks)
identify the tested commit for each subsequent update. PR118 was later merged
as `54a33c78`, with [main CI passing](https://github.com/cluster2600/porscheparts/actions/runs/37117710821).
These are historical verification results, not a claim that a later translation
has already passed its own checks. Passing software verification closes no
physical validation gate.
