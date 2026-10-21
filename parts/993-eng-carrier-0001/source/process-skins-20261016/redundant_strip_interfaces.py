"""Omit only attested strips proven wholly redundant inside the source sheet.

This private adapter retains the lossless incremental constructor814 and all
943 operations. It neither reverses a contact role nor suppresses attestation.
The only changed decision certifies an entire contrary-directed quadrilateral
as already present in D before omitting its addition to the positive chain.
"""
import hashlib
import importlib.util
import math
from pathlib import Path

_IDS_PATH=Path(__file__).with_name('incremental_combinatorial_interfaces_ids.py')
_IDS_SHA256='81422bc8ce95beab8039e33f70a9d1274083be1ce1426c778c700a06a8b21df8'
if hashlib.sha256(_IDS_PATH.read_bytes()).hexdigest()!=_IDS_SHA256:
    raise ValueError('The frozen lossless incremental constructor changed')
_SPEC=importlib.util.spec_from_file_location('_private_redundant_strip_incremental',_IDS_PATH)
_IDS=importlib.util.module_from_spec(_SPEC);_SPEC.loader.exec_module(_IDS)
_BASE=_IDS._BASE
_BAND,_EXACT,Q=_BASE._BAND,_BASE._EXACT,_BASE.Q


def _coverage(*args):return _BASE._coverage(*args)
def _assemble(*args):return _BASE._assemble(*args)
def _exact_boundary_check(*args):return _BASE._exact_boundary_check(*args)


def _redundant_strip(domain,a,b,direction,penetration,message):
    aa=(a[0],Q(float(a[1])+direction*penetration))
    bb=(b[0],Q(float(b[1])+direction*penetration))
    points=[a,b,bb,aa]
    strip=_BASE.Polygon([[float(c) for c in p] for p in points])
    if strip.is_empty or not strip.is_valid or not strip.area:
        raise ValueError(message)
    proof=_BAND._COVERAGE.prove_polygon_covered(strip,domain)
    if not proof['passed']:
        error=ValueError(message)
        error.receipt=dict(proposed_strip_geometry_wkb_hex=strip.wkb_hex,
            proposed_strip_geometry_sha256=hashlib.sha256(strip.wkb).hexdigest(),
            source_domain_geometry_sha256=hashlib.sha256(domain.wkb).hexdigest(),
            exact_redundancy_coverage=proof)
        raise error
    return dict(schema='whole_attested_strip_already_in_source_domain-1',
        status='certified_redundant_no_addition',original_contact_role='upper' if direction>0 else 'lower',
        proposed_direction=direction,contact_role_unchanged=True,source_trace_unchanged=True,
        proposed_strip_geometry_wkb_hex=strip.wkb_hex,
        proposed_strip_geometry_sha256=hashlib.sha256(strip.wkb).hexdigest(),
        source_domain_geometry_sha256=hashlib.sha256(domain.wkb).hexdigest(),
        exact_redundancy_coverage=proof,exact_area_mm2=abs(_BAND._signed_area(points)),
        added_material_area_mm2=0,removed_source_material_area_mm2=0)


