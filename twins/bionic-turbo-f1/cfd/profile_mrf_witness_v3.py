#!/usr/bin/env python3
"""Test native-coordinate rounding without changing the mesh recipe or solver tolerances."""
import json
from pathlib import Path
from prepare_case import sha
import profile_mrf_witness_v2 as previous


def prepare(parent, case, profile_path, omega):
    manifest = previous.prepare(parent, case, profile_path, omega)
    path = case/'system/controlDict'
    text = path.read_text()
    if text.count('writePrecision 12;') != 1:
        raise ValueError('Expected frozen 12-digit native output')
    path.write_text(text.replace('writePrecision 12;', 'writePrecision 16;'))
    manifest['file_sha256']['system/controlDict'] = sha(path)
    manifest['profile_witness'].update(precision_source_sha256=sha(Path(__file__)), native_write_precision=16,
        precision_reason='025 native face-normal rotation reaches 1.7951e-8 m/s, comparable to its 1.3976e-8 m/s gas velocity. Isolate coordinate serialization error with identical vertex definitions, physical inputs and solver tolerances.')
    (case/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    return manifest
