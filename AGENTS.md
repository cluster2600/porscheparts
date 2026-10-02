# Repository instructions

This repository builds an evidence-backed catalogue of reproducible Porsche 993
parts for additive and conventional manufacturing.

## Working rules

- Treat `catalog/parts/*.json` as the catalogue source of truth.
- Prefer editable source geometry (`.FCStd`, `.scad`, `.step`) over derived
  meshes (`.3mf`, `.stl`).
- Never label a part as dimensionally accurate, fitted, tested, safe, or
  released without linked evidence in its catalogue record.
- Before generating a functional part, list its required attachments and load
  path for the exact catalogue variant. Establish measured hole patterns, axes,
  mating faces, datums and tolerances before designing around those interfaces.
  Missing evidence blocks functional completion; never fill it with plausible
  coordinates. Compilation, a watertight mesh, lightening windows and a metal
  shader do not establish attachment completeness or material qualification.
  Check model proposals against an independent interface contract before
  accepting them; model output must not supply its own inspection evidence.
- A publicly visible model or photograph is not automatically reusable. Record
  its licence and provenance before adding it.
- Do not commit raw scans, proprietary manuals, supplier quotes, personal data,
  credentials, or vehicle identifiers.
- Do not release braking, steering, suspension, restraint, fuel-system, wheel,
  or highly loaded engine parts without documented professional engineering
  review and an approved validation plan.
- For titanium parts, document alloy, build process, orientation, heat
  treatment, machining, inspection, fatigue assumptions, and galvanic isolation.
- Keep changes surgical and run `make check` before proposing a merge.

## Repository location

The repository must live on a **native Linux file system**, for example
`/home/<user>/porscheparts`, and **not on a WSL DrvFs mount** such as
`/mnt/c/...`.

This is not a preference. `tests/test_917_parametric_layout_master_f30.py`
fails systematically from `/mnt/c` on
`test_authoring_publishes_only_wireframe_contract_with_completion_marker`, with
status `failed_closed_no_output` and an internal error `authoring_failed:OSError`.
The cause is that authoring publishes its output through POSIX operations
relative to a directory descriptor — creating a staging directory, then an
atomic rename — which DrvFs does not serve correctly. The script therefore fails
closed, which is the intended behavior, but for an environment reason rather
than a data one.

Verified: the same commit passes on ext4 and fails on `/mnt/c`, including on
commits older than any change. On ext4 the full suite gave **915 tests OK**,
30 skipped, in 31 seconds versus 190 seconds on DrvFs.

## The name `3dprinting993` survives, and it is not an oversight

The repository is now called `porscheparts`. Four families of occurrences of the
old name were **deliberately kept**, because they do not designate the
repository:

| occurrence | why it does not change |
|---|---|
| `ghcr.io/cluster2600/3dprinting993-*` and local docker tags | GHCR is a namespace separate from GitHub: renaming the repository renames no package. Images are pinned by SHA-256 digest and checked by lock tests. |
| USD keys `3dprinting993:*` in `customData` | engraved in USD stages already produced. Renaming them would force regenerating everything and break comparison with existing stages. |
| paths `/opt/3dprinting993/...` | paths **internal to the images**, part of the image contract and asserted by the image tests. |
| GitHub Actions run URLs in evidence files | these are **historical attestations**: that run did take place under the old name. Rewriting history would falsify provenance. |

The general rule that follows, and that holds beyond the rename:

**Never edit a file whose SHA-256 is pinned by a lock or an evidence contract.**
This covers `containers/*.lock.json`, their recipe inputs — Dockerfiles,
`.github/workflows/containers.yml`, requirements — and all of `evidence/**`. A
mere string rename there breaks the provenance chain, and `make check` detects
it: that is what happened on 2026-09-04, on ten files.

## Repository language

The project was written in French and is being translated to English, in
phases: [docs/TRANSLATION.md](docs/TRANSLATION.md) holds the scope, the
glossary and the files that must never be translated in place (`evidence/**`,
`archive/**`, locks). New documentation, record prose and command-line messages
are written in English. Stable identifiers, schema field names and filenames
remain unchanged until a dedicated rename phase.
