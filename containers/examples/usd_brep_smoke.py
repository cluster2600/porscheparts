"""Synthetic exact-solid/OpenUSD witness; no part qualification."""

import argparse
import hashlib
import json
import math
import platform
from importlib.metadata import version
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    output = parser.parse_args().output
    output.mkdir(parents=True, exist_ok=False)

    import usd_brep

    assert version("usd-brep") == "1.0.1"
    sphere = usd_brep.primitives.create_sphere((0., 0., 0.), 1.)
    box = usd_brep.primitives.create_box((0., 0., 0.), 1., 1., 1.)
    # The default integration accuracy (0.001) is looser than this witness.
    assert math.isclose(sphere.volume(relative_accuracy=1e-7), 4 * math.pi / 3, rel_tol=1e-6)
    assert math.isclose(box.volume(relative_accuracy=1e-7), 1., rel_tol=1e-6)
    cut = usd_brep.booleans.boolean_difference(sphere, box)
    expected = 7 * math.pi / 6
    cut_volume = cut.volume(relative_accuracy=1e-7)
    assert math.isclose(cut_volume, expected, rel_tol=1e-6)
    stage = output / "cut.usda"
    usd_brep.usd.export_brep(cut, str(stage))
    (restored,) = usd_brep.usd.import_breps(str(stage))
    restored_volume = restored.volume(relative_accuracy=1e-7)
    assert math.isclose(restored_volume, expected, rel_tol=1e-6)
    report = {
        "status": "passed_synthetic_software_witness",
        "version": version("usd-brep"),
        "architecture": platform.machine(),
        "python": platform.python_version(),
        "units": "arbitrary_synthetic_modeling_units",
        "expected_volume": expected,
        "cut_volume": cut_volume,
        "restored_volume": restored_volume,
        "relative_tolerance": 1e-6,
        "usd_sha256": hashlib.sha256(stage.read_bytes()).hexdigest(),
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "manufacturing_qualified": False,
        "simready_validated": False,
    }
    (output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
