"""Construct every free interval continuously, with audited source-edge strips.

The rounded GEOS band is retained as a diagnostic. Confinement is decided only
by the exact union of the original domain triangle sweeps. Native material is
compared diagnostically; this policy constructs a new sheet from the complete D.
"""
import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np
import shapely
from shapely.geometry import MultiPolygon, box

SOURCE = Path(__file__).resolve().parent
CONSTRUCTION_SHA256 = '94393c465fb15c1c3129ad8e482ea19cd597d3e716714e069b4eaee38b80e2fa'
COVERAGE_SHA256 = '0b1c7598a7358b9e9a384dd5b90dc66aa9e1ea53828033b6722477ec11409bed'
BAND_SHA256 = 'c6452e918ed5fd04bfd1595102eb8c691c697c18477d7b924e29ff7465c62286'


def _load(name, expected):
    path = SOURCE / (name + '.py')
    if not path.is_file():
        path = SOURCE.parent / 'process-scanpath-audit-20261016' / path.name
    if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
        raise ValueError('A combinatorial construction dependency changed')
    spec = importlib.util.spec_from_file_location('carrier_continuous_' + name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_CONSTRUCTION = _load('combinatorial_interfaces', CONSTRUCTION_SHA256)
_COVERAGE = _load('exact_polygon_coverage', COVERAGE_SHA256)
_UNION = _load('exact_band_union_v3', BAND_SHA256)


def repair(material, domain, interfaces, penetration):
    from grid_intervals import parts, vertical_contact_band, contacts
    from continuous_prism_interfaces import no_positive_connection
    if interfaces is None or set(interfaces) != {'upper', 'lower'}:
        raise ValueError('Continuous construction requires attested source interfaces')
    if not np.isfinite(penetration) or penetration <= 0:
        raise ValueError('Explicit positive penetration is required')
    interface_trees = {name: shapely.STRtree([shapely.LineString(path) for path in interfaces[name]])
                       for name in ['upper', 'lower']}
    pieces, rows = [], []
    for index, free in enumerate(parts(domain)):
        local_interfaces = {name: [interfaces[name][int(i)] for i in
            sorted(interface_trees[name].query(box(*free.bounds)))] for name in ['upper', 'lower']}
        interface_sha = hashlib.sha256(json.dumps(local_interfaces, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()
        result, construction = _CONSTRUCTION.construct(free, local_interfaces, penetration)
        exact_core = _COVERAGE.prove_polygon_covered(free, result)
        exact_union = _UNION.prove_band_covered(result, free, penetration)
        if not exact_core['passed'] or not exact_union['passed']:
            error = ValueError('The continuous construction failed exact inclusion or confinement')
            error.receipt = dict(exact_free_domain_coverage=exact_core,
                exact_intended_band_union_confinement=exact_union, construction=construction)
            raise error
        allowed = vertical_contact_band(free, penetration)
        allowed = allowed.intersection(box(allowed.bounds[0], 0., allowed.bounds[2], max(0., allowed.bounds[3])))
        native = material.intersection(allowed)
        contact = contacts(result, free, local_interfaces, required_only=True)
        required = [r for r in contact if r['kind'] == 'required_free_interval']
        if not required or not all(r['passed'] for r in required):
            error = ValueError('The constructed continuous interval lacks a true contact')
            error.receipt = dict(contacts=required, construction=construction)
            raise error
        outside = result.difference(allowed).area
        rows.append(dict(domain_index=index, continuous_interface_selected=True,
            reason='explicit_continuous_domain_with_attested_nonoverlapping_edge_strips',
            source_domain_geometry_wkb_hex=free.wkb_hex,
            source_domain_geometry_sha256=hashlib.sha256(free.wkb).hexdigest(),
            generated_material_geometry_wkb_hex=result.wkb_hex,
            generated_material_geometry_sha256=hashlib.sha256(result.wkb).hexdigest(),
            own_allowed_domain_geometry_wkb_hex=allowed.wkb_hex,
            own_allowed_domain_geometry_sha256=hashlib.sha256(allowed.wkb).hexdigest(),
            attested_source_interfaces=local_interfaces, attested_source_interfaces_sha256=interface_sha,
            combinatorial_construction=construction, exact_free_domain_coverage=exact_core,
            exact_intended_band_union_confinement=exact_union,
            band_authority='exact_intended_sweep_union', legacy_overlay_confinement_passed=outside == 0.,
            native_material_components=len(parts(native)), generated_material_components=1,
            original_free_area_mm2=free.area, native_material_area_mm2=native.area,
            generated_material_area_mm2=result.area,
            removed_native_material_area_mm2=native.difference(result).area,
            added_material_area_mm2=result.difference(native).area,
            upper_contact_after_mm=sum(r['upper_contact_trace_mm'] for r in required),
            lower_contact_after_mm=sum(r['lower_contact_trace_mm'] for r in required),
            negative_Z_area_mm2=result.intersection(box(result.bounds[0], min(-1.,result.bounds[1]-1.), result.bounds[2], 0.)).area,
            outside_own_free_vertical_contact_band_area_mm2=outside))
        pieces.append(result)
    if not pieces:
        raise ValueError('Continuous construction requires at least one free interval')
    tree = shapely.STRtree(pieces)
    pair_proofs = []
    for i, piece in enumerate(pieces):
        for j in tree.query(piece):
            if j <= i:
                continue
            proof = no_positive_connection(piece, pieces[j])
            pair_proofs.append(dict(intervals=[i, int(j)], receipt=proof))
            if not proof['passed']:
                raise ValueError('The continuous construction joins distinct free intervals')
    result = pieces[0] if len(pieces) == 1 else MultiPolygon(pieces)
    if not result.is_valid:
        raise ValueError('The direct interval collection is invalid')
    return result, dict(strategy='continuous_domain_with_nonoverlapping_attested_edge_strips',
        vertical_contact_penetration_mm=penetration, plate_Z_mm=0., intervals=rows,
        selected_intervals=len(rows), distinct_interval_connection_proofs=pair_proofs,
        combinatorial_construction_source_sha256=CONSTRUCTION_SHA256,
        exact_polygon_coverage_source_sha256=COVERAGE_SHA256,
        exact_intended_band_union_source_sha256=BAND_SHA256,
        polygon_overlay_operations_for_material=0,
        increased_contact_requires_detachment=True, distinct_free_intervals_joined=0,
        source_domain_geometry_sha256=hashlib.sha256(domain.wkb).hexdigest(),
        generated_material_geometry_sha256=hashlib.sha256(result.wkb).hexdigest())
