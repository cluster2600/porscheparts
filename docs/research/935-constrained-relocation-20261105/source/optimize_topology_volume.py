"""Call the default native optimizer with retained region and raw-label audits."""
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
    spec = importlib.util.spec_from_file_location("retained_topology_audit", args.audited_recipe)
    audited = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(audited)
    native = gmsh.model.mesh.optimize

    def optimize(method="", force=False, niter=1, dimTags=None):
        assert method == "Netgen" and force and niter == 1
        record = {"retained_requested_method": method, "actual_method": "Gmsh default",
                  "native_method_argument": "", "niter_argument": niter,
                  "one_native_api_call": True, "physics_admitted": False}
        (output / "actual-method.json").write_text(json.dumps(record, indent=2) + "\n")
        native("", force=force, niter=niter, dimTags=dimTags or [])

    gmsh.model.mesh.optimize = optimize
    previous = sys.argv
    sys.argv = [str(args.audited_recipe), *forward]
    try:
        audited.main()
    finally:
        gmsh.model.mesh.optimize = native
        sys.argv = previous


if __name__ == "__main__":
    main()
