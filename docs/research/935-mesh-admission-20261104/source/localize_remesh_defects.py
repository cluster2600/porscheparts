"""Map rejected candidate defects to the frozen parent without editing geometry."""
import argparse
import json
from pathlib import Path
import subprocess
import numpy as np
import igl
from trial_planar_flips import sha, save_json


def query(points, v, f):
    squared, face_ids, closest = igl.point_mesh_squared_distance(points, v, f)
    return np.sqrt(np.maximum(squared, 0)), face_ids, closest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--trial', type=Path, required=True)
    parser.add_argument('--inspector', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists(): raise SystemExit('Existing diagnostic directory refused.')
    args.output.mkdir(parents=True)
    inputs = {name: sha(args.trial/name) for name in ('parent.npz','candidate.npz','candidate.off')}
    save_json(args.output/'plan.json', {'input_sha256': inputs,
        'inspector_sha256': sha(args.inspector), 'source_sha256': sha(Path(__file__)),
        'distance_cutoff_mm': .01, 'sampling': 'Every parent and candidate triangle centroid; seven points on each intersecting candidate face.',
        'scope': 'Diagnostic mapping only; nearest-parent face is spatial support, not anatomical identity.'})
    p = subprocess.run([str(args.inspector), str(args.trial/'candidate.off')],
                       capture_output=True, text=True, timeout=300, check=True)
    indexed = json.loads(p.stdout); save_json(args.output/'intersection-indices.json', indexed)
    with np.load(args.trial/'parent.npz', allow_pickle=False) as a: v, f = a['vertices'], a['triangles']
    with np.load(args.trial/'candidate.npz', allow_pickle=False) as a: v2, f2 = a['vertices'], a['triangles']
    if indexed['triangles'] != len(f2) or indexed['vertices'] != len(v2):
        raise SystemExit('Native import dimensions differ from candidate arrays.')
    parent_dist, _, _ = query(v[f].mean(axis=1), v2, f2)
    candidate_dist, parent_nearest, _ = query(v2[f2].mean(axis=1), v, f)
    parent_bad = np.flatnonzero(parent_dist > .01)
    candidate_bad = np.flatnonzero(candidate_dist > .01)
    crossing_faces = np.unique(np.asarray(indexed['face_pairs'], dtype=np.int64).reshape(-1))
    if len(crossing_faces):
        points = v2[f2[crossing_faces]]
        probes = np.concatenate((points.reshape(-1,3), points.mean(axis=1),
                                 ((points + np.roll(points, 1, axis=1))/2).reshape(-1,3)))
        _, mapped_crossing_faces, _ = query(probes, v, f)
    else: mapped_crossing_faces = np.empty(0, dtype=np.int64)
    seeds = np.unique(np.concatenate((parent_bad, parent_nearest[candidate_bad], mapped_crossing_faces)))
    np.savez_compressed(args.output/'defect-face-ids.npz',
        parent_centroid_failures=parent_bad, candidate_centroid_failures=candidate_bad,
        intersecting_candidate_faces=crossing_faces, parent_seed_face_ids=seeds)
    report = {'parent_triangles_checked': len(f), 'candidate_triangles_checked': len(f2),
        'parent_centroid_failures': len(parent_bad), 'candidate_centroid_failures': len(candidate_bad),
        'parent_centroid_max_mm': float(parent_dist.max()),
        'candidate_centroid_max_mm': float(candidate_dist.max()),
        'intersection_pairs': len(indexed['face_pairs']), 'intersecting_candidate_faces': len(crossing_faces),
        'parent_seed_faces': len(seeds), 'parent_seed_fraction': len(seeds)/len(f),
        'raw_scan_edited': False, 'candidate_repaired': False,
        'admission': 'Rejected candidate retained; diagnostic seeds are not an accepted repair mask.',
        'limitations': 'Centroids and finite crossing probes do not bound whole triangles. OFF import counts are checked; semantic face identity and complete geometric mapping remain outside this diagnostic.'}
    for name, expected in inputs.items():
        if sha(args.trial/name) != expected: raise SystemExit('Input changed during diagnostic.')
    save_json(args.output/'report.json', report)
    print(json.dumps(report))


if __name__ == '__main__':
    main()
