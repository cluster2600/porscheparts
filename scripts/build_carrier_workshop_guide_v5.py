"""Retain the frozen v4 guide and publish only the v5 reproduction command."""
import argparse
import importlib.util
import json
from pathlib import Path

from build_part_workflow_guide import build, digest

BASE = Path(__file__).with_name('build_carrier_workshop_guide_v4.py')
BASE_SHA256 = 'c63efb29816cf83365286e9cdca004a4044b9fddd879e339c8c08521716c5d00'
SOURCE_SHA256 = digest(Path(__file__))
OLD_RECIPE = 'manufacturing/workflows/993-carrier-lpbf-v4.json'
NEW_RECIPE = 'manufacturing/workflows/993-carrier-lpbf-v5.json'


def verify_sources():
    if digest(BASE) != BASE_SHA256 or digest(Path(__file__)) != SOURCE_SHA256:
        raise ValueError('Carrier guide sources changed')


verify_sources()
_spec = importlib.util.spec_from_file_location('_carrier_workshop_v5_base', BASE)
_base = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_base)


def render(description, output):
    verify_sources()
    data = json.loads(description.read_text())
    if data['stages'][5]['id'] != 'delivery':
        raise ValueError('The six-stage carrier guide layout changed')
    command = data['stages'][5]['commands'][0]
    if command.split().count(OLD_RECIPE) != 1:
        raise ValueError('The v4 carrier reproduction command changed')
    data['stages'][5]['commands'][0] = command.replace(OLD_RECIPE, NEW_RECIPE)
    data['workshop_adapter'] = dict(source='scripts/build_carrier_workshop_guide_v5.py',
        sha256=SOURCE_SHA256, base_sha256=BASE_SHA256,
        retained_adapter=data.get('workshop_adapter'))
    description.write_text(json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False)+'\n')
    result = build(description, output)
    verify_sources()
    return result


# Substitute only the generic renderer of this private v4 module instance.
_base.build = render


def package(run):
    verify_sources()
    result = _base.package(run)
    verify_sources()
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    package(parser.parse_args().run)
