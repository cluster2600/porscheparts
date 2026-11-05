#!/usr/bin/env python3
"""Install a private offline CAD runtime, then qualify actual acquired-source exports."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys
import time


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ["root", "acquired"]: p.add_argument("--"+name, type=Path, required=True)
    p.add_argument("--contract-sha256", required=True)
    a = p.parse_args(); root = a.root; results = root/"results"; env = root/"venv"
    if results.exists() or env.exists(): raise ValueError("Existing isolated runtime or qualification refused")
    if sha(root/"input-contract.json") != a.contract_sha256:
        raise ValueError("Runtime contract changed")
    contract = json.loads((root/"input-contract.json").read_text())
    for item in contract["files"]:
        relative = Path(item["path"])
        if relative.is_absolute() or ".." in relative.parts: raise ValueError("Runtime input escapes bundle")
        f = root/relative
        if f.is_symlink() or f.stat().st_size != item["bytes"] or sha(f) != item["sha256"]:
            raise ValueError("Runtime source or wheel checksum failed: "+item["path"])
    if sha(a.acquired/"input-contract.json") != "86267413477431b7dceb1033c3da0f3071de87a5a532b5e7878b8d2335b91258":
        raise ValueError("Qualified acquired-input contract changed")
    if importlib.util.find_spec("OCP") is not None:
        raise ValueError("Expected unchanged base interpreter without OCP")
    results.mkdir()
    stages = []

    def run(name, argv, expected_reason=None):
        (results/(name+"-job.json")).write_text(json.dumps({"argv":list(map(str,argv)),"timeout_seconds":600},indent=2)+"\n")
        started = time.monotonic()
        with (results/(name+".log")).open("x") as stream:
            process = subprocess.run(list(map(str,argv)), stdout=stream, stderr=subprocess.STDOUT, timeout=600)
        entry = {"stage":name,"exit_code":process.returncode,"seconds":time.monotonic()-started}
        stages.append(entry)
        if expected_reason is None:
            if process.returncode: raise RuntimeError("Qualification stage failed: "+name)
        elif process.returncode == 0 or expected_reason not in (results/(name+".log")).read_text():
            raise RuntimeError("Reason-specific refusal failed: "+name)
        print(json.dumps(entry), flush=True)

    run("create-venv", [sys.executable,"-I","-m","venv",env])
    python = env/"bin/python"
    run("offline-install", [python,"-I","-m","pip","--isolated","--disable-pip-version-check","install",
                            "--no-index","--only-binary=:all:","--require-hashes","--find-links",root/"wheels","-r",root/"requirements.lock"])
    run("pip-check", [python,"-I","-m","pip","--isolated","--disable-pip-version-check","check"])
    run("inspect-runtime", [python,"-I",root/"source/inspect_runtime.py","--venv",env,"--output",results/"runtime.json"])
    run("raw-input-verification", [python,"-I",a.acquired/"source/verify_acquired_inputs.py","--root",a.acquired,
        "--contract-sha256","86267413477431b7dceb1033c3da0f3071de87a5a532b5e7878b8d2335b91258","--output",results/"acquired-verification.json"])
    common = ["--selection",root/"selection","--arrays",a.acquired/"arrays/exact-source-arrays.npz"]
    run("build-source-reference", [python,"-I",root/"source/reference_region.py","build",*common,
        "--helper",root/"source/build_source_shells.py","--output",results/"cad-001"])
    run("verify-actual-reference", [python,"-I",root/"source/reference_region.py","verify",*common,
        "--helper",root/"source/verify_source_shells.py","--step",results/"cad-001/observed-fourth-region.step","--output",results/"verification-001"])
    run("inspect-native-controls", [python,"-I",root/"source/check_native_controls.py","--helper",root/"source/verify_source_shells.py",
        "--cad",results/"cad-001","--output",results/"native-controls.json"])
    run("wrong-actual-STEP-refusal", [python,"-I",root/"source/reference_region.py","verify",*common,
        "--helper",root/"source/verify_source_shells.py","--step",results/"cad-001/shared-square-control.step","--output",results/"must-not-exist"],
        "Actual STEP moved source coordinates")
    if (results/"must-not-exist").exists(): raise ValueError("Invalid STEP published a verification")
    step = results/"cad-001/observed-fourth-region.step"
    if not re.search(r"SI_UNIT\s*\(\s*\.MILLI\.\s*,\s*\.METRE\.\s*\)", step.read_text()):
        raise ValueError("Actual acquired STEP lacks explicit millimetre units")
    if importlib.util.find_spec("OCP") is not None: raise ValueError("Base interpreter was modified")
    qualification = {"status":"passed", "stages":stages, "base_interpreter_OCP_still_absent":True,
                     "venv_isolated_from_existing_site_packages":True,"offline_hash_required_install":True,
                     "actual_STEP_sha256":sha(step),"explicit_STEP_millimetres":True,
                     "source_sha256":sha(__file__),"native_source_patch_only":True,
                     "complete_engineering_chain_prepared":False,"physical_acceptance":False,"manufacturing_authorized":False}
    (results/"qualification.json").write_text(json.dumps(qualification,indent=2)+"\n")
    print("ISOLATED_KALI_CAD_SOURCE_QUALIFICATION_OK",flush=True)


if __name__ == "__main__": main()
