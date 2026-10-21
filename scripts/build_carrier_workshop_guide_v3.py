"""Reuse frozen carrier admission checks and publish the v3 reproduction command."""
import argparse
import importlib.util
import json
from pathlib import Path

from build_part_workflow_guide import build, digest

BASE = Path(__file__).with_name('build_carrier_workshop_guide_v2.py')
BASE_SHA256 = 'b019281ec19c5d71c0ee909c579b8cf65c6afa7c368caf3379768eaa04319ff4'
SOURCE_SHA256 = digest(Path(__file__))
OLD_RECIPE = 'manufacturing/workflows/993-carrier-lpbf-v2.json'
NEW_RECIPE = 'manufacturing/workflows/993-carrier-lpbf-v3.json'
if digest(BASE) != BASE_SHA256:
    raise ValueError('The frozen carrier guide admission source changed')
_spec = importlib.util.spec_from_file_location('_carrier_workshop_v3_base', BASE)
_base = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_base)


def render(description, output):
    data = json.loads(description.read_text())
    if data['stages'][3]['id'] != 'supports' or data['stages'][5]['id'] != 'delivery':
        raise ValueError('The six-stage carrier guide layout changed')
    command = data['stages'][5]['commands'][0]
    if command.split().count(OLD_RECIPE) != 1:
        raise ValueError('The frozen carrier reproduction command changed')
    data['stages'][5]['commands'][0] = command.replace(OLD_RECIPE, NEW_RECIPE)
    data['stages'][3]['purpose'] = (
        'Placer la pièce à plat et générer ses supports avec leurs interfaces de contact. '
        'Le dossier conserve les surfaces réellement calculées, leurs contrôles et leurs trajectoires.')
    data['workshop_adapter'] = dict(source='scripts/build_carrier_workshop_guide_v3.py',
                                   sha256=SOURCE_SHA256, base_sha256=BASE_SHA256)
    description.write_text(json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False)+'\n')
    return build(description, output)


# The private module keeps the frozen public v2 builder and its callers intact.
_base.build = render


def package(run):
    if digest(BASE) != BASE_SHA256 or digest(Path(__file__)) != SOURCE_SHA256:
        raise ValueError('Carrier guide sources changed before packaging')
    result = _base.package(run)
    if digest(BASE) != BASE_SHA256 or digest(Path(__file__)) != SOURCE_SHA256:
        raise ValueError('Carrier guide sources changed during packaging')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    package(parser.parse_args().run)
