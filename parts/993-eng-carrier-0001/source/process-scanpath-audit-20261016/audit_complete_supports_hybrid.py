"""Mandatory full exposure and every-group audit using the sealed mixed store."""
import argparse
import json
from pathlib import Path
import shutil

import audit_support_scanpaths_hybrid as base

SOURCE = Path(__file__).resolve().parent
BASE_SHA256 = '0b4cf4909f251634d6a15ea44bf2feb2ce8a847786abf3ad3bf3d53c8b6592f9'
FROZEN_COMPLETE_SHA256 = 'f3e7fc36931c59574aa9c74dad168265bbe6f7375565702336366bfadf190d41'


def frozen_complete_module():
    module = base.private_module(SOURCE/'audit_complete_supports_exact_anchors.py',
        FROZEN_COMPLETE_SHA256, '_private_carrier_complete_hybrid_audit')
    module.base, module.BASE_SHA256 = base, BASE_SHA256
    return module


def audit(directory, output, source_stl, part_cache=None):
    own = base.sha(__file__)
    if base.sha(base.__file__) != BASE_SHA256:
        raise ValueError('Hybrid full-build audit adapter identity changed')
    module = frozen_complete_module()
    result = module.audit(directory, output, source_stl, part_cache)
    output = Path(output).resolve()
    scanned = json.loads((output/'scanpaths/assessment.json').read_text())
    if (scanned.get('hybrid_envelope_store_verified') is not True or
            scanned.get('rational_part_contact_intersections') is not True or
            scanned.get('part_contact_intermediate_encoding') is not False):
        raise ValueError('Complete audit did not verify the mixed store and rational anchors')
    if (base.sha(__file__) != own or base.sha(base.__file__) != BASE_SHA256 or
            base.sha(module.__file__) != FROZEN_COMPLETE_SHA256):
        raise ValueError('Complete hybrid audit sources changed')
    shutil.copy2(__file__, output/Path(__file__).name)
    result.update(schema='carrier-complete-support-hybrid-store-v1',
        hybrid_envelope_store_verified=True, rational_part_contact_intersections=True,
        hybrid_store_sources_sha256=scanned['hybrid_store_sources_sha256'],
        frozen_complete_rational_audit_source_sha256=FROZEN_COMPLETE_SHA256,
        audit_source_sha256=own)
    (output/'assessment.json').write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--source-stl', type=Path, required=True)
    parser.add_argument('--part-cache', type=Path)
    args = parser.parse_args()
    result = audit(args.directory, args.output, args.source_stl, args.part_cache)
    print(json.dumps({key: result[key] for key in ('status', 'layers_audited',
        'every_material_group_exposed', 'rational_part_contact_intersections',
        'hybrid_envelope_store_verified')}))
    raise SystemExit(0 if result['status'] == 'passed' else 3)
