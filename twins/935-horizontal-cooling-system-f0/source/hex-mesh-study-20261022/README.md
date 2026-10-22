# Executed 935 hex-mesh study sources

These are byte-preserved experiment snapshots, not a new general-purpose
meshing API. The [report](../../../../docs/research/935-horizontal-cooling/HEX_MESH_CONTINUATION_20261022.md)
and [checkpoint](../../../../docs/research/935-horizontal-cooling/hex-mesh-continuation-20261022.json)
bind source hashes to the observed native controls and interrupted real cases.
Private case inputs and their parent receipts are required. The user paused
the programme; publishing these files does not authorise a restart.

| Order | Sources | Recorded action |
|---|---|---|
| 1 | `prepare-hex-template-001.py`, `run-hex-native-001.py` | Prepare the strict surface/layer recipe; retain the castellated mesh after the serial deadline. |
| 2 | `probe-rootless-mpi-001.py`, `qualify-parallel-mesh-001.py` | Check unchanged isolation, local transports and the analytic four-rank mesh control. |
| 3 | `prepare-parallel-snap-001.py`, `run-parallel-snap-001.py` | Validate native decomposition/refinement addressing and run snapping to its actual deadline. |
| 4 | `prepare-parallel-snap-002.py`, `run-parallel-snap-002.py` | Fresh case with a longer deadline; stopped by the user before completion. |
| 5 | `prepare-hex-review-control-001.py`, `check-hex-review-control-001.py` | Check complete cube boundary export, exact OBJ coordinates and rounded VTK data. |
| 6 | `prepare-castellation-review-001.py`, `render-castellation-review-001.py` | Export and inspect the complete saved pre-snap wall; do not infer a surface certificate from sampled gaps. |
| 7 | `backup/*.py` | Seal completed cases, controls and the user-stopped checkpoint without overwriting earlier archives. |

The existing Python environment supplies NumPy, SciPy and VTK for Mac review;
native Linux execution uses the pinned rootless Foundation 13 userspace.
The snapshot code retains its original absolute/private paths. It refuses
existing output directories and records its own executed source hash. A new
execution needs fresh paths and a new receipt; editing snapshots would break
the current provenance. No raw scan, private mesh or derivative image is
included here. No new flow or manufacturing admission is granted.
