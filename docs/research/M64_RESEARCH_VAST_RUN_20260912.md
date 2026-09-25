# M64 reader run — September 12, 2026

## Scope

At the user's request, the reading work is organized into **24 independent
missions, four concurrent on a single Vast LLM server**. The categories are
CAD/scan, CFD/thermal, material/oil/LPBF and verification/mathematics/AI.
GitHub is the public synthesis folder; the corpora and raw answers stay
private, with no replication into Obsidian.

These readers work on supplied excerpts: they do not browse autonomously,
execute no code proposed by a publication and hold no secret. Proposals are
reviewed before they become decisions. A reading, a software test and a
physical validation have separate statuses.

## Inputs and reproduction

- [24 versioned missions](m64-research-missions-20260912.json).
- 42 sources collected: 28 excerpts of documents/pages, five abstracts, nine
  publisher notices only; this is not a full reading of 42 articles.
- SHA-256 of the private corpus:
  `b98f050a44eb8ad0c74ffb94595038e0a4ca19312f5e35702dd1df52b6e53446`.
- SHA-256 of the private retrieval register:
  `f8ab7fa9c104a58a4b7d982e39bc93f4e9013e4538c2fa8e612b57041cbdf884`.
- Each entry keeps the URL, final URL, retrieval date, digest of the download
  and of the text, reading level and access limitation.
- The dispatcher sends at most 8,000 characters per source, three sources per
  mission; the truncation and the digests of the excerpts are kept.
- Pilot: `cad_01`, `cfd_01`, `am_01`, `vv_01`; the other twenty missions are in
  a separate queue to avoid redoing the first four.

For installation, SSH checks, the corpus format and the commands, see the
[operating guide](../../deploy/vast/research/README.md).

## Qualification before rental

Public image `vllm/vllm-openai:v0.19.0`, `linux/amd64` manifest verified:
`sha256:7a0f0fdd2771464b6976625c2b2d5dd46f566aa00fbc53eceab86ef50883da90`.
The 27 compressed layers amount to **9,577,304,117 bytes**; no complete image
was downloaded to the Mac.

Public, unrestricted model `Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8`, revision
`dcaee4d4dfc5ee71ad501f01f530e5652438fde0`; all the files of the repository
amount to **31,195,132,826 bytes**. This is not Flash Next. The recipe limits
the context to 16,384 tokens and concurrency to four; this configuration must
be confirmed by a real response, not inferred from the VRAM size.

The Finnish L40S offer `27979081` lists a 46,068 MB GPU, 16 effective CPUs,
128,965 MB of allocated RAM and 100 GB of requested storage: **0.779630 USD/h**
including storage. The RAM fields of an instance response can refer to the
whole host: do not announce its terabyte as RAM allocated to the container.

Initial credit read back: **38.275118 USD**. The target budget for the whole
pilot and the startup fixes remains **4 USD**, with no top-up; the last
attempts are each capped at 2 USD including a cleanup reserve. The cost
controls do not guarantee a banking limit in the event of a provider outage or
a lasting loss of the supervising workstation.

## Software verification and fixed incidents

- The `gpu_frac=1` filter required the whole server: fixed for this profile
  only, with a full GPU and its VRAM verified separately.
- Vast can report `cur_state=running` before the SSH ports appear. A transient
  absence waits; already known violations stay refused.
- Actually loading the image takes more than two minutes. The startup window is
  now `min(now + 900 s, global deadline − 300 s)`, cost included.
- The host clock is **11,480 seconds** ahead of the Mac: the launch that
  compared their epochs expired before any inference. After SSH verification,
  confirming no existing server and the time remaining on the Mac side, the
  server was launched with a relative timeout of 1,800 seconds. The external
  guard keeps its Mac deadline; no system clock was modified.
