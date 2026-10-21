"""Fixed nine-node Exodus cube readback; no generic mesh/format fallback."""
import hashlib
import json
import math
from pathlib import Path
from collections import Counter, defaultdict


def need(ok, message):
    if not ok: raise ValueError(message)


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def oriented(row):
    return min(tuple(row[i:]+row[:i]) for i in range(3))


def determinant(p):
    e = [tuple(p[j][k]-p[0][k] for k in range(3)) for j in [1,2,3]]
    return sum(e[0][k]*(e[1][(k+1)%3]*e[2][(k+2)%3]-e[1][(k+2)%3]*e[2][(k+1)%3]) for k in range(3))


def compare(coords, cells, side_elements, side_numbers, side_table, exodus_w, sampled_rows, reference):
    """Lists are copied from one fixed Exodus block; table must be separately source-bound."""
    need(len(coords)==9 and len(cells)==12 and len(exodus_w)==9, 'Complete 9-node/12-TET4 data required')
    need(all(len(p)==3 and all(math.isfinite(v) for v in p) for p in coords), 'Finite complete 3D coordinates required')
    coords=list(map(tuple,coords));expected=dict(zip(map(tuple,reference['coordinates_mm']),reference['node_tags']))
    need(len(set(coords))==9 and set(coords)==set(expected), 'Exact complete authored coordinates required')
    need(all(len(row)==4 and all(type(v) is int and 1<=v<=9 for v in row) and len(set(row))==4 for row in cells), 'Four distinct valid internal node indices per TET4')
    cells=[[v-1 for v in row] for row in cells]
    signatures=[tuple(sorted(expected[coords[v]] for v in row)) for row in cells]
    wanted=[tuple(sorted(row)) for row in reference['positive_tetrahedra_node_tags']]
    need(len(set(signatures))==12 and Counter(signatures)==Counter(wanted), 'Exact complete authored cell set/no duplicates')
    used={v for row in cells for v in row};need(used==set(range(9)), 'No orphan imported node')
    determinants=[determinant([coords[v] for v in row]) for row in cells]
    need(all(v==4 and math.isfinite(v) and v>0 for v in determinants), 'All imported positive Jacobians must equal exact authored4')
    faces=defaultdict(list)
    for i,row in enumerate(cells):
        for corners in [(1,2,3),(0,3,2),(0,1,3),(0,2,1)]:
            face=[row[k] for k in corners];faces[tuple(sorted(face))].append((i,oriented(face)))
    boundary={}
    for key,items in faces.items():
        need(len(items) in (1,2), 'Manifold tetrahedral face incidence required')
        if len(items)==1:boundary[key]=items[0]
        else:
            rev=oriented(list(reversed(items[0][1])))
            need(rev==items[1][1], 'Interior face orientations must oppose')
    need(len(boundary)==12, 'Exactly twelve count-one tetrahedral boundary faces')
    actual_boundary=Counter(oriented([expected[coords[v]] for v in row]) for _,row in boundary.values())
    need(actual_boundary==Counter(oriented(row) for row in reference['outward_triangles_node_tags']), 'Exact complete outward authored boundary')
    need(isinstance(side_table,dict) and set(side_table)=={1,2,3,4} and all(len(v)==3 and set(v)<={0,1,2,3} and len(set(v))==3 for v in side_table.values()), 'Source-bound TET4 Exodus side map required')
    need(len(side_elements)==len(side_numbers)==12 and all(type(v) is int and 1<=v<=12 for v in side_elements) and all(type(v) is int and v in side_table for v in side_numbers), 'Complete valid sideset11 entries')
    selected=[]
    for element,side in zip(side_elements,side_numbers):
        row=[cells[element-1][k] for k in side_table[side]];key=tuple(sorted(row))
        need(key in boundary and boundary[key][0]==element-1 and oriented(row)==boundary[key][1], 'Sideset source orientation/owning cell association')
        selected.append(key)
    need(len(set(selected))==12 and set(selected)==set(boundary), 'Sideset11 complete exterior coverage without duplicates')
    need(all(math.isfinite(v) for v in exodus_w), 'Finite complete Exodus final field')
    samples={};sample_ids=set()
    for row in sampled_rows:
        xyz=tuple(float(row[k]) for k in ['x','y','z']);value=float(row['w']);tag=float(row['id'])
        need(math.isfinite(tag) and tag==int(tag) and tag>=0 and int(tag) not in sample_ids and xyz in expected and xyz not in samples and math.isfinite(value), 'Complete unique sampled node/field association')
        samples[xyz]=value;sample_ids.add(int(tag))
    need(set(samples)==set(coords), 'Complete nine-node CSV/Exodus coordinate association')
    errors=[abs(float(exodus_w[i])-samples[p]) for i,p in enumerate(coords)]
    reference_errors=[abs(float(exodus_w[i])-(.25 if p==(0,0,0) else 0.)) for i,p in enumerate(coords)]
    need(max(errors)<=1e-10 and max(reference_errors)<=1e-10, 'Complete final field agreement/discrete oracle')
    return dict(status='fixed_imported_cube_topology_sideset_and_field_readback_passed',nodes=9,tetrahedra=12,
        unique_coordinates=9,orphan_nodes=0,duplicate_cells=0,minimum_Jacobian=4,maximum_Jacobian=4,
        total_tetrahedral_volume_mm3=sum(determinants)/6,count_one_boundary_faces=12,exact_outward_boundary=True,
        all_internal_face_orientations_opposite=True,sideset11_complete=True,
        maximum_Exodus_vs_CSV_w_difference_mm2=max(errors),maximum_Exodus_discrete_reference_error_mm2=max(reference_errors),
        row_equals_original_Gmsh_or_PETSc_ID_assumed=False,head_or_convergence_or_physical_qualification=False)


