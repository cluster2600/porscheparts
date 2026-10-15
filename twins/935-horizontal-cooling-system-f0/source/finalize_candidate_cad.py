#!/usr/bin/env python3
"""Native FreeCAD union of private candidate components, with pinned source hashes."""
import argparse
import json
from pathlib import Path
import sys

sys.path.append('/opt/freecad/usr/lib')
import FreeCAD as App
import Part
import MeshPart

from run_reconstruction import fresh, save, sha


def build(source, expected, case_path, output):
    source, case_path = Path(source), Path(case_path)
    case = json.loads(case_path.read_text())
    if sha(source) != expected or case.get('purpose') != 'hypothesis_screen' or case.get('scale_verified') is not False:
        raise ValueError('Pinned private geometry and an uncalibrated hypothesis required')
    out = fresh(output)
    components = Part.read(str(source.resolve())).Solids
    if len(components) < 3 or any(not s.isValid() or s.Volume <= 0 for s in components):
        raise ValueError('Valid hub and blade components required')
    doc = App.newDocument('935CandidateRotorHypothesis')
    objects = []
    for i, shape in enumerate(components):
        obj = doc.addObject('Part::Feature', f'Component{i}')
        obj.Shape = shape
        obj.addProperty('App::PropertyString', 'InputSHA256').InputSHA256 = expected
        objects.append(obj)
    union = doc.addObject('Part::MultiFuse', 'CandidateRotor')
    union.Shapes = objects
    union.addProperty('App::PropertyString', 'Status').Status = 'Uncalibrated hypothesis; no manufacturing release'
    doc.recompute()
    shape = union.Shape
    if not shape.isValid() or len(shape.Solids) != 1 or shape.Volume <= 0:
        raise ValueError('Candidate rotor is invalid or disconnected')
    doc.saveAs(str((out / 'candidate-rotor.FCStd').resolve()))
    Part.export([union], str((out / 'candidate-rotor.step').resolve()))
    MeshPart.meshFromShape(Shape=shape, LinearDeflection=.2 * case['scale_mm_per_source_unit'],
                          AngularDeflection=.1, Relative=False).write(str((out / 'candidate-rotor.stl').resolve()))
    step = Part.read(str((out / 'candidate-rotor.step').resolve()))
    error = abs(step.Volume - shape.Volume) / shape.Volume
    if not step.isValid() or len(step.Solids) != 1 or error > 1e-6:
        raise ValueError('STEP reread failed')
    volume = shape.Volume
    App.closeDocument(doc.Name)
    reopened = App.openDocument(str((out / 'candidate-rotor.FCStd').resolve()))
    if not reopened.getObject('CandidateRotor') or len(reopened.getObject('CandidateRotor').Shapes) != len(objects):
        raise ValueError('Native assembly history lost')
    App.closeDocument(reopened.Name)
    if sha(source) != expected:
        raise ValueError('Input geometry changed during union')
    save(out / 'receipt.json', {'status':'closed_hypothesis_not_historical_replica',
        'FreeCAD_version':App.Version()[:3], 'input_sha256':expected, 'case_sha256':sha(case_path),
        'conditional_volume_mm3':volume, 'solid_count':1, 'STEP_reread_relative_volume_error':error,
        'scale_verified':False, 'manufacturing_authorized':False, 'physical_validation':False,
        'artifacts':{p.name:sha(p) for p in out.iterdir() if p.is_file()}})
    return out


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path); parser.add_argument('sha256')
    parser.add_argument('case', type=Path); parser.add_argument('output', type=Path)
    args = parser.parse_args()
    print(build(args.source, args.sha256, args.case, args.output))
