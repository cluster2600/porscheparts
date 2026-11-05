# Readiness verification — 26 September 2026

## Real GPU session of 26 September 2026

Vast VM 52810563, RTX PRO 6000 Blackwell 96 GB, 32 vCPU, 500 GB disk,
1.924074 USD/h advertised (transfers extra). Session capped at three
hours by the local wrapper; guest shutdown scheduled separately.
Container trials 52809699 and 52810056 were destroyed and their absence
verified before the final VM.

- Original 935 raw scan verified by SHA-256, with no reuse of earlier geometries.
- Three CAD-Recode GPU inferences: 7.33 / 6.14 / 5.81 s excluding loading.
  PyTorch peak memory near 3.34 GB. Candidate 1 rejected: invalid solid.
  Candidates 2 and 3 exported to STEP in the isolated Docker worker.
- p95 distances scan → CAD / CAD → scan: candidate 2 **27.321 / 23.414**;
  candidate 3 **48.200 / 20.204**, in unknown OBJ units. No dimensional
  acceptance and no manufacturing validation.
- Nemotron Nano FP8 served by vLLM 0.12.0: real tool call succeeded.
- OpenClaw 2026.9.6 connected to Nemotron: real write of the requested file,
  then reading of the reports and drafting of a review. No Docker/shell access
  given to the agent; results mounted read-only.
- An automatic NVIDIA update caused an NVML mismatch, corrected by reloading
  guest driver 580.178.04 while the GPU was idle.
- Nine targeted Python tests pass. `make check` runs 912 tests, three
  skips, then fails on the pre-existing missing PET `/tmp/kat517-993.txt`.
- Local Qwen2.5-VL-7B answers image queries: red and blue recognised on
  256 × 256 test charts. A 64 × 64 chart was described as white; this test
  is not a qualification of recognition of cylinder head details.
- The OpenClaw review needed a correction: it initially claimed to exceed
  criteria that did not exist. The corrected version keeps the four exact
  p95 values and no longer claims to apply a threshold. The agent's outputs
  remain proposals subject to deterministic checks.
- OVRTX, Material and Physics healthy. Scan and STEP converted with NVIDIA
  `usd-convert-cad` 0.2.0, USD minimum validated, relative composition retrieved.
  The first composed render was uniform (references not embedded); the
  flattened diagnostic render passes, then the separate scan/candidate renders pass.
- Visual inspection: candidate 2 is rejected as a cylinder head reconstruction
  (fins, openings and details lost in favour of blocks/cylinders).
- Aluminium fixture 20 × 40 × 60 mm: Material first chose plastic.
  The corrected material instruction produces Aluminum_Matte. Physics writes 0.1296 kg,
  density 2700 kg/m³ and gravity 9.81 m/s² after unit normalisation.
  `check_simready_fixture.py` rejects the plastic version and accepts the
  corrected version. The four validators, including Prop-Robotics-Neutral, pass
  on the final fixture after the documented addition of its grasp line.
  None of these results is a physical validation of a cylinder head.
- The memory actually visible in the guest is 101139 MiB, below the
  128 GB targeted. The configuration holds for these trials; it is not
  evidence of capacity for a cylinder head CAE calculation.

Evidence retrieved outside Git: `work/cad-recode-935-fresh/vm-results/`.
The full report is `work/cad-recode-935-fresh/vm-results/RESULTATS.md`.
The SimReady success concerns only the synthetic fixture.

## Local preparation before deployment

- New independent pipeline, with no import of the modules or results of the
  earlier cylinder heads. Original 935 unchanged; digest verified before analysis.
- Raw scan analysed: 1,281,608 vertices, 2,466,040 triangles, four connected components.
  Units remain unknown; the anatomical segmentation remains to be reviewed.
- CAD-Recode v1.5 weights and tokeniser downloaded by revision, local digests
  kept. A real CPU inference produces a non-truncated proposal in
  62.39 seconds. This time excludes loading and verification of the weights.
- First proposal executed in the confined CAD container; STEP export
  succeeded. This proposal is not accepted geometry.
