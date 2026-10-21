"""Audit source-rational exposure contacts against recorded part boundary rings.

The frozen whole-build and two-domain audits remain unchanged. Only their
isolated contact callbacks are replaced. A hit is never encoded to float64
before deciding whether it has positive length in the recorded part section.
"""
import argparse
from fractions import Fraction as Q
import importlib.util
import json
import math
from pathlib import Path
import shutil

import audit_support_scanpaths_both as previous

SOURCE = Path(__file__).resolve().parent
PREVIOUS_SHA256 = 'be4ce81a979ad2a42ca6136e7321f926630bbb2b6fae1f5739a71941aedb5d9a'
COVERAGE_SHA256 = '0b1c7598a7358b9e9a384dd5b90dc66aa9e1ea53828033b6722477ec11409bed'
if previous.sha(previous.__file__) != PREVIOUS_SHA256:
    raise ValueError('The frozen two-domain audit adapter changed')
path = SOURCE/'exact_polygon_coverage.py'
if previous.sha(path) != COVERAGE_SHA256:
    raise ValueError('The frozen rational intersection kernel changed')
spec = importlib.util.spec_from_file_location('_exposure_anchor_polygon', path)
coverage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(coverage)
exact = coverage._EXACT
utilities = previous.legacy_module()
triangle_section, encode, canonical = previous.triangle_section, previous.encode, previous.canonical
verified_file, sha = previous.verified_file, previous.sha


class RecordedPartSection:
    def __init__(self, boundaries):
        self.boundaries = boundaries
        self.index = exact.BoundaryIndex(boundaries) if boundaries else None


def section_domain(points, offsets):
    # Preserve the original finite/closed/valid topology gate, but discard its
    # overlay coordinates. All contact predicates use the original rings.
    utilities.section_domain(points, offsets)
    boundaries = [[tuple(Q(float(c)) for c in p) for p in points[start:end]]
                  for start, end in zip(offsets[:-1], offsets[1:])]
    return RecordedPartSection(boundaries)


PLATE = RecordedPartSection([[tuple(Q(c) for c in p) for p in
    [(-250, -250), (250, -250), (250, 250), (-250, 250), (-250, -250)]]])


def positive_part_intervals(segment, domain):
    """Return all positive exact intervals of a rational hit in the closed rings."""
    if not isinstance(domain, RecordedPartSection):
        raise ValueError('Raw recorded part rings are required for rational anchors')
    if not domain.boundaries:
        return []
    a, b = (tuple(c if isinstance(c, Q) else Q(float(c)) for c in p) for p in segment)
    if a == b:
        return []
    intervals = []
    split = coverage._splits(a, b, domain.index)
    for first, last in zip(split[:-1], split[1:]):
        p = tuple(a[k]+(first+last)*(b[k]-a[k])/2 for k in (0, 1))
        if exact.inside(domain.boundaries, p, domain.index):
            intervals.append(tuple(tuple(a[k]+t*(b[k]-a[k]) for k in (0, 1)) for t in (first, last)))
    return intervals


