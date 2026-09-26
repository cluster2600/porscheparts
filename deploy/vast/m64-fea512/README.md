# Bounded M64 FEA512 rental

`m64-fea512-v1` is one separately authorized additional paid attempt, capped at
USD 5 including USD 1 cleanup reserve, transfers and up to three hours. It does
not change the older PicoGK, research, engine-twin or CAD-VM policies. A new
manifest must not be created to bypass an already-consumed paid-attempt journal.

The fixed offer query requires one whole-host GPU, 32 effective CPU cores,
512000 MB provider RAM, verified reliability >=0.99, on-demand availability,
500 GB allocated disk, total hourly price <=USD 1 and both transfer tariffs
<=USD 0.01/GB. GPU compute is not required by this CPU FEA job.

Read-only discovery: `openbao-vastai fea512-offers [offer_id]`. The selected ID
is refreshed with 500 GB storage pricing immediately before the paid call.
The initial candidate was 50924858; availability and its quoted price are not
assumed. Post-create identity, allocated resources, price, image and SSH checks
must pass. Separately verify actual Linux/cgroup usable memory before solving.

Use the existing PicoGK manifest fields with profile `m64-fea512-v1`, job ID
`m64-fea512-<suffix>` and label `3dprinting993-m64-fea512-<20 hex digits>`.
Add `guard_path` (this absolute helper path), `guard_sha256` (the wrapper-pinned
SHA256) and this exact `background_instance` object:

```json
{"id":52810563,"label":"3dprinting993-cad-recode-vm-20260926","image":"docker.io/vastai/kvm:cuda-12.9.1-auto"}
```

This tag is an exact provider identity, not an immutable image digest. It must
match fresh inventory before both guard arming and launch. Only this exact VM
is excluded from the new job's inventory view and budget; it is never deleted.
Changed or unexpected rows stay visible and block arming or terminate only the
new owned attempt. The new job's image remains an independently qualified,
digest-pinned PicoGK image. Its geometry smoke does not qualify Linux CCX.

Start `python3 /absolute/path/to/this/deadline_guard.py /absolute/job.json`
before `openbao-vastai launch-picogk-m64 <offer_id> /absolute/job.json`.
Keep the unchanged sibling `../picogk/deadline_guard.py`: its hash is checked.
The wrapper verifies guard source, live process command, manifest hash and its
own hash before the one-shot paid attempt. The guard requests exact destruction
five minutes before the original monotonic/wall deadline, retries uncertain
cleanup, and watches a late creation until the original deadline. Stopping a
container is not billing-stop evidence; verified provider absence is required.

The repository wrapper is immutable: its original SHA256
`42fe39ebcf7fc81e8f6c4a85e38fa9da03fd4637bb93a37b3a422c315e8a5aa4`
is pinned by historical F46 evidence. The extension is distributed only as
[`wrapper-fea512.patch`](wrapper-fea512.patch), SHA256
`32510f26cfffd17f3e5d34fb1caf1a894154b09f174a760cd285a5046d7f8c3c`.
The installed wrapper has additional CAD-VM helpers and a request-logs URL fix.
For an explicitly approved installation, review and dry-run this patch against
that exact installed source, then apply only the delta; do not overwrite the
installed wrapper wholesale or apply the patch to the pinned repository file.
The tests copy the pinned source into a temporary hierarchy, apply the delta
with local `git apply`, and check the resulting variant's exact source hash.
No secret access, rental, image pull or remote qualification is performed by
the synthetic tests: `python3 -m unittest discover -s tests -p 'test_openbao_vastai*.py'`.
