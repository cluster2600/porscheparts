#!/usr/bin/env python3
"""Author a small synthetic workflow corpus; no repository crawling or real dimensions."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SYSTEM = (
    'You assist the M64 engineering project. Answer in English with one JSON object only. '
    'Follow the supplied project context. Never invent dimensions, material properties, '
    'physical qualification or spending approval. Do not execute commands.'
)
SOURCES = [
    'docs/architecture/README.md',
    'docs/architecture/engineering-workflow.md',
    'docs/decisions/0012-local-compute-gpu-last.md',
    'twins/picogk-station-demo/Program.cs',
]
FAMILIES = {
    'train': ['duct', 'bracket', 'shroud', 'plenum', 'cover', 'baffle', 'spacer', 'nozzle'],
    'valid': ['diffuser', 'enclosure'],
    'test': ['oil-cooler', 'cam-carrier', 'valve-guide', 'heat-exchanger'],
}
ROUTES = {
    'new_geometry': ('PicoGK', 'kali1'),
    'fluid_analysis': ('OpenFOAM Foundation 13', 'kali1'),
    'structural_analysis': ('CalculiX', 'kali2'),
    'usd_preparation': ('OpenUSD', 'mac'),
}
CONTEXT = (
    'Project routing: new_geometry -> PicoGK on kali1 (qualified runtime assumed); '
    'fluid_analysis -> OpenFOAM Foundation 13 on kali1; structural_analysis -> '
    'CalculiX on kali2; usd_preparation -> OpenUSD on mac. This routing does not '
    'claim a worker is currently reachable.'
)


def dumps(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=True, allow_nan=False)


def digest(path):
    with path.open('rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest()


def examples():
    """Family-disjoint synthetic templates, intentionally a narrow contract benchmark."""
    rows = []
    for split, families in FAMILIES.items():
        for index, family in enumerate(families):
            operation = list(ROUTES)[index % len(ROUTES)]
            tool, host = ROUTES[operation]
            scenarios = [
                ('route', f'{CONTEXT}\nFor the synthetic {family}, route {operation}. '
                 'Return exactly tool and host.', {'tool': tool, 'host': host}),
                ('units', f'A synthetic {family} fixture has a design length of {24 + index * 7} mm. '
                 'This is not a measured Porsche dimension. Convert to meters. '
                 'Return exactly value_m and provenance="synthetic".',
                 {'value_m': (24 + index * 7) / 1000, 'provenance': 'synthetic'}),
                ('material', f'The {family} has a visually assigned metal shader but no '
                 'sourced fatigue curve. Return exactly fatigue_curve=null and '
                 'physically_qualified=false. A shader is not material-test evidence.',
                 {'fatigue_curve': None, 'physically_qualified': False}),
            ]
            numerical = index % 4 != 0
            usd = index % 4 != 1
            approval = index % 4 != 2
            scenarios.append((
                'rental', f'For a {family} review, numerical_ready={str(numerical).lower()}, '
                f'usd_ready={str(usd).lower()}, budget_approved={str(approval).lower()}. '
                'Return exactly rental_eligible (true only if all three are true) '
                'and manufacturing_authorized=false. This answer cannot execute a rental.',
                {'rental_eligible': numerical and usd and approval, 'manufacturing_authorized': False},
            ))
            # Code is read as data. The evaluator never executes generated code.
            scenarios.append((
                'code', f'For the synthetic {family} C# input parser, the variable voxel is a float. '
                'Return exactly guard containing this C# rejection condition as a string: '
                '!float.IsFinite(voxel) || voxel < 0.1f || voxel > 0.5f. '
                'These are software-witness bounds, not engine design limits.',
                {'guard': '!float.IsFinite(voxel) || voxel < 0.1f || voxel > 0.5f'},
            ))
            for task, prompt, expected in scenarios:
                rows.append({
                    'id': f'{split}-{family}-{task}', 'split': split, 'family': family,
                    'task': task, 'source': SOURCES[3] if task == 'code' else SOURCES[1],
                    'messages': [{'role': 'system', 'content': SYSTEM},
                                 {'role': 'user', 'content': prompt},
                                 {'role': 'assistant', 'content': dumps(expected)}],
                    'expected': expected,
                })
    return rows


def validate(rows):
    if not isinstance(rows, list) or not rows:
        raise ValueError('dataset must be a nonempty list')
    ids, prompts, assigned = set(), set(), {}
    counts = dict.fromkeys(FAMILIES, 0)
    for row in rows:
        if row['split'] not in FAMILIES or row['family'] not in FAMILIES[row['split']]:
            raise ValueError('unexpected split or family')
        if row['id'] in ids or row['messages'][1]['content'] in prompts:
            raise ValueError('duplicate example or prompt')
        ids.add(row['id']); prompts.add(row['messages'][1]['content'])
        previous = assigned.setdefault(row['family'], row['split'])
        if previous != row['split']:
            raise ValueError('family leakage')
        if [m['role'] for m in row['messages']] != ['system', 'user', 'assistant']:
            raise ValueError('invalid conversation')
        if any(not isinstance(m['content'], str) or not m['content'].strip() for m in row['messages']):
            raise ValueError('empty or invalid message')
        if dumps(json.loads(row['messages'][2]['content'])) != dumps(row['expected']):
            raise ValueError('answer differs from expected output')
        if row['source'] not in SOURCES or not (ROOT / row['source']).is_file():
            raise ValueError('missing or unapproved source')
        counts[row['split']] += 1
    if counts != {'train': 40, 'valid': 10, 'test': 20}:
        raise ValueError(f'incomplete dataset: {counts}')
    return counts


def write_dataset(output):
    rows = examples()
    counts = validate(rows)
    output.mkdir(parents=True, exist_ok=False)
    for split in FAMILIES:
        with (output / f'{split}.jsonl').open('x') as handle:
            for row in rows:
                if row['split'] == split:
                    handle.write(dumps({'messages': row['messages']}) + '\n')
    (output / 'cases.json').write_text(json.dumps(rows, indent=2) + '\n')
    manifest = {
        'counts': counts, 'families': FAMILIES, 'synthetic': True,
        'license': 'Repository proprietary license; owner-authorized local training only',
        'source_hashes': {name: digest(ROOT / name) for name in SOURCES},
        'data_hashes': {p.name: digest(p) for p in sorted(output.iterdir())},
        'limitation': 'Shared templates across disjoint families; not a general coding benchmark',
    }
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    return manifest