def contacts_at_layer(segments, sections, face_groups, groups, z, penetration, domain, layer):
    lower, upper, witnesses = set(), set(), []
    relevant = {int(face_groups[r][f]) for owners in sections.values() for r, f in owners}
    bands = {i: {side: utilities.contact_band_segments(groups[i], side, z, penetration)
                 for side in ('lower', 'upper')} for i in relevant}
    for index, segment in enumerate(segments):
        owners = sorted({int(face_groups[r][f]) for r, f in sections[segment]})
        for owner in owners:
            group = groups[owner]
            for side in ('lower', 'upper'):
                hits = [utilities.overlap_segment(segment, trace) for trace in bands[owner][side]]
                hits = [hit for hit in hits if hit is not None]
                part = [interval for hit in hits for interval in positive_part_intervals(hit, domain)]
                plate_hits = []
                if layer == 0 and side == 'lower':
                    flat = [path for path in group['lower_contact_traces_2d_mm']
                            if all(float(p[1]) == 0 for p in path)]
                    plate_group = dict(group, lower_contact_traces_2d_mm=flat)
                    if '_exact_lower_contact_traces' in group:
                        plate_group['_exact_lower_contact_traces'] = [trace for trace in group['_exact_lower_contact_traces']
                            if all(p[1] == 0 for p in trace)]
                    for trace in utilities.contact_band_segments(plate_group, 'lower', z, penetration):
                        hit = utilities.overlap_segment(segment, trace)
                        if hit is not None:
                            plate_hits.extend(positive_part_intervals(hit, PLATE))
                if part or plate_hits:
                    (lower if side == 'lower' else upper).add(index)
                    # This diagnostic encoding/length follows the exact verdict;
                    # neither contributes to the decision that contact is real.
                    length = sum(math.hypot(*(float(b[k]-a[k]) for k in (0, 1))) for a, b in part)
                    witnesses.append(coverage._encoded(dict(segment=index, group=group['id'],
                        region=group['region'], side=side,
                        anchor='plate_first_layer' if plate_hits else 'positive_rational_interval_in_recorded_part_section',
                        part_overlap_length_mm=length, part_overlap_length_is_diagnostic=True,
                        exact_part_overlap_intervals=part, exact_plate_overlap_intervals=plate_hits)))
    return lower, upper, witnesses


def audit(directory, output, source_stl, part_cache=None):
    directory, output = Path(directory).resolve(), Path(output).resolve()
    paths = [Path(__file__), SOURCE/'audit_support_scanpaths_both.py', SOURCE/'audit_support_scanpaths.py',
             SOURCE/'exact_contacts.py', SOURCE/'exact_contacts_both.py', SOURCE/'exact_polygon_coverage.py',
             directory/'report.json']
    frozen = {path: sha(path) for path in paths}
    if frozen[SOURCE/'audit_support_scanpaths_both.py'] != PREVIOUS_SHA256:
        raise ValueError('The frozen two-domain adapter changed')
    if frozen[SOURCE/'exact_polygon_coverage.py'] != COVERAGE_SHA256:
        raise ValueError('The frozen rational intersection helper changed')
    legacy = previous.legacy_module()
    domains = previous.ContactDomains(json.loads((directory/'report.json').read_text()), legacy.pointer)
    legacy.clip_contacts, legacy.contact_encoding_check = domains.clip, domains.encoding_check
    legacy.section_domain, legacy.contacts_at_layer = section_domain, contacts_at_layer
    result = legacy.audit(directory, output, source_stl, part_cache)
    if any(sha(path) != digest for path, digest in frozen.items()):
        raise ValueError('Rational anchor source, predicate or process changed during audit')
    for path in paths[:-1]:
        shutil.copy2(path, output/'source'/path.name)
    result.update(schema='carrier-support-exposure-exact-anchors-v1',
        contact_clip_scope=previous.CONTRACT, contact_domain_groups_verified=domains.groups,
        rational_part_contact_intersections=True, part_contact_intermediate_encoding=False,
        part_contact_domain='Exact parity of the same-layer recorded closed part boundary rings; no overlay coordinates used.',
        encoded_anchor_scope='Anchors proved on rational source hits; correctly rounded exposure graph connectivity checked separately.',
        rational_anchor_adapter_source_sha256=frozen[Path(__file__)],
        frozen_two_domain_adapter_source_sha256=PREVIOUS_SHA256,
        frozen_full_audit_source_sha256=previous.LEGACY_SHA256,
        rational_anchor_dependencies_sha256={path.name: digest for path, digest in frozen.items() if path != directory/'report.json'})
    (output/'assessment.json').write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--source-stl', type=Path, required=True)
    parser.add_argument('--part-cache', type=Path)
    args = parser.parse_args()
    result = audit(args.directory, args.output, args.source_stl, args.part_cache)
    print(json.dumps({key: result[key] for key in ('status', 'layers_audited', 'rational_part_contact_intersections')}))
    raise SystemExit(0 if result['status'] == 'passed' else 3)
