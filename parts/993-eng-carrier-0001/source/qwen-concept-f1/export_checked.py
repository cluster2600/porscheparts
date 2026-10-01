"""Gate the historical geometry exporter; preserve its original receipt and source."""
import json
from pathlib import Path
import runpy
import sys

from interfaces import require_preflight

shape_study = '--shape-study' in sys.argv
if shape_study:
    sys.argv.remove('--shape-study')
if len(sys.argv) != 3:
    raise SystemExit('Usage: export_checked.py <native-output> <new-export-directory> [--shape-study]')
result = require_preflight(shape_study)
output = Path(sys.argv[2])
if output.exists():
    raise ValueError('Refusing to replace an existing export')
runpy.run_path(str(Path(__file__).with_name('export.py')), run_name='__main__')
(output / 'attachment-check.json').write_text(json.dumps(result, indent=2) + '\n')
