# Executed reference-fluid-wall study sources

These are byte-identical copies of the dated private experiment sources, not a
new portable meshing API. Their original paths and assertions are retained for
replay against the private archive. Run from the repository root with the
existing scientific environments and Python assertions enabled. Geometry and
results remain private.

- `compose-reference-wall-001.py` reuses the full SI analysis reference and
  retains the old outer duct. Nested boxes and an open-surface refusal run before
  the real construction. Its scientific environment includes Trimesh.
- `verify-reference-wall-001.py` uses the independent existing OBJ reader and
  reads the complete SMESH to check serialized wall identity.
- `diagnose-added-boundary-point-001.py` locates the refused boundary subdivision
  and checks collinearity using exact integer coordinates.
- `restore-reference-edge-001.py` restores the original two wall facets and
  replaces the incident cavity through the existing positive-kernel proposal.
  Unit-volume and refusal tests are in `tests/test_935_reference_fluid_wall.py`.

```sh
export PYTHONPATH=twins/935-horizontal-cooling-system-f0/source
python "$PYTHONPATH/reference-fluid-wall-study-20261022/compose-reference-wall-001.py"
python "$PYTHONPATH/reference-fluid-wall-study-20261022/verify-reference-wall-001.py"
python -m unittest discover -s tests -p test_935_reference_fluid_wall.py -v
```

Composition expects the original `work/935-cfd-pilot-20261022/rotor-001/coarse`
reference and `work/935-cfd-mesh-correction-20261022/prepared-concavity20-001`
boundary. Native scripts expect the recorded `/home/lolman` layout. Existing
TetGen, volume-audit, native conversion and readback sources are reused without
editing their pinned bytes; the dated report/checkpoint identifies them. Native
TetGen uses its existing 8 GiB / 600 s limits; conversion commands use 8 GiB /
300 s each. The correction has a 300 s alarm, and the subsequent full native
volume audit additionally has an 8 GiB address-space limit and 300 s process
deadline. No limit is represented as a physical tolerance.

Every replay requires fresh output paths. Rejected outputs are evidence; do not
overwrite them or upgrade a successful command into a passed quality gate.
