"""Independent tiny-fixture array readback; no authoring or repair."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import resource
import signal


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def readback(source, derivative, expected, hashes, report):
    if Path(report).exists() or Path(report).is_symlink():
        raise FileExistsError("Fresh independent readback report required")
    paths = [Path(source), Path(derivative), Path(expected)]
    if [sha(p) for p in paths] != hashes:
        raise ValueError("Frozen fixture/input hash drift")
    import numpy as np
    from pxr import Usd, UsdGeom
    if Usd.GetVersion() != (0, 25, 5):
        raise ValueError("Recorded OpenUSD 25.5 required")
    reference = json.loads(paths[2].read_text())
    records = []
    for number, path in enumerate(paths[:2]):
        stage = Usd.Stage.Open(str(path), Usd.Stage.LoadAll)
        if not stage:
            raise ValueError("Fixture stage did not open")
        mesh = UsdGeom.Mesh(stage.GetPrimAtPath("/Head/Solid"))
        if (not mesh or str(stage.GetDefaultPrim().GetPath()) != "/Head"
                or UsdGeom.GetStageUpAxis(stage) != "Z"
                or UsdGeom.GetStageMetersPerUnit(stage) != 0.001
                or mesh.GetSubdivisionSchemeAttr().Get() != "none"
                or mesh.GetOrientationAttr().Get() != "rightHanded"
                or mesh.GetPrim().HasProperty("primvars:normals")
                or not np.array_equal(np.asarray(UsdGeom.XformCache().GetLocalToWorldTransform(
                    mesh.GetPrim())), np.eye(4))):
            raise ValueError("Known fixture frame changed")
        arrays = {"points": np.asarray(mesh.GetPointsAttr().Get()),
                  "face_counts": np.asarray(mesh.GetFaceVertexCountsAttr().Get()),
                  "face_indices": np.asarray(mesh.GetFaceVertexIndicesAttr().Get())}
        if number:
            if mesh.GetNormalsInterpolation() != "uniform":
                raise ValueError("Uniform normals required")
            arrays["expected_normals"] = np.asarray(mesh.GetNormalsAttr().Get())
        elif stage.GetRootLayer().GetAttributeAtPath("/Head/Solid.normals"):
            raise ValueError("Original fixture unexpectedly authors normals")
        for name, actual in arrays.items():
            wanted = reference[name]
            if (actual.dtype != np.dtype(wanted["dtype"])
                    or actual.shape != tuple(wanted.get("shape", [len(wanted["values"])]))
                    or actual.tobytes().hex() != wanted["bytes_hex"]):
                raise ValueError(f"Full known analytic array mismatch: {number}:{name}")
        records.append({"role": "derivative" if number else "source", "point_count": len(arrays["points"]),
                        "face_count": len(arrays["face_counts"]), "full_expected_bytes_equal": True,
                        "array_sha256": {k: hashlib.sha256(a.tobytes()).hexdigest()
                                         for k, a in arrays.items()}})
    if [sha(p) for p in paths] != hashes:
        raise ValueError("Fixture inputs changed during readback")
    result = {"status": "known_five_face_arrays_and_frame_pass", "input_sha256": hashes,
              "reader_sha256": sha(__file__), "stages": records,
              "full_layer_property_invariance": "separate frozen author checker required",
              "CLI_controls": {"cpu_affinity": [0, 1], "RLIMIT_AS_bytes": 4294967296,
                               "SIGALRM_seconds": 30, "outer_deadline_cleanup_required": True},
              "official_minimum_or_full_validator_run": False,
              "head_geometry_or_physics_acceptance": False, "manufacturing_authorized": False}
    with Path(report).open("x") as stream:
        json.dump(result, stream, indent=2, allow_nan=False); stream.write("\n")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ["source", "derivative", "expected", "report"]:
        parser.add_argument(name, type=Path)
    parser.add_argument("--source-sha256", required=True)
    parser.add_argument("--derivative-sha256", required=True)
    parser.add_argument("--expected-sha256", required=True)
    args = parser.parse_args()
    os.sched_setaffinity(0, {0, 1})
    resource.setrlimit(resource.RLIMIT_AS, (4294967296, 4294967296))
    def expired(signum, frame):
        raise TimeoutError("Independent tiny readback exceeded 30 seconds")
    signal.signal(signal.SIGALRM, expired); signal.alarm(30)
    try:
        print(json.dumps(readback(args.source, args.derivative, args.expected,
            [args.source_sha256, args.derivative_sha256, args.expected_sha256], args.report)))
    finally:
        signal.alarm(0)
