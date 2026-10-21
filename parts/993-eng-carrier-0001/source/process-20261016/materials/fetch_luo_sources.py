"""Fetch only the three pinned, publicly licensed source files for the RT sensitivity."""
import argparse,hashlib,json,subprocess,zipfile
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__);p.add_argument('directory',type=Path);a=p.parse_args();a.directory.mkdir(parents=True,exist_ok=False);manifest=json.loads((Path(__file__).parent/'sources.json').read_text())
for item in manifest['files']:
    target=a.directory/item['filename'];subprocess.run(['curl','--silent','--show-error','--fail','--location','--proto','=https','--proto-redir','=https','--max-time','120',item['url'],'-o',str(target)],check=True);data=target.read_bytes();assert len(data)==item['bytes'] and hashlib.sha256(data).hexdigest()==item['sha256']
curves=a.directory/'curves';curves.mkdir()
with zipfile.ZipFile(a.directory/'stress-strain curves.zip') as z:
    assert set(z.namelist())==set(manifest['archive_members'])
    for name in manifest['archive_members']:
        assert Path(name).name==name;(curves/name).write_bytes(z.read(name))
(a.directory/'download-receipt.json').write_text(json.dumps({'license':manifest['license'],'source_manifest_sha256':hashlib.sha256((Path(__file__).parent/'sources.json').read_bytes()).hexdigest(),'files_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in a.directory.iterdir() if p.is_file()},'extract_archive_members':manifest['archive_members']},indent=2)+'\n');print('Downloaded and verified three public files; extracted four curve workbooks')
