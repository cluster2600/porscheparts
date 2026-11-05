#!/usr/bin/env python3
"""Inspect only the four installed CAD/scientific wheel distributions."""
import argparse
import base64
import csv
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import sys

import OCP
import numpy
import scipy


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--venv", type=Path, required=True); p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    if a.output.exists(): raise ValueError("Existing runtime inspection refused")
    root = a.venv.resolve()
    if Path(sys.prefix).resolve() != root or platform.machine() != "x86_64" or sys.version_info[:3] != (3,12,11):
        raise ValueError("Wrong isolated runtime or platform")
    if "include-system-site-packages = false" not in (root/"pyvenv.cfg").read_text().lower():
        raise ValueError("Existing system site packages exposed")
    for module in [OCP,numpy,scipy]:
        if not Path(module.__file__).resolve().is_relative_to(root):
            raise ValueError("CAD/scientific module escaped isolated runtime")
    expected = {"cadquery-ocp-novtk":"7.9.3.1.1", "cadquery-ocp-proxy":"7.9.3.1.1", "numpy":"2.5.4", "scipy":"1.18.1"}
    packages = []
    for name, version in expected.items():
        distribution = importlib.metadata.distribution(name)
        if distribution.version != version: raise ValueError("Installed version differs from lock")
        records = [f for f in distribution.files if str(f).endswith(".dist-info/RECORD")]
        if len(records) != 1: raise ValueError("Ambiguous installed package record")
        record = Path(distribution.locate_file(records[0])); checked, unhashed = 0, 0
        with record.open(newline="") as stream:
            for filename, digest, size in csv.reader(stream):
                path = Path(distribution.locate_file(filename)).resolve()
                if not path.is_relative_to(root): raise ValueError("Package record escapes isolated runtime")
                if not digest:
                    unhashed += 1; continue
                algorithm, encoded = digest.split("=",1)
                if algorithm != "sha256": raise ValueError("Unexpected installed-file hash algorithm")
                expected_hash = base64.urlsafe_b64decode(encoded+"="*((-len(encoded))%4)).hex()
                if sha(path) != expected_hash or (size and path.stat().st_size != int(size)):
                    raise ValueError("Installed wheel file differs from RECORD")
                checked += 1
        packages.append({"package":name,"version":version,"record_sha256":sha(record),
                         "hashed_installed_files_verified":checked,"unhashed_record_entries":unhashed})
    result = {"status":"passed","python":sys.version.split()[0],"python_binary_sha256":sha(Path(sys.executable).resolve()),
              "machine":platform.machine(),"libc":platform.libc_ver(),"OCP_module_version":OCP.__version__,
              "numpy":numpy.__version__,"scipy":scipy.__version__,"packages":packages,
              "isolated_site_packages_confirmed":True,"entire_operating_system_fingerprinted":False,
              "physical_acceptance":False,"manufacturing_authorized":False}
    a.output.write_text(json.dumps(result,indent=2)+"\n")
    print("Four installed wheel distributions and isolated module origins verified.")


if __name__ == "__main__": main()
