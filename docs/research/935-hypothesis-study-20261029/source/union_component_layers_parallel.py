"""Ordered, bounded parallel execution of the component-layer union checks."""
import argparse
from concurrent.futures import ProcessPoolExecutor
import hashlib
import itertools
import json
import multiprocessing
from pathlib import Path
import time
import numpy as np
import pyclipper
import shapely
from shapely.geometry import Polygon
from union_component_layers import unite,SCALE
from validate_cli import section

def initialise(h):
    global columns,plate,circle,coupon
    assert h['base_plate_mm'][2]==5 and h['stem_radius_mm']==1.2 and h['contact_tip_radius_mm']==.5 and h['coupon_radius_mm']==6 and h['coupon_height_mm']==20
    columns=np.asarray(h['support_columns']);width,length,_=h['base_plate_mm']
    plate=np.array([[0,0],[width,0],[width,length],[0,length],[0,0]])
    angle=np.linspace(0,2*np.pi,49);circle=np.column_stack([np.cos(angle),np.sin(angle)]);circle[-1]=circle[0]
    coupon=h['coupon_centre_mm']

def evaluate(item):
    z,previous,rings=item;material=section(rings,return_geometry=True);fixtures=[];cx,cy,cz=coupon
    if 0<z<=5:fixtures.append(plate)
    if cz-.5<=z<=cz+20:fixtures.append(circle*6+[cx,cy])
    for x,y,lo,hi in columns[(columns[:,2]<=z)&(columns[:,3]>=z)]:
        radius=1.2 if z<=hi-1 else 1.2-.7*(z-(hi-1));fixtures.append(circle*radius+[x,y])
    expected=shapely.union_all([material]+[Polygon(xy) for xy in fixtures])
    result=unite(rings+[(1,xy) for xy in fixtures]);actual=section(result,return_geometry=True)
    difference=expected.symmetric_difference(actual).area;limit=4/SCALE*(0 if expected.is_empty else expected.boundary.length)+1e-8
    assert difference<=limit,(z,difference,limit)
    lines=[f'$$LAYER/{z:.9f}\n'];vertices=0
    for direction,xy in result:
        lines.append(f'$$POLYLINE/1,{direction},{len(xy)},'+','.join(f'{v:.12f}' for v in xy.ravel())+'\n');vertices+=len(xy)
    row={'z_mm':z,'height_mm':z-previous,'independent_area_mm2':float(expected.area),'output_area_mm2':float(actual.area),'symmetric_difference_mm2':float(difference),'numerical_area_limit_mm2':float(limit),'contours':len(result)}
    return ''.join(lines),row,vertices

def layers(path):
    current=None;previous=0.;rings=[];ended=False
    with path.open() as source:
        for raw in source:
            line=raw.strip()
            if line.startswith('$$LAYER/'):
                if current is not None:yield current,previous,rings;previous=current
                current=float(line.split('/')[1]);rings=[]
            elif line.startswith('$$POLYLINE/'):
                fields=line.split('/')[1].split(',');identifier,direction,n=map(int,fields[:3]);assert identifier==1 and direction in (0,1) and len(fields)==3+2*n
                rings.append((direction,np.asarray(fields[3:],float).reshape(n,2)))
            elif line=='$$GEOMETRYEND':
                yield current,previous,rings;ended=True
    assert ended

def main():
    p=argparse.ArgumentParser();p.add_argument('head_cli',type=Path);p.add_argument('hypotheses',type=Path);p.add_argument('output',type=Path);p.add_argument('--workers',type=int,default=8);p.add_argument('--serial-prefix',type=Path);a=p.parse_args();a.output.mkdir()
    start=time.monotonic();h=json.loads(a.hypotheses.read_text());declared=None
    with a.head_cli.open() as source:
        for line in source:
            if line.startswith('$$LAYERS/'):declared=int(line.split('/')[1])
            if line.startswith('$$GEOMETRYSTART'):break
    assert declared==4946
    outer=np.array([[0,0],[2,0],[2,2],[0,2],[0,0]],float);hole=np.array([[.5,.5],[.5,1.5],[1.5,1.5],[1.5,.5],[.5,.5]])
    for rings,expected in [([(1,outer),(1,outer+1)],7),([(1,outer),(0,hole)],3),([(1,outer),(0,hole),(1,outer*.25+.75)],3.25)]:assert abs(section(unite(rings))[0]-expected)<1e-10
    output=a.output/'935-supported-30um.cli';rows=[];vertices=0;iterator=layers(a.head_cli)
    with output.open('x') as stream,ProcessPoolExecutor(max_workers=a.workers,mp_context=multiprocessing.get_context('spawn'),initializer=initialise,initargs=(h,)) as pool:
        stream.write('$$HEADERSTART\n$$ASCII\n$$UNITS/1.0\n$$VERSION/200\n$$LABEL/1,"935 conditional composite - neutral contours only"\n'+f'$$LAYERS/{declared}\n$$HEADEREND\n$$GEOMETRYSTART\n')
        while batch:=list(itertools.islice(iterator,64)):
            for text,row,n in pool.map(evaluate,batch,chunksize=1):stream.write(text);rows.append(row);vertices+=n
            stream.flush();print('Verified layer',len(rows),'of',declared,flush=True)
        assert len(rows)==declared and rows[0]['z_mm']==0 and rows[0]['contours']==0
        stream.write('$$GEOMETRYEND\n')
    prefix_bytes=0
    if a.serial_prefix:
        # The terminated serial producer may end mid-layer. Compare complete layers only.
        data=a.serial_prefix.read_bytes();prefix_bytes=data.rfind(b'$$LAYER/');assert prefix_bytes>0
        with output.open('rb') as stream:assert stream.read(prefix_bytes)==data[:prefix_bytes]
    def sha(path):
        with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
    report={'head_cli_sha256':sha(a.head_cli),'hypotheses_sha256':sha(a.hypotheses),'output_cli_sha256':sha(output),'clipper_wrapper_version':pyclipper.__version__,'shapely_version':shapely.__version__,'geos_version':shapely.geos_version_string,'coordinate_grid_mm':1/SCALE,'workers':a.workers,'serial_prefix_bytes_compared_exactly':prefix_bytes,'layers_including_empty_zero_layer':len(rows),'contours':sum(r['contours'] for r in rows),'vertices':vertices,'all_layers_independently_checked':True,'all_contours_closed_valid_and_disjoint':True,'all_layer_unions_match_independent_geometry_within_numerical_grid_bound':True,'output_layer_volume_mm3':sum(r['output_area_mm2']*r['height_mm'] for r in rows),'independent_layer_volume_mm3':sum(r['independent_area_mm2']*r['height_mm'] for r in rows),'maximum_layer_symmetric_difference_mm2':max(r['symmetric_difference_mm2'] for r in rows),'seconds':time.monotonic()-start,'inter_layer_discretisation_is_a_hypothesis':True,'machine_job':False,'hatch_or_exposure_parameters_present':False,'manufacturing_qualified':False,'engine_qualified':False}
    (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');(a.output/'layers.json').write_text(json.dumps(rows)+'\n');print(json.dumps(report,indent=2),flush=True)
if __name__=='__main__':main()
