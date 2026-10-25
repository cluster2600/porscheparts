"""Fetch the exact public archives and patch/test sources used by the corrected build."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import subprocess
import build_macos_ccx as sources
from build_native_spooles_fixed import UPSTREAM_MANIFEST


def main():
    p=argparse.ArgumentParser(__doc__);p.add_argument('--output',type=Path,required=True);p.add_argument('--manifest',type=Path,default=Path(__file__).resolve().parents[5]/'docs/reports/carrier-convergence-20261022/evidence/mesh-quality-20261025/spooles-upstream-review-015/source-manifest.json');a=p.parse_args()
    staging=a.output.with_name(a.output.name+'.fetching')
    if a.output.exists() or staging.exists():raise ValueError('Fresh source destination required')
    if sources.sha(a.manifest)!=UPSTREAM_MANIFEST:raise ValueError('Pinned upstream source manifest differs')
    jobs=[]
    for name in ['calculix-ccx_2.21.orig.tar.bz2','calculix-ccx_2.21-1.debian.tar.xz','spooles.2.2.tgz']:
        url,digest,_=sources.ASSETS[name];jobs.append((name,url,digest))
    for row in json.loads(a.manifest.read_text()):
        relative='upstream/'+row['repository'].split('/')[-1]+'/'+row['path'];url='https://raw.githubusercontent.com/'+row['repository']+'/'+row['commit']+'/'+row['path'];jobs.append((relative,url,row['sha256']))
    staging.mkdir(parents=True);(staging/'upstream').mkdir();(staging/'upstream/source-manifest.json').write_bytes(a.manifest.read_bytes())
    def fetch(job):
        name,url,expected=job;target=staging/name;target.parent.mkdir(parents=True,exist_ok=True)
        subprocess.run(['/usr/bin/curl','--fail','--location','--silent','--show-error','--proto','=https','--proto-redir','=https','--connect-timeout','15','--max-time','90','--max-filesize','16777216',url,'--output',str(target)],check=True,timeout=95)
        size=target.stat().st_size
        if size>16*1024**2 or sources.sha(target)!=expected:raise ValueError('Public source identity refused: '+name)
        return dict(path=name,url=url,sha256=expected,bytes=size)
    with ThreadPoolExecutor(max_workers=4)as pool:results=list(pool.map(fetch,jobs))
    (staging/'sources-ready.json').write_text(json.dumps(dict(status='all_pinned_public_sources_verified',upstream_manifest_sha256=UPSTREAM_MANIFEST,source_sha256=sources.sha(Path(__file__)),files=results),indent=2)+'\n');staging.rename(a.output);print(json.dumps(dict(status='all_pinned_public_sources_verified',files=len(results))))


if __name__=='__main__':main()
