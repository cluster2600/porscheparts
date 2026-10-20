"""Bounded MeshLib evaluation: simplify every PicoGK surface facet.

The requested maxError is the backend's estimated deviation setting, not an
independent complete Hausdorff certificate. No input face may disappear on load.
"""
import argparse
import hashlib
import importlib.metadata as metadata
import json
import os
from pathlib import Path
import resource
import signal
import subprocess
import sys
import time
import traceback


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def worker(a):
    out=a.output;out.mkdir(parents=True,exist_ok=True)
    if any(out.iterdir()):raise ValueError('Fresh worker output required')
    report=dict(status='incomplete',mechanical_mesh_admitted=False,source_interfaces_unchanged=False,geometry_adopted=False);start=time.monotonic()
    def phase(name,**data):(out/'progress.json').write_text(json.dumps(dict(phase=name,**data),indent=2)+'\n')
    try:
        import numpy as np
        from meshlib import mrmeshpy as mr,mrmeshnumpy as mn
        versions={name:metadata.version(name)for name in ['meshlib','meshlib-core','numpy']}
        if versions!={'meshlib':'3.1.4.297','meshlib-core':'3.1.4.297','numpy':'2.2.6'}:raise ValueError('Pinned runtime versions differ')
        cube=mr.makeCube(mr.Vector3f(1,1,1),mr.Vector3f(0,0,0));control_settings=mr.DecimateSettings();control_settings.maxError=0.;mr.decimateMesh(cube,control_settings)
        control=dict(volume=cube.volume(),area=cube.area(),faces=cube.topology.getValidFaces().count(),holes=len(cube.topology.findHoleRepresentiveEdges()))
        if control!=dict(volume=1.,area=6.,faces=12,holes=0):raise ValueError('Analytic unit-cube control failed')
        with a.mesh.open('rb')as stream:header=stream.read(84)
        count=int.from_bytes(header[80:84],'little')
        if a.mesh.stat().st_size!=84+50*count:raise ValueError('Binary STL input length differs')
        phase('loading',input_faces=count);mesh=mr.loadMesh(a.mesh);loaded=mesh.topology.getValidFaces().count()
        if loaded!=count:raise ValueError(f'Loader did not retain every input face: {loaded}/{count}')
        initial_volume=mesh.volume();settings=mr.DecimateSettings();settings.maxError=a.max_error;settings.packMesh=True
        last=[0.]
        def progress(value):
            if time.monotonic()-last[0]>2:phase('decimating',backend_progress=float(value),input_faces=count);last[0]=time.monotonic()
            return True
        settings.progressCallback=progress;phase('decimating',input_faces=count);result=mr.decimateMesh(mesh,settings)
        if result.cancelled:raise ValueError('Backend decimation cancelled')
        phase('exporting');mr.saveMesh(mesh,out/'decimated-study.stl');v=mn.getNumpyVerts(mesh).copy();f=mn.getNumpyFaces(mesh.topology).astype(np.int64)
        if not np.isfinite(v).all()or v.shape[1]!=3 or f.shape[1]!=3:raise ValueError('Finite packed mesh arrays required')
        with (out/'surface.mesh64').open('w')as stream:stream.write(f'{len(v)} {len(f)}\n');np.savetxt(stream,v,fmt='%.17g');np.savetxt(stream,f,fmt='%d')
        raw=(out/'decimated-study.stl').read_bytes()
        if len(raw)!=84+50*len(f)or int.from_bytes(raw[80:84],'little')!=len(f):raise ValueError('Saved binary STL face count differs')
        dtype=np.dtype([('normal','<f4',3),('points','<f4',(3,3)),('attribute','<u2')]);saved=np.frombuffer(raw,offset=84,dtype=dtype)['points']
        identical=np.array_equal(saved.astype(np.float64),v[f])
        if not identical:raise ValueError('STL exporter changed triangle coordinates or order')
        report.update(status='complete_meshlib_decimation_exported',versions=versions,analytic_control=control,input_faces=count,loaded_faces=loaded,output_vertices=len(v),output_faces=len(f),backend_deleted_faces=result.facesDeleted,backend_deleted_vertices=result.vertsDeleted,backend_estimated_error_introduced_mm=result.errorIntroduced,requested_max_error_mm=a.max_error,requested_error_independently_certified=False,all_input_faces_retained_on_load=True,STL_triangle_bytes_match_indexed_geometry=True,initial_volume_mm3=initial_volume,output_volume_mm3=mesh.volume(),nominal_mass_kg=mesh.volume()*4.42e-6,boundary_holes=len(mesh.topology.findHoleRepresentiveEdges()),maximum_new_triangle_aspect_ratio_setting=settings.maxTriangleAspectRatio,source_sha256=sha(a.mesh),output_sha256={p.name:sha(p)for p in [out/'decimated-study.stl',out/'surface.mesh64']},pending=['independent all-facet audit','independent reference fidelity','protected interfaces and source material','mechanical cases and print preparation'])
    except BaseException as error:report['failure']=dict(type=type(error).__name__,message=str(error),traceback=traceback.format_exc());raise
    finally:report['elapsed_seconds']=time.monotonic()-start;(out/'assessment.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k]for k in ['status','input_faces','output_faces','nominal_mass_kg','backend_estimated_error_introduced_mm']}))


def child_limits():
    os.nice(10);resource.setrlimit(resource.RLIMIT_CPU,(2400,2420))


def main():
    p=argparse.ArgumentParser(__doc__);p.add_argument('--mesh',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--max-error',type=float,required=True);p.add_argument('--worker',action='store_true');a=p.parse_args()
    if not 0<a.max_error<=.06:raise ValueError('Explicit error request must be in (0,0.06] mm')
    if a.worker:return worker(a)
    out=a.output.resolve()
    if out.exists():raise ValueError('Fresh output required')
    out.mkdir(parents=True);mesh=a.mesh.resolve();source=Path(__file__).resolve();inputs={str(p):sha(p)for p in [mesh,source,Path(sys.executable)]};cmd=[sys.executable,'-I','-B',str(source),'--worker','--mesh',str(mesh),'--output',str(out/'output'),'--max-error',str(a.max_error)]
    (out/'plan.json').write_text(json.dumps(dict(argv=cmd,input_sha256=inputs,resources=dict(wall_seconds=300,CPU_seconds=[2400,2420],sampled_RSS_limit_bytes=6*1024**3,nice=10),native_thread_limit_independently_verified=False),indent=2)+'\n');start=time.monotonic();peak=0;reason=None
    with (out/'stdout.log').open('w')as stdout,(out/'stderr.log').open('w')as stderr:
        child=subprocess.Popen(cmd,stdout=stdout,stderr=stderr,start_new_session=True,preexec_fn=child_limits)
        try:
            while child.poll()is None:
                r=subprocess.run(['ps','-o','rss=','-p',str(child.pid)],capture_output=True,text=True)
                if r.returncode==0 and r.stdout.strip():peak=max(peak,int(r.stdout.strip())*1024)
                if peak>6*1024**3 or time.monotonic()-start>300:reason='RSS_limit'if peak>6*1024**3 else'wall_limit';break
                time.sleep(.5)
            if child.poll()is None:
                os.killpg(child.pid,signal.SIGTERM)
                try:child.wait(timeout=10)
                except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);child.wait(timeout=10)
            rc=child.wait()
        finally:
            if child.poll()is None:os.killpg(child.pid,signal.SIGKILL);child.wait(timeout=10)
    receipt=dict(actual_returncode=rc,termination_reason=reason,elapsed_seconds=time.monotonic()-start,peak_sampled_RSS_bytes=peak,child_reaped=child.returncode is not None,inputs_unchanged=inputs=={str(p):sha(p)for p in [mesh,source,Path(sys.executable)]})
    (out/'actual-terminal.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt));return rc

if __name__=='__main__':raise SystemExit(main())
