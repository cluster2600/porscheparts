"""Restore the exact V6f pad material lost by narrowing overlapping back ribs."""
import json
from pathlib import Path
import sys

SOURCE = Path(__file__).resolve().parent
ROOT = SOURCE.parents[3]
sys.path.insert(0, str(SOURCE.parent / 'bionic-20261011/correction-20261013'))
from corrected_cad import precise_volume, sha


def restore(source_folder, output):
    from build123d import Box, export_step, export_stl, import_step
    source_folder, output = Path(source_folder), Path(output)
    plan = json.loads((SOURCE / 'plan.json').read_text())
    baseline_path = ROOT / 'parts/993-eng-carrier-0001/derived/correction-20261013/carrier.step'
    assert sha(baseline_path) == plan['baseline_STEP_sha256']
    original_receipt = json.loads((source_folder / 'geometry.json').read_text())
    assert sha(source_folder / 'carrier.step') == original_receipt['geometry_sha256']['carrier.step']
    baseline, body = import_step(baseline_path), import_step(source_folder / 'carrier.step')
    region = Box(130, 72, 8)
    frozen, current = baseline & region, body & region
    missing, added = frozen - current, current - frozen
    assert added is None or abs(precise_volume(added)[0]) <= 1e-8
    assert missing is not None and precise_volume(missing)[0] > 0
    restored_volume = precise_volume(missing)[0]
    body = body + missing
    assert body.is_valid and len(body.solids()) == 1
    output.mkdir(parents=True, exist_ok=False)
    (output / 'source-snapshot.py').write_bytes(Path(__file__).read_bytes())
    export_step(body, output / 'carrier.step')
    export_stl(body, output / 'carrier.stl', tolerance=.06, angular_tolerance=.10)
    reread = import_step(output / 'carrier.step')
    assert reread.is_valid and len(reread.solids()) == 1
    volume, error = precise_volume(body)
    readback_volume, readback_error = precise_volume(reread)
    integration = {'adaptive_original_mm3': volume, 'adaptive_readback_mm3': readback_volume,
                   'estimated_relative_integration_errors': [error, readback_error],
                   'adaptive_relative_difference': readback_volume / volume - 1}
    (output / 'volume-integration.json').write_text(json.dumps(integration, indent=2) + '\n')
    assert abs(integration['adaptive_relative_difference']) < 1e-8
    settings = json.loads((source_folder / 'study.json').read_text())
    settings['design_id'] = 'carrier-design-20261016-candidate-restored'
    settings['postprocessing'] = {'action': 'Restore exactly the missing frozen V6f central pad material',
                                 'protected_box_mm': [130, 72, 8], 'restored_volume_mm3': restored_volume,
                                 'baseline_STEP_sha256': sha(baseline_path),
                                 'input_STEP_sha256': sha(source_folder / 'carrier.step'),
                                 'source_sha256': sha(__file__)}
    (output / 'study.json').write_text(json.dumps(settings, indent=2) + '\n')
    mass = volume * settings['material']['density_tonne_mm3'] * 1000
    receipt = {'design_id': settings['design_id'], 'volume_mm3': volume,
               'dense_reference_mass_kg': mass, 'mass_ceiling_pass': mass <= 1.2,
               'CAD_valid': True, 'solid_count': 1, 'STEP_readback_volume_match': True,
               'geometry_sha256': {name: sha(output / name) for name in ('carrier.step', 'carrier.stl')},
               'postprocessing': settings['postprocessing'],
               'dimension_source': 'provisional_study_contract_not_OEM',
               'fitment_validated': False, 'manufacturing_authorized': False}
    (output / 'geometry.json').write_text(json.dumps(receipt, indent=2) + '\n')
    assert receipt['mass_ceiling_pass']
    print(json.dumps(receipt))
    return receipt


if __name__ == '__main__':
    restore(sys.argv[1], sys.argv[2])
