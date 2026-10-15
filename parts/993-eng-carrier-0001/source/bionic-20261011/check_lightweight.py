"""Independent readback against the frozen, explicitly assumed V1 interfaces."""
import hashlib
import json
import sys
from pathlib import Path

from build123d import Box, Cylinder, Pos, import_step


def check(folder, baseline):
    expected = 'b217328fc28fa1d517e9c771348b31b3f790612d25e8771eba7e4e2445316159'
    assert hashlib.sha256(baseline.read_bytes()).hexdigest() == expected
    original = import_step(baseline)
    candidate = import_step(folder/'carrier.step')
    assert candidate.is_valid and len(candidate.solids()) == 1
    density = 4.42e-6  # kg/mm3; dense Ti-6Al-4V reference, no porosity credit.
    mass = candidate.volume*density
    assert mass <= 1.2, f'{mass:.6f} kg exceeds the user ceiling'
    regions = {'central_mating_face': Pos(0, 0, -53.99)*Box(130, 200, 100)}
    for x in (-48, 48):
        for y in (-23, 23):
            regions[f'central_bolt_seat_{x}_{y}'] = Pos(x, y, 0)*Cylinder(12.5, 200)
    for x in (-20, 20):
        regions[f'central_opening_{x}'] = Pos(x, 0, 0)*Cylinder(12.5, 200)
    for x in (-280, 280):
        regions[f'end_bore_{x}'] = Pos(x, 0, 0)*Cylinder(8, 200, rotation=(90, 0, 0))
        for side in (-1, 1):
            regions[f'end_seat_{x}_{side}'] = Pos(x, side*72.99, 0)*Box(60, 100, 60)
    difference = {}
    for name, mask in regions.items():
        before, after = original & mask, candidate & mask
        if before is None:
            delta = 0 if after is None else after.volume
        elif after is None:
            delta = before.volume
        else:
            delta = (before-after).volume + (after-before).volume
        difference[name] = delta
        assert delta < 1e-4, (name, delta)
    # shortcut: these are provisional tool columns; measured sockets/approach paths must replace them before fitment review.
    for x in (-48, 48):
        for y in (-23, 23):
            for side in (-1, 1):
                tool = Pos(x, y, side*29.001)*Cylinder(12.5, 50)
                collision = candidate & tool
                assert collision is None or collision.volume < 1e-4
    report = {
        'candidate_STEP_sha256': hashlib.sha256((folder/'carrier.step').read_bytes()).hexdigest(),
        'baseline_STEP_sha256': expected,
        'reference_is': 'V1 assumed geometry, not measured OEM interfaces',
        'mass_scope': 'Carrier alone, excluding separate bracket, mountings and fasteners',
        'dense_reference_mass_kg': mass, 'target_kg': 1.0, 'ceiling_kg': 1.2,
        'target_met': mass <= 1.0, 'ceiling_met': True,
        'joint_region_symmetric_difference_mm3': difference,
        'assumed_central_pad_mm': 8, 'assumed_central_tool_radius_mm': 12.5,
        'eight_assumed_tool_columns_clear': True,
        'OEM_pad_thickness_mm': None, 'OEM_available_bolt_grip_mm': None,
        'OEM_fastener_compatibility_verified': False,
        'manufacturing_authorized': False,
    }
    (folder/'constraint-check.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    check(Path(sys.argv[1]), Path(sys.argv[2]))
