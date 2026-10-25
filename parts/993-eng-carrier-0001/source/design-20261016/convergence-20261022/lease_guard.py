"""Bounded owned Vast lease guard through the existing approved provider wrapper.

Arms before launch; only an atomically published exact launch receipt grants
ownership. Provider credentials are never read by this process.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

WRAPPER=Path('/Users/maxime/.local/bin/openbao-vastai')


def call(*args):
    r=subprocess.run([str(WRAPPER),*args],capture_output=True,text=True,timeout=45)
    if r.returncode:raise RuntimeError('Approved wrapper operation failed: '+args[0])
    return json.loads(r.stdout)


def main():
    p=argparse.ArgumentParser(__doc__);p.add_argument('--manifest',type=Path,required=True);a=p.parse_args();m=json.loads(a.manifest.read_text());base=a.manifest.parent
    if not 0<m['deadline_epoch']-m['created_epoch']<=3600 or m['budget_usd']!=2:raise ValueError('Fixed one-hour/two-dollar envelope required')
    cutoff=time.monotonic()+max(0,m['deadline_epoch']-time.time());receipt=base/'launch-receipt.json';(base/'guard-ready.json').write_text(json.dumps(dict(armed=True,pid=os.getpid(),deadline_epoch=m['deadline_epoch'],manifest_sha256=hashlib.sha256(a.manifest.read_bytes()).hexdigest()))+'\n')
    subprocess.Popen(['/usr/bin/caffeinate','-ims','-w',str(os.getpid())],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    identifier=None
    while True:
        if receipt.exists()and identifier is None:
            launch=json.loads(receipt.read_text())
            if launch['image']!=m['image']or launch['label']!=m['label']or launch['selected_offer']['id']!=m['offer_id']:raise ValueError('Launch ownership differs')
            identifier=launch['instance_id']
        if identifier is not None:
            try:
                inventory=call('instances');matches=[x for x in inventory if x['id']==identifier]
                if not matches:
                    (base/'guard-terminal.json').write_text(json.dumps(dict(status='owned_instance_verified_absent',instance_id=identifier,observed_epoch=time.time()))+'\n');return
                if len(matches)!=1 or matches[0]['label']!=m['label']or matches[0]['image']!=m['image']:raise ValueError('Provider ownership mismatch')
                if time.monotonic()>=cutoff or time.time()>=m['deadline_epoch']:
                    result=call('destroy',str(identifier),'--confirm');(base/'guard-destroy-result.json').write_text(json.dumps(result,indent=2)+'\n')
            except RuntimeError as error:(base/'guard-last-error.json').write_text(json.dumps(dict(error=str(error),epoch=time.time()))+'\n')
        elif time.monotonic()>=cutoff:raise RuntimeError('Deadline reached without an ownership receipt; inspect paid launch outcome')
        time.sleep(15)

if __name__=='__main__':main()
