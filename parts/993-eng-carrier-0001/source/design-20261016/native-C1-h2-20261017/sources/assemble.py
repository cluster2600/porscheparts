"""Assemble only the fixed three actual delta ZIPs and source utilities; no analysis."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
HERE=Path(__file__).resolve().parent

def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb')as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()
def write(path,value):
    with path.open('x')as f:json.dump(value,f,indent=2,allow_nan=False);f.write('\n')
def copy(source,target,digest):
    target.parent.mkdir(parents=True,exist_ok=True)
    with source.open('rb')as src,target.open('xb')as dst:shutil.copyfileobj(src,dst,1024*1024)
    if sha(target)!=digest:raise ValueError('Exact capsule copy differs')

def run(plan_sha,template_sha,receipt_sha):
    planpath=HERE/'pack-plan.json';templatepath=HERE/'manifest-template.json';receiptpath=HERE/'packaging.json'
    if (sha(planpath),sha(templatepath),sha(receiptpath))!=(plan_sha,template_sha,receipt_sha):raise ValueError('Reviewed plan/template/actual packaging receipt differs')
    plan=json.loads(planpath.read_text());template=json.loads(templatepath.read_text());receipt=json.loads(receiptpath.read_text())
    if (receipt['status']!='three_deterministic_archives_created_no_solver' or not receipt['originals_unchanged'] or
        receipt['plan_sha256']!=plan_sha or receipt['source_sha256']!='697277ea5c4ccc10cec323f6815409e4d948726f55b52045c17d1be99bfa1a9a' or
        set(receipt['archives'])!=set(plan['archives'])):raise ValueError('Actual unchanged packer receipt required')
    output=HERE/'capsule-001'
    if output.exists() or any(p.is_symlink()for p in [output,*output.parents]):raise ValueError('Fresh capsule required')
    auxiliary={name:HERE/'capsule-source'/name for name in ('README.md','restore.py','replay_analysis.py','selfcheck.py')}
    auxiliary.update({'source-derivation.json':HERE/'source-derivation.json','sources/package_owned.py':HERE/'package_owned.py',
        'sources/assemble.py':HERE/'assemble.py','verification/pack-plan.json':planpath,'verification/packaging.json':receiptpath})
    prepared={name:row for name,row in template['utility_sources'].items()}
    actual_sources={name:str(path.relative_to(HERE.parents[2])) for name,path in auxiliary.items() if not name.startswith('verification/')}
    if actual_sources!={name:row['source'] for name,row in prepared.items()} or any(sha(auxiliary[name])!=row['sha256'] for name,row in prepared.items()):
        raise ValueError('Reviewed utility source paths or whole SHA differ')
    needed=sum(row['bytes']for row in receipt['archives'].values())+sum(p.stat().st_size for p in auxiliary.values())+templatepath.stat().st_size
    if shutil.disk_usage(output.parent).free<needed:raise ValueError('Insufficient free space for one exact capsule copy')
    for name,row in receipt['archives'].items():
        source=Path(plan['destination'])/name
        if row['members']!=plan['archives'][name] or not row['bytes']<100000000 or source.stat().st_size!=row['bytes'] or sha(source)!=row['sha256']:
            raise ValueError('Actual ZIP identity, original member inventory or strict100MB bound differs')
    output.mkdir()
    for name,row in receipt['archives'].items():copy(Path(plan['destination'])/name,output/name,row['sha256'])
    for name,path in auxiliary.items():copy(path,output/name,prepared[name]['sha256'] if name in prepared else sha(path))
    if any(sha(auxiliary[name])!=row['sha256'] for name,row in prepared.items()):raise ValueError('A reviewed utility changed during assembly')
    template['archives']=receipt['archives']
    template['files_sha256']={name:sha(output/name)for name in auxiliary}
    write(output/'manifest.json',template)
    write(HERE/'assembly.json',dict(status='actual_delta_archives_and_sources_copied_no_reanalysis',manifest_sha256=sha(output/'manifest.json'),packaging_sha256=receipt_sha,
        inherited_C1_members=186,new_H2_members=sum(len(row['members'])for row in receipt['archives'].values()),new_solver_run=False,numerical_replay=False))
    print(json.dumps(dict(capsule=str(output),manifest_sha256=sha(output/'manifest.json'),assembly_sha256=sha(HERE/'assembly.json'))))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--plan-sha256',required=True);p.add_argument('--template-sha256',required=True);p.add_argument('--packaging-sha256',required=True)
    a=p.parse_args();run(a.plan_sha256,a.template_sha256,a.packaging_sha256)
