#!/usr/bin/env python3
"""Independently reload native fixture exports against separately stated geometry."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re

import numpy as np
from OCP.TopAbs import TopAbs_SOLID


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for n in ["helper", "cad", "output"]: p.add_argument("--"+n, type=Path, required=True)
    a = p.parse_args()
    if a.output.exists(): raise ValueError("Existing native control inspection refused")
    if hashlib.sha256(a.helper.read_bytes()).hexdigest() != "3a2ddf947a1083399890dc167ec631fec0bce4d5a7a564613a765fcd95158658":
        raise ValueError("Independent source verifier changed")
    spec = importlib.util.spec_from_file_location("independent_native_controls", a.helper)
    helper = importlib.util.module_from_spec(spec); spec.loader.exec_module(helper)
    fixtures = [("shared-square-control.step", [[0,0,0],[1,0,0],[1,1,0],[0,1,0]], [[0,1,2],[0,2,3]]),
                ("point-contact-control.step", [[0,0,0],[1,0,0],[0,1,0],[-1,0,0],[0,-1,0]], [[0,1,2],[0,3,4]])]
    results = []
    for name, points, triangles in fixtures:
        path = a.cad/name
        result = helper.inspect_source(path, np.asarray(points, float), np.asarray(triangles), np.array([0,1]))
        if helper.indexed(helper.load(path), TopAbs_SOLID).Extent():
            raise ValueError("Unexpected solid in reference control")
        if not re.search(r"SI_UNIT\s*\(\s*\.MILLI\.\s*,\s*\.METRE\.\s*\)", path.read_text()):
            raise ValueError("Native STEP millimetre declaration absent")
        results.append({"fixture": name, **result, "actual_zero_solids": True, "explicit_STEP_millimetres": True})
    a.output.write_text(json.dumps({"status":"passed", "fixtures":results, "physical_acceptance":False}, indent=2)+"\n")
    print("Both actual native fixture exports match independently stated source geometry.")


if __name__ == "__main__": main()
