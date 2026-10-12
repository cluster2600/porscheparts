#!/usr/bin/env python3
"""Refine the measured source wheel/nut gap in a fresh mesh-only control."""
import json, math, re
from pathlib import Path
import numpy as np
from prepare_case import sha
from prepare_castellated_control import prepare as prepare_unsnapped


def gap_spec(components, block_text):
    closed=sorted((c for c in components if c['closed']),key=lambda c:c['bounds_mm'][0][2])
    if len(closed)!=2:raise ValueError('Exactly two closed source components required')
    a,b=[np.asarray(c['bounds_mm'],dtype=float) for c in closed]
    if a.shape!=(2,3) or b.shape!=(2,3) or not np.isfinite([a,b]).all() or np.any(a[1]<=a[0]) or np.any(b[1]<=b[0]):raise ValueError('Invalid source component bounds')
    low,high=a[1,2],b[0,2];gap=high-low
    if gap<=0:raise ValueError('Positive axial gap required')
    vertices_text=block_text.split('vertices (',1)[1].split(');',1)[0]
    vertices=np.array([[float(x) for x in v.split()] for v in re.findall(r'\(([^()]*)\)',vertices_text)])*1000
    heights=[]
    for labels,counts in re.findall(r'hex\s*\(([^()]*)\)\s*(?:rotorZone\s*)?\(([^()]*)\)',block_text):
        ids=[int(x) for x in labels.split()];n=[int(x) for x in counts.split()]
        if len(ids)!=8 or len(n)!=3 or min(n)<=0:raise ValueError('Invalid native block definition')
        z=vertices[ids,2]
        if z.min()<=high and z.max()>=low:heights.append(float(np.ptp(z)/n[2]))
    if not heights or min(heights)<=0:raise ValueError('No background cells cover the gap')
    height=max(heights);level=max(0,math.ceil(math.log2(4*height/gap)))
    if level>3:raise ValueError('Gap needs refinement beyond the frozen level-three ceiling')
    # The source nut bounds cover the overlap; one parent cell pads the refinement box.
    lo=[b[0,0]-height,b[0,1]-height,low-height];hi=[b[1,0]+height,b[1,1]+height,high+height]
    return dict(source_axial_gap_mm=float(gap),parent_max_axial_cell_mm=height,minimum_cells_across_gap=4,level=level,predicted_axial_cell_mm=height/2**level,box_min_mm=lo,box_max_mm=hi)


def dictionary(text,spec):
    if text.count('geometry {')!=1 or text.count('refinementRegions {')!=1 or 'wheelNutGap' in text:raise ValueError('Unexpected meshing dictionary')
    vector=lambda v:'('+' '.join(format(x/1000,'.17g') for x in v)+')'
    geometry='wheelNutGap {type searchableBox; min '+vector(spec['box_min_mm'])+'; max '+vector(spec['box_max_mm'])+';} '
    region='wheelNutGap {mode inside; levels ((1e15 '+str(spec['level'])+'));} '
    return text.replace('geometry {','geometry {'+geometry).replace('refinementRegions {','refinementRegions {'+region)


def prepare(parent,inventory_path,control,output):
    inv=json.loads(inventory_path.read_text());prior=json.loads((parent/'case-manifest.json').read_text());reference=json.loads((control/'case-manifest.json').read_text())
    if inv['inventory_source_sha256']!=sha(Path(__file__).with_name('rotor_shell_inventory.py')) or inv['surface_sha256']!=prior['surface']['sha256']:raise ValueError('Frozen source inventory required')
    spec=gap_spec(inv['source_rotor_components'],(parent/'system/blockMeshDict').read_text())
    result=prepare_unsnapped(parent,output)
    if result['file_sha256']!=reference['file_sha256']:raise ValueError('Unsnapped inputs differ from control')
    path=output/'system/snappyHexMeshDict';path.write_text(dictionary(path.read_text(),spec))
    result.update(source_sha256=sha(Path(__file__)),inventory_sha256=sha(inventory_path),control_manifest_sha256=sha(control/'case-manifest.json'),gap_refinement=spec,control_change='Only add a source-derived local refinement box to unsnapped control 032; geometry unchanged.')
    result['file_sha256']['system/snappyHexMeshDict']=sha(path)
    (output/'case-manifest.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n');return result
