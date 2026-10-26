"""Optional native OpenTURNS and OpenMDAO controls, separate from carrier qualification."""

from __future__ import annotations

import argparse
import importlib.metadata
from pathlib import Path
import sys

from ft_common import HERE, ROOT, finite, load, new_directory, receipt, sha256, write


def evaluate_samples(samples, evaluator):
    outputs = []
    for sample in samples:
        values = [finite(x) for x in sample]
        outputs.append([finite(evaluator(values))])
    return outputs


def sensitivity(output):
    import openturns as ot

    output = new_directory(output)
    ot.RandomGenerator.SetSeed(2600)
    sample_count = 8192
    distribution = ot.JointDistribution([ot.Uniform(-1, 1), ot.Uniform(-1, 1)])
    design = ot.SobolIndicesExperiment(distribution, sample_count, False).generate()
    values = ot.Sample(evaluate_samples(design, lambda x: x[0] + 2 * x[1]))
    algorithm = ot.SaltelliSensitivityAlgorithm(design, values, sample_count)
    indices = list(algorithm.getFirstOrderIndices())
    passed = all(
        abs(finite(value) - expected) <= 0.03
        for value, expected in zip(indices, [0.2, 0.8])
    )
    report = receipt(
        "openturns",
        "passed" if passed else "failed",
        [],
        checks={
            "indices": indices,
            "expected": [0.2, 0.8],
            "absolute_tolerance": 0.03,
            "seed": 2600,
            "base_sample_count": sample_count,
            "version": importlib.metadata.version("openturns"),
        },
        limitations=[
            "Synthetic additive model; no carrier probability distribution or reliability claim."
        ],
    )
    write(output / "receipt.json", report)
    if not passed:
        raise ValueError("analytical sensitivity control failed")
    return report


def optimization(output, deflection_limit=0.01):
    import openmdao.api as om

    output = new_directory(output).resolve()
    finite(deflection_limit, positive=True)

    class Beam(om.ExternalCodeComp):
        def setup(self):
            self.add_input("height", val=0.03, units="m")
            self.add_output("mass", val=1.0, units="kg")
            self.add_output("deflection", val=0.001, units="m")
            self.declare_partials("*", "*", method="fd")
            self.iteration = 0
            self.options["timeout"] = 10.0

        def compute(self, inputs, outputs):
            folder = new_directory(output / f"evaluation-{self.iteration:04}")
            self.iteration += 1
            values = {
                "length": 1.0,
                "width": 0.05,
                "height": finite(float(inputs["height"][0]), positive=True),
                "force": 10.0,
                "modulus": 70e9,
                "density": 2700.0,
                "units": {
                    "length": "m",
                    "force": "N",
                    "modulus": "Pa",
                    "density": "kg/m3",
                },
            }
            write(folder / "input.json", values)
            self.options["command"] = [
                sys.executable,
                str(HERE / "ft_beam_solver.py"),
                "--input",
                str(folder / "input.json"),
                "--output",
                str(folder / "output.json"),
            ]
            self.options["external_input_files"] = [str(folder / "input.json")]
            self.options["external_output_files"] = [str(folder / "output.json")]
            self.stdout = str(folder / "stdout.log")
            self.stderr = str(folder / "stderr.log")
            super().compute(inputs, outputs)
            result = load(folder / "output.json")
            outputs["mass"] = finite(result["mass"], positive=True)
            outputs["deflection"] = finite(result["deflection"], positive=True)

    problem = om.Problem(reports=False)
    problem.model.add_subsystem("beam", Beam())
    problem.driver = om.ScipyOptimizeDriver(
        optimizer="SLSQP", disp=False, tol=1e-9, maxiter=60
    )
    problem.model.add_design_var("beam.height", lower=0.005, upper=0.05, ref=0.01)
    problem.model.add_objective("beam.mass")
    problem.model.add_constraint(
        "beam.deflection", upper=deflection_limit, ref=deflection_limit
    )
    problem.setup()
    failed = not problem.run_driver().success
    height = finite(float(problem.get_val("beam.height")[0]), positive=True)
    mass = finite(float(problem.get_val("beam.mass")[0]), positive=True)
    problem.cleanup()
    # Independent closed form and independent replay outside the optimizer.
    expected = (4 * 10.0 / (70e9 * 0.05 * deflection_limit)) ** (1 / 3)
    from ft_beam_solver import solve

    replay = solve(
        {
            "length": 1.0,
            "width": 0.05,
            "height": height,
            "force": 10.0,
            "modulus": 70e9,
            "density": 2700.0,
            "units": {"length": "m", "force": "N", "modulus": "Pa", "density": "kg/m3"},
        }
    )
    passed = (
        not failed
        and abs(height / expected - 1) <= 0.005
        and replay["deflection"] <= deflection_limit * 1.000001
        and abs(replay["mass"] - mass) <= 1e-8
    )
    report = receipt(
        "openmdao",
        "passed" if passed else "failed",
        [],
        checks={
            "height_m": height,
            "analytical_height_m": expected,
            "relative_tolerance": 0.005,
            "mass_kg": mass,
            "independent_replay": replay,
            "optimizer_success": not failed,
            "version": importlib.metadata.version("openmdao"),
        },
        limitations=["Synthetic beam; no carrier geometry changed or optimized."],
    )
    write(output / "receipt.json", report)
    if not passed:
        raise ValueError("analytical optimization control failed or infeasible")
    return report


def carrier_external(manifest, root, output):
    import openmdao.api as om

    output = new_directory(output).resolve()
    component = om.ExternalCodeComp()
    component.options["command"] = [
        sys.executable,
        str(HERE / "pilot.py"),
        "replay",
        "--manifest",
        str(Path(manifest).resolve()),
        "--root",
        str(Path(root).resolve()),
        "--output",
        str(output / "carrier"),
    ]
    component.options["timeout"] = 120.0
    component.options["external_input_files"] = [str(Path(manifest).resolve())]
    component.options["external_output_files"] = [str(output / "carrier/receipt.json")]
    component.stdout = str(output / "stdout.log")
    component.stderr = str(output / "stderr.log")
    problem = om.Problem(reports=False)
    problem.model.add_subsystem("carrier", component)
    problem.setup()
    try:
        problem.run_model()
    finally:
        problem.cleanup()
    result = load(output / "carrier/receipt.json")
    if (
        result["status"] != "blocked_engineering"
        or result["checks"]["optimization_enabled"] is not False
    ):
        raise ValueError("carrier gate unexpectedly changed")
    report = receipt(
        "openmdao-carrier",
        "blocked_engineering",
        result["inputs"],
        checks={
            "external_component_executed": True,
            "carrier_receipt_sha256": sha256(output / "carrier/receipt.json"),
            "optimization_enabled": False,
        },
        limitations=[
            "Replayed the admission contract, not a new native FEM solve.",
            "Parameter ranges and mechanical convergence remain unqualified.",
        ],
    )
    write(output / "receipt.json", report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["sensitivity", "optimization", "carrier"])
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, default=HERE / "baseline.json")
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    if args.command == "sensitivity":
        sensitivity(args.output)
    elif args.command == "optimization":
        optimization(args.output)
    else:
        carrier_external(args.manifest, args.root, args.output)


if __name__ == "__main__":
    main()
