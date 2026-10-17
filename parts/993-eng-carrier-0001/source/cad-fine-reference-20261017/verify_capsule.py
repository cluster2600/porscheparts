"""Verify this documentary capsule offline; never import CAD or read its runtime."""
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    manifest=json.loads((HERE/'manifest.json').read_text())
    actual={str(p.relative_to(HERE)) for p in HERE.rglob('*') if p.is_file() or p.is_symlink()}
    if actual!=set(manifest['files_sha256'])|{'manifest.json'}:
        raise ValueError('Unexpected or missing capsule files')
    for name,digest in manifest['files_sha256'].items():
        relative=Path(name)
        if relative.is_absolute() or '..' in relative.parts:raise ValueError('Invalid capsule-relative path')
        path=HERE/relative
        if path.is_symlink() or sha(path)!=digest:raise ValueError('Capsule document changed: '+name)
    identity=json.loads((HERE/'reference-identity.json').read_text())
    mesh=json.loads((HERE/'evidence/mesh-assessment.json').read_text())
    execution=json.loads((HERE/'evidence/execution-receipt.json').read_text())
    if (execution['status']!='completed_reference_mesh_only' or execution['actual_child_exit_code']!=0 or
            execution['inputs_and_runtime_unchanged'] is not True or
            sha(HERE/'evidence/execution-receipt.json')!=identity['execution']['receipt_sha256']):
        raise ValueError('The original actual execution is not bound')
    if mesh['output_sha256']!=identity['NPZ']['sha256'] or mesh['STEP_sha256']!=identity['STEP_sha256']:
        raise ValueError('The reference identities differ')
    for name in ('vertices','triangles','complete_CAD_faces','parameters','exact_signed_volume_mm3'):
        if mesh[name]!=identity[name]:raise ValueError('The copied reference metadata differs: '+name)
    if identity['NPZ']['copied_into_capsule'] is not False or identity['runtime_files_copied']!=0:
        raise ValueError('Unexpected heavy artifact inclusion')
    if identity['BREP_global_error_bound_mm'] is not None or identity['global_admission'] is not False:
        raise ValueError('Unexpected scope expansion')
    print(json.dumps(dict(status='capsule_document_integrity_pass',documents_checked=len(manifest['files_sha256']),
                         manifest_sha256=sha(HERE/'manifest.json'),runtime_files_read=0,
                         geometric_calculation_or_renderer_executed=False),sort_keys=True))


if __name__=='__main__':main()
