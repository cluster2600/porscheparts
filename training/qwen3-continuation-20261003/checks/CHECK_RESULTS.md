# Frozen D snapshot: bounded native Linux check

The frozen D package and its two test files pass the full `make -k check`
dependency set on native Linux, exit status 0. The tested snapshot contains
137 files over base commit `09f2728a646d0cf6e30c07df28800f26454a5276`.
Its manifest SHA-256 is
`68114e5800bce9f9e961c8f8edd8837a52f8a96daeeb51f77dd7a5b37d6a1864`.

- Main unittest suite: 3,420 cases, including 194 optional skips, with no
  failures or errors. All 49 new Qwen tests pass: 41 continuation tests and
  eight native MLX controls tests.
- All other Make targets pass. Strict documentation links report zero broken
  links across 688 Markdown files.
- Elapsed time: 186.93 seconds. CPU affinity 10 and 11, two library threads,
  nice level 10 and `umask 022` were enforced. The 900-second time guard and
  1.5 GiB owned-process-group memory guard did not trigger.
- Sampled process-group peak RSS: 429,248,512 bytes (409.4 MiB). Linux child
  `rusage.maxrss`: 450,140 KiB (439.6 MiB). Preflight memory availability
  exceeded the registered 8 GiB gate, preserving the impeller reservation.
- Existing Python 3.13.15, NumPy 2.2.6 and Matplotlib 3.10.8 were reused without
  installation. The old checkout remains clean at its original commit.
- Every transferred source, receipt and weight hash, and the exact training
  file roster, were verified before and after the checks.

The neighboring `training/qwen3-next-preparation-20261003` package was excluded.
The local `NEXT_DATA_PLAN.md`, `next-data-plan.json` and `README.md` changed
during the check; their tested and subsequent hashes are explicitly retained
in `current-snapshot-diff.json`. No code, data, protocol, weight, outcome or
review file changed in that comparison. These later documentation edits and
the final commit require the final PR HEAD CI.

The sanitized `public-check-summary.json` contains all tested file hashes and
receipt hashes. Raw infrastructure evidence remains local in
`check-receipt.json`, `make-check.log`, `linux-ssh-execution.json` and
`snapshot-integrity-receipt.json`. The earlier 22-file successful check and
its launch history remain preserved in the parent directory.

This receipt establishes software-check results for this exact snapshot. It
does not measure model gain or establish scientific or manufacturing validity.
