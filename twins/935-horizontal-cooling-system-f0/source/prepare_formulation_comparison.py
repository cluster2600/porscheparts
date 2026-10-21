#!/usr/bin/env python3
"""Change only C3D8 to C3D8I in a pinned 935 rotor deck; retain the baseline."""
import argparse
import hashlib
import json
from pathlib import Path


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def replace_formulation(text):
    header='*ELEMENT,TYPE=C3D8,ELSET=ROTOR\n'
    if (text.count(header)!=1 or sum(line.startswith('*ELEMENT') for line in text.splitlines())!=1
            or '*BOUNDARY\nBORE,1,3,0\n' not in text or text.count('*STATIC\n')!=1
            or text.count('ROTOR,CENTRIF,')!=1):
        raise ValueError('Single static C3D8 rotor domain with the inherited fixed bore required')
    return text.replace(header,'*ELEMENT,TYPE=C3D8I,ELSET=ROTOR\n',1)


def prepare(parent, expected, output):
    parent,output=Path(parent),Path(output)
    if set(expected)!= {'rotor.inp','case.json','receipt.json'}:
        raise ValueError('Pin all three parent preparation files')
    if any(sha(parent/name)!=value for name,value in expected.items()):
        raise ValueError('Parent preparation changed')
    receipt=json.loads((parent/'receipt.json').read_text());case=json.loads((parent/'case.json').read_text())
    if (receipt['deck_sha256']!=expected['rotor.inp'] or case['scale_verified'] is not False
            or case['purpose']!='hypothesis_screen' or receipt['manufacturing_authorized'] is not False):
        raise ValueError('Pinned unqualified centrifugal screen required')
    before=(parent/'rotor.inp').read_text();after=replace_formulation(before)
    if after.replace('*ELEMENT,TYPE=C3D8I,ELSET=ROTOR\n','*ELEMENT,TYPE=C3D8,ELSET=ROTOR\n',1)!=before:
        raise ValueError('Non-formulation text changed')
    output.mkdir(mode=0o700,exist_ok=False)
    (output/'rotor.inp').write_text(after)
    (output/'case.json').write_text(json.dumps(case,indent=2)+'\n')
    (output/'parent-receipt.json').write_bytes((parent/'receipt.json').read_bytes())
    receipt.update(deck_sha256=sha(output/'rotor.inp'),status='C3D8I_formulation_comparison_prepared_not_solved',
                   element_formulation='C3D8I',parent_preparation_sha256=expected,
                   unchanged_non_formulation_text_sha256=hashlib.sha256(before.encode()).hexdigest(),
                   legacy_count_field='C3D8_elements retains the parent eight-node brick count; formulation is C3D8I',
                   formulation_comparison_complete=False)
    (output/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    if any(sha(parent/name)!=value for name,value in expected.items()):
        raise ValueError('Input changed during preparation')
    return receipt


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('parent',type=Path);parser.add_argument('pins',type=Path);parser.add_argument('new_output',type=Path)
    args=parser.parse_args();print(json.dumps(prepare(args.parent,json.loads(args.pins.read_text()),args.new_output),indent=2))
