# Kali native verification — 28 October 2026

Kali1 is reachable through **Thunderbolt IPv6** using the existing trusted SSH
host key. The IPv4 connection used by the earlier attempt still did not answer.
The working connection was recovered from the concurrent local session, then
independently verified here. No SSH service, authentication, route or host-key
policy was changed.

The [sanitized execution receipt](../../../benchmarks/free-tools/results/kali-20261028.json)
records actual execution, versions, commands, hashes and remaining blockers.
PR #297 is merged. This follow-up verifies the storage and Python stages on the
native Linux worker; full host acceptance remains incomplete.

## Measured results

| Stage | Actual result | Accepted scope |
|---|---|---|
| Host and resources | `kali1`, x86-64, ext4, UID/GID 1000, 12 logical CPUs | Host identity matched its existing trusted SSH key |
| Runtime | Separate CPython 3.12.11 environment; all 112 installed versions match the existing requirements lock | Existing Qwen and CAE runtimes unchanged |
| Mac → Kali transfer | Public pilot packet and private DVC object archive transferred over SFTP; archive SHA-256 verified before extraction | Five registered pilot inputs; no historical archive migration |
| Kali independent recovery | Restored from the persistent Kali store into a fresh DVC workspace/cache; all five SHA-256 identities match | Replica store is separate from disposable caches |
| Kali → Mac recovery | Returned the Kali store objects and restored them into another fresh Mac cache | Recovery used only the returned Kali objects; the original primary store remains intact |
| Focused tests | 32 tests: 31 passed, one explicit CloudCompare skip, zero failures/errors | Native Python tests; the infeasible optimization control deliberately prints a rejected optimizer result |
| SQLite FTS5 | 30/30 frozen retrieval/boundary cases passed; authorized PorscheFanatics identity reference appears in the production results | Retrieval and source attribution, not Qwen answer qualification |
| OpenTURNS | Indices 0.19942885009108358 / 0.8017120442305217 | Synthetic expected 0.2/0.8, unchanged absolute tolerance 0.03 |
| OpenMDAO | Optimum height 0.010455159171866592 m; independent target 0.010455159171494206 m; external replay passed | Synthetic constrained beam, unchanged relative tolerance 0.005 |
| Carrier admission | `blocked_engineering` from the frozen independent contract | No native carrier FEM solve, geometry replacement or optimization |

The worker inherited CPU affinity limited to two logical CPUs, a 4 GiB address
space limit, single-threaded BLAS/OpenMP settings and finite command deadlines.
The other session's CFD job and services were left running.

The controller's full `make check` ran 5,000 tests: two existing last-digit
floating-point failures, zero errors and 384 skips. The affected suites are
`test_993_cooling_impeller_we43_f1` and `test_993_fan_stator_alsi10mg_f1`; their
historical results and tolerances were retained. Strict Markdown verification
reported zero broken links in 1,865 files. Linux PR checks remain the separate
merge verification.

## Reusing the verified IPv6 connection

Use the actual link-local address and Mac interface scope from a verified
connection. A previously trusted host-key record can bind the new transport
address to the same host identity:

```sh
FREE_TOOLS_SSH_PEER='lolman@<verified-link-local-ipv6>%bridge0'
FREE_TOOLS_HOST_KEY_ALIAS='<existing-trusted-host-key-record>'
ssh -6 -o BatchMode=yes -o StrictHostKeyChecking=yes \
  -o ForwardAgent=no -o HostKeyAlias="$FREE_TOOLS_HOST_KEY_ALIAS" \
  "$FREE_TOOLS_SSH_PEER" 'hostname; uname -m'
```

Keep strict host-key checking enabled. A host-key alias selects an existing
trusted identity; it does not authorize an unknown or changed key. Recheck the
host and resources before execution. Link-local interface scopes are local to
the Mac and are not portable hostnames.

This run used native SFTP because the controller's `openrsync` is compatible
with rsync 2.6.9 and the optional adapter requires `--protect-args`. Only the
selected DVC object archive and metadata were transferred. Archives were checked
for absolute paths, parent traversal, links and special files, and their digests
were verified before extraction into fresh private directories.

After transfer, the existing restore command was executed on Kali:

```sh
<isolated-python> benchmarks/free-tools/storage.py restore \
  --metadata <private-artifact-root>/metadata \
  --workspace <private-artifact-root>/restore-native-new \
  --store <private-artifact-root>/store
```

The same command on the Mac used a new cache and the object store returned from
Kali. The machine receipt retains both restore reports and their five matching
input hashes. Private paths and raw logs remain outside Git. No object deletion
or DVC garbage collection was performed.

## Outstanding acceptance

The `lolman` session cannot access the Docker daemon socket. The bounded
noninteractive sudo probe returned **password required**. CloudCompare and
SALOME container execution on Kali therefore remains **unexecuted**. Their
earlier native Linux CI results remain valid for their tested image identities;
they are not Kali host receipts. No group, socket-permission or daemon change
was made. An administrator must provide authorized Docker access before running
the existing bounded image commands in the [runbook](IMPLEMENTATION_TEST_PLAN.md).

The carrier still lacks measured interfaces, verified loads and established
mechanical convergence. Its external component currently replays admission;
the requested numerical FEM baseline replay remains an outstanding integration
step. Documentary Qwen output remains unqualified; no model inference was
performed on Kali and the existing Mac geometry command was not changed. No
training, paid infrastructure, publication or manufacturing authorization follows.
