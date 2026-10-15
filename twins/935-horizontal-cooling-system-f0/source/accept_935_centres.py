#!/usr/bin/env python3
"""Import one JSON-only Qwen layout proposal against independent six-cylinder hypotheses."""
import argparse
import json
from pathlib import Path
import re


def unique_object(pairs):
    result = dict(pairs)
    if len(result) != len(pairs):
        raise ValueError('Duplicate JSON key')
    return result


def accept(text):
    match = re.fullmatch(r'```json\s*([\s\S]*?)\s*```', text.strip())
    payload = match.group(1) if match else text.strip()
    expected = {'centres_mm':[[x,y,-205] for y in (-190,190) for x in (-115,0,115)],
                'axis':'Y','classification':'hypothesis','scale_verified':False}
    actual = json.loads(payload, object_pairs_hook=unique_object)
    if json.dumps(actual,sort_keys=True,allow_nan=False) != json.dumps(expected,sort_keys=True):
        raise ValueError('Proposal differs from independently prescribed six-cylinder layout')
    return actual


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('responses'); p.add_argument('new_output')
    a = p.parse_args(); out = Path(a.new_output)
    if out.exists(): raise ValueError('Use a new output file')
    rows = json.loads(Path(a.responses).read_text())
    row = next(r for r in rows if r['model']=='base' and r['case']=='six_centres')
    out.write_text(json.dumps(accept(row['response']),indent=2)+'\n')