- Synthetic fixture 20 × 40 × 60: isolated export, STEP reimport and
  bidirectional p95 distances below 1e-12 unit; inverse ×100 transformation
  verified separately, including with a non-zero centre.
- Seven targeted tests pass in the dedicated venv: integrity, transformations,
  STEP, errors, timeout, request contract and synthetic USD composition.
- CalculiX run on two synthetic analytical problems: tensile displacement
  0.05 and heat flux -1000, matching the expected values.
- OpenFOAM F25 benchmark run: three meshes, two repetitions,
  solver verification succeeded and order of convergence close to 2.
- Linux amd64 CAD image built on the Mac by emulation, with dependencies
  locked by version and digest. OpenClaw image built for local
  checking; `openclaw config validate` succeeds with version 2026.9.6.
- Compose configuration, shell syntax and Python compilation verified.

## Limits observed before the VM session (historical)

- Kali unreachable during the trials; no GPU build and no Blackwell run.
- Nemotron: model/revision/configuration and tool-call smoke test prepared,
  server not started. No Nemotron tool-call success is claimed.
- Omniverse: per-step commands and USD composition prepared; only the
  synthetic USD tests were run. No RTX service, cylinder head render,
  Material/Physics call or GPU SimReady result is claimed.
- Generated CAD can be very far from the scan despite its valid export.
  No deviation threshold, physical unit, material or real loading is invented.
- The new physical-inputs dossier remains deliberately incomplete: six
  families of missing data, cylinder head solvers and training blocked.
- `make check` passed its suite of 907 tests (two skips at that time), then
  failed on the pre-existing missing PET file `/tmp/kat517-993.txt`.
  The seven final targeted tests were then run without skips.
- No purchase, push, Vast rental or change to earlier work.

## Local evidence, outside Git

In `work/cad-recode-935-fresh/`: `intake/intake.json`,
`proposals-cpu/candidate-1.json`, `export-1/execution.json`, the candidate STEP,
`physics-readiness/readiness.json` and `runtime-verification.json`.
The CalculiX and OpenFOAM reports are respectively in
`work/cad-recode-ccx-smoke/checks.json` and
`work/cad-recode-poiseuille-smoke/report.json`.

Failed technical attempts are kept separately (macOS SciPy dependency,
then Docker mount, both corrected), without overwriting earlier results.

## Quality of the first proposal

Native evaluation of the STEP exported from the inspected code gives, over 8192
samples in each direction:

| Direction | Median | p95 | Sampled maximum |
|---|---:|---:|---:|
| Scan → CAD | 10.531 | 38.568 | 60.200 |
| CAD → scan | 6.186 | 29.438 | 69.397 |

All these values are in **unknown OBJ units**, never in verified mm.
The proposal remains `needs_review`, `geometry_accepted=false`. The valid solid
does not reproduce enough detail to be promoted to a CAD definition.
The useful next step is a review of the segmentation and datums from the raw scan.

The calculation reported a numerical proximity warning on the source
mesh; all final statistics are finite. The candidate tessellation
uses a deflection of 0.01 OBJ unit and an angle of 0.1 radian. This does not
constitute a metrological uncertainty or an acceptance threshold.

The duplicate of this evaluation under Docker emulation was stopped after
the native result was obtained; its execution status remains `failed`, not
`passed`. The isolated pipeline test uses a separate synthetic fixture.
Local geometric evidence:
`work/cad-recode-935-fresh/evaluate-native/deviation.json`.

The isolated dispatcher completed on the synthetic fixture: valid STEP and
bidirectional p95 below 1e-6 unit. Evidence:
`work/cad-recode-fixture/evaluate-1/report/deviation.json`.

## Vast pre-check of 26 September 2026

The installed wrapper `/Users/maxime/.local/bin/openbao-vastai` passes `--check`
and `--auth-check`. `instances` returns an empty list. The available credit
reported by `account-balance` is 46.178 USD; no top-up was requested.

