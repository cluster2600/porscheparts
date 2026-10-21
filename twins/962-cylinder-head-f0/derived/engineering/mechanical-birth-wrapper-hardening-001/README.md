# Later portable-wrapper hardening and runtime-resolution probe

This addendum preserves the earlier mechanical witness capsule unchanged.
The current portable wrapper executes the explicitly checked
`/opt/moose/bin/moose-opt` path inside its read-only runtime. It rejects false
input/runtime invariance flags, nonzero native status, the wrong target digest,
a missing source banner or fewer than six equilibrium solves before numerical
assessment. Fifteen focused tests pass, including a mocked complete wrapper
run and changed-input refusal. No numerical native solve was repeated.

The original successful run used bare `moose-opt` after `. /environment`.
It checked the expected target's digest and recorded a matching source banner,
but did not record original process execve resolution. The separately named
postrun probe uses the same read-only/no-network startup and resolves that
name to `/opt/moose/bin/moose-opt`, with the expected binary SHA-256. It also
records the exact `/environment` digest. This corroborates current startup
resolution; it does not manufacture original process attestation. The probe
ran for 0.069 s and did not execute a numerical case.

The original capsule retains its earlier wrapper/test snapshots and original
13-test result. This addendum identifies the current wrapper and 15-test source
separately. The original thermal/constitutive/mechanical values, references,
tolerances, native inputs and outputs remain unchanged. No physical material,
head, LPBF process or manufacturing qualification follows from these checks.
