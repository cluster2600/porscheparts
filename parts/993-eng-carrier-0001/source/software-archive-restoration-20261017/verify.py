"""Check the small immutable evidence capsule without a native runtime."""
import hashlib,json
from pathlib import Path

HERE=Path(__file__).resolve().parent
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(name):return json.loads((HERE/name).read_text())
def require(condition,message):
    if not condition:raise ValueError(message)

def main():
    manifest=read('manifest.json')
    require(manifest['schema']=='carrier-software-archive-restoration-evidence-capsule-1','Capsule schema differs')
    actual={str(p.relative_to(HERE))for p in HERE.rglob('*')if p.is_file()and p.name!='manifest.json'}
    require(actual==set(manifest['files_sha256']),'Capsule files missing or extra')
    for name,digest in manifest['files_sha256'].items():
        path=HERE/name
        require(not Path(name).is_absolute()and '..'not in Path(name).parts,'Capsule path escapes')
        require(not path.is_symlink()and path.resolve().is_relative_to(HERE)and sha(path)==digest,'Capsule file differs: '+name)
    for name,source in manifest['copied_from'].items():
        require(manifest['files_sha256'][name]==source['source_sha256'],'Copy identity differs: '+name)
    for name,digest in manifest['external_repository_dependencies_sha256'].items():
        require(sha(HERE/name)==digest,'Historical repository source changed: '+name)
    ccx=read('ccx/execution-receipt.json');py=read('pymesh/execution-receipt.json');cg=read('cgal-b4e8/execution-receipt.json')
    require(ccx['status']=='archive_accepted_and_native_smokes_passed_cached_image_explicit','CCX incomplete')
    require(ccx['inputs_and_image_preserved']and ccx['clean_daemon_claim']is False,'CCX provenance changed')
    require([x['actual_container_exit_code']for x in ccx['containers']]==[201,0],'Actual CCX codes differ')
    require(all(x['container_removed']for x in ccx['containers']),'CCX cleanup incomplete')
    for name,receipt in [('pymesh',py),('cgal-b4e8',cg)]:
        require(receipt['status']=='pinned_archive_restored_and_native_smoke_passed_no_carrier_admission',name+' incomplete')
        require(receipt['owned_scopes_inactive']and receipt['local_frozen_files_unchanged'],name+' cleanup/integrity incomplete')
        require(all(x.get('returncode')==0 for x in receipt['events']),name+' actual operation failed')
    require(py['runtime']['smoke']['volume_mm3']==4000,'PyMesh witness differs')
    require([r['actual_exact_volume_mm3']for r in cg['runtime']['smoke']['cases']]==['4000','2000','3200'],'CGAL exact volumes differ')
    require(all(r['passed']and r['source_face_lineage_complete']for r in cg['runtime']['smoke']['cases']),'CGAL witness gate refused')
    selected=read('cgal-b4e8/source-restoration-selection.json')
    require(selected['selection_not_full_original']is True and selected['original_source_sha256']==cg['runtime']['source_restoration_receipt_sha256'],'CGAL source selection differs')
    require(selected['source_file_count']==cg['runtime']['source_file_count']==17487,'CGAL source count differs')
    for name,receipt in [('ccx',ccx),('pymesh',py),('cgal-b4e8',cg)]:
        require(sha(HERE/name/'plan.json')==receipt['plan_sha256'],'Executed plan differs: '+name)
        require(sha(HERE/name/'run.py')==receipt['caller_sha256'],'Executed caller differs: '+name)
    print(json.dumps(dict(status='evidence_capsule_verified',files=len(actual),bytes=sum((HERE/n).stat().st_size for n in actual),
        actual_restoration_experiments=3,stable_cgal_offline_install_proved=False,global_carrier_admission=False)))

if __name__=='__main__':main()