Deployment blocker: the creation operations of the installed wrapper use
fixed container images and profiles (`runtype=ssh_direct`). No CAD-Recode/Nemotron
VM profile covers the Docker/NVIDIA target described in the README.
The `cad-specialist-offers` offers concern the old container profile and do not
prove VM availability. The installed wrapper differs from the repository
copy: do not overwrite it with the latter.

No machine was rented, no GPU test started. Resuming requires
an SSH-reachable VM with Docker/NVIDIA, or a VM launch profile
explicitly available in the authorised OpenBao wrapper. Do not bypass
this boundary by retrieving the Vast API key directly.

### VM search after authorisation to adapt the launcher

The extension `deploy/openbao/cad_recode_vm_profile.py` is integrated into the
installed launcher under the command `cad-recode-vm-offers`. It reuses its existing
OpenBao access, without changing the authentication functions or the old
profiles. Its current scope is search; no VM rental operation
is yet implemented or qualified.

The Vast search returns **zero offers on the provider side** for the variants
RTX PRO 6000 WS / Blackwell Max-Q / S: one card, at least 95,000 MB of VRAM,
32 vCPU, 128,000 MB of RAM, 500 GB, VM enabled, verified host, reliability ≥ 99 %,
price ≤ 2.50 USD/h and transfers ≤ 0.05 USD/GB. This one-off observation does not
prove general unavailability of Vast VMs.

The test `tests/test_cad_recode_vm_profile.py` validates the hardware,
VM and price limits. The search then seemed blocked by the absence of a compliant offer.
No instance created and no expense incurred by this attempt.

### Filter correction and available offer

The unavailability conclusion was too broad: `gpu_frac=1` required
all the server's GPUs. This field is the ratio between the offer's GPUs and the
server's GPUs, not a fraction of one card's VRAM. The profile now accepts
`0 < gpu_frac <= 1`, keeping one card and the full VRAM. The test explicitly
covers one card on a two-GPU server.

Offer **49400940**, Bulgaria: RTX PRO 6000 WS, 97,887 MB VRAM, 32 vCPU,
128,713 MB RAM, VM enabled, verified host, advertised reliability 99.2834 %.
Price for **500 GB: 1.924074 USD/h**, storage included; inbound transfers
0.002604 USD/GB, outbound 0.003906 USD/GB. Three hours: about 5.77 USD
excluding transfers. Re-read availability and price before renting.
Evidence: `work/cad-recode-935-fresh/vast-vm-offers-corrected.json`.

The search command `cad-recode-vm-alternatives` also accepts L40S and
RTX 6000 Ada, at least 48 GB nominal, 12 vCPU, 64 GB RAM and 300 GB, with
the same hourly cap. No launch and no GPU test performed.

Source: https://docs.vast.ai/cli/reference/search-instances (`gpu_frac`).

### Actual launch

The profile `launch-cad-recode-vm OFFER_ID` is installed and tested offline.
It refuses already-present instances, requires 15 USD of credit without top-up,
re-reads the admissible offers and creates an exclusive state before renting.
The local LaunchAgent `com.3dprinting993.cad-recode-vm-expiry` calls, every
60 seconds, the clean-up limited to this session's label after three hours.
It depends on the Mac and its OpenBao access; `shutdown -h +180` in the VM is
a second operational limit, not evidence that billing has ended.

Trials 52809699 and 52810056 with a KVM image by digest resulted
in a container launch unusable over SSH. They were destroyed and their
absence verified. The parameter `vm=true` alone was not enough with that image.
The profile now uses the officially recommended VM template
`fc393e1a4058a2f2b88e0c0e1a92e540`, observed with `vm=true`. It resolves
`docker.io/vastai/kvm:cuda-12.9.1-auto`: this boot image is chosen
by Vast; the application images remain pinned separately.
Instance 52810563 was created at 1.924074 USD/h; the logs show
libvirt/QEMU starting. This does not yet prove SSH, CUDA or the stack.

The log request path of the installed wrapper also received
its trailing slash required by the provider, fixing its HTTP 400.
