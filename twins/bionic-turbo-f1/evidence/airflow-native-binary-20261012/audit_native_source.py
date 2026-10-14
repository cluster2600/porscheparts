"""Compare original archive payloads with the native Linux compilation tree."""
import hashlib,json,subprocess,tarfile
from pathlib import Path
w=Path(__file__).parent
sha=lambda p:hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
receipt=json.loads((w/'source-receipt.json').read_text())
assert sha(w/'OpenFOAM-v2406.tgz')==receipt['archive_sha256']
expected={}
with tarfile.open(w/'OpenFOAM-v2406.tgz','r:gz') as archive:
    for member in archive:
        if member.isfile():expected[member.name]=hashlib.file_digest(archive.extractfile(member),'sha256').hexdigest()
manifest=json.loads((w/'baseline-build-v6/manifest.json').read_text())
cmd=['docker','run','--name','bionic-native-source-audit-20261012','--pull=never','--network','none','--read-only','--cap-drop','ALL','--pids-limit','32','--cpus','1','--memory','256m','--mount','type=volume,source=bionic-native-source-20261012,target=/native,readonly','--entrypoint','/bin/bash',manifest['image_id'],'-c','timeout 120 tar -cf - -C /native OpenFOAM-v2406']
checked={}
with (w/'source-audit-stderr.txt').open('x') as error:
    process=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=error)
    with tarfile.open(fileobj=process.stdout,mode='r|') as actual:
        for member in actual:
            if member.name in expected:
                assert member.isfile(),member.name
                digest=hashlib.file_digest(actual.extractfile(member),'sha256').hexdigest()
                assert digest==expected[member.name],member.name
                checked[member.name]=digest
    code=process.wait(timeout=140)
assert code==0 and set(checked)==set(expected)
result=dict(script_sha256=sha(Path(__file__)),archive_sha256=receipt['archive_sha256'],original_regular_files_verified=len(checked),all_original_regular_payloads_unchanged=True,command=cmd,exit_code=code,compiled_binary_sha256=sha(w/'baseline-build-v6/bin/rhoPimpleFoam'),flow_executed=False)
with (w/'source-audit.json').open('x') as f:json.dump(result,f,indent=2)
print(json.dumps(result))
