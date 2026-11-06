"""Export the canonical assumed F2 midsurfaces to editable STEP.

This deliberately exports surfaces, not physical wall solids. Physical normal
offsets and their native voxel union have separate tessellation/voxel evidence.
"""
from pathlib import Path
import argparse
import hashlib
import json
import time

import build123d as cad
from bezier import occ_face


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists():
        raise FileExistsError('Use a fresh output directory')
    source_hash=sha(args.model)
    model=json.loads(args.model.read_text())
    if model['units']!='mm' or model['status']!='assumed':
        raise ValueError('Expected an assumed millimetre geometry contract')
    components=model['components'];names=[c['name'] for c in components]
    if not 0<len(names)<=100 or len(set(names))!=len(names):
        raise ValueError('Expected 1..100 uniquely named components')
    if any(c['scope']!='structural_cell' for c in components):
        raise ValueError('Structural midsurface CAD cannot include packaging proxies')
    args.output.mkdir(parents=True,mode=0o700)
    started=time.monotonic();faces=[];records=[]
    for component in components:
        face=occ_face(component);face.label=component['name']
        if not face.is_valid:
            raise ValueError('Invalid canonical midsurface face: '+component['name'])
        box=face.bounding_box()
        records.append({'name':component['name'],'type':component['type'],
                        'bounds_min_mm':list(box.min),'bounds_max_mm':list(box.max),
                        'nominal_wall_mm_metadata_only':component['thickness_mm']})
        faces.append(face)
        print(json.dumps({'midsurface_completed':component['name']}),flush=True)
    shape=cad.Compound(children=faces)
    step=args.output/'sculpted-cell-midsurfaces.step'
    cad.export_step(shape,step)
    restored=cad.import_step(step)
    before,after=shape.bounding_box(),restored.bounding_box()
    if (not shape.is_valid or not restored.is_valid or len(restored.solids())!=0
            or len(restored.faces())!=len(faces)):
        raise ValueError('STEP roundtrip did not retain the valid midsurface face set')
    if any(abs(a-b)>1e-4 for a,b in zip(list(before.min)+list(before.max),
                                      list(after.min)+list(after.max))):
        raise ValueError('STEP roundtrip changed midsurface bounds')
    if sha(args.model)!=source_hash:
        raise ValueError('Canonical model changed during export')
    report={'status':'executed_assumed_midsurface_STEP_only',
            'geometry_sha256':source_hash,'exporter_sha256':sha(__file__),
            'bezier_helper_sha256':sha(Path(__file__).with_name('bezier.py')),
            'parameter_sha256':model.get('parameter_sha256'),
            'method':'Composite cubic Catmull-Rom surfaces and exact closed-profile planar cap boundaries. Redundant knots removed within 1e-9 mm; closed profiles represented periodically. No physical offsets or Boolean union.',
            'components':records,'face_count':len(faces),
            'valid_before_and_after':True,'solid_count_before_and_after':0,
            'bounds_min_mm':list(before.min),'bounds_max_mm':list(before.max),
            'step_sha256':sha(step),'step_bytes':step.stat().st_size,
            'build123d_version':cad.__version__,
            'elapsed_seconds':time.monotonic()-started,
            'physical_wall_STEP':False,'volume_or_mass_admitted':False,
            'physical_junction_completeness_verified':False,
            'donor_fitment_verified':False,'strength_verified':False,
            'manufacturing_authorized':False,'native_omniverse':False}
    (args.output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    main()
