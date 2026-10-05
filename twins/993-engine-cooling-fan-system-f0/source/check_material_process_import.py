#!/usr/bin/env python3
"""Check original material research hashes, record identity and admission boundaries."""
import csv
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1] / 'program/research/materials-20261003'


def read_csv(root, name):
    with (root/name).open(newline='') as stream:
        return list(csv.DictReader(stream))


def equivalent(rows, objects):
    if len(rows) != len(objects):
        raise ValueError('CSV/JSON record counts differ')
    for row, obj in zip(rows, objects):
        if set(row) != set(obj):
            raise ValueError('CSV/JSON fields differ')
        for key, value in obj.items():
            expected = '' if value is None else str(value)
            if row[key] != expected:
                raise ValueError(f'CSV/JSON value differs: {key}')


def check(root=ROOT):
    manifest = json.loads((root/'import-manifest.json').read_text())
    for item in manifest['files']:
        raw = (root/item['path']).read_bytes()
        if len(raw) != item['bytes'] or hashlib.sha256(raw).hexdigest() != item['sha256']:
            raise ValueError(f'Original imported research changed: {item["path"]}')
    data = json.loads((root/'material_evidence.json').read_text())
    process = json.loads((root/'process_simulation_inputs.json').read_text())
    equivalent(read_csv(root,'material_evidence.csv'),data['properties'])
    equivalent(read_csv(root,'process_parameters.csv'),process['parameters'])
    equivalent(read_csv(root,'simulation_requirements.csv'),process['requirements'])
    sources = read_csv(root,'source_manifest.csv')
    equivalent(sources,[{'source_id':key,**value} for key,value in data['sources'].items()])
    properties = data['properties']
    if len({r['id'] for r in properties}) != len(properties):
        raise ValueError('Duplicate material record identity')
    if any(r['source_id'] not in data['sources'] for r in properties):
        raise ValueError('Unresolved material source')
    if data['manufacturing_selection_confirmed'] or data['selected_machine'] is not None or data['release_admissible']:
        raise ValueError('Unqualified material selection or release claim')
    if any(r['admissible_for_release'] for r in properties) or any(r['release_admissible'] for r in process['parameters']):
        raise ValueError('Coupon/research properties must not become release allowables')
    if any(r['status'] != 'required_unresolved_for_target_route' for r in process['requirements']):
        raise ValueError('Process requirement advanced without target-route evidence')
    # Scenario names alone are not identities: the imported EOS naming is shared
    # by different alloys. Never silently join AlSi10Mg and AlF357 by this key.
    groups = {}
    for row in properties:
        groups.setdefault(row['scenario_id'],set()).add(row['material'])
    return {'status':'original_import_verified_not_engineering_admitted',
            'original_files':len(manifest['files']),'property_records':len(properties),
            'sources':len(sources),'process_parameters':len(process['parameters']),
            'unresolved_process_requirements':len(process['requirements']),
            'shared_scenario_names':{k:sorted(v) for k,v in groups.items() if len(v)>1},
            'required_join_key':['material','scenario_id','source_id','orientation','test_temperature_C','property'],
            'manufacturing_selection_confirmed':False,'release_admissible':False}


if __name__ == '__main__':
    print(json.dumps(check(),indent=2))
