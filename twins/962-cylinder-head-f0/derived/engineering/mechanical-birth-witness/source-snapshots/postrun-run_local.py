"""Run one frozen witness in an already installed, read-only MOOSE runtime."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import time
from assess import SOURCE, assess_fields, node_reference, references, sha, tensor_reference


def freeze(output):
    output = Path(output)
    card = json.loads((SOURCE/"card.json").read_text())
    history = references(card)
    contract = dict(schema_version="1.0.0", classification=card["classification"],
        created_unix=time.time(), frozen_before_native_run=True, card=card,
        card_sha256=sha(SOURCE/"card.json"), input_sha256=sha(SOURCE/"mechanical-birth.i"),
        assessor_sha256=sha(SOURCE/"assess.py"), references=history,
        full_tensor_references=[{s:tensor_reference(h,s) for s in ("A","B") if s == "A" or h["born"]}
                                for h in history],
        full_nodal_end_references=[[
            dict(x=x,y=y,z=z,**node_reference(h,x,y,z)) for x in (0.,1.) for y in (0.,1.)
            for z in ((0.,5.,10.,15.,20.) if h["born"] else (0.,5.,10.))] for h in history])
    with (output/"frozen-contract.json").open("x") as stream:
        json.dump(contract,stream,indent=2);stream.write("\n")
    for name in ("mechanical-birth.i","card.json","assess.py"):
        shutil.copyfile(SOURCE/name,output/name)
    return output/"frozen-contract.json"


def reproduce(rootfs, output):
    rootfs, output = Path(rootfs).resolve(), Path(output).resolve()
    card=json.loads((SOURCE/"card.json").read_text())
    binary=rootfs/"opt/moose/bin/moose-opt"
    if sha(binary) != card["native_binary_sha256"]:
        raise ValueError("Exact existing MOOSE binary required")
    output.mkdir(parents=True,exist_ok=False)
    contract=freeze(output)
    inputs={p.name:sha(p) for p in output.iterdir() if p.is_file()}
    command=["bwrap","--unshare-user","--uid","0","--gid","0","--ro-bind",str(rootfs),"/",
        "--dev","/dev","--proc","/proc","--tmpfs","/tmp","--bind",str(output),"/tmp/work",
        "--unshare-net","--unshare-pid","--die-with-parent","--chdir","/tmp/work"]
    for key,value in {"OMP_NUM_THREADS":"1","OPENBLAS_NUM_THREADS":"1","OMPI_ALLOW_RUN_AS_ROOT":"1",
        "OMPI_ALLOW_RUN_AS_ROOT_CONFIRM":"1","OMPI_MCA_btl_vader_single_copy_mechanism":"none"}.items():
        command += ["--setenv",key,value]
    command += ["/bin/bash","-c",". /environment; exec moose-opt -i mechanical-birth.i"]
    cap=["systemd-run","--user","--scope","--quiet","-p","MemoryMax=2G","-p","MemorySwapMax=0",
        "-p","CPUQuota=200%","-p","TasksMax=128","-p","RuntimeMaxSec=115",
        "timeout","--signal=TERM","--kill-after=5s","100"]
    started=time.time();clock=time.monotonic()
    with (output/"native.log").open("xb") as stream:
        native=subprocess.run(cap+command,stdout=stream,stderr=subprocess.STDOUT,timeout=110)
    receipt=dict(returncode=native.returncode,started_unix=started,wall_seconds=time.monotonic()-clock,
        deadline_seconds=100,native_argv=cap+command,network="none",rootfs="read_only",
        binary_sha256=sha(binary),binary_unchanged=sha(binary)==card["native_binary_sha256"],
        input_sha256=inputs,inputs_unchanged=all(sha(output/n)==h for n,h in inputs.items()),
        artifact_sha256={p.name:sha(p) for p in sorted(output.iterdir()) if p.is_file()})
    with (output/"native-execution.json").open("x") as stream:
        json.dump(receipt,stream,indent=2);stream.write("\n")
    if native.returncode:
        raise RuntimeError("Native attempt refused; exact inputs and log retained")
    # A new direct local run has its own native receipt, not the original SSH capture.
    result=assess_fields(output,json.loads(contract.read_text()))
    result.update(native_receipt_sha256=sha(output/"native-execution.json"),
                  scope="Fresh local reproduction; original retained SSH capture not claimed")
    with (output/"assessment.json").open("x") as stream:
        json.dump(result,stream,indent=2);stream.write("\n")
    return result


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rootfs",required=True,type=Path)
    parser.add_argument("--output",required=True,type=Path)
    args=parser.parse_args();print(json.dumps(reproduce(args.rootfs,args.output)))
