"""Verify that exact facets without shared source topology are not accepted."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("cad", "arrays", "paper", "unsewn-reference", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("Existing refusal check refused")
    with tempfile.TemporaryDirectory(prefix="935-source-chart-refusal-") as directory:
        directory = Path(directory)
        for name in ("shared-square-control.step", "point-contact-control.step"):
            shutil.copy2(args.cad / name, directory / name)
        for index in (2, 3):
            name = f"stud_passage_{index}_wall_candidate-source-shells.step"
            shutil.copy2(args.cad / name, directory / name)
        shutil.copy2(args.unsewn_reference, directory / "stud_passage_1_wall_candidate-source-shells.step")
        command = [sys.executable, str(Path(__file__).with_name("verify_source_shells.py")),
                   "--cad", str(directory), "--arrays", str(args.arrays), "--paper", str(args.paper),
                   "--output", str(directory / "refused")]
        result = subprocess.run(command, capture_output=True, text=True, timeout=120)
        passed = (result.returncode != 0 and "Native source edge was duplicated or introduced" in result.stderr
                  and not (directory / "refused").exists())
    if not passed:
        raise ValueError("Unsewn-source topology refusal failed")
    args.output.mkdir(parents=True)
    (args.output / "verifier.log").write_text(result.stdout + result.stderr)
    report = {"unsewn_exact_facets_refused": True, "no_successful_output_created": True,
              "scope": "Original geometric facets alone do not prove shared edge/vertex-fan topology.",
              "physical_acceptance": False, "manufacturing_authorized": False}
    (args.output / "refusal.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
