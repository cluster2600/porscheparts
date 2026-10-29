# Derived fields: hashes kept, bytes not committed

The sources in this report produce large derived numpy archives — voxel
transports, candidate geometries and selected volumes. They were going to be
committed alongside the results, **75.0 MiB** in all across the three stages
of this series.

Git retains every blob it is given. A payload committed once stays in the
repository's history even after the file is deleted, so the only moment to
decline it is before the push. These archives are declined, and what carried
their provenance is kept:

- every archive's **SHA-256 is already recorded in the assessment that consumes
  it**, so a regenerated field can be checked against the published result;
- the **producing and checking sources are committed** next to those
  assessments;
- the [payload manifest](payload-manifest.json) lists each declined archive with
  its hash, byte size, and array names, shapes and dtypes, so its structure is
  known without the bytes.

Two kinds of large file are **not** declined. `fixed-r24.step.gz` is editable
source geometry, which this repository prefers to keep over a derived mesh. The
`core-envelopes-006/envelope-*.obj` meshes back a published figure and are small
enough to review in a diff. Figures, logs and every assessment, contract and
receipt JSON are kept as well.

The declined archives are removed from `publication-manifest.json`, because that
manifest pins files the repository publishes and these are no longer among them.
Their hashes move to the payload manifest rather than disappearing, and the two
records were cross-checked: every hash agreed.

## Reproducing a field rather than retrieving it

[REPRODUCE.md](finite-gyroid-001/REPRODUCE.md) pins the dependencies, commands
and input hashes for the finite-region networks.

For the powder-route candidate,
[replay-receipt.json](powder-ports-001/replay-receipt.json) records a replay
whose regenerated archive **matched the published SHA-256**. That is the
reproducibility claim this report rests on: the candidate is reproducible from
the committed runner, not retrievable from git. Nothing here authorises
manufacturing.
