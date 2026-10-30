"""Read all CLI coordinates and validate every material cross-section with GEOS."""
import argparse
import hashlib
import json
from pathlib import Path
import time
import numpy as np
import shapely
from shapely.geometry import Polygon, MultiPolygon, Point
from shapely.strtree import STRtree

def section(rings,return_geometry=False):
    positive=[];negative=[]
    for direction,xy in rings:
        if len(xy)<4 or not np.array_equal(xy[0],xy[-1]):raise ValueError('Open contour')
        polygon=Polygon(xy)
        if not polygon.is_valid or polygon.area<=0:raise ValueError(shapely.is_valid_reason(polygon))
        centred=xy-xy[0]
        signed=float(np.sum(centred[:-1,0]*centred[1:,1]-centred[1:,0]*centred[:-1,1])/2)
        if (signed>0)!=(direction==1):raise ValueError('Direction disagrees with coordinate winding')
        (positive if direction==1 else negative).append((polygon,xy))
    boundaries=[polygon.exterior for polygon,xy in positive+negative]
    if boundaries:
        pairs=STRtree(boundaries).query(boundaries,predicate='intersects')
        if np.any(pairs[0]<pairs[1]):raise ValueError('Distinct contours touch or intersect')
    if not positive:
        if negative:raise ValueError('Negative contours without positive exterior')
        return MultiPolygon() if return_geometry else (0.,0)
    tree=STRtree([p for p,xy in positive]);holes=[[] for _ in positive]
    for p,xy in negative:
        # A boundary vertex lies inside its parent because valid contours cannot touch.
        candidates=tree.query(Point(xy[0]),predicate='within')
        if len(candidates)==0:raise ValueError('Uncontained internal contour')
        parent=min(candidates,key=lambda i:positive[i][0].area)
        holes[parent].append(xy)
    material=MultiPolygon([Polygon(xy,holes[i]) for i,(p,xy) in enumerate(positive)])
    if not material.is_valid:raise ValueError(shapely.is_valid_reason(material))
    return material if return_geometry else (material.area,len(positive))

def main():
    p=argparse.ArgumentParser();p.add_argument('input',type=Path);p.add_argument('output',type=Path);p.add_argument('--volume-mm3',type=float,required=True);p.add_argument('--layer-mm',type=float,required=True);p.add_argument('--volume-reference-kind',choices=['surface','independent-layer-integral'],default='surface');a=p.parse_args()
    start=time.monotonic()
    # Independent analytic controls: cavity area, disjoint islands and crossed contours.
    outer=np.array([[0,0],[2,0],[2,2],[0,2],[0,0]],float)
    hole=np.array([[.5,.5],[.5,1.5],[1.5,1.5],[1.5,.5],[.5,.5]])
    assert section([(1,outer),(0,hole)])[0]==3
    assert section([(1,outer),(1,outer+3)])[0]==8
    try:section([(1,outer),(1,outer+1)])
    except ValueError:pass
    else:raise AssertionError('Overlap control not detected')
    try:section([(1,outer),(1,outer+2)])
    except ValueError:pass
    else:raise AssertionError('Point-touching contour control not detected')
    try:section([(1,np.array([[0,0],[2,2],[0,2],[2,0],[0,0]],float))])
    except ValueError:pass
    else:raise AssertionError('Self-intersection control not detected')
    rings=[];z=None;previous=0.;layers=[];errors=[];count=0;vertices=0;declared=None;ended=False;units=None;geometry=False
    def finish():
        nonlocal rings,previous
        if z is None:return
        try:area,components=section(rings)
        except ValueError as error:errors.append({'z_mm':z,'reason':str(error)});area=None;components=None
        layers.append({'z_mm':z,'height_mm':z-previous,'area_mm2':area,'contours':len(rings),'material_regions':components});previous=z;rings=[]
    with a.input.open() as stream:
        for raw in stream:
            line=raw.strip()
            if line.startswith('$$UNITS/'):units=float(line.split('/')[1]);assert units==1
            elif line.startswith('$$LAYERS/'):declared=int(line.split('/')[1])
            elif line=='$$GEOMETRYSTART':geometry=True
            elif line=='$$GEOMETRYEND':finish();ended=True
            elif line.startswith('$$LAYER/'):
                assert geometry and not ended
                finish();new=float(line.split('/')[1]);assert z is None or new>z
                if z is not None:assert abs(new-z-a.layer_mm)<1e-9
                z=new
            elif line.startswith('$$POLYLINE/'):
                assert geometry and not ended and z is not None
                fields=line.split('/')[1].split(',');part,direction,n=map(int,fields[:3]);assert part==1 and direction in (0,1) and len(fields)==3+2*n
                assert all('.' in s and 'e' not in s.lower() and sum(c.isdigit() for c in s)<=16 for s in fields[3:])
                xy=np.asarray(fields[3:],float).reshape(n,2);assert np.isfinite(xy).all();rings.append((direction,xy));count+=1;vertices+=n
    assert ended and units==1 and len(layers)==declared
    assert layers[0]['z_mm']==0 and layers[0]['contours']==0
    volume=sum(r['area_mm2']*r['height_mm'] for r in layers if r['area_mm2'] is not None)
    relative=abs(volume-a.volume_mm3)/a.volume_mm3
    limit=.002 if a.volume_reference_kind=='surface' else 1e-10
    report={'input_sha256':hashlib.sha256(a.input.read_bytes()).hexdigest(),'shapely_version':shapely.__version__,'geos_version':shapely.geos_version_string,'layers_including_empty_zero_layer':len(layers),'layer_mm':a.layer_mm,'contours':count,'vertices':vertices,'invalid_layers':len(errors),'errors':errors[:100],'all_layers_examined':True,'contour_controls_passed':True,'slice_volume_mm3':volume,'volume_reference_kind':a.volume_reference_kind,'surface_volume_mm3':a.volume_mm3 if a.volume_reference_kind=='surface' else None,'independent_layer_integral_mm3':a.volume_mm3 if a.volume_reference_kind=='independent-layer-integral' else None,'relative_slice_volume_difference':relative,'volume_difference_limit':limit,'contour_export_gate_passed':not errors and relative<limit,'machine_job':False,'manufacturing_qualified':False,'seconds':time.monotonic()-start}
    a.output.write_text(json.dumps(report,indent=2)+'\n');a.output.with_suffix('.layers.json').write_text(json.dumps(layers)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
