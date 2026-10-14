#!/usr/bin/env python3
"""Register each observed 935 blade independently before native PicoGK lofting."""
import argparse
import json
from pathlib import Path

from complete_candidate_rotor import completed_sections
from run_reconstruction import fresh, save, sha


def prepare(case_path, output):
    case = json.loads(Path(case_path).read_text())
    source = Path(case['sections_path'])
    if sha(source) != case['sections_sha256']:
        raise ValueError('Observed section hash mismatch')
    data = json.loads(source.read_text())
    names = sorted({row['blade_id'] for row in data['regions']})
    if len(names) != 9:
        raise ValueError('Nine separately identified observed blades required')
    regions = []
    for name in names:
        proposal = completed_sections(data, dict(case, reference_blade_id=name))
        row = next(row for row in proposal if row['id']==name)
        if any('periodic' in p['classification'] for p in row['provenance']):
            raise ValueError('No other blade may supply an acquired profile')
        regions.append(dict(row, blade_id=name, stations_source_units=case['stations_source_units']))
    out = fresh(output)
    save(out/'sections.json', {'schema':data['schema'],'source_sha256':data['source_sha256'],
        'observed_sections_sha256':sha(source),'preparation_case_sha256':sha(Path(case_path)),
        'classification':'nine_individually_observed_blades_with_missing_root_tip_hypotheses',
        'regions':regions,'blades':regions,'scale_verified':False})


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('case'); p.add_argument('new_output')
    a = p.parse_args(); prepare(a.case, a.new_output)