- The versioned fix now computes the timeout on the controller, reserving 900
  seconds for startup, 300 for cleanup and 60 of tolerance. An inference
  timeout below 60 seconds blocks creation before the paid call. This fix was
  not substituted for the active wrapper during its guard; it was installed
  after destruction and passed the local wrapper check. Its fixed automatic
  launch path remains tested offline, not presented as the path that ran this
  instance.
- A durable creation receipt records the ID before the first check; a
  diagnostic limited to the permitted metadata precedes any cleanup.
- The debugging instances are deleted and their absence verified. A Turkish
  offer that was still listed was refused by Vast with `no_such_ask`: that call
  was not replayed.

**245 targeted offline tests pass**: 233 on the Vast profiles, 29 of them for
research, and 12 on the dispatcher. The global `make check` hits a fingerprint
drift of the historical F46 report, because the shared wrapper changed. That
report is not regenerated to turn old runs into new evidence.

## Pilot results

Work instance `50780391` passed the identity, key association and SSH
connection checks. Versions read: vLLM 0.19.0, PyTorch 2.10.0+cu129, driver
560.35.03; a real CUDA computation returns the expected result on the L40S. The
server is configured on `127.0.0.1:8000` and its local tunnel on
`127.0.0.1:18000`.

**All 24 missions were run**, with at most four concurrent readings. The
[public results register](m64-research-run-summary-20260912.json) contains
their states, durations and digests, without reproducing the source texts.

| Batch | Requests | Citations compliant on this pass | Batch time |
|---|---:|---:|---:|
| Initial pilot | 4 | 1 | 44.597 s |
| Single retry of the three refused | 3 | 2 | 36.455 s |
| Twenty remaining missions | 20 | 15 | 130.690 s |

After replacing the first three reports with their retry, **18 missions out of
24 pass the citation check**. The other six stay refused: `cad_02`, `cfd_01`,
`cfd_04`, `cfd_06`, `am_05`, `vv_06`. Five contain an excerpt absent from the
text sent; `am_05` cites a URL outside the supplied list (which does not prove
that this URL does not exist). There was no automatic rerun and no weakening of
the check.

The retry only strengthened the verbatim-copy instruction. The compliant
reports have the status **unreviewed**: URL/excerpt match, not full semantic
validation. A review of the pilot shows in particular:

- a chemical composition compliance does not qualify the whole cylinder head;
- the absence of M64 evidence in an excerpt does not prove that a CAD method
  was never evaluated on any real data;
- an abstract or notice without results provides no hot property.

These limits confirm the use as a **document triage aid**. The decisions remain
those of the [sourced scientific dossier](../reports/M64_RESEARCH_EXECUTION_20260912.md),
with explicit tests and unknowns. No LLM report automatically modified the
CAD, the material cards, the loads or the manufacturing authorizations.

The 27 requests consumed **85,907 input tokens + 19,400 output = 105,307 tokens
on the Vast model**. The times of the three batches total 211.742 seconds,
excluding preparation, loading and review. No OpenAI savings rate is computed:
this is not an end-to-end cost comparison at equal quality, and the debugging
required work on the controller.

## Shutdown, cost and retention

Instance `50780391` was **destroyed**, then its absence was verified by the
wrapper, the external guard and a new, empty inventory. The tunnel closed. The
model and its remote cache were deleted with the instance; the useful logs and
responses were brought back before it disappeared.

The credit shown after cleanup is **38.051516 USD**, against 38.275118 before:
**observed decrease of 0.223602 USD**. This reading may precede the final
invoice; the instance rate was 0.779630 USD/h, storage included. No top-up, no
instance left running and no new paid account.

A persistent private archive keeps the corpus, metadata, logs, manifests and 27
responses (including refused ones), outside the files tracked by Git. SHA-256:
`8be8d4067eba90c166ea25d95a39407ffdcf93829260b78d78f3324f64fdac59`.
The public register contains the digest of the last report of each mission.
Neither copyrighted full texts nor unreviewed raw responses are published.

**Outcome: GPU reader operational and documented; no strength, combustion,
cooling or cylinder head printing computation was run by this batch.**
