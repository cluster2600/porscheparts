"""Represent the same observed cylindrical footprint using half-period charts."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import numpy as np
from shapely.geometry import Polygon,box
from shapely.ops import unary_union


def sha(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--input',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    if args.output.exists():raise SystemExit('Existing atlas directory refused.')
    args.output.mkdir(parents=True)
    data=json.loads((args.input/'cad-domains.json').read_text());audit=[]
    for model in data:
        shutil.copy2(args.input/(model['id']+'-reference.npz'),args.output/(model['id']+'-reference.npz'))
        if not model['admitted']:continue
        charts=[];old_area=0.;difference=0.
        for domain_index,domain in enumerate(model['domains']):
            original=Polygon(domain['outer'],domain['holes']);parts=[]
            low,high=original.bounds[1]-1,original.bounds[3]+1
            for left,right in [(0,np.pi),(np.pi,2*np.pi)]:
                clipped=original.intersection(box(left,low,right,high))
                if clipped.is_empty:continue
                polygons=[clipped] if clipped.geom_type=='Polygon' else list(clipped.geoms)
                for polygon in polygons:
                    if polygon.geom_type!='Polygon' or not polygon.is_valid:raise SystemExit('Invalid chart; no automatic geometry repair.')
                    parts.append(polygon);charts.append({'outer':list(polygon.exterior.coords),'holes':[list(r.coords) for r in polygon.interiors],
                        'source_domain_index':domain_index,'chart_width_radians':right-left})
            delta=original.symmetric_difference(unary_union(parts)).area
            if delta>1e-10*original.area:raise SystemExit('Atlas altered the support footprint.')
            old_area+=original.area;difference+=delta
        audit.append({'id':model['id'],'original_domains':len(model['domains']),'charts':len(charts),
            'relative_symmetric_difference':difference/old_area,'model_parameters_changed':False})
        model['domains']=charts
    (args.output/'cad-domains.json').write_text(json.dumps(data,indent=2)+'\n')
    shutil.copy2(args.input/'admissibility.json',args.output/'admissibility.json')
    report={'input_domains_sha256':sha(args.input/'cad-domains.json'),'source_sha256':sha(Path(__file__)),
        'regions':audit,'scope':'Representation seams only; no source gap fill, model refit or support extension.'}
    (args.output/'atlas-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))


if __name__=='__main__':main()
