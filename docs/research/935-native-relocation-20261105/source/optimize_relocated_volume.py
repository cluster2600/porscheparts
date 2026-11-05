"""Test native node relocation with the retained exact-array and tag audits."""
import argparse
import importlib.util
import json
from pathlib import Path
import sys

import gmsh


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audited-recipe", type=Path, required=True)
    args, forward = parser.parse_known_args()
    output = Path(forward[forward.index("--output") + 1])
    spec = importlib.util.spec_from_file_location("retained_native_tag_recipe", args.audited_recipe)
    audited = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(audited)
    native = gmsh.model.mesh.optimize

    def relocate(method="", force=False, niter=1, dimTags=None):
        assert method == "Netgen" and force and niter == 1
        receipt = {"retained_requested_method": method, "actual_method": "Relocate3D",
                   "niter_argument": niter, "one_native_api_call": True,
                   "new_topology_requested": False, "physics_admitted": False}
        (output / "actual-method.json").write_text(json.dumps(receipt, indent=2) + "\n")
        native("Relocate3D", force=force, niter=niter, dimTags=dimTags or [])

    gmsh.model.mesh.optimize = relocate
    previous = sys.argv
    sys.argv = [str(args.audited_recipe), *forward]
    try:
        audited.main()
    finally:
        gmsh.model.mesh.optimize = native
        sys.argv = previous


if __name__ == "__main__":
    main()
