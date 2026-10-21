"""Complete support audit with rational part contacts and every-group exposure."""
import argparse
import importlib.util
import json
from pathlib import Path
import shutil

import audit_support_scanpaths_exact_anchors as base

SOURCE = Path(__file__).resolve().parent
BASE_SHA256 = 'fb47084b163648df7eac3f99b7c2fb2a9982ac48b919bef31cb84b68b77dfd06'
FROZEN_COMPLETE_SHA256 = '4eac35d2de9702b6871b4829cff38fbff3a4e71387f93edab17bd22ce8d7a7a9'


def frozen_complete_module():
    path = SOURCE/'audit_complete_supports_both.py'
    if base.sha(path) != FROZEN_COMPLETE_SHA256:
        raise ValueError('The frozen every-group complete audit changed')
    spec = importlib.util.spec_from_file_location('_isolated_complete_rational_anchor_audit', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.base, module.BASE_SHA256 = base, BASE_SHA256
    return module


def audit(directory, output, source_stl, part_cache=None):
    own = base.sha(__file__)
    if base.sha(base.__file__) != BASE_SHA256:
        raise ValueError('Rational part contact adapter identity changed')
    module = frozen_complete_module()
    result = module.audit(directory, output, source_stl, part_cache)
    output = Path(output).resolve()
    scanned = json.loads((output/'scanpaths/assessment.json').read_text())
    if (scanned.get('rational_part_contact_intersections') is not True or
            scanned.get('part_contact_intermediate_encoding') is not False):
        raise ValueError('The complete audit did not use rational part contacts')
    if (base.sha(__file__) != own or base.sha(base.__file__) != BASE_SHA256 or
            base.sha(module.__file__) != FROZEN_COMPLETE_SHA256):
        raise ValueError('Complete rational contact audit sources changed')
    shutil.copy2(__file__, output/Path(__file__).name)
    result.update(schema='carrier-complete-support-exact-anchors-v1',
        rational_part_contact_intersections=True, part_contact_intermediate_encoding=False,
        encoded_anchor_scope=scanned['encoded_anchor_scope'],
        frozen_complete_audit_source_sha256=FROZEN_COMPLETE_SHA256,
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
    print(json.dumps({key: result[key] for key in
                     ('status', 'layers_audited', 'every_material_group_exposed', 'rational_part_contact_intersections')}))
    raise SystemExit(0 if result['status'] == 'passed' else 3)
