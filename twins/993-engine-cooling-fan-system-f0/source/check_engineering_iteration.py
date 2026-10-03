#!/usr/bin/env python3
"""Check original-model engineering receipts and prevent unsupported qualification."""
import gzip
import hashlib
import json
from pathlib import Path

FAN=Path(__file__).resolve().parents[1]
RESULT=FAN/'results/engineering-iteration-20261003'


def digest(data):return hashlib.sha256(data).hexdigest()


def check():
    manifest=json.loads((RESULT/'manifest.json').read_text())
    if manifest['private_scan_used'] or manifest['manufacturing_authorized']:
        raise ValueError('Publication must remain original-model unqualified work')
    for name,expected in manifest['files_sha256'].items():
        if digest((FAN/name).read_bytes())!=expected:raise ValueError(f'Engineering receipt changed: {name}')
    intake=json.loads((RESULT/'inputs/intake.json').read_text())
    for name in ['candidate-centrifugal.inp','candidate-analysis-mm.stl']:
        if digest(gzip.decompress((RESULT/'inputs'/f'{name}.gz').read_bytes()))!=intake[name]['source_sha256']:
            raise ValueError('Original-model input identity mismatch')
    contract=json.loads((FAN/'program/research/corpus/geometry/parameter-contract.json').read_text())
    ids={row['id'] for row in contract['parameter_dictionary']}
    modal=json.loads((RESULT/'modal/rotating-modes.json').read_text())
    if modal['validated_campbell_diagram'] or modal['mode_tracking_performed'] or modal['safe_speed_rpm'] is not None:
        raise ValueError('No mode-tracking/safe-speed validation evidence')
    if len(modal['cases'])!=4 or modal['assumptions']['source_deck_sha256']!=intake['candidate-centrifugal.inp']['source_sha256']:
        raise ValueError('Modal calculation coverage/provenance mismatch')
    for case in modal['cases']:
        for name in ['rotor.dat','log.ccx']:
            raw=gzip.decompress((RESULT/'modal'/case['case']/f'{name}.gz').read_bytes())
            if digest(raw)!=case['file_sha256'][name]:raise ValueError('Native modal receipt mismatch')
        if case['version']!='2.17':raise ValueError('Unexpected rotating-mode runtime')
    for case in ['eigenstrain-flat-0','eigenstrain-flat-0p001','eigenstrain-edge-0p001','eigenstrain-flat-0p0005']:
        report=json.loads((RESULT/'lpbf'/f'{case}-summary.json').read_text())
        prep=report['assumptions']
        if prep['source_deck_sha256']!=intake['candidate-centrifugal.inp']['source_sha256'] or set(prep['contract_ids'])-ids:
            raise ValueError('Manufacturing sensitivity input contract mismatch')
        if any(report[k] for k in ['process_calibrated','distortion_prediction_qualified','mesh_independence','manufacturing_authorized']):
            raise ValueError('Sensitivity cannot qualify a material/build')
        raw=gzip.decompress((RESULT/'lpbf'/f'{case}-log.ccx.gz').read_bytes())
        if digest(raw)!=report['file_sha256']['log.ccx'] or b'Job finished' not in raw:
            raise ValueError('Native manufacturing solve receipt mismatch')
    if set(modal['assumptions']['contract_ids'])-ids:raise ValueError('Unknown rotating-mode input contract ID')
    zero=json.loads((RESULT/'lpbf/eigenstrain-flat-0-summary.json').read_text())
    if any(s['maximum_displacement_mm'] or s['von_mises_max_MPa'] for s in zero['states']):raise ValueError('Zero strain control failed')
    benchmark=json.loads((RESULT/'lpbf/analytic-benchmark.json').read_text())
    for name,expected in benchmark['file_sha256'].items():
        if digest((RESULT/'lpbf'/name).read_bytes())!=expected:raise ValueError('Analytic benchmark changed')
    linearity=json.loads((RESULT/'lpbf/linearity.json').read_text())
    if benchmark['status']!='passed' or linearity['status']!='passed':raise ValueError('Required numerical controls failed')
    for orientation in ['flat','edge']:
        record=json.loads((RESULT/'usd'/f'{orientation}-usd-validation.json').read_text())
        if record['asset_sha256']!=digest((RESULT/'usd'/f'organic-e-{orientation}-release.usdc').read_bytes()):raise ValueError('Native-field asset changed')
        if record['all_generic_validator_issues'] or record['meters_per_unit']!=1 or record['up_axis']!='Z' or record['deformation_scale']!=1:
            raise ValueError('USD field metadata/validation mismatch')
        if any(record[k] for k in ['simready_validated','digital_twin_validated','process_calibrated','manufacturing_authorized','scan_included']):
            raise ValueError('Generic USD checks cannot qualify a physical twin')
    print('Engineering input identities, native receipts and qualification boundaries passed')


if __name__=='__main__':check()