def side_table_from_primary(path, digest):
    import re
    need(sha(path)==digest, 'Exact reviewed SEACAS primary source required')
    source=Path(path).read_text()
    match=re.search(r'static const int tetra_table\[4\]\[7\]\s*=\s*\{(.*?)\};',source,re.S)
    need(match is not None, 'Explicit primary tetra_table missing')
    rows=[list(map(int,re.findall(r'\d+',row))) for row in re.findall(r'\{([^{}]+)\}',match.group(1))]
    need(len(rows)==4 and all(len(row)==7 for row in rows), 'Exact four primary side rows required')
    return {i+1:[v-1 for v in row[:3]] for i,row in enumerate(rows)}


def read_exodus(path):
    # Existing SciPy API; importing it is permitted only during a separately reviewed launch.
    from scipy.io import netcdf_file
    import scipy
    import numpy
    need(scipy.__version__=='1.17.1' and numpy.__version__=='2.2.6', 'Existing probed reader versions required')
    with Path(path).open('rb') as stream:need(stream.read(4)==b'CDF\x02', 'Recorded CDF2 Exodus format required')
    with netcdf_file(str(path),mode='r',mmap=False,maskandscale=False) as dataset:
        dims=dataset.dimensions
        need(all(dims.get(k)==v for k,v in {'num_dim':3,'num_nodes':9,'num_elem':12,'num_el_blk':1,'num_side_sets':1,'num_nod_var':1}.items()), 'Fixed cube Exodus dimensions')
        def array(name, shape):
            need(name in dataset.variables, 'Required Exodus variable missing: '+name)
            value=dataset.variables[name].data.copy()
            need(value.shape==shape, 'Exact Exodus variable shape: '+name)
            return value.tolist()
        def text(row):
            return b''.join(row).split(b'\0',1)[0].decode('ascii').strip()
        coords=list(map(list,zip(*(array('coord'+axis,(9,)) for axis in 'xyz'))))
        cells=array('connect1',(12,4))
        element_type=getattr(dataset.variables['connect1'],'elem_type',b'')
        need(isinstance(element_type,bytes) and element_type.decode('ascii').strip().upper() in {'TET4','TETRA','TETRA4'}, 'Explicit four-node tetrahedral element type')
        need(array('ss_prop1',(1,))==[11] and array('ss_status',(1,))==[1], 'One active boundary sideset11 required')
        names=dataset.variables.get('ss_names');need(names is not None and names.data.shape[0]==1 and text(names.data.copy().tolist()[0])=='all_boundary', 'Exact boundary sideset name')
        elements=array('elem_ss1',(12,));sides=array('side_ss1',(12,))
        node_map=array('node_num_map',(9,));element_map=array('elem_num_map',(12,))
        need(all(type(v) is int and v>0 for v in node_map+element_map) and len(set(node_map))==9 and len(set(element_map))==12, 'Complete unique observed external node/element maps')
        times=dataset.variables['time_whole'].data.copy().tolist()
        need(isinstance(times,list) and times and all(math.isfinite(v) for v in times) and all(a<b for a,b in zip(times,times[1:])), 'Finite ordered time export')
        names=dataset.variables.get('name_nod_var');need(names is not None and names.data.shape[0]==1 and text(names.data.copy().tolist()[0])=='w', 'Exactly the declared nodal field w')
        fields=array('vals_nod_var1',(len(times),9));w=fields[-1]
        return dict(coords=coords,cells=cells,side_elements=elements,side_numbers=sides,exodus_w=w,
            observed_external_node_map=node_map,observed_external_element_map=element_map,times=times,
            variable_names=sorted(dataset.variables),dimensions=dict(dims),element_type=element_type.decode('ascii'))


