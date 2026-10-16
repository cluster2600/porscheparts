"""Check real PostProcessor VTUs against the independent deviatoric invariant."""
import argparse
import hashlib
import json
from pathlib import Path

import meshio
import numpy as np


def invariant(tensor):
    deviator = tensor - np.eye(3) * np.trace(tensor) / 3
    return float(np.sqrt(1.5 * np.sum(deviator * deviator)))


def tensors():
    result = []
    for i, j in [(0, 1), (0, 2), (1, 2)]:
        value = np.zeros((3, 3))
        value[i, j] = value[j, i] = 1
        result.append([value])
    result += [[np.diag([3., 2., 1.])], [np.eye(3) * 7]]
    result.append([np.array([[3., -4., 3.], [-4., -2., 2.], [3., 2., 1.]])])
    result.append([np.array([[0., 0., -2.], [0., 0., 0.], [-2., 0., 0.]])])
    result.append([result[1][0], result[2][0] * 3])
    return result


def assess(directory):
    result = {"status": "passed", "physical_validation": False, "cases": []}
    for mode in ["mechanical", "coupled"]:
        for i, samples in enumerate(tensors()):
            path = directory / mode / f"witness.{i}.0.vtu"
            expected = np.mean([invariant(sample) for sample in samples])
            entry = {"mode": mode, "case": i, "expected_Pa": float(expected)}
            try:
                assert path.is_file(), "native VTU missing from output_dir"
                mesh = meshio.read(path)
                fields = [mesh.point_data["stress"]] if "stress" in mesh.point_data else mesh.cell_data["stress"]
                values = np.concatenate([np.asarray(field).ravel() for field in fields])
                assert values.size and np.isfinite(values).all(), "invalid stress field"
                entry.update(native_min_Pa=float(values.min()),
                             native_max_Pa=float(values.max()),
                             sha256=hashlib.sha256(path.read_bytes()).hexdigest())
                assert np.allclose(values, expected, rtol=2e-7, atol=2e-7), "incorrect stress invariant"
                entry.update(status="passed")
            except (AssertionError, FileNotFoundError, KeyError) as error:
                entry.update(status="failed", error=str(error))
                result["status"] = "failed"
            result["cases"].append(entry)
    return result


def self_check():
    expected = [np.sqrt(3), np.sqrt(3), np.sqrt(3), np.sqrt(3), 0,
                np.sqrt(106), 2 * np.sqrt(3), 2 * np.sqrt(3)]
    assert np.allclose([np.mean([invariant(t) for t in case]) for case in tensors()], expected)
    # Both historical indexing errors must be detected by these controls.
    xz, yz = tensors()[1][0], tensors()[2][0]
    assert invariant(xz) > 0
    assert not np.isclose(invariant(yz), np.sqrt(6))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    self_check()
    result = assess(args.directory)
    args.report.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"status": result["status"], "cases": len(result["cases"])}))
    raise SystemExit(0 if result["status"] == "passed" else 1)
