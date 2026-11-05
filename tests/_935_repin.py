"""Resolve a historical 935 source pin through the dated re-pin record (#416).

Research records keep the source hashes their results were produced with. A
later re-pin record lists, per source, that historical hash and the hash of the
current file; tests compare the working tree with the current pin while the
historical pin stays verifiable through the record's guard_replacement text.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPIN = ROOT / 'docs/research/935-horizontal-cooling/source-repin-20261105.json'


def current_pin(path, historical):
    """Return the hash the file at `path` must have now, given its historical pin."""
    entry = json.loads(REPIN.read_text())['sources'].get(str(path))
    if entry and entry['historical_sha256'] == historical:
        return entry['current_sha256']
    return historical
