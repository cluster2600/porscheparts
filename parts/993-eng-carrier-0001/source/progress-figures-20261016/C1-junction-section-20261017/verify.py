"""Complete stdlib integrity/provenance check; no CAD, plot runtime or rendering."""
import hashlib
import importlib.util
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
P003='work/carrier-C1-junction-section-figure-003/'
P004='work/carrier-C1-junction-section-figure-004/'
KEYS=['status','data_sha256','source_sha256','common_axes_and_aspect','checks',
      'annotation_ray_actual_XYZ_mm','coarse_source_peak','h2_peak_plotted',
      'runtime_files_sha256','no_geometry_modified','no_FEA']
def require(ok,message):
    if not ok:raise ValueError(message)
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(path):return json.loads(Path(path).read_text())
def check_inventory(root,files,excluded=()):
    actual={str(p.relative_to(root))for p in root.rglob('*')if p.is_file()and str(p.relative_to(root))not in excluded}
    require(actual==set(files),'Capsule file set differs')
    for name,row in files.items():
        p=Path(name);require(not p.is_absolute()and '..'not in p.parts,'Unsafe capsule path')
        path=root/p;require(not any(q.is_symlink()for q in [path,*path.parents]),'Symlink capsule path')
        require(path.stat().st_size==row['bytes']and sha(path)==row['sha256'],'Capsule size/full SHA differs')
def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def main():
    archive=read(HERE/'archive.json');files=archive['files'];check_inventory(HERE,files,('archive.json',))
    manifest=read(HERE/'sources/manifest.json');mirror=HERE/'sources/mirror'
    require(len(manifest['files_sha256'])==31 and sha(HERE/'sources/manifest.json')==archive['tested_mirror_manifest_sha256'],'Tested31-file mirror manifest differs')
    for name,h in manifest['files_sha256'].items():require(sha(mirror/name)==h,'A tested mirror payload differs')
    producer=mirror/P003/'figure.py';renderer=mirror/P004/'figure.py'
    require(sha(producer)=='284ebdcb1ef0a94c8fddbc1e51ebd38245c00c50649c2d4a9d5de44e3354d2f9'
        and sha(renderer)=='c8b60303eceefd1f8652bb2078174df138e1f36c4aa012ee7c3d7fe645bac4fd','Distinct producer/presentation identity differs')
    require(renderer.read_text().replace('top=.75,bottom=.31,wspace=.2','top=.75,bottom=.25,wspace=.2',1)==producer.read_text(),'Presentation differs beyond single layout literal')
    data=read(mirror/P003/'data-001/section-data.json');original=load(producer,'_pure_original003_profile_checks');original.check(data)
    context=original.context(*[read(HERE/'evidence'/name)for name in ['native-diagnostic-002.json','root-native-diagnostic-002.json','native-static-interpretation.json','root-qualified-h2-context.json']])
    require(context==data['diagnostic_context'],'Entire native diagnostic context differs')
    plan=read(HERE/'verification/plan-001.json');plan['capsule_root']=str(mirror)
    for key,rel in [('data','data-001/section-data.json'),('extraction_receipt','data-001/extraction-receipt.json'),('extraction_supervision','export-execution-001/execution-receipt.json')]:plan[key]=str(mirror/P003/rel)
    load(HERE/'sources/historical_closure.py','_declared_portable003_closure').closed_extraction(plan)
    ref=read(mirror/P004/'render-001/render-receipt.json');actual=read(HERE/'verification/replay-001/render-receipt.json')
    require(all(ref[k]==actual[k]for k in KEYS),'Eleven whole scientific records differ')
    require(len(actual['runtime_files_sha256'])==219 and actual['runtime_files_sha256']==plan['runtime_sha256'],'Historical219-file plotting authority differs')
    for name,h in ref['outputs_sha256'].items():require(sha(HERE/name)==h==sha(mirror/P004/'render-001'/name),'Whole final export differs')
    portable=read(HERE/'verification/replay-001/portable-replay-receipt.json');supervision=read(HERE/'verification/replay-execution-001/execution-receipt.json');root=read(HERE/'verification/root-terminal-review-001.json')
    require(supervision['status']=='executed'and supervision['actual_returncode']==0 and supervision['direct_child_reaped']
        and not supervision['final_group_members']and supervision['sources_and_plan_unchanged']and not supervision['timeout']and not supervision['interrupted'],'Actual portable group was not successfully closed')
    require(root['actual_tool_RC']==0 and root['supervision_sha256']==sha(HERE/'verification/replay-execution-001/execution-receipt.json')
        and root['portable_replay_receipt_sha256']==sha(HERE/'verification/replay-001/portable-replay-receipt.json')
        and root['terminal_sha256']==sha(HERE/'verification/terminal-collection-001.json')
        and root['eleven_entire_scientific_record_keys_equal']==portable['whole_scientific_record_keys_equal']==KEYS
        and root['all3_exports_BYTE_equal_original004']==portable['whole_exports_sha256']==ref['outputs_sha256'],'Root actual replay joins differ')
    qa=read(mirror/P004/'root-render-terminal-review-001.json')
    require(qa['actual_tool_RC']==0 and qa['actual_PNG_view']and qa['actual_PDF_sips_and_view']
        and root['source004_actual_PNG_and_PDF_visual_QA_sha256']==sha(mirror/P004/'root-render-terminal-review-001.json'),'Root actual004 visual QA differs')
    history=read(HERE/'history/layout003/root-render-terminal-review-001.json')
    require(history['publication_GO']is False and history['presentation_revision_needed']is True,'Historical003 layout refusal was lost')
    print(json.dumps(dict(status='verified_actual_junction_picture25_capsule',payloads=len(files),tested_mirror_payloads=31,
        native_profile_edges=[s['edge_count']for s in data['sections']],all11_records_and3_exports_equal=True,
        portable_scope='drawing of already sampled native profiles',CAD_parents_included=False,
        current_installed_runtime_rehashed=False,historical_runtime_files=219,no_native_or_render=True)))

if __name__=='__main__':main()
