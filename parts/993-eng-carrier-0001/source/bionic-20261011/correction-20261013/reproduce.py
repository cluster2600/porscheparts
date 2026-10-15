"""Build the selected study parameters into a fresh directory."""
import json
from pathlib import Path
import sys

from corrected_cad import build

if __name__=='__main__':
    if len(sys.argv)!=3:
        raise SystemExit('Usage: reproduce.py STUDY_JSON NEW_OUTPUT')
    build(json.loads(Path(sys.argv[1]).read_text()),Path(sys.argv[2]))
