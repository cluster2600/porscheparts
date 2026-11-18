"""Screen the owner's DDK and PorscheFanatics data for the blocking inputs of the 3D plan.

Read-only. It opens files of a local PorscheFanatics checkout, never writes there,
and prints counts, record ids, bases and part numbers only: no post text, no
member names and no member fields. The committed result is the `screen` block of
fillet-radius/3d-inputs.json; `--check` recomputes it and compares.

  python3 owner_data_screen.py --data ~/porschefanatics.com            # print the screen
  python3 owner_data_screen.py --data ~/porschefanatics.com --check    # compare with 3d-inputs.json
"""
import argparse
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INPUTS = ROOT / 'fillet-radius/3d-inputs.json'
DDK = 'data/forum-measurements.json'
PET = 'data/oem-listed.json'
PARTS = 'data/parts'
# Other structured files read in full for the same terms; each is reported with its hash and hit count.
OTHER = ['data/993-manual/technical-data.json', 'data/993-manual/torque-specs.json', 'data/993-manual/procedures.json',
         'data/builds.json', 'data/engine-reference-data.json', 'data/tuneup-specs.json', 'data/factory-literature.json',
         'data/magazine-archive.json', 'data/raw/factory-manuals/930-1976-1984.txt']
# The screens. Case-insensitive; English and German terms.
CHARGE_AIR = r'intercool|ladeluft|\bllk\b|charge[- ]?air|charge[- ]cool|boost(?!er)|ladedruck|wastegate|blow-?off|schubumluft'
JOINT = r'hose|schlauch|clamp|schelle|\bbead|fitting|spigot|coupler|union|sleeve|manschette'
STANDARD = r'DIN ?3017|DIN ?3021|DIN ?71802|ISO ?1179|ISO ?228|ISO ?6149|SAE ?J1926|SAE ?J20\b|bead roll|beaded|t-bolt clamp|hose barb'
FLOW_UNITS = r'kg/s|kg/h|m³/h|m3/h|m³/s|m3/s|\bcfm\b'
PET_PLATES = ['107-20', '107-45']


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def find(pattern, text):
    return re.search(pattern, text, re.I) is not None


def ddk(root):
    path = root / DDK
    data = json.loads(path.read_text())
    records = data['measurements']

    def fields(r, title=True):
        # PorscheFanatics' own words (subject, context) plus the stated value and models; the topic title is searched, never kept.
        parts = [r['subject'], r['context'], str(r.get('asStated', '')), ' '.join(r.get('models') or [])]
        return ' '.join(parts + ([r['post'].get('topicTitle', '')] if title else []))

    def cite(rows):
        return [{'id': r['id'], 'basis': r['basis']} for r in sorted(rows, key=lambda r: r['id'])]

    tagged = [r for r in records if set(r['generationIds']) & {'993', '964'}]
    counts = {}
    for category in ['flow', 'temperature', 'pressure']:
        counts[category] = sum(r['category'] == category for r in records)
    return {
        'path': DDK, 'sha256': sha(path), 'records': len(records), 'reviewed_on': data['reviewedOn'],
        'records_tagged_993': sum('993' in r['generationIds'] for r in records),
        'category_counts': counts,
        'charge_air_terms': cite(r for r in records if find(CHARGE_AIR, fields(r))),
        'joint_terms_on_964_or_993_records': cite(r for r in tagged if find(JOINT, fields(r, False))),
        'standard_terms': cite(r for r in records if find(STANDARD, fields(r, False))),
        'flow_units': cite(r for r in records if find(FLOW_UNITS, r['unit'] + ' ' + fields(r, False))),
    }


def pet(root):
    path = root / PET
    lines = [x for x in json.loads(path.read_text())['listings'] if x['generationId'] == '993' and x['petIllustration'] in PET_PLATES]
    plates = {}
    for plate in PET_PLATES:
        rows = [x for x in lines if x['petIllustration'] == plate]
        joints = sorted({(x['position'], x['oemReference']) for x in rows if find(r'hose|clamp|sleeve|o-ring|seal|gasket', x['description'])})
        plates[plate] = {'lines': len(rows), 'joint_lines': [{'position': p, 'reference': ref} for p, ref in joints]}
    return {'path': PET, 'sha256': sha(path), 'plates': plates}


def parts(root):
    hits, sized = [], []
    files = sorted((root / PARTS).glob('*.json'))
    for file in files:
        for e in json.loads(file.read_text()):
            if '993' not in [f.get('generationId') for f in e.get('fitment', [])]:
                continue
            text = e['name'] + ' ' + e.get('summary', '')
            if find(CHARGE_AIR, text) or (find(JOINT, text) and find(r'turbo|intercool|charge', text)):
                hits.append(e['id'])
                if re.search(r'\d+(\.\d+)?\s?mm\b', e['name']):
                    sized.append(e['id'])
    return {'path': PARTS, 'files': len(files), 'sha256': {f.name: sha(f) for f in files},
            'records_with_993_fitment_and_charge_air_or_joint_terms': len(hits), 'of_which_name_states_a_size_in_mm': sorted(sized)}


def others(root):
    rows = {}
    for name in OTHER:
        path = root / name
        text = path.read_text(errors='replace')
        rows[name] = {'sha256': sha(path), 'charge_air_hits': len(re.findall(CHARGE_AIR, text, re.I)),
                      'standard_hits': len(re.findall(STANDARD, text, re.I)), 'flow_unit_hits': len(re.findall(FLOW_UNITS, text, re.I))}
    return rows


def run(root):
    return {'patterns': {'charge_air': CHARGE_AIR, 'joint': JOINT, 'standard': STANDARD, 'flow_units': FLOW_UNITS},
            'ddk_forum_measurements': ddk(root), 'pet_transcription': pet(root), 'parts_catalogue': parts(root), 'other_files': others(root)}


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--data', type=Path, required=True, help='local PorscheFanatics checkout, read only')
    p.add_argument('--check', action='store_true')
    args = p.parse_args()
    result = run(args.data.expanduser())
    if args.check:
        committed = json.loads(INPUTS.read_text())['screen']['computed']
        if committed != result:
            raise SystemExit('screen differs from fillet-radius/3d-inputs.json')
        print('screen matches fillet-radius/3d-inputs.json')
    else:
        print(json.dumps(result, indent=2, ensure_ascii=False))
