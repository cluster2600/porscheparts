# Kali1 repository verification

Date: 2026-11-04. Scope: verify the public software/documentation source on the
native Linux worker after the Mac's Python 3.10 validation failures. This is a
repository check, not reconstruction, a head simulation or physical qualification.
The tested source is commit `df7d0982d6266907e0fc7ace1894bf196aeb0fc4`.
New CAD-chart sources have their own
[actual STEP/native checks](../935-source-shells-20261104/README.md).

## Transport, source and isolation

The existing trusted SSH identity was reused over Thunderbolt IPv6 with strict
host-key checking, batch mode and no agent forwarding. The actual worker reports
`kali1`, x86-64, ext4 and 12 logical CPUs; approximately 10 GiB available RAM and
167 GiB free disk were observed before execution. No service, route, DNS, group,
socket permission or system package was changed.

Kali could not resolve GitHub. The existing local repository cache also lacked
some historical Git objects. Fresh task-owned validation clones were therefore
populated through hash-checked SFTP transfers from the Mac: a commit-object pack,
the standalone changed-object pack and the required current tree objects. The
initial thin bundle could not be used with the incomplete cache; that failure
was retained. A batch object audit then found **zero missing current-tree
objects**, and checkout matched the exact commit with clean tracked source.
Existing caches and checkouts were read only. The new clones reuse cached blob
objects; they are not a separately complete historical repository archive.
No scan or derived private CAD was transferred for these repository checks.

The bounded runner uses two logical CPUs, one BLAS/OpenMP thread, a 6 GiB address
space limit and a 900-second deadline. It terminates the complete process group
on timeout and records the actual exit state, duration, peak child RSS, log hash
and tracked-file state. Result directories are private. All attempts use fresh
output paths, with earlier logs/source snapshots preserved.

## Runtime and environment findings

The existing isolated Python is 3.12.11, with NumPy 2.5.4 and SciPy 1.18.1.
The already installed portable .NET SDK is 9.0.320. Its directory is placed before
the system SDK only in the validation child environment, with an explicit
`DOTNET_ROOT`; no global installation or shell configuration is changed.

The first complete native test target ran 5,167 tests and reported 26 failures,
97 errors and 410 skips. The inherited `002` umask made fixtures/source writable
by the group, so security guards correctly refused them. The default system
.NET 6 SDK also could not compile the existing .NET 9 target.

A fresh private checkout and the existing .NET 9 SDK resolved those issues. The
next target ran 5,172 tests with one failure, no errors and 410 skips. Its `077`
test-process umask inadvertently turned a deliberately public `0755` negative
fixture into `0700`, so the expected privacy refusal could not occur. The source
test was inspected; no test or application guard was changed. The corresponding
17-test module passes with the normal `022` process umask. The final runner uses
that mask inside the already-private checkout and creates its result directory
as `0700`. Production safety rules are unchanged.

The [execution receipt](kali-verification.json) records the final outcome and
the 38-file private-manifest identity. The primary target ran **5,172 tests:
4,762 passed, 410 skipped, zero failures and zero errors**. Subsequent ten-test
contract and seven-test published-evidence checks also passed. The bounded run
took 235.04 seconds, with peak child RSS 687,248 KiB, no timeout and no tracked
source changes.

**Full native `make check` remains incomplete.** It stops at
`917-manufacturing-f37-lpbf-audit-check` because the existing Docker socket is
`root:docker` mode `0660` and this user is not in that group. The Docker command
returns 126; the overall Make invocation returns 2. No container audit ran and
no group, socket, daemon or privilege change was attempted. An authorized Docker
runtime is needed to execute that target and the remaining native targets.
Earlier failures remain distinct from this final, software-only outcome.
GitHub run `41866259218` independently completed successfully for the same tested
commit; Linux worker evidence and GitHub CI are separate attestations.

## Reproduction

Use a fresh exact-commit native Linux checkout, prepared under `umask 077` to
protect its source and parent directory. Set the existing verified Python and
portable .NET paths, then invoke the bounded runner with a fresh output path:

```sh
"$NATIVE_PYTHON" docs/research/935-kali-validation-20261104/source/run_repository_check.py \
  --repository "$NATIVE_CHECKOUT" --output "$NEW_PRIVATE_RESULT" \
  --commit df7d0982d6266907e0fc7ace1894bf196aeb0fc4 \
  --dotnet-root "$EXISTING_DOTNET9_ROOT"
```

The runner is supplied separately when testing the older exact commit, which
does not yet contain this report/runner. Bind its source hash and the actual
runtime paths in the job record. Do not reuse an existing result directory or
substitute a different commit while reporting the old identity. Keep strict
SSH verification and transfer hashes; failure to resolve a host does not justify
changing host trust or authentication.

The private validation bundle is
`~/Developer/PorschePartsArtifacts/935-kali-validation-20261104/`. It retains
the transfer packs/identities, bounded-runner snapshots, actual native logs and
reports, focused replay and final hashes. Public files contain aggregate results
and hashes only. No paid compute, real cloud lifecycle command, supplier contact,
fabrication order or engineering release is granted by repository verification.
All nineteen 962 engineering phases remain unchanged; no 962 campaign or phase
readiness is claimed by running the repository tests.
