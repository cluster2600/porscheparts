"""Export a diagnostic raw Gmsh volume before quality optimization.

Reuse the frozen authoring recipe without editing it. An explicit API witness
checks Mesh.Optimize at the actual generate(3) call. Cell quality remains an
independent admission decision, never an inferred consequence of export.
"""
import argparse
import hashlib
import json
from pathlib import Path
import runpy
import sys

import gmsh


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--recipe", type=Path, required=True)
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--threads", type=int, required=True)
    args = parser.parse_args()
    assert sha(args.recipe) == "3cf167772ab4e4d90674693cb47e986e08c43e872db0b43c7529a533dc07dae6"
    assert gmsh.__version__ == "4.12.1" and 1 <= args.threads <= 8
    original_initialize = gmsh.initialize
    original_generate = gmsh.model.mesh.generate
    witnessed = []

    def initialize(*positional, **keywords):
        original_initialize(*positional, **keywords)
        gmsh.option.setNumber("Mesh.Optimize", 0)
        gmsh.option.setNumber("Mesh.OptimizeNetgen", 0)

    def generate(dim=3):
        options = {name: gmsh.option.getNumber(name) for name in (
            "Mesh.Optimize", "Mesh.OptimizeNetgen", "Mesh.Algorithm3D",
            "General.NumThreads", "Mesh.OptimizeThreshold")}
        assert dim == 3 and not witnessed
        assert options["Mesh.Optimize"] == options["Mesh.OptimizeNetgen"] == 0
        assert options["Mesh.Algorithm3D"] == 10
        assert options["General.NumThreads"] == args.threads
        witnessed.append(options)
        record = {"recipe_sha256": sha(args.recipe), "wrapper_sha256": sha(Path(__file__)),
                  "gmsh_version": gmsh.__version__, "options_at_generate": options,
                  "optimization_intentionally_disabled": True,
                  "quality_admission_weakened": False, "physics_admitted": False}
        with (args.output / "generation-options.json").open("x") as stream:
            stream.write(json.dumps(record, indent=2) + "\n")
        return original_generate(dim)

    gmsh.initialize = initialize
    gmsh.model.mesh.generate = generate
    old_argv = sys.argv
    sys.argv = [str(args.recipe), args.input, str(args.output), "--size", "2.0",
                "--algorithm", "10", "--threads", str(args.threads)]
    try:
        runpy.run_path(str(args.recipe), run_name="__main__")
        assert len(witnessed) == 1
    finally:
        gmsh.initialize = original_initialize
        gmsh.model.mesh.generate = original_generate
        sys.argv = old_argv


if __name__ == "__main__":
    main()
