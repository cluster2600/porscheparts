"""Fixed native-BREP provenance only; no CAD import or mechanical calculation."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent

def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()

def verify(folder, metadata):
    folder = Path(folder)
    authority = json.loads((HERE / 'binding-authority.json').read_text())
    master_path = folder.parent / 'brep-master.json'
    body_path = folder.parent / 'carrier.brep'
    if any(not p.is_file() or p.is_symlink() for p in (master_path, body_path)):
        raise ValueError('Regular explicit native BREP and master description required')
    if sha(master_path) != authority['master_description_sha256']:
        raise ValueError('Native master description differs')
    master = json.loads(master_path.read_text())
    if (metadata.get('CAD_source_format') != 'BREP' or
        metadata.get('CAD_source_file') != 'carrier.brep' or 'STEP_sha256' in metadata or
        master['CAD_source_format'] != 'BREP' or
        metadata['BREP_sha256'] != authority['BREP_sha256'] or
        sha(body_path) != authority['BREP_sha256'] or
        metadata['CAD_master_receipt_sha256'] != authority['native_containment_receipt_sha256'] or
        metadata['CAD_volume_receipt_sha256'] != authority['native_volume_receipt_sha256'] or
        master['native_containment_receipt_sha256'] != metadata['CAD_master_receipt_sha256'] or
        master['native_volume_receipt_sha256'] != metadata['CAD_volume_receipt_sha256'] or
        metadata['OCC_import_reference_receipt_sha256'] != authority['nonadaptive_volume_receipt_sha256'] or
        master['nonadaptive_volume_receipt_sha256'] != authority['nonadaptive_volume_receipt_sha256'] or
        metadata['CAD_adaptive_master_volume_mm3'] != authority['adaptive_volume_mm3'] or
        metadata['OCC_import_check_reference_mm3'] != authority['nonadaptive_volume_mm3'] or
        metadata['CAD_volume_operator'] != authority['adaptive_operator'] or
        metadata['OCC_import_check_operator'] != authority['nonadaptive_operator']):
        raise ValueError('Native BREP mesh provenance differs')
    return dict(format='BREP', filename='carrier.brep', sha256=authority['BREP_sha256'],
                master_description_sha256=authority['master_description_sha256'],
                native_containment_receipt_sha256=authority['native_containment_receipt_sha256'],
                native_volume_receipt_sha256=authority['native_volume_receipt_sha256'],
                nonadaptive_volume_receipt_sha256=authority['nonadaptive_volume_receipt_sha256'],
                adaptive_volume_mm3=authority['adaptive_volume_mm3'], adaptive_operator=authority['adaptive_operator'],
                nonadaptive_import_reference_mm3=authority['nonadaptive_volume_mm3'],
                nonadaptive_import_operator=authority['nonadaptive_operator'],
                imported_CAD_absolute_identity_proved=False,
                STEP_exchange_qualified=False)
