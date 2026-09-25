# M64 — bounded handling of Vast HTTP 429

Date: 2026-09-07. **Offline** verification of the fix, then deployment of the
same diff to the installed wrapper, verified identical with `cmp`.
OpenBao permissions, identities and paths are not modified. No rental or
provider request was made by the unit tests. The later real attempt is
documented separately in `M64_VAST_EXECUTION_20260907.md`.

## Diagnosis and fix

Before the fix, `vast_request` immediately propagated any `SafeHttpError`,
including a temporary HTTP 429 rate limit on a GET read. The scenario is
reproduced by a mock raising this exception: not by a new paid call or a
secret retrieval.

The wrapper now retries only **Vast GETs with HTTP 429**: three waits of 20,
40 and 60 seconds, i.e. four attempts at most. The messages state only the
service, the attempt number and the delay: no key, no URL, no provider error
body. After exhaustion, a 429 error is still raised; no artificially empty
response or success is returned.

POST, PUT, DELETE, PATCH, other HTTP statuses and network unavailability are
not replayed. The OpenBao connection and the secret read stay outside this
loop, in their existing functions.

The SSH/READY availability polling of **SimReady only** goes from 2 to 15
seconds, still bounded by its remaining delay. The constant of the other
workflows stays at 2 seconds. Image, cost, uniqueness and cleanup checks are
not relaxed.

A heavily rate-limited read can take up to 120 seconds of additional waiting,
on top of the existing network timeouts. A verified external delay between two
calls can therefore be exceeded during the blocking call: this fix is not a
new real-time deadline guarantee.

## Checks

Command:

```sh
python3 -m unittest discover -s tests -p test_openbao_vastai_wrapper.py -q
```

Result: **87 tests passed**, including five new tests covering GET retry,
fail-closed exhaustion, no replay of mutations, other errors/offline and the
separation of the SimReady cadence. The waits of the new tests are mocked: no
real sleep or network access. The rental logs displayed by other tests of this
suite are synthetic fixtures.

This fix demonstrates neither the current availability of a Vast offer, nor
the success of a rental, nor the state of Omniverse, nor a cylinder head
simulation.

## Additional diagnosis: SSH pairing

After an `ssh_authentication_failed` failure was reported, an offline reading
of the code reveals another defect: `safe_instance` kept `ssh_host`
(potentially a proxy), but took the direct port `ports[22/tcp].HostPort` if
`ssh_port` was absent. A hybrid pair could therefore be passed to
`verify_simready_ssh_ready`.

Fix in the repository, then deployed identically (`cmp`): keep the complete
proxy pair if it exists; otherwise use `public_ipaddr` and the mapped direct
port together; otherwise leave both values absent. The existing format/port
and SSH identity checks stay active. No automatic fallback after an
authentication failure, no additional key, no host key relaxation.

Three additional tests cover the complete proxy pair, an absent or null proxy
port, and incomplete pairs. **90 wrapper tests passed** after the fix.
The normalized snapshot of the failed attempt does not keep the provenance of
the port: this defect is reproduced synthetically, but **is not established as
the cause of the paid failure**. No new live call or rental during this
diagnosis.