def _construct(domain, interfaces, penetration):
    """Return (Polygon, receipt), with no overlay and no new XY coordinate."""
    if (domain.geom_type != 'Polygon' or domain.is_empty or not domain.is_valid or
            not math.isfinite(penetration) or penetration <= 0):
        raise ValueError('A valid Polygon and positive finite penetration are required')
    if set(interfaces) != {'upper', 'lower'}:
        raise ValueError('Attested upper and lower interfaces are required')
    triangles, partition = _BAND._triangulation(domain)
    rings = [[_EXACT.point(p) for p in list(ring.coords)[:-1]]
             for ring in [domain.exterior, *domain.interiors]]
    for index, ring in enumerate(rings):
        if (_BAND._signed_area(ring) > 0) != (index == 0):
            ring.reverse()
    edge_rows = []
    all_triangles = list(triangles)
    for ring_index, ring in enumerate(rings):
        kinds = []
        for edge_index, (a, b) in enumerate(zip(ring, ring[1:] + ring[:1])):
            matches = {name: _coverage(a, b, paths) for name, paths in interfaces.items()}
            dx = b[0] - a[0]
            kind = 0
            redundant = None
            if dx:
                upper, lower = matches['upper'][0], matches['lower'][0]
                if upper and lower:
                    raise ValueError('One boundary edge has contradictory interface roles')
                if upper:
                    if dx >= 0:
                        redundant = _redundant_strip(domain,a,b,1,penetration,
                            'An upper interface points toward the material interior')
                    kind = 1
                elif lower:
                    if dx <= 0:
                        redundant = _redundant_strip(domain,a,b,-1,penetration,
                            'A lower interface points toward the material interior')
                    if not (a[1] == b[1] == 0):
                        if min(a[1], b[1]) <= Q(penetration):
                            raise ValueError('A lower strip would need a new plate intersection')
                        kind = -1
            kinds.append(kind)
            edge_rows.append(dict(ring=ring_index, edge=edge_index, direction=kind,
                source_edge=[a,b],
                whole_edge_attested={name: value[0] for name, value in matches.items()},
                exact_coverage_parameters={name: value[1] for name, value in matches.items()}))
            if redundant is not None:
                edge_rows[-1].update(strip_status='excluded_redundant_inside_source_domain',
                    proposed_strip_exact_area_mm2=redundant.pop('exact_area_mm2'),
                    redundancy_certificate=redundant)
                continue
            if kind:
                aa = (a[0], Q(float(a[1]) + kind * penetration))
                bb = (b[0], Q(float(b[1]) + kind * penetration))
                additions = []
                for tri in ([a, aa, bb], [a, bb, b]):
                    area = _BAND._signed_area(tri)
                    if area < 0:
                        raise ValueError('An added strip has negative orientation')
                    if area:
                        additions.append(tri)
                edge_rows[-1]['proposed_strip_exact_area_mm2'] = sum(_BAND._signed_area(t) for t in additions)
                try:
                    _assemble(all_triangles + additions)
                except ValueError as exc:
                    edge_rows[-1]['strip_status'] = 'excluded_would_not_form_simple_positive_sheet'
                    edge_rows[-1]['exclusion_receipt'] = getattr(exc, 'receipt', dict(error=str(exc)))
                else:
                    all_triangles.extend(additions)
                    edge_rows[-1]['strip_status'] = 'included'
    result, area = _assemble(all_triangles)
    simplicity = _exact_boundary_check(result)
    inclusion = _BAND._COVERAGE.prove_polygon_covered(domain, result)
    if not inclusion['passed']:
        raise ValueError('The assembled sheet lost source material')
    return result, _BAND._COVERAGE._encoded(dict(schema='combinatorial-continuous-interfaces-prototype-1',
        status='constructed_not_admitted', domain_geometry_sha256=hashlib.sha256(domain.wkb).hexdigest(),
        result_geometry_sha256=hashlib.sha256(result.wkb).hexdigest(), penetration_mm=penetration,
        polygon_overlay_operations=0, exact_positive_triangle_boundary_chain_equal=True,
        edge_subdivision='Exact collinear endpoints already present in source triangles or vertical strips',
        rational_boundary_simplicity=simplicity,
        exact_triangle_area_mm2=area, source_partition=partition, generated_triangles=len(all_triangles),
        added_triangles=len(all_triangles)-len(triangles), whole_edge_interfaces=edge_rows,
        included_strips=sum(row.get('strip_status') == 'included' for row in edge_rows),
        explicitly_excluded_strips=sum(row.get('strip_status','').startswith('excluded') for row in edge_rows),
        partially_attested_edges_not_extended=sum(not any(row['whole_edge_attested'].values()) and
            any(row['exact_coverage_parameters'].values()) for row in edge_rows),
        source_domain_coverage=inclusion,
        partial_source_edges_extended=False, intended_band_proof_required=True))


# These mutations affect only the constructor instance loaded above. Its
# original coverage/index and incremental assembly locks remain authoritative.
_BASE.construct=_construct
construct_with_statistics=_IDS.construct_with_statistics
construct=_IDS.construct
