"""Reproduce local software controls and explicitly retain unexecuted native stages."""

import argparse
import importlib.metadata
from pathlib import Path
import sys

from ft_common import HERE, ROOT, checked, load, new_directory, receipt, sha256, write
import knowledge
import pilot
import storage
import studies


def run(root, private_root, output, porschefanatics_export=None):
    output = new_directory(output).resolve()
    private_root = storage.private_root(private_root)
    if private_root.exists():
        raise ValueError("fresh private acceptance directory required")
    private_root.mkdir(parents=True, mode=0o700)
    index = knowledge.build(HERE / "corpus.json", output / "index")
    retrieval = knowledge.evaluate(
        index, HERE / "corpus.json", HERE / "retrieval-cases.json"
    )
    write(output / "retrieval.json", retrieval)
    if retrieval["status"] != "passed":
        raise ValueError("retrieval acceptance failed")
    storage.archive(
        HERE / "baseline.json",
        root,
        private_root / "source",
        private_root / "store-mac",
    )
    restored = storage.restore(
        private_root / "source", private_root / "restore", private_root / "store-mac"
    )
    production_snapshot = output / "production-snapshot.json"
    production = knowledge.snapshot(
        private_root / "restore/payload", production_snapshot, porschefanatics_export
    )
    production_index = knowledge.build(production_snapshot, output / "production-index")
    brief = knowledge.context(
        production_index, production_snapshot, "993 115 021 53 measured interfaces"
    )
    write(output / "carrier-context.json", brief)
    replay = pilot.replay(
        HERE / "baseline.json", private_root / "restore/payload", output / "carrier"
    )
    sensitivity = studies.sensitivity(output / "sensitivity")
    optimization = studies.optimization(output / "optimization")
    external = studies.carrier_external(
        HERE / "baseline.json",
        private_root / "restore/payload",
        output / "external-carrier",
    )
    result = receipt(
        "free-tools-acceptance",
        "partial_native_acceptance",
        load(HERE / "baseline.json")["inputs"],
        checks={
            "retrieval": retrieval["status"],
            "production_context_sources": len(brief["sources"]),
            "porschefanatics_export": production["porschefanatics_export"],
            "dvc_mac_restore": restored["status"],
            "openturns": sensitivity["status"],
            "openmdao": optimization["status"],
            "carrier": replay["status"],
            "carrier_external": external["status"],
            "cloudcompare": "not_executed_by_this_command",
            "salome": "not_executed_by_this_command",
            "kali_restore": "not_executed_by_this_command",
            "versions": {
                name: importlib.metadata.version(name)
                for name in ("dvc", "openturns", "openmdao")
            },
        },
        limitations=[
            "Native image receipts and an actual Kali restore are separate mandatory acceptance evidence.",
            "Carrier admission replay is not a new FEM solve. No optimization or qualification.",
        ],
    )
    write(output / "receipt.json", result)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--private-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--porschefanatics-export", type=Path)
    args = parser.parse_args()
    run(args.root, args.private_root, args.output, args.porschefanatics_export)
