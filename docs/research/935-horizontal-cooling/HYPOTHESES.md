# Reverse-engineering hypotheses for the horizontal 935 system

Owner's decision, October 7, 2026: move forward with explicit hypotheses
rather than wait for all the dimensions. The target remains first the
historical 935 assembly, then the horizontal 993 adaptation.

A hypothesis carries a justification, the calculations that depend on it and
a way to reject it. The nominal under hypotheses can serve to prepare
calculations and a candidate CAD. It does not turn an interpolated surface
into a measurement and does not change the 17 independent interfaces still open.

| Identifier | Working hypothesis | Planned confrontation |
|---|---|---|
| H-SCALE | Provisionally reuse 1 mm per OBJ unit; compare 0.9 and 1.1 without imposing a nominal diameter. | Two independent dimensions on the same parts; consistency of the seats and the stack-up. A partial bore assumed to be standardized is not enough to calibrate. |
| H-DRIVE | Belt, horizontal shaft and angle drive to the vertical shaft; bevel gearing as the first internal candidate. | Architecture documented by [Gunnar Racing](https://www.gunnarracing.com/team/lola/stage4.htm). Photograph a disassembled angle drive; record axes, gear teeth, tooth counts and ratios. The exact type remains hypothetical. |
| H-RATIO | Compare three total rotor/engine speed ratios: 0.8, 1.0 and 1.2. | Measure both speeds simultaneously and record the pitch diameters/gear teeth. These are exploration points, not published Porsche ratios. |
| H-ROTOR | Use nine blades for the first kinematics, based on the nine acquired regions. | Check the repetition over the full revolution, then the roots, tips and back-side acquisitions; keep the localized repairs. |
| H-COUPLING | Provide a flexible coupling in the torque path; do not replace it outright with a rigid connection. | Usage account in the [Rennlist thread](https://rennlist.com/forums/911-turbo-930-forum/94486-935-users-flat-fan.html). Locate the component on a disassembled view and characterize its stiffness/damping. |

The bearing references, their preloads and the lubrication become
design variants to compare once the envelopes and load
paths are fitted. No commercial reference is presented as
the historical internal definition. The contract unknowns remain null.

## Kinematic campaign

The [existing calculator](../../../twins/935-horizontal-cooling-system-f0/source/build_system_twin.py)
now accepts `purpose: hypothesis_screen`. Each input used must
reference a `kind: assumption` source, with `locator` and `rejection_test`.
The status of the results is `hypothesis_calculation`. The synthetic tests
and the measured inputs keep their earlier checks; a hypothesis
cannot be promoted to evidence about the specimen.

Initial grid run: 3 engine speeds (3,000, 6,000, 8,000 rpm),
3 total ratios (0.8, 1.0, 1.2), 3 chosen diameters (250, 275, 300 mm),
9 blades and zero slip. **These diameters are neither measurements from the scans,
nor sourced 935/993 dimensions, nor an adopted calibration.** The decomposition
"variable belt ratio, gear ratio equal to 1" serves only
to factor the total ratio; it does not define the pulleys or gear teeth.

The 27 scenarios give 2,400–9,600 rpm at the rotor, 31.42–150.80 m/s
at the periphery and 360–1,440 Hz blade-passing frequency. These ranges describe the
chosen grid; they establish neither the allowable speed nor the
characteristics of the historical fan. Zero input uncertainties
mean here a fixed scenario point, not a metrological certainty.
The tool does not propagate uncertainties.

Minimal reproduction from the repository root, with no new software:

```python
from pathlib import Path
import importlib.util, itertools, json

study = Path('twins/935-horizontal-cooling-system-f0')
spec = importlib.util.spec_from_file_location('twin', study/'source/build_system_twin.py')
twin = importlib.util.module_from_spec(spec)
spec.loader.exec_module(twin)
output = Path('work/935-hypotheses-new')
output.mkdir(mode=0o700)  # new destination; do not overwrite an earlier batch
for rpm, ratio, diameter in itertools.product((3000, 6000, 8000), (0.8, 1.0, 1.2), (0.25, 0.275, 0.30)):
    case = json.loads((study/'operating-case.template.json').read_text())
    case.update(id=f'hypothesis-n{rpm}-r{ratio}-d{diameter}', purpose='hypothesis_screen')
    case['evidence'] = [{'id': 'H-KINEMATICS', 'kind': 'assumption',
        'locator': 'docs/research/935-horizontal-cooling/HYPOTHESES.md',
        'sha256': None, 'rejection_test': 'Compare calibrated geometry and independent tachometer measurements'}]
    values = dict(engine_rpm=rpm, belt_speed_ratio=ratio, belt_slip_fraction=0,
                  gear_speed_ratio=1, rotor_diameter=diameter, blade_count=9)
    for key, value in values.items():
        case['parameters'][key].update(value=value, uncertainty=0, evidence_ids=['H-KINEMATICS'])
    path = output/(case['id']+'.json')
    path.write_text(json.dumps(case, indent=2)+'\n')
    result = twin.build(path, output/case['id'])
    assert not result['manufacturing_release_allowed']
    assert result['models']['airflow']['values'] is None
```

The flow, aerodynamic torque, temperatures, inertia and imbalance
forces remain without results in this batch: their inputs are not
provided. The scanned CAD is not loaded by this kinematic campaign.
The [community research](COMMUNITY_RESEARCH.md) questions target
the information that will make it possible to reduce the hypotheses.

The [next campaign](HYPOTHESIS_TESTS.md) runs 160 scenarios of inertia,
imbalance, transmission, air network and thermal, plus a three-mesh CalculiX
centrifugal witness. It keeps its hypotheses distinct from the specimen
data.
