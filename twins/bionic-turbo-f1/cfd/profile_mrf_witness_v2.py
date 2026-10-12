#!/usr/bin/env python3
"""Refine only the angular faceting to resolve the rejected witness cell aspect."""
import json
from pathlib import Path
from prepare_case import sha
import profile_mrf_witness as previous


def prepare(parent, case, profile_path, omega):
    manifest = previous.prepare(parent, case, profile_path, omega)
    spec = manifest['profile_witness']
    (case/'system/blockMeshDict').write_text(previous.mesh_text(spec['nodes_z_radius_mm'], spec['shell_half_width_mm'], 128))
    manifest['file_sha256']['system/blockMeshDict'] = sha(case/'system/blockMeshDict')
    spec.update(angular_refinement_source_sha256=sha(Path(__file__)), sectors=128,
                expected_cells=2560, expected_rotating_cells=1280, expected_interface_faces=1280,
                reason='024 has 512 cells below determinant 0.001. Fourfold angular refinement reduces long azimuthal edges without changing the meridional profile or solver criteria. Faceted walls differ, while the analytic profiles stay identical.')
    (case/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    return manifest
