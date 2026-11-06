"""Complete vertex/triangle bound for a finite binary64 translation using TwoSum."""
import ctypes
import numpy as np
LIMIT_MM = 1e-12

def translate(local, origin):
    local = np.asarray(local, dtype=np.float64)
    origin = np.asarray(origin, dtype=np.float64)
    if local.ndim != 2 or local.shape[1] != 3 or origin.shape != (3,):
        raise ValueError('XYZ coordinates required')
    if not np.isfinite(local).all() or not np.isfinite(origin).all():
        raise ValueError('Finite coordinates required')
    if np.max(np.abs(local)) > 256 or np.max(np.abs(origin)) > 256:
        raise ValueError('Outside admitted coordinate range')
    if not np.array_equal(local, local.astype(np.float32).astype(np.float64)):
        raise ValueError('Native binary32 local coordinates required')
    if ctypes.CDLL(None).fegetround() != 0:
        raise ValueError('Round-to-nearest environment required')
    # Distinct NumPy operations prevent contraction. Float32 locals and bounded
    # origins preclude overflow; TwoSum recovers the exact addition residual.
    world = local + origin
    recovered_origin = world - local
    error = (local - (world - recovered_origin)) + (origin - recovered_origin)
    magnitude = np.abs(error)
    bounds = np.nextafter(np.nextafter(magnitude[:, 0] + magnitude[:, 1], np.inf) + magnitude[:, 2], np.inf)
    bounds[np.all(error == 0, axis=1)] = 0
    maximum = float(bounds.max())
    if maximum > LIMIT_MM:
        raise ValueError('Complete translation budget exceeded')
    return world, error, dict(
        method='Error-free TwoSum; outward-rounded L1 bound extended over every triangle by convexity',
        complete_translation_bound_mm=maximum, fixed_limit_mm=LIMIT_MM,
        nonexact_coordinate_additions=int(np.count_nonzero(error)),
        all_additions_exact=bool(np.all(error == 0)), rounding_mode='nearest',
        local_binary32=True, coordinate_absolute_limit_mm=256)
