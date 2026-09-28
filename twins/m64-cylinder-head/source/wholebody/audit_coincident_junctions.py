#!/usr/bin/env python3
"""Audit exact-coordinate junctions without welding or deleting any mesh cell."""
import argparse
from collections import Counter, defaultdict
import itertools
import json
from pathlib import Path
import time

import numpy as np
from render_v5_v2 import sha, save
from trial_meshers_2026 import boundary, normalize_convention, read_gmsh
from audit_pinched_junction import BODY_SHA, locate


def components(nodes, pairs):
    adjacency = {n: set() for n in nodes}
    for a, b in pairs:
        adjacency[a].add(b); adjacency[b].add(a)
    count = 0
    remaining = set(nodes)
    while remaining:
        todo = [remaining.pop()]; count += 1
        while todo:
            for n in adjacency[todo.pop()] & remaining:
                remaining.remove(n); todo.append(n)
    return count


def link_summary(cells, node):
    """Combinatorial link necessary conditions; not geometric intersection proof."""
    selected = cells[np.any(cells == node, axis=1)]
    if not len(selected) or np.any((selected == node).sum(axis=1) != 1):
        raise ValueError('nondegenerate_incident_tetrahedra_required')
    triangles = [tuple(sorted(int(v) for v in c if v != node)) for c in selected]
    owners = defaultdict(list)
    for i, triangle in enumerate(triangles):
        for edge in itertools.combinations(triangle, 2): owners[edge].append(i)
    links = [pair for group in owners.values() for pair in itertools.combinations(group, 2)]
    edge_boundary = [edge for edge, group in owners.items() if len(group) == 1]
    degree = Counter(v for edge in edge_boundary for v in edge)
    vertices = set(v for tri in triangles for v in tri)
    region_count = components(range(len(triangles)), links)
    chi = len(vertices) - len(owners) + len(triangles)
    boundary_cycle = bool(edge_boundary and all(n == 2 for n in degree.values())
                          and components(degree, edge_boundary) == 1)
    necessary = (region_count == 1 and len(set(triangles)) == len(triangles)
                 and all(len(g) <= 2 for g in owners.values())
                 and ((not edge_boundary and chi == 2) or (boundary_cycle and chi == 1)))
    return dict(incident_tetrahedra=len(selected), link_components=region_count,
                link_euler=chi, link_edges_over_two=sum(len(g) > 2 for g in owners.values()),
                link_boundary_edges=len(edge_boundary), link_boundary_is_one_cycle=boundary_cycle,
                necessary_ball_or_halfball_conditions=necessary)


def run(args):
    source = Path(__file__)
    mesh = args.trial/'output-private.npz'; receipt = args.trial/'report.json'
    serialized = args.trial/'result-private.msh'
    if args.output.exists() or any(p.is_symlink() for p in (mesh, receipt, serialized, args.body)):
        raise ValueError('fresh_output_and_regular_inputs_required')
    pins = {p: sha(p) for p in (source, mesh, receipt, serialized, args.body)}
    producer = json.loads(receipt.read_text())
    if (pins[args.body] != BODY_SHA or producer.get('status') != 'completed_diagnostic_only'
            or producer.get('inputs_and_sources_unchanged') is not True
            or producer.get('mesh',{}).get('sha256') != pins[serialized]):
        raise ValueError('completed_bound_trial_and_native_body_required')
    with np.load(mesh, allow_pickle=False) as data:
        points, cells = data['points'], data['cells']
    import gmsh
    gmsh.initialize(['coincident-audit','-nopopup'],readConfigFiles=False,run=False)
    gmsh.option.setNumber('General.Terminal',0)
    try: rp, rc, _, _ = read_gmsh(serialized)
    finally: gmsh.finalize()
    if not np.array_equal(points,rp) or not np.array_equal(cells,rc):
        raise ValueError('producer_serialization_does_not_match_arrays')
    cells, reverse = normalize_convention(points, cells)
    if reverse or len(cells) > 3000000: raise ValueError('bounded_positive_mesh_required')
    started = time.monotonic()
    unique, inverse, counts = np.unique(points, axis=0, return_inverse=True, return_counts=True)
    repeated = np.flatnonzero(counts > 1)
    if len(repeated) > 100: raise ValueError('at_most_100_duplicate_groups')
    quotient = inverse[cells]  # Hypothesis only, never exported as a repaired mesh.
    qfaces = boundary(quotient)
    edges = np.concatenate([qfaces[:,ids] for ids in ((0,1),(1,2),(2,0))])
    _, incidence = np.unique(np.sort(edges,axis=1),axis=0,return_counts=True)
    from OCP.BRep import BRep_Builder
    from OCP.BRepTools import BRepTools
    from OCP.TopoDS import TopoDS_Shape
    shape = TopoDS_Shape()
    if not BRepTools.Read_s(shape,str(args.body),BRep_Builder()): raise ValueError('body_read_failed')
    rows = []
    for index in repeated:
        ids = np.flatnonzero(inverse == index)
        rows.append(dict(point_private=unique[index].tolist(), node_ids=ids.tolist(),
            separate_links=[link_summary(cells,int(n)) for n in ids],
            hypothetical_identified_link=link_summary(quotient,int(index)),
            nearby_native_faces_private=locate(shape,unique[index],.1)))
    report = dict(schema='m64-coincident-junction-audit/v1', status='completed_diagnostic_only',
        input_sha256=pins[mesh], producer_receipt_sha256=pins[receipt], source_sha256=pins[source],
        native_BRep_sha256=BODY_SHA, exact_duplicate_groups=len(rows),
        surplus_coordinate_records=int((counts-1).sum()), groups_private=rows,
        hypothetical_identification_boundary_edges_not_twice=int((incidence != 2).sum()),
        hypothetical_identification_rejected=bool((incidence != 2).any() or any(
            not r['hypothetical_identified_link']['necessary_ball_or_halfball_conditions'] for r in rows)),
        geometric_self_intersections_checked=False, geometry_modified=False,
        physical_millimetres_certified=False, CAE_authorized=False, manufacturing_authorized=False,
        elapsed_seconds=time.monotonic()-started, inputs_unchanged=all(sha(p)==s for p,s in pins.items()))
    save(args.output, report)
    print(json.dumps({k:v for k,v in report.items() if k != 'groups_private'}))


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('trial','body','output'): parser.add_argument('--'+name,type=Path,required=True)
    run(parser.parse_args())
