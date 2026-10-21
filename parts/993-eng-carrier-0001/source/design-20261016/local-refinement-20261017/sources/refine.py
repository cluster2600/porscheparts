"""Thin experimental T4 API; no CAD, real mesh, tag transfer, or T10 export."""
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
TARGET = HERE / 'software/site-packages'
CAD = ROOT / 'work/part-workflow/runtimes/cad-base/lib/python3.10/site-packages'
sys.path.insert(0, str(CAD))
sys.path.insert(0, str(TARGET))
import numpy as np
import scipy
import skfem
from skfem import MeshTet1

assert skfem.__version__ == '12.0.2'
assert Path(skfem.__file__).resolve().is_relative_to(TARGET)
assert Path(np.__file__).resolve().is_relative_to(CAD)
assert Path(scipy.__file__).resolve().is_relative_to(CAD)


def refine_marked(points, cells, marked):
    """Return raw MeshTet1.refined output, preserving caller's global RNG state.

    The unmodified package resets its legacy NumPy RNG to 1337 for the temporary
    longest-edge ordering copy. This wrapper restores the previous caller state;
    it does not alter the package's refinement or returned coordinates/order.
    Inputs are compact T4 corners, not a T10 node table with unused midsides.
    """
    assert points.dtype == np.float64 and points.ndim == 2 and points.shape[1] == 3
    assert cells.ndim == 2 and cells.shape[1] == 4 and cells.dtype.kind in 'iu'
    assert marked.ndim == 1 and marked.dtype.kind in 'iu'
    assert np.isfinite(points).all() and np.all(cells >= 0) and np.all(cells < len(points))
    assert np.all(marked >= 0) and np.all(marked < len(cells))
    assert np.array_equal(np.unique(cells), np.arange(len(points)))
    state = np.random.get_state()
    try:
        result = MeshTet1(points.T.copy(), cells.T.copy()).refined(marked.copy())
    finally:
        np.random.set_state(state)
    return result.p.T.copy(), result.t.T.copy()
