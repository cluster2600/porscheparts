"""Bounded, six/26-neighbour connectivity of sampled voids, not CFD topology."""
from array import array
import argparse
import hashlib
import json
import math
from pathlib import Path
import time

MAX_CELLS = 4_000_000


def classify(void_mask, shape, spacing, neighbours):
    """Label a finite sample lattice; any void on its six outer faces is exterior.

    Index = x + nx * (y + ny * z). No periodic wrap, interpolated edges or
    geometric channel are invented. One byte of state and one uint queue slot
    per sample bound storage. Returned component boxes are private grid indices.
    """
    if len(shape) != 3 or any(type(n) is not int or n < 3 for n in shape):
        raise ValueError('Three integer dimensions >=3 required')
    nx, ny, nz = shape
    size = nx * ny * nz
    if size > MAX_CELLS:
        raise ValueError('Sample count exceeds the fixed memory/work bound')
    if len(void_mask) != size or any(v not in (0, 1) for v in void_mask):
        raise ValueError('Mask must contain exactly one 0/1 byte per sample')
    if not math.isfinite(spacing) or spacing <= 0 or neighbours not in (6, 26):
        raise ValueError('Finite positive spacing and 6 or 26 neighbours required')
    labels = bytearray(void_mask)
    started = time.monotonic()
    offsets = [(dx, dy, dz) for dz in (-1, 0, 1) for dy in (-1, 0, 1)
               for dx in (-1, 0, 1) if (dx or dy or dz)
               and (neighbours == 26 or abs(dx) + abs(dy) + abs(dz) == 1)]
    queue = array('I')
    if queue.itemsize != 4:
        raise RuntimeError('This bounded queue requires a four-byte unsigned int')
    for z in range(nz):
        for y in range(ny):
            xs = range(nx) if z in (0, nz - 1) or y in (0, ny - 1) else (0, nx - 1)
            for x in xs:
                index = x + nx * (y + ny * z)
                if labels[index] == 1:
                    labels[index] = 2
                    queue.append(index)
    boundary_seeds = len(queue)

    def flood(marker):
        head = 0
        lo, hi = [nx, ny, nz], [-1, -1, -1]
        while head < len(queue):
            if head % 65536 == 0 and time.monotonic() - started > 240:
                raise TimeoutError('Connectivity time budget exceeded')
            index = queue[head]
            head += 1
            x = index % nx
            y = (index // nx) % ny
            z = index // (nx * ny)
            for i, value in enumerate((x, y, z)):
                lo[i], hi[i] = min(lo[i], value), max(hi[i], value)
            for dx, dy, dz in offsets:
                xx, yy, zz = x + dx, y + dy, z + dz
                if not (0 <= xx < nx and 0 <= yy < ny and 0 <= zz < nz):
                    continue
                other = xx + nx * (yy + ny * zz)
                if labels[other] == 1:
                    labels[other] = marker
                    queue.append(other)
        return {'sample_count': len(queue), 'grid_bbox_private': [lo, hi]}

    exterior_count = flood(2)['sample_count'] if queue else 0
    del queue[:]
    isolated = []
    for index in range(size):
        if labels[index] != 1:
            continue
        labels[index] = 3
        queue.append(index)
        isolated.append(flood(3))
        if len(isolated) > 100_000:
            raise ValueError('Isolated component count exceeds the report/memory bound')
        del queue[:]
    isolated.sort(key=lambda item: item['sample_count'], reverse=True)
    isolated_count = sum(item['sample_count'] for item in isolated)
    total_void = sum(void_mask)
    assert total_void == exterior_count + isolated_count
    return {
        'neighbours': neighbours, 'shape_xyz': list(shape),
        'sample_spacing_mm_under_scale_hypothesis': spacing,
        'boundary_void_seed_count': boundary_seeds,
        'total_void_sample_count': total_void,
        'exterior_connected_sample_count': exterior_count,
        'isolated_sample_count': isolated_count,
        'potential_isolated_component_count': len(isolated),
        'isolated_components_private': isolated,
        'voxel_sum_isolated_volume_mm3_estimate': isolated_count * spacing**3,
        'classification_is_grid_dependent': True,
        'physical_sealed_cavity_proved': False,
        'intake_exhaust_or_cooling_regions_classified': False,
        'CFD_domain_qualified': False, 'manufacturing_authorized': False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('sample_directory', type=Path)
    parser.add_argument('new_report', type=Path)
    args = parser.parse_args()
    if args.new_report.exists():
        parser.error('Output must not exist')
    metadata_path = args.sample_directory / 'sampling-report.json'
    metadata = json.loads(metadata_path.read_text())
    if metadata['status'] != 'native_sampling_passed_not_topology_qualification':
        parser.error('Native sampling did not pass its witnesses/partition screen')
    binary_path = args.sample_directory / 'void-occupancy.bin'
    if binary_path.stat().st_size > MAX_CELLS:
        parser.error('Occupancy file exceeds the fixed bound')
    mask = binary_path.read_bytes()
    digest = hashlib.sha256(mask).hexdigest()
    if digest != metadata['occupancy_sha256']:
        parser.error('Occupancy hash mismatch')
    sensitivity_path = args.sample_directory / 'void-occupancy-zero-as-void.bin'
    if sensitivity_path.stat().st_size != len(mask):
        parser.error('Sensitivity mask size mismatch')
    sensitivity_mask = sensitivity_path.read_bytes()
    sensitivity_digest = hashlib.sha256(sensitivity_mask).hexdigest()
    if sensitivity_digest != metadata['zero_as_void_occupancy_sha256']:
        parser.error('Sensitivity occupancy hash mismatch')
    if any(a > b for a, b in zip(mask, sensitivity_mask)):
        parser.error('The zero-as-void sensitivity must contain the primary void mask')
    changed_samples = sum(a != b for a, b in zip(mask, sensitivity_mask))
    if changed_samples != metadata['overlap_exact_zero_both_fields_samples']:
        parser.error('Mask differences must equal the exact shared-zero count')
    started = time.monotonic()
    results = [classify(mask, metadata['shape_xyz'], metadata['sample_spacing_mm'], n) for n in (6, 26)]
    sensitivity_results = results if mask == sensitivity_mask else [
        classify(sensitivity_mask, metadata['shape_xyz'], metadata['sample_spacing_mm'], n) for n in (6, 26)]
    assert results[1]['isolated_sample_count'] <= results[0]['isolated_sample_count']
    assert sensitivity_results[1]['isolated_sample_count'] <= sensitivity_results[0]['isolated_sample_count']
    report = {
        'schema': 'm64-picogk-void-connectivity-private/v1',
        'status': 'sampled_connectivity_classified_not_CFD_qualification',
        'sampling_report_sha256': hashlib.sha256(metadata_path.read_bytes()).hexdigest(),
        'occupancy_sha256': digest,
        'zero_as_void_occupancy_sha256': sensitivity_digest,
        'shared_exact_zero_samples': changed_samples,
        'primary_boundary_convention': metadata['primary_boundary_convention'],
        'sensitivity_boundary_convention': metadata['sensitivity_boundary_convention'],
        'VDB_sha256': metadata['VDB_sha256'],
        'source_body_STL_sha256': metadata['source_body_STL_sha256'],
        'algorithm_source_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'native_voxel_mm': metadata['native_voxel_mm'],
        'sample_phase': metadata['sample_phase'],
        'sampling_bounds_private': metadata['enclosure_bounds_private'],
        'results': results,
        'zero_as_void_sensitivity_results': sensitivity_results,
        'sensitivity_results_reused_because_masks_identical': mask == sensitivity_mask,
        'additional_exterior_samples_when_zeros_belong_to_void': [
            alternative['exterior_connected_sample_count'] - primary['exterior_connected_sample_count']
            for primary, alternative in zip(results, sensitivity_results)],
        'extra_exterior_samples_via_diagonal_adjacency': results[1]['exterior_connected_sample_count'] - results[0]['exterior_connected_sample_count'],
        'six_and_twenty_six_exterior_counts_agree': results[0]['exterior_connected_sample_count'] == results[1]['exterior_connected_sample_count'],
        'elapsed_seconds': time.monotonic() - started,
        'grid_resolution_and_phase_convergence_proved': False,
        'continuous_geometric_connectivity_proved': False,
        'CFD_domain_qualified': False, 'manufacturing_authorized': False,
    }
    with args.new_report.open('x') as stream:
        json.dump(report, stream, indent=2)
    print(json.dumps({key: report[key] for key in ('status', 'elapsed_seconds', 'extra_exterior_samples_via_diagonal_adjacency')}))


if __name__ == '__main__':
    main()
