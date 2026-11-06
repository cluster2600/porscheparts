# Station qualification — 28 September 2026

The image is **published and verified anonymously**; Vast instance **53246885**
is rented. The GPU preflight, the CPU witnesses, the Qwen response, the OpenClaw
tool call, the OVRTX render on GPU 3 and the Omniverse edit/save/reconnection
via the SSH relay pass. The video is also received on Kali2. The first simultaneous trial failed on the GPU memory
threshold; the Qwen API is verified again after its limit was explicitly set
to 0.90; a new OpenClaw tool call also passes. The second trial
was interrupted to diagnose the absence of responses in the user
dashboard, which confirmed that responses had resumed. The [third thirty-minute trial](runtime/soak/README.md)
**passes**, from 21:25:42 to 21:55:42 UTC: 120 Qwen requests, 53 complete chains,
no OOM and no restart. The 1,219 expected files are identical between
Vast and the persistent copy on Kali2. These results prove no
physical qualification of any part.

The [deployment status](deployment-status.json), the
[final publication evidence](publication-final.json) and the
[run evidence on Vast](runtime/README.md) specify each observed state.
The published manifest is:

```text
ghcr.io/cluster2600/3dprinting993-picogk-m64@sha256:6548a22795a01bf6b4a1d79a4bf9415d839ef5f445773d19d3df81bec2bef154
```

The publication reused the built image, without a rebuild, via GitHub
Actions and a JIT runner on Kali2. The final run `36490231264` succeeded; the
runner 23 was automatically removed. The 78 layers, the configuration
`4f58a4e28ab7…`, the platform and the only ports `22/tcp`, `47998/udp` are
verified anonymously. The [initial publication](publication.json) remains preserved.
The earlier refusals of direct
publication and the budget refusal prior to any creation remain kept in
the status as history; they no longer describe the current state.

The rental covers offer **49181720**, machine **44690**. The initial manifest
reserved **26.99 USD** and set a deadline of 29 September at
00:12:16 UTC. At **21:36:31 UTC**, the user explicitly asked to
keep Vast running after adding credit: the [destructive guard was removed](runtime/keep-running.json),
the historical manifest is kept and no destruction was called.
The station now runs **without an automatic deadline**, at the observed rate
of **6.237037 USD/h**, i.e. about **149.69 USD/day excluding transfers**.
The real invoice remains unknown. The [permanent synchronisation to Kali2](runtime/sync-persistent.json)
is active, without deletion or following links; its last recorded copy
succeeds at 21:42:55 UTC.

The OVRTX render required an explicit fix of the cache permissions
on the instance. The [final persistent layer](runtime/image-hotfix-persistent/final-image.json)
incorporates it with the Qwen/client/relay fixes and passes the CPU witness in
4.157 s; it is published at the digest above. The GPU evidence and the endurance run
concern the initial instance with these fixes applied while running.
A new instance started from the final digest has not been tested;
the active work is preserved on the existing rental.
The UDP failures observed from the Mac and Kali2 do not
allow the cause to be attributed to the provider, since both machines
may share the same Internet access.

Kali1 is also available for [bounded CPU PicoGK computation](runtime/kali1-cpu/summary.json).
Launch from Kali2 and automatic collection are proven with
`kali1-picogk`: two CPUs, 2 GiB, reduced priority and five minutes maximum,
without system installation or gateway restart. The link goes through the
tunnel of the Mac controller, which must remain available.

OpenClaw monitoring is scheduled every **30 minutes**: it follows
the real progress of the 911 993 engine, the sources and results, and the
services. The generic witness of this qualification does not represent a
part of this engine. The GitHub token is kept at the user's request;
the API responses filter the temporary authentication metadata.

The [built image and the initial CPU witnesses](build/README.md) are documented
separately, with the C# sources, the editable FreeCAD document, the STEP/STL,
the USD assembly and the logs extracted from the image.

The [latest `make check` receipt](runtime/make-check-final-release.json) records exit code
**0** on the macOS controller: **3,231 main tests**, 148 skipped and
**574 Markdown documents without a broken link**. The code remained frozen during this
check, which includes the Git 2.53 regressions and the filtering of sensitive
metadata. The documentary receipts added afterwards are checked separately. The [GitHub evidence on Kali2](runtime/github-access/proof.json)
confirms native read and `push --dry-run` on the two authorised repositories, without
remote modification. The history below keeps the first complete
check and its run conditions.

## History of the first software check

`make check` finished with exit code **0** on Kali2, in an isolated copy of
3,898 files of the worktree, from 28 September 2026 at 18:49:46 UTC until
18:57:39 UTC (472.58 s). No file of this copy changed during the
check. The new files were added to the index of this copy before
the run in order to include their documentary links.

| Check | Observed result |
|---|---|
| Main suite | 3,213 tests; 140 explicitly skipped; no errors |
| All 32 suites invoked by `make check` | 3,490 invocations, with repetitions; 141 skipped |
| Markdown links of the checked copy | 567 documents; no broken link |
| Native LPBF F37 check | `mesh-cfd` image pinned by the Makefile; run without network |

The copies of the results are [summary.json](summary.json) and
[result.json](result.json). The full log is kept locally under
`work/station-linux-check-r8kj70sz/make-check.log`, outside Git. Its SHA-256 is:

```text
5db7a308778d76816b8a6787acb2dd0f263f0645c3ac634b3e0538977dfa4d51
```

The run uses Python 3.14.7, a dedicated virtual environment with the
system packages, `PYTHONNOUSERSITE=1`, `umask 022` and a dedicated `TMPDIR`. No
global package was installed. These settings avoid the incomplete OCP bindings
of the user site and the full `/tmp` of the host. The preliminary trials
had also revealed umask-sensitive fixtures; the targeted GHCR
suite (17 tests) then the complete check pass under `022`.

The skipped tests mainly concern the optional runtimes
OCP/CadQuery, OpenUSD and Trimesh, as well as local evidence deliberately
absent from Git. Their absence does not amount to validation of these features.

After the addition of `soak.py` and `qualify_image.py`, the **29 targeted station tests**
pass with no skipped test. The four new registry tests use
simulated responses: compliant manifest and configuration, layer checksums,
rejection of divergent digests, extra ports and invalid sizes.
`soak.py --self-check` also passes; it verifies its parsers without running
the 30-minute qualification. These additions postdate the Linux copy
above and are therefore not covered by its `make check` result.

The evidence of publication, GPU preflight, CPU witnesses, Qwen response, OpenClaw
tool, OVRTX render, USD manipulation/save and WebRTC reconnection
on Vast and the report of the thirty simultaneous minutes are now linked
above. The real invoice and the final transfer balance remain unknown;
the destructive guard was removed at the user's request. Calibrated
thermomechanical simulation and physical qualification remain outside the scope
of this first installation.
