"""Partition UV rings touching at source vertices; never fill or remove support."""
import argparse
import json
from pathlib import Path
import shutil
import numpy as np
from shapely.geometry import Polygon,LineString
from shapely.ops import split,unary_union


def partition(polygon):
    pending=[polygon];done=[];cuts=0
    while pending:
        item=pending.pop();contact=None;hole=None
        for ring in item.interiors:
            region=Polygon(ring);intersection=item.exterior.intersection(region.boundary)
            if not intersection.is_empty:
                contact=intersection if intersection.geom_type=='Point' else list(intersection.geoms)[0]
                hole=region;break
        if contact is None:done.append(item);continue
        if contact.geom_type!='Point' or cuts>=20:raise ValueError('Unsupported UV contact; no automatic healing.')
        origin=np.array(contact.coords[0]);inside=np.array(hole.representative_point().coords[0]);direction=inside-origin
        direction/=np.linalg.norm(direction);extent=4*max(item.bounds[2]-item.bounds[0],item.bounds[3]-item.bounds[1])
        pieces=list(split(item,LineString([origin-direction*extent,origin,inside,inside+direction*extent])).geoms)
        if len(pieces)<2 or any(p.geom_type!='Polygon' or not p.is_valid for p in pieces):raise ValueError('Contact cut did not create valid charts.')
        pending.extend(pieces);cuts+=1
    return done,cuts


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--input',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    if args.output.exists():raise SystemExit('Existing contact atlas refused.')
    args.output.mkdir(parents=True);models=json.loads((args.input/'cad-domains.json').read_text());audit=[]
    for model in models:
        shutil.copy2(args.input/(model['id']+'-reference.npz'),args.output/(model['id']+'-reference.npz'))
        if not model['admitted']:continue
        charts=[];delta=0.;area=0.;cuts=0
        for d in model['domains']:
            original=Polygon(d['outer'],d['holes']);pieces,count=partition(original);cuts+=count
            difference=original.symmetric_difference(unary_union(pieces)).area
            if difference>1e-10*original.area:raise SystemExit('Contact partition changed source support.')
            delta+=difference;area+=original.area
            for piece in pieces:charts.append({'outer':list(piece.exterior.coords),'holes':[list(r.coords) for r in piece.interiors],'source_domain_index':d['source_domain_index']})
        audit.append({'id':model['id'],'input_charts':len(model['domains']),'output_charts':len(charts),'source_contact_cuts':cuts,'relative_support_difference':delta/area,'model_parameters_changed':False})
        model['domains']=charts
    (args.output/'cad-domains.json').write_text(json.dumps(models,indent=2)+'\n');shutil.copy2(args.input/'admissibility.json',args.output/'admissibility.json')
    (args.output/'contact-atlas-report.json').write_text(json.dumps(audit,indent=2)+'\n');print(json.dumps(audit))


if __name__=='__main__':main()
