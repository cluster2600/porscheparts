"""Contrôle documentaire M64 ; ne certifie ni CAO ni fabrication."""
import json
from pathlib import Path


REQUIRED_INTERFACES = (
    'main_stud_axes', 'cylinder_register_diameter', 'cylinder_register_depth',
    'sealing_surface_definition', 'cam_carrier_axes',
    'oil_feed_and_return_interfaces', 'intake_and_exhaust_flange_interfaces',
    'seat_guide_and_spark_plug_interfaces',
)
REQUIRED_EVIDENCE = (
    'professional_engineering_review', 'approved_validation_plan',
    'material_process_qualification', 'physical_correlation',
)


def manufacturing_blockers(contract):
    blockers = []
    if contract.get('target_family') != 'M64':
        blockers.append('target_family must be M64')
    if not contract.get('selected_variant'):
        blockers.append('selected_variant is unknown')
    if contract.get('legacy_917_geometry_transferred') is not False:
        blockers.append('legacy 917 geometry is not an established M64 interface')
    sources = contract.get('sources', {})
    for name in REQUIRED_INTERFACES:
        item = contract.get('critical_interfaces', {}).get(name, {})
        for field in ('nominal', 'tolerance'):
            if item.get(field) is None:
                blockers.append(f'{name}.{field} is unknown')
        if item.get('source') not in sources:
            blockers.append(f'{name}.source is missing or unregistered')
    for name in REQUIRED_EVIDENCE:
        if not contract.get('release_evidence', {}).get(name):
            blockers.append(f'release_evidence.{name} is missing')
    return blockers


def validate(contract):
    """Refuse une affirmation de fabrication ; autorise un dossier incomplet honnête."""
    blockers = manufacturing_blockers(contract)
    if contract.get('manufacturing_authorized') is not False:
        if blockers:
            raise ValueError('Manufacturing claim rejected: ' + '; '.join(blockers))
        raise ValueError('This documentary validator cannot grant manufacturing release')
    references = contract.get('documented_reference_dimensions', {})
    if not references:
        raise ValueError('Documented references are missing')
    for name, item in references.items():
        if item.get('source') not in contract.get('sources', {}):
            raise ValueError(f'{name}: unregistered source')
        if not item.get('source_locator') or not item.get('applies_to'):
            raise ValueError(f'{name}: source locator or applicability is missing')
    return {'documentary_contract_valid': True, 'manufacturing_authorized': False,
            'manufacturing_blockers': blockers}


if __name__ == '__main__':
    contract_path = Path(__file__).with_name('interface-contract.json')
    print(json.dumps(validate(json.loads(contract_path.read_text())), indent=2))
