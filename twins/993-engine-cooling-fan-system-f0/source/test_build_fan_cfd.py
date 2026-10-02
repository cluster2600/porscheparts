"""Run with python test_build_fan_cfd.py; no solver or GPU required."""
import hashlib
import json
import tempfile
from pathlib import Path

from build_fan_cfd import generate


with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    surface = root / "organic-fan-metres.stl"
    surface.write_bytes(b"audited surface fixture")
    report = root / "picogk-report.json"
    report.write_text(json.dumps({"input_parameters": {
        "outer_diameter_mm": 245, "housing_diameter_mm": 250, "depth_mm": 60,
        "alternator": {"geometry_status": "test_fixture"}}}))
    audit = root / "physicsnemo-surface-audit.json"
    audit.write_text(json.dumps({
        "status": "surface_audit_passed", "metres_export_matches_mm": True,
        "metres_surface_sha256": hashlib.sha256(surface.read_bytes()).hexdigest(),
        "picogk_report_sha256": hashlib.sha256(report.read_bytes()).hexdigest(),
    }))
    case = root / "case"
    try:
        generate(case, surface, 4200)
    except ValueError as error:
        assert "alternator" in str(error) and not case.exists()
    else:
        raise AssertionError("Missing alternator accepted without explicit isolated-rotor scope")
    generate(case, surface, 4200, rotor_only=True)
    assert json.loads((case / "fan-input.json").read_text())["installed_assembly_represented"] is False
    assert "radius 0.125" in (case / "system/snappyHexMeshDict").read_text()
    assert "0.036" in (case / "system/topoSetDict").read_text()
    assert "omega 4200 [rpm]" in (case / "constant/MRFProperties").read_text()
    assert "outlet {type totalPressure; p0 uniform 0;" in (case / "0/p").read_text()
    assert (case / "system/controlDict").read_text().count("operation sumMag;") == 2
    clockwise = root / "clockwise"
    generate(clockwise, surface, 4200, rotor_only=True, rotation_sign=-1)
    assert "omega -4200 [rpm]" in (clockwise / "constant/MRFProperties").read_text()
    assert json.loads((clockwise / "fan-input.json").read_text())["rpm"] == -4200
    try:
        generate(root / "invalid-sign", surface, 4200, rotor_only=True, rotation_sign=0)
    except ValueError:
        assert not (root / "invalid-sign").exists()
    else:
        raise AssertionError("Zero rotation sign accepted")
    for changed in (surface, report):
        original = changed.read_bytes()
        changed.write_bytes(original + b" ")
        try:
            generate(root / "rejected", surface, 4200, rotor_only=True)
        except ValueError:
            assert not (root / "rejected").exists()
        else:
            raise AssertionError("Changed geometry or report was accepted after audit")
        changed.write_bytes(original)
    stationary = root / "alternator-and-supports-metres.stl"
    stationary.write_bytes(b"audited stationary surface fixture")
    stationary_audit = json.loads(audit.read_text())
    stationary_audit["metres_surface_sha256"] = hashlib.sha256(stationary.read_bytes()).hexdigest()
    (root / "alternator-surface-audit.json").write_text(json.dumps(stationary_audit))
    assembly = root / "assembly"
    generate(assembly, surface, 4200, with_alternator=True)
    assert (assembly / "constant/geometry/alternator.stl").read_bytes() == stationary.read_bytes()
    assert "alternator {level (4 4)" in (assembly / "system/snappyHexMeshDict").read_text()
    assert '"(duct|sides|alternator)" {type noSlip;}' in (assembly / "0/U").read_text()
    for field in ("p", "k", "omega", "nut"):
        assert "duct|sides|alternator" in (assembly / "0" / field).read_text()
    stationary.write_bytes(b"changed geometry")
    try:
        generate(root / "changed-fixed", surface, 4200, with_alternator=True)
    except ValueError:
        assert not (root / "changed-fixed").exists()
    else:
        raise AssertionError("Unaudited stationary geometry accepted")
print("CFD input provenance and domain checks passed")
