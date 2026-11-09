# Open-issue work — 6 November 2026

## Coverage and limits

The [inventory](open-issues-20261106.json) contains 111 unique open issues from
`cluster2600/porscheparts` at the initial live snapshot. The ascending search
was supplemented by an overlapping 6 November search to cover results beyond
the connector's first 100. Routing comes from tracker #582 and is explicitly
not an independent engineering verdict. Additional targeted issue/PR checks covered #4, #394–#395, #404–#406,
#417, #426, #452–#453, #458, #467, #579 and #607; this is not a fresh
acceptance audit of every issue.
This is not completion of all 111 issues. No issue was closed or merged.
Follow-up #607 was created after the snapshot, so it is listed separately.

## Delivered changes

| Issue | Result | Remaining acceptance |
|---|---|---|
| #424 | Owner chose freeze for all nine named data-only corpora; [ADR 0020 in PR #609](https://github.com/cluster2600/porscheparts/pull/609) records each directory | PR #609 awaits review and merge before GitHub closure |
| #581 | Owner chose a new English generation, preserving historical pins; [translation policy](../TRANSLATION.md) records it; [#607](https://github.com/cluster2600/porscheparts/issues/607) opened | PR #609 awaits review and merge; generation build remains separate in #607 |
| #394, #579 | [Mac runtime readback in PR #610](https://github.com/cluster2600/porscheparts/pull/610), four executable hashes, paused automation, Kali SSH/Docker verification, separate precision-16 generator | PR #610 binds the new attestations; G01 evaluates may_open, with formal acceptance and downstream work separate |
| #426 | [Fifteen grouped archival obligations](917-archive-pending-ledger-20261106.md) carried forward without editing archive | Owner disposition; no abandonment or execution inferred |

The sole open PR observed in the initial PR search was #602, translation phase 5 batch 1.
Its changes were not duplicated. Tracker #582's older ready-to-merge list is not
used as current PR status. ADR 0019 already permits contributed measurements;
those issues wait for admissible contributions, not a new digital-only decision.

## Verification

- Three new precision revision tests passed: frozen-source digest, all generated
  dictionaries across three mesh levels and both rotation signs, publication hashes.
- All 22 existing turbo baseline tests passed; `baseline.py check` reported OK.
- Runtime receipt parent/source SHA-256 values independently re-read and matched.
- `git diff --check` passed. Archive and historical evidence were not edited.
- `make check` failed at the unit-test stage on this macOS interpreter:
  **5,193 tests, 4 failures, 135 errors, 770 skipped, 286.137 seconds**.
  Missing NumPy accounts for many errors and the face-diagnostics failure.
  Other failures include `/var` versus `/private/var` path spelling in dashboard
  intake and exact floating-point comparisons in two intercooler tests. The run
  does not establish a qualified native-Linux result. Later Make targets did not run.

## Runtime blocker

Kali1 was verified through the documented direct IPv4 endpoint with strict
host-key checking and no agent forwarding. Docker 28.5.2+dfsg4 is accessible;
no containers were running. Its native ext4 filesystem reports **100% use and
111,352 KiB available**. No substantial checkout/build was attempted there and
nothing was deleted. Native-Linux verification and the new image generation
need adequate capacity. No provider rental or physical test was launched.

The remaining issues retain their own acceptance criteria: measured interfaces,
source rights, independent review, qualified runtimes and admitted upstream
results cannot be supplied by this inventory. Unexecuted items are explicitly
marked in the JSON; no inference of success is made from their inclusion.

## Continued execution

The isolated `.venv-check` now uses Python 3.12.13, the exact numerical test dependencies and the hash-verified native oracle. The two intercooler failures disappeared under the intended interpreter without changing numerical assertions. The dashboard test now compares the resolved capture path with `file.resolve()`; rejection checks remain intact.

The full unit stage passed **5,823 tests**, with **414 skips against the budget of 416**. The three new Mac-baseline tests were run separately, with all 28 turbo-focused tests passing. Later Make checks required regenerating the reports index and staging its new report targets for the tracked-file link checker; all remaining targets then passed with `make check -o test`. A final reports-index and strict documentation-link check also passed (zero broken links).

Independent PRs prepared, without merging:

- [#608](https://github.com/cluster2600/porscheparts/pull/608): dashboard path-test portability.
- [#609](https://github.com/cluster2600/porscheparts/pull/609): owner decisions for #424 and #581.
- [#610](https://github.com/cluster2600/porscheparts/pull/610): additive Mac turbo baseline and precision-16 source for #579 and #394.

The turbo revision now binds matrix, ledger and attestations. The unchanged validator returns `may_open: true` for both G01 gates; no gate is promoted to `engineering_passed`. Exact-head CI must be checked before treating a PR as ready. The overall backlog goal remains active.

## English generation and historical-output recovery

PRs #608, #609 and #610 now have successful exact-head CI and are ready for
review; none was merged here. [PR #611](https://github.com/cluster2600/porscheparts/pull/611)
adds the separate English F34b generation for #607. Its regenerated manifest
preserves all 2,570 planned cases, splits, numerical inputs and authority flags.
Six generation tests pass, as do 46 context tests with one host Cantera skip.
The actual image build and offline, read-only, non-root Cantera smoke passed
on Docker Desktop's Linux filesystem under amd64 emulation on an arm64 Mac.
Native amd64 workflow execution, integration with the parallel stack upgrade
and registry publication remain pending. The large manifest is outside Git.

For #417, [merged PR #594](https://github.com/cluster2600/porscheparts/pull/594)
already removed solver outputs and added a guard. The current tree retains
38 deck/initial-condition/record files; no further deletion was needed. All
52 removed files were recovered from the register's immutable commit, checked
against their individual sizes and SHA-256 values, then reread from a new
local TAR archive. The recovered payload is 564,489 bytes; the archive is
665,600 bytes with SHA-256
`e07665c40490ea8739f375074c8e6b857a13c558ed9e32f9cba9d705056dabf2`.
Nothing was uploaded or deleted. Deck placement and the private-release
destination remain pending. The existing register retains individual recovery
paths and hashes.
