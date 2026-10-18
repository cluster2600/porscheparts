"""Verify compact report bytes and receipt joins only; no numerical/runtime import."""
import hashlib,json,re
from pathlib import Path
HERE=Path(__file__).resolve().parent
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def verify():
    inventory=read(HERE/'inventory.json')
    for name,row in inventory['files'].items():
        path=Path(name)
        assert not path.is_absolute() and '..' not in path.parts
        file=HERE/path
        assert file.is_file() and not file.is_symlink() and file.stat().st_size==row['bytes'] and sha(file)==row['sha256'],name
    actual={str(f.relative_to(HERE)) for f in HERE.rglob('*') if f.is_file() and '__pycache__' not in f.parts}
    assert actual==set(inventory['files'])|{'inventory.json'}
    provenance=read(HERE/'provenance.json')
    for name,row in provenance['evidence'].items():
        assert inventory['files'][name]=={k:row[k] for k in ['bytes','sha256']} and row['copy_byte_equal_at_creation'] is True
    root=read(HERE/'evidence/root-final-seal-review.json');proof=read(HERE/'evidence/semantic-overlay-proof.json');assessment=read(HERE/'evidence/seal-assessment.json');tool=read(HERE/'evidence/actual-tool-terminal.json')
    assert sha(HERE/'evidence/root-final-seal-review.json')=='7bdf0451287d2f1a202f827dca7e14f16322eee90cb4c7c6de739357ad3270df'
    assert root['semantic_proof_sha256']==assessment['semantic_overlay_proof']['sha256']==sha(HERE/'evidence/semantic-overlay-proof.json')
    assert root['owner_terminal_sha256']==provenance['full_work_owner']['sha256'] and root['native_audit_sha256']==assessment['native_audit_sha256']
    assert tool['actual_handle']==root['actual_tool']['handle']==89852 and tool['actual_outer_returncode']==root['actual_tool']['RC']==0 and tool['chunks']==root['actual_tool']['chunks']
    assert root['actual_all_array_canonical_sha256']==proof['actual_array_canonical_sha256'] and root['semantic_arrays']==proof['semantic_arrays']
    assert root['effective_unknown_final_face_ids']==proof['effective_unknown_final_face_ids'] and proof['effective_unknown_count']==assessment['unknown_final_faces']==22
    assert all(root[k] is False for k in ['strict12_reader_passed','continuous_coverage_claimed','process_anchor_admission'])
    assert all(proof[k] is True for k in ['all_positive_faces_pass_original_exact_oriented_identity','unknown_source_and_source_face_minus_one','unknown_positive_CSR_empty','history_never_positive_authority'])
    for target in re.findall(r'\]\(([^)]+)\)',(HERE/'README.md').read_text()):
        assert not target.startswith(('http:','https:')) and (HERE/target).is_file(),target
    return dict(status='compact_report_bytes_receipt_joins_and_links_verified_no_reanalysis',evidence_copies=len(provenance['evidence']),inventory_files=len(inventory['files']),inventory_bytes=sum(v['bytes'] for v in inventory['files'].values()),strict12_reader_passed=False,process_anchor_admission=False)
if __name__=='__main__':print(json.dumps(verify(),indent=2))