def main(contract_path,digest,output):
    import csv
    import sys
    need(sha(contract_path)==digest, 'Exact frozen readback contract required');c=json.loads(Path(contract_path).read_text())
    need(c['readback_launch_authorized'] is True and c['root_and_peer_review_complete'] is True, 'Separate exact readback launch required')
    output=Path(output);need(str(output.resolve())==c['expected_output'] and not output.exists() and not output.is_symlink(), 'Fresh exact report path required')
    need(sha(sys.executable)==c['python_sha256'] and sha(__file__)==c['reader_sha256'], 'Reader/interpreter identity')
    for name,h in c['input_sha256'].items():need(sha(name)==h, 'Before readback input drift: '+name)
    data=read_exodus(c['Exodus_file']);reference=json.loads(Path(c['cube_reference']).read_text())
    table=side_table_from_primary(c['primary_side_source'],c['primary_side_source_sha256'])
    with Path(c['nodal_CSV']).open() as stream:
        csv_reader=csv.DictReader(stream);need(csv_reader.fieldnames and len(set(csv_reader.fieldnames))==len(csv_reader.fieldnames), 'Unique CSV columns');rows=list(csv_reader)
    result=compare(data['coords'],data['cells'],data['side_elements'],data['side_numbers'],table,data['exodus_w'],rows,reference)
    for name,h in c['input_sha256'].items():need(sha(name)==h, 'After readback input drift: '+name)
    need(sha(contract_path)==digest, 'Contract drift during readback')
    result.update(contract_sha256=digest,reader_sha256=sha(__file__),input_sha256=c['input_sha256'],
        primary_side_table_zero_based=table,external_node_map=data['observed_external_node_map'],external_element_map=data['observed_external_element_map'],
        all_serialized_times=data['times'],final_time=data['times'][-1],Exodus_dimensions=data['dimensions'],Exodus_element_type=data['element_type'],all_inputs_unchanged=True,
        solver_rerun=False,mesh_modified=False,reference_scope='One exact imported software cube; no head or continuum convergence qualification')
    with output.open('x') as stream:json.dump(result,stream,indent=2,allow_nan=False);stream.write('\n')


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--contract',type=Path,required=True)
    parser.add_argument('--contract-sha256',required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    main(args.contract,args.contract_sha256,args.output)
