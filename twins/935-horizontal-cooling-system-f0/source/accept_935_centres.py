#!/usr/bin/env python3
"""Import one JSON-only Qwen layout proposal against independent six-cylinder hypotheses."""
import argparse
import json
from pathlib import Path
import re

from test_qwen_935 import cases, exact_match


def accept(text):
    match = re.fullmatch(r'```json\s*([\s\S]*?)\s*```', text.strip())
    payload = match.group(1) if match else text.strip()
    expected = next(row['expected'] for row in cases() if row['id']=='six_centres')
    if not exact_match(payload, expected):
        raise ValueError('Proposal differs from independently prescribed six-cylinder layout')
    return json.loads(payload)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('responses'); p.add_argument('new_output')
    a = p.parse_args(); out = Path(a.new_output)
    if out.exists(): raise ValueError('Use a new output file')
    rows = json.loads(Path(a.responses).read_text())
    row = next(r for r in rows if r['model']=='base' and r['case']=='six_centres')
    out.write_text(json.dumps(accept(row['response']),indent=2)+'\n')
