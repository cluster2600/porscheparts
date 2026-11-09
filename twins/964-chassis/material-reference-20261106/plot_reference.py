"""Plot computed directional elasticity, never measured vehicle performance."""
import argparse
import importlib.util
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--result", type=Path, required=True)
parser.add_argument("--result-sha256", required=True)
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()
program = Path(__file__).with_name("check_elastic_reference.py")
spec = importlib.util.spec_from_file_location("checked_reference", program)
check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check)
if check.sha(args.result) != args.result_sha256:
    raise ValueError("Result hash changed")
data = json.loads(args.result.read_text())
if check.sha(program) != data["executed_script_sha256"] or not data["self_checks_passed"]:
    raise ValueError("Reference implementation or verification changed")
q = np.array(data["Q_MPa"])
angles = np.linspace(0, 180, 181)
moduli = np.array([1/np.linalg.inv(check.rotate_tensor(q, float(a)))[0, 0]/1000 for a in angles])
assert np.all(np.isfinite(moduli)) and np.min(moduli) > 0
assert np.allclose(moduli, moduli[::-1], rtol=check.EPS, atol=0)
assert abs(moduli[0] - 1/np.linalg.inv(q)[0, 0]/1000) < check.EPS
args.output.mkdir(parents=True, exist_ok=False)
fig, ax = plt.subplots(figsize=(9, 5.5), layout="constrained")
ax.plot(angles, moduli, color="#155e75", linewidth=2, label="UD lamina: computed rotation of source constants")
ax.axhline(data["effective_E_MPa"]/1000, color="#b45309", linestyle="--", linewidth=2,
           label="Equal 0 / +45 / -45 / 90 fractions: in-plane reference")
ax.set(xlabel="Fibre direction relative to loading axis (degrees)", ylabel="Computed Young modulus (GPa)",
       title="IM7 / 8552 UD 190 gsm, 35% RC — in-plane elastic reference", xlim=(0, 180), ylim=(0, 180),
       xticks=[0, 30, 60, 90, 120, 150, 180])
ax.grid(alpha=.2)
ax.legend(frameon=False, fontsize=9, loc="upper center")
fig.supxlabel("NCAMP Table 2-1, RTD measured means. No vehicle, bending, failure or cure validation.", fontsize=9)
for extension in ("png", "svg"):
    fig.savefig(args.output / ("elastic-reference."+extension), dpi=160)
plt.close(fig)
receipt = {"result_sha256": args.result_sha256, "plot_program_sha256": check.sha(Path(__file__)),
           "kind": "computed_elastic_reference_plot_not_photograph_or_Omniverse_capture",
           "images": {p.name: check.sha(p) for p in sorted(args.output.glob("elastic-reference.*"))},
           "physical_or_manufacturing_validation": False}
(args.output / "plot-receipt.json").write_text(json.dumps(receipt, indent=2)+"\n")
print(json.dumps(receipt))
