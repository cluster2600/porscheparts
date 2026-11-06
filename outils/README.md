# `outils/`: frozen

This directory is **frozen in place** (issue #425). It no longer duplicates
`benchmarks/` or `containers/`. Its other former contents were consolidated
earlier, and only one item is left:

| path | what it is |
|---|---|
| [`benchmarks/openfoam-poiseuille-f25/`](benchmarks/openfoam-poiseuille-f25/) | the F25 OpenFOAM Poiseuille verification benchmark ([dossier](../docs/OPENFOAM_POISEUILLE_VERIFICATION_F25.md)) |

## Why it cannot move to `benchmarks/`

The path is part of two image recipes, and those recipes are pinned:

- `containers/openfoam-engine-f35.Dockerfile` and
  `containers/917-f47-cfd-cae/Dockerfile` copy this exact path into their images
  (`COPY outils/benchmarks/openfoam-poiseuille-f25 ...`), and their
  `.dockerignore` files re-include it by name. The image tests assert both.
- `containers/openfoam-engine-f35.lock.json` lists
  `outils/benchmarks/openfoam-poiseuille-f25/benchmark-contract-f25.json` and
  `generate_cases.py` among its recipe inputs.
- Derived 962 and 935 manifests cite files under this path.

Moving it would mean editing pinned recipe inputs, which AGENTS.md forbids.
No test fails after a move, which is why the earlier trial recorded in
[docs/ARCHIVE.md](../docs/ARCHIVE.md) looked compliant, but the image builds
and the lock would no longer match. A move belongs to a new image generation
(#404–#406), with a new recipe and lock, and the old ones kept frozen.

**Rule:** add nothing new here. New benchmarks go in `benchmarks/`.
