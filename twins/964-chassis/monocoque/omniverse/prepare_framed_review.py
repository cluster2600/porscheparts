#!/usr/bin/env python3
"""Prepare a new review copy with explicit camera apertures; preserve geometry."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

from pxr import Sdf

from build_twin import validate
from capture_rtx import digest, verify_inputs

HERE = Path(__file__).resolve().parent


def prepare(source, output):
    source, output = source.resolve(), output.absolute()
    original = verify_inputs(source)
    if output.exists() or output.is_symlink():
        raise FileExistsError("Use a new review directory")
    with tempfile.TemporaryDirectory(prefix="964-framing-", dir=output.parent) as temp:
        staged = Path(temp) / "bundle"
        staged.mkdir()
        for name in original["outputs_sha256"]:
            shutil.copy2(source / name, staged / name)
        shutil.copy2(HERE / "camera-framing.usda", staged / "camera-framing.usda")
        for name in ("monocoque.usda", "interior.usda"):
            layer = Sdf.Layer.FindOrOpen(str(staged / name))
            layer.subLayerPaths.insert(0, "camera-framing.usda")
            layer.Save()
        report = validate(staged)
        subprocess.run(["usdchecker", "--strict", str(staged / "interior.usda")],
                       check=True, capture_output=True, text=True)
        if digest(staged / "geometry.usdc") != original["outputs_sha256"]["geometry.usdc"]:
            raise ValueError("Framing must not change the geometry")
        report.update({
            "inputs_sha256": {"source_validation.json": digest(source / "validation.json"),
                              "prepare_framed_review.py": digest(Path(__file__)),
                              "camera-framing.usda": digest(HERE / "camera-framing.usda")},
            "outputs_sha256": {p.name: digest(p) for p in sorted(staged.iterdir())},
            "change_scope": "Camera apertures and interior focal length only",
            "native_framing_verified": False,
        })
        (staged / "validation.json").write_text(json.dumps(report, indent=2) + "\n")
        verify_inputs(staged)
        if output.exists() or output.is_symlink():
            raise FileExistsError("Review output appeared during preparation")
        staged.rename(output)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    print(json.dumps(prepare(args.source, args.output), indent=2))
