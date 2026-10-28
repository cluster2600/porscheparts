"""Fresh native tessellation at an explicitly declared refinement setting."""
import argparse
import hashlib
import json
from pathlib import Path
import resource
import signal
import sys
import time


def main():
    p=argparse.ArgumentParser(__doc__);p.add_argument('--body',type=Path,required=True);p.add_argument('--native-site',type=Path,required=True);p.add_argument('--deflection',type=float,required=True);p.add_argument('--angle',type=float,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists()or not 0<a.deflection<=.06 or not 0<a.angle<=.1:raise ValueError('Fresh output and valid refinement parameters required')
    a.output.mkdir(parents=True);start=time.monotonic();resource.setrlimit(resource.RLIMIT_CPU,(90,100));signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(TimeoutError('120 second tessellation bound')));signal.alarm(120);sys.path.insert(0,str(a.native_site.resolve()))
    from build123d import import_brep,export_stl
    from OCP.BRepTools import BRepTools
    from OCP.OSD import OSD_ThreadPool
    OSD_ThreadPool.DefaultPool_s().Init(1)
    digest=hashlib.sha256(a.body.read_bytes()).hexdigest();body=import_brep(a.body)
    if not body.is_valid or len(body.solids())!=1:raise ValueError('One valid native body required')
    BRepTools.Clean_s(body.wrapped);target=a.output/'candidate.stl';export_stl(body,target,tolerance=a.deflection,angular_tolerance=a.angle);raw=target.read_bytes();triangles=int.from_bytes(raw[80:84],'little')
    if len(raw)!=84+50*triangles:raise ValueError('Binary STL length differs')
    report=dict(status='fresh_native_tessellation_exported',requested_deflection_mm=a.deflection,requested_angle_radians=a.angle,requested_deflection_is_not_an_independent_complete_distance_proof=True,triangles=triangles,body_source_sha256=digest,source_unchanged=digest==hashlib.sha256(a.body.read_bytes()).hexdigest(),STL_sha256=hashlib.sha256(raw).hexdigest(),worker_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),elapsed_seconds=time.monotonic()-start)
    (a.output/'assessment.json').write_text(json.dumps(report,indent=2)+'\n');signal.alarm(0);print(json.dumps(report))

if __name__=='__main__':main()
