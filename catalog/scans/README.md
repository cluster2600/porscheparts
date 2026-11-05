# Raw scan register

A `catalog/scans/*.json` record registers a raw 3D scan (OBJ) kept outside
Git, identified by absolute path, SHA-256, size in bytes and mtime. The raw
file (100 MB and more) is never copied into the repository, in accordance with
`AGENTS.md`.

A scan record is not a source record: the `catalog/sources/` record carries
the rights and the upstream access method, the scan record carries the digest
and the state of the local file. When a source record already exists (prefix
`SRC-`), the scan record references it through `linked_source_ids` without
duplicating its claims.

Rules:

- `path` is absolute on the compute host (`kali2`); the file may not
  exist on other hosts.
- `sha256`, `bytes` and `mtime` were recomputed on the host on the day given by
  `recorded_on`. Any later divergence invalidates the derivatives.
- `resolution` is a declaration (often taken from the filename), never
  a verified metrological precision, until the
  `containers/obj-metrology-f15` pipeline or a physical measurement has established it.
- OBJ files carry no unit metadata; mm is an assumed convention,
  flagged in `notes`.
- `license` and provenance are marked `unknown` as long as no evidence
  is archived. Never invent.

Validate with `python3 scripts/validate_scans.py` (covered by `make check`).
