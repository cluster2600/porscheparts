# Bounded native monocoque review

This policy supports the existing OpenBao wrapper's
`launch-simready-validation-only` operation. It uses the same immutable
`simready-local-ai` image as the prepared 964 review, without starting an LLM
or Content Agents. The existing heavy-offer contract requires one RTX Pro
6000 WS, at least 80,000 MB VRAM, 24 effective CPU cores, 128,000 MB RAM and
500 GB disk. These are review resources; they do not qualify a structural
solver or the composite body.

The original engine-twin profile additionally requires 64 CPU cores and
256,000 MB RAM for its larger orchestration workload. When it returned no
offers, the existing validation-only profile provided a native review route
without changing that profile, the installed wrapper, or either parent guard.

The user approved **USD 5 total and 90 minutes maximum** on 29 October 2026.
The review guard applies those bounds, a 40 GB download allowance, 15 GB upload
allowance and a USD 1 cleanup reserve. The first offer disappeared before
arming; it was not rented. A fresh offer must be checked before each permitted
paid call. An uncertain paid call consumes its attempt and must be reconciled,
never blindly retried. Approval is not a renewable budget for repeated attempts.

`deadline_guard.py` loads the existing engine-twin guard by its frozen SHA-256;
that guard in turn verifies the frozen PicoGK guard. The review policy retains
exact label/image/ID ownership, an empty initial account inventory, tariff and
total-cost checks, five-minute cleanup reserve, monotonic time protection,
late-creation watching and signal-triggered cleanup. It accepts no sibling
exclusion. It only uses the approved wrapper's sanitized inventory, lookup and
destruction operations. No secret is read by the guard.

Before the paid call, create a private manifest and start this guard, verify its
live PID and readiness receipt against the manifest and installed-wrapper
hashes, and durably record the single paid attempt. The launcher is then:

```sh
openbao-vastai launch-simready-validation-only OFFER_ID --attempt-label EXACT_LABEL
```

The label must be the same `3dprinting993-simready-local-ai-<20 hex digits>`
recorded in the manifest. Use the verified SSH endpoint and host key returned
by the launcher. Preserve the guard until exact provider absence is verified.
Do not treat a stopped container or a killed SSH command as stopped billing.

Run the upstream OVRTX example before the monocoque capture. Follow the
[Kit review procedure](../../../twins/964-chassis/monocoque/omniverse/kit-review.md)
for the private relay, actual viewport screenshots, working-layer save/reopen,
reconnection and output collection. Preserve frozen bundle hashes and retain
all native execution evidence separately from local preparation checks.

Verification without a rental:

```sh
python3 -m unittest discover -s tests -p test_964_omniverse_rental_guard.py -v
python3 -m unittest discover -s tests -p test_openbao_vastai_engine_twin.py -v
```

These policy tests are not evidence of native RTX or Kit execution.

The [29 October execution](../../../twins/964-chassis/monocoque/omniverse/native-review-20261029/README.md)
ended with `contract_or_cost_guard` and verified destruction. Another rental
was subsequently observed on the shared account. The triggering snapshot was
not retained, so the guard now logs nonexclusive instance IDs and rejected
cost metadata without changing its policy. Coordinate the account before a
new approved attempt; do not hide an unrelated rental from this guard.
