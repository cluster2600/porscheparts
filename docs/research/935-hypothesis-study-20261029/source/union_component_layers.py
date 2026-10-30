"""Clipper component unions, checked independently against GEOS on every layer."""
import argparse
import hashlib
import json
from pathlib import Path
import time
import numpy as np
import pyclipper
import shapely
from shapely.geometry import Polygon
from validate_cli import section

SCALE=10**12  # Preserve the input CLI decimal grid; this is not process accuracy.

def signed_area(path):
    points=np.asarray(path,dtype=np.int64);points=points-points[0]
    return pyclipper.Area(points.tolist())

def unite(rings):
    paths=[]
    for direction,xy in rings:
        q=np.rint(np.asarray(xy)*SCALE).astype(np.int64)
        if np.array_equal(q[0],q[-1]):q=q[:-1]
        area=signed_area(q)
        if len(np.unique(q,axis=0))<3 or area==0:raise ValueError('Input contour collapsed on numerical grid')
        assert (area>0)==(direction==1)
        paths.append(q.tolist())
    if not paths:return []
    clipper=pyclipper.Pyclipper();clipper.StrictlySimple=True;clipper.PreserveCollinear=True
    clipper.AddPaths(paths,pyclipper.PT_SUBJECT,True)
    result=[]
    for path in clipper.Execute(pyclipper.CT_UNION,pyclipper.PFT_POSITIVE,pyclipper.PFT_POSITIVE):
        area=signed_area(path);assert area!=0
        points=np.asarray(path+[path[0]],float)/SCALE;result.append((1 if area>0 else 0,points))
    return result

def main():
    p=argparse.ArgumentParser();p.add_argument('head_cli',type=Path);p.add_argument('hypotheses',type=Path);p.add_argument('output',type=Path);a=p.parse_args();a.output.mkdir()
    start=time.monotonic();h=json.loads(a.hypotheses.read_text())
    assert h['base_plate_mm'][2]==5 and h['stem_radius_mm']==1.2 and h['contact_tip_radius_mm']==.5 and h['coupon_radius_mm']==6 and h['coupon_height_mm']==20
    outer=np.array([[0,0],[2,0],[2,2],[0,2],[0,0]],float);hole=np.array([[.5,.5],[.5,1.5],[1.5,1.5],[1.5,.5],[.5,.5]])
    for rings,expected in [([(1,outer),(1,outer+1)],7),([(1,outer),(0,hole)],3),([(1,outer),(0,hole),(1,(outer-.0)*.25+.75)],3.25)]:
        assert abs(section(unite(rings))[0]-expected)<1e-10
    angle=np.linspace(0,2*np.pi,49);circle=np.column_stack([np.cos(angle),np.sin(angle)]);circle[-1]=circle[0]
    width,length,_=h['base_plate_mm'];plate=np.array([[0,0],[width,0],[width,length],[0,length],[0,0]])
    cx,cy,cz=h['coupon_centre_mm'];columns=np.asarray(h['support_columns'])
    current=None;rings=[];rows=[];declared=None;ended=False;contours=0;vertices=0;previous=0.
    output=a.output/'935-supported-30um.cli'
    with output.open('x') as stream:
        def finish():
            nonlocal rings,contours,vertices,previous
            if current is None:return
            material=section(rings,return_geometry=True)
            fixtures=[]
            if 0<current<=5:fixtures.append(plate)
            if cz-.5<=current<=cz+20:fixtures.append(circle*6+[cx,cy])
            for x,y,lo,hi in columns[(columns[:,2]<=current)&(columns[:,3]>=current)]:
                radius=1.2 if current<=hi-1 else 1.2-.7*(current-(hi-1))
                fixtures.append(circle*radius+[x,y])
            expected=shapely.union_all([material]+[Polygon(xy) for xy in fixtures])
            result=unite(rings+[(1,xy) for xy in fixtures]);actual=section(result,return_geometry=True)
            difference=expected.symmetric_difference(actual).area
            limit=4/SCALE*(0 if expected.is_empty else expected.boundary.length)+1e-8
            assert difference<=limit,(current,difference,limit)
            stream.write(f'$$LAYER/{current:.9f}\n')
            for direction,xy in result:
                stream.write(f'$$POLYLINE/1,{direction},{len(xy)},'+','.join(f'{v:.12f}' for v in xy.ravel())+'\n');contours+=1;vertices+=len(xy)
            rows.append({'z_mm':current,'height_mm':current-previous,'independent_area_mm2':float(expected.area),'output_area_mm2':float(actual.area),'symmetric_difference_mm2':float(difference),'numerical_area_limit_mm2':float(limit),'contours':len(result)})
            previous=current;rings=[]
            if len(rows)%100==0:stream.flush();print('Verified layer',len(rows),'of',declared,flush=True)
        with a.head_cli.open() as source:
            for raw in source:
                line=raw.strip()
                if line.startswith('$$LAYERS/'):
                    declared=int(line.split('/')[1]);stream.write('$$HEADERSTART\n$$ASCII\n$$UNITS/1.0\n$$VERSION/200\n$$LABEL/1,"935 conditional composite - neutral contours only"\n'+f'$$LAYERS/{declared}\n$$HEADEREND\n$$GEOMETRYSTART\n')
                elif line.startswith('$$LAYER/'):
                    finish();current=float(line.split('/')[1])
                elif line.startswith('$$POLYLINE/'):
                    fields=line.split('/')[1].split(',');identifier,direction,n=map(int,fields[:3]);assert identifier==1 and direction in (0,1) and len(fields)==3+2*n
                    rings.append((direction,np.asarray(fields[3:],float).reshape(n,2)))
                elif line=='$$GEOMETRYEND':finish();ended=True
        assert ended and len(rows)==declared and rows[0]['z_mm']==0 and rows[0]['contours']==0
        stream.write('$$GEOMETRYEND\n')
    volume=sum(r['output_area_mm2']*r['height_mm'] for r in rows);independent=sum(r['independent_area_mm2']*r['height_mm'] for r in rows)
    def sha(path):
        with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
    report={'head_cli_sha256':sha(a.head_cli),'hypotheses_sha256':sha(a.hypotheses),'output_cli_sha256':sha(output),'clipper_wrapper_version':pyclipper.__version__,'shapely_version':shapely.__version__,'geos_version':shapely.geos_version_string,'coordinate_grid_mm':1/SCALE,'layers_including_empty_zero_layer':len(rows),'contours':contours,'vertices':vertices,'all_layers_independently_checked':True,'all_contours_closed_valid_and_disjoint':True,'all_layer_unions_match_independent_geometry_within_numerical_grid_bound':True,'output_layer_volume_mm3':volume,'independent_layer_volume_mm3':independent,'maximum_layer_symmetric_difference_mm2':max(r['symmetric_difference_mm2'] for r in rows),'seconds':time.monotonic()-start,'inter_layer_discretisation_is_a_hypothesis':True,'machine_job':False,'hatch_or_exposure_parameters_present':False,'manufacturing_qualified':False,'engine_qualified':False}
    (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');(a.output/'layers.json').write_text(json.dumps(rows)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
