#!/usr/bin/env python3
"""Writes source/bionic.json and its region meshes for the bionic titanium oval tip.

Same geometry as the IN625 record (see the catalogue record): this delegates to
parts/993-exh-oval-tip-in625-f0-0001/source/bionic_regions.py with this part's
folder, so parameters, part id and screening mass come from this record.
"""
import runpy
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.argv = [sys.argv[0], str(HERE.parent)]
runpy.run_path(str(HERE.parents[1] / "993-exh-oval-tip-in625-f0-0001" / "source" / "bionic_regions.py"), run_name="__main__")
