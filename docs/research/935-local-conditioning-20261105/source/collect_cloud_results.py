"""Freeze terminal task files and archive results; omit two duplicate Mac inputs."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import tarfile
import time


def sha(path):
    with path.open("rb") as stream:return hashlib.file_digest(stream,"sha256").hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--root",type=Path,required=True)
    a=p.parse_args();root=a.root.resolve();state=root.with_name(root.name+".collection.json")
    archive=root.with_name(root.name+"-results.tar.gz")
    assert not state.exists() and not archive.exists(),"Existing collection refused; inspect its recorded PID/state"
    assert (root/"terminal-state.json").exists() and (root/"result-manifest.json").exists()
    worker=json.loads((root/"worker-pid.json").read_text())["pid"]
    process=Path('/proc')/str(worker)/'stat'
    assert not process.exists() or process.read_text().rsplit(')',1)[1].split()[0]=='Z',"Worker still live"
    os.umask(0o077)
    status={"pid":os.getpid(),"stage":"hashing_terminal_files","started_epoch":time.time(),
            "source_sha256":sha(Path(__file__)),"archive":str(archive)}
    def save():
        tmp=state.with_suffix('.tmp');tmp.write_text(json.dumps(status,indent=2)+'\n');tmp.replace(state)
    save()
    try:
        files=[];omitted=[]
        for path in sorted(root.rglob('*')):
            assert not path.is_symlink(),"Task symlink refused"
            if not path.is_file() or path.name=="recovery-manifest.json":continue
            row={"path":str(path.relative_to(root)),"sha256":sha(path),"bytes":path.stat().st_size}
            if row["path"] in ("inputs.tar","candidate.npz"):
                row["reason"]="Duplicate input already retained and checksum-verified on the owner Mac"
                omitted.append(row)
            else:files.append(row)
        assert {row["path"] for row in omitted}=={"inputs.tar","candidate.npz"}
        manifest={"files":files,"omitted_duplicate_inputs":omitted,
                  "worker_terminal":json.loads((root/"terminal-state.json").read_text()),
                  "source_sha256":sha(Path(__file__)),"worker_confirmed_terminal_before_hashing":True}
        with (root/"recovery-manifest.json").open("x") as stream:stream.write(json.dumps(manifest,indent=2)+'\n')
        status["stage"]="archiving_terminal_files";save()
        with tarfile.open(archive,'w:gz',compresslevel=1) as target:
            for row in files:target.add(root/row['path'],arcname=row['path'],recursive=False)
            target.add(root/"recovery-manifest.json",arcname="recovery-manifest.json",recursive=False)
        status.update(stage="complete",archive_sha256=sha(archive),archive_bytes=archive.stat().st_size,
                      files=len(files),omitted_duplicate_inputs=len(omitted),completed_epoch=time.time())
        save();print(json.dumps(status),flush=True)
    except Exception as error:
        status.update(stage="failed",exception_type=type(error).__name__,completed_epoch=time.time())
        save();raise


if __name__=="__main__":main()
