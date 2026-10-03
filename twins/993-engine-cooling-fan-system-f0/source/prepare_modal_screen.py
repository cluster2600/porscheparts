#!/usr/bin/env python3
"""Reuse an existing fixed-bore elastic deck for an unprestressed modal screen."""
import argparse
import hashlib
import json
from pathlib import Path


def prepare(source, output, modes=12):
    if not 1 <= modes <= 30:
        raise ValueError("Mode count must be 1..30")
    text = source.read_text()
    step = text.upper().find("*STEP")
    if step < 0 or "*BOUNDARY" not in text[:step].upper() or "*DENSITY" not in text[:step].upper():
        raise ValueError("Expected an existing restrained elastic deck with density")
    output.mkdir(parents=True, exist_ok=False)
    deck = text[:step] + f"*STEP\n*FREQUENCY\n{modes}\n*END STEP\n"
    (output / "modal.inp").write_text(deck)
    report = {
        "status": "prepared_not_solved", "source_deck_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "modal_deck_sha256": hashlib.sha256(deck.encode()).hexdigest(), "requested_modes": modes,
        "units": "mm,N,s,tonne", "boundary": "inherited hypothetical fixed bore",
        "prestress_included": False, "rotating_gyroscopic_terms_included": False,
        "bearing_belt_contact_included": False, "material_qualified": False,
        "campbell_diagram_validated": False, "manufacturing_authorized": False,
        "scope": "linear unprestressed modal screening of existing parametric model, not the private scan",
    }
    (output / "preparation.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("source", type=Path)
    ap.add_argument("output", type=Path)
    ap.add_argument("--modes", type=int, default=12)
    args = ap.parse_args()
    print(json.dumps(prepare(args.source, args.output, args.modes), indent=2))
