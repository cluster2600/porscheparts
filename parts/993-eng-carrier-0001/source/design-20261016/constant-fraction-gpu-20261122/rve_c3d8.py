"""The periodic gyroid cell of the constant-fraction study, assembled once and solved by a direct solver.

run_constant_fraction_case.py writes one CalculiX deck per strain mode and solves it on one thread;
at N=48 that passed the runner's 1200 s ceiling and multithreaded SPOOLES returned wrong solves. This
script states the same discrete problem and solves it with one factorisation for the six modes:

  geometry   gyroid_magnitude and threshold_for_fraction imported from run_constant_fraction_case.py,
             so the cells are the same cells;
  elements   C3D8, eight nodes, 2 x 2 x 2 Gauss points, isotropic E = 107 GPa or E x floor, nu = 0.31;
  periodity  u(x + e_a) = u(x) + H e_a on the unit cube, node (0,0,0) held: the *EQUATION set of the
             deck, written here as u = H x + w with w periodic, which is the same space of solutions;
  output     the mean of the integration-point stresses / 0.001 per mode, the same six-mode tensor.

Backends: "scipy" (SuperLU, CPU) and "cudss" (NVIDIA cuDSS through nvmath-python, GPU). A backend is
admitted only if it reproduces CalculiX's committed tensors (see study.py and contract.json).

It establishes no carrier convergence, no cellular part and no manufacturing release.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import time
from pathlib import Path

import numpy as np
import scipy.sparse as sp
from scipy.sparse.csgraph import connected_components

HERE = Path(__file__).resolve().parent
CASE = HERE.parent / "constant-fraction-20261026" / "run_constant_fraction_case.py"
_spec = importlib.util.spec_from_file_location("cf_case", CASE)
cf_case = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cf_case)
E_MPA, NU, AMPLITUDE = cf_case.E_MPA, cf_case.NU, cf_case.AMPLITUDE
CORNERS = np.array([[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0], [0, 0, 1], [1, 0, 1], [1, 1, 1], [0, 1, 1]])
VOIGT = [(0, 0), (1, 1), (2, 2), (0, 1), (0, 2), (1, 2)]      # CalculiX stress order: 11 22 33 12 13 23


def elasticity(E: float, nu: float) -> np.ndarray:
    lam, mu = E * nu / ((1 + nu) * (1 - 2 * nu)), E / (2 * (1 + nu))
    D = np.zeros((6, 6))
    D[:3, :3] = lam
    D[np.arange(3), np.arange(3)] += 2 * mu
    D[3:, 3:] = np.eye(3) * mu
    return D


def element(h: float):
    """B at the eight Gauss points (8, 6, 24) and the stiffness for E = 1 (24, 24) of a cube of side h."""
    g = 1 / np.sqrt(3)
    B = np.zeros((8, 6, 24))
    for q, (a, b, c) in enumerate(CORNERS):
        xi = np.array([(2 * a - 1) * g, (2 * b - 1) * g, (2 * c - 1) * g])
        s = 2 * CORNERS - 1                                         # corner signs
        dN = np.stack([s[:, 0] * (1 + s[:, 1] * xi[1]) * (1 + s[:, 2] * xi[2]),
                       s[:, 1] * (1 + s[:, 0] * xi[0]) * (1 + s[:, 2] * xi[2]),
                       s[:, 2] * (1 + s[:, 0] * xi[0]) * (1 + s[:, 1] * xi[1])], axis=1) / 8 * (2 / h)
        for n in range(8):
            dx, dy, dz = dN[n]
            B[q, 0, 3 * n], B[q, 1, 3 * n + 1], B[q, 2, 3 * n + 2] = dx, dy, dz
            B[q, 3, 3 * n], B[q, 3, 3 * n + 1] = dy, dx
            B[q, 4, 3 * n], B[q, 4, 3 * n + 2] = dz, dx
            B[q, 5, 3 * n + 1], B[q, 5, 3 * n + 2] = dz, dy
    D1 = elasticity(1.0, NU)
    K = np.einsum("qai,ab,qbj->ij", B, D1, B) * (h ** 3 / 8)          # Gauss weights 1, Jacobian (h/2)^3
    return B, K


def strain_mode(mode: int) -> np.ndarray:
    H = np.zeros((3, 3))
    if mode < 3:
        H[mode, mode] = AMPLITUDE
    else:
        i, j = VOIGT[mode]
        H[i, j] = H[j, i] = AMPLITUDE / 2
    return H


def periodic_components(solid: np.ndarray, n: int) -> int:
    idx = np.arange(n ** 3).reshape(n, n, n)                            # [k, j, i]
    rows, cols = [], []
    for axis in range(3):
        nb = np.roll(idx, -1, axis=axis)
        both = solid & np.roll(solid, -1, axis=axis)
        rows.append(idx[both]), cols.append(nb[both])
    g = sp.coo_matrix((np.ones(sum(map(len, rows))), (np.concatenate(rows), np.concatenate(cols))), shape=(n ** 3,) * 2)
    count, labels = connected_components(g, directed=False)
    return len(np.unique(labels[solid.ravel()]))


class Cell:
    def __init__(self, n: int, floor: float, target: float):
        self.n, self.floor, self.target = n, floor, target
        self.threshold, self.rho = cf_case.threshold_for_fraction(n, target)
        self.solid = (cf_case.gyroid_magnitude(n) <= self.threshold)
        assert abs(self.solid.mean() - self.rho) < 1e-12
        self.components = periodic_components(self.solid.reshape(n, n, n), n)
        assert self.components == 1, "periodic solid phase is disconnected"
        self.E = np.where(self.solid, E_MPA, E_MPA * floor)
        k, j, i = np.indices((n, n, n))
        base = np.stack([i.ravel(), j.ravel(), k.ravel()], axis=1)          # cell order of gyroid_magnitude
        corner = (base[:, None, :] + CORNERS[None]) % n
        node = corner[..., 0] + n * (corner[..., 1] + n * corner[..., 2])    # periodic node of each corner
        self.dofs = (3 * node[..., None] + np.arange(3)).reshape(len(base), 24).astype(np.int64)
        self.B, self.Ke = element(1.0 / n)
        self.local = CORNERS / n                                            # corner offsets in the unit cube

    def assemble(self):
        """K on the periodic dofs with node 0 held (its three dofs removed), in CSR, float64."""
        n3 = self.n ** 3
        t = time.time()
        r = np.repeat(self.dofs, 24, axis=1).ravel()
        c = np.tile(self.dofs, (1, 24)).ravel()
        v = (self.E[:, None] * self.Ke.ravel()[None]).ravel()
        K = sp.csr_matrix((v, (r, c)), shape=(3 * n3, 3 * n3))
        del r, c, v
        K.sum_duplicates()
        self.assembly_s = time.time() - t
        return K[3:, 3:].tocsr()

    def rhs(self) -> np.ndarray:
        """-K (H x) for the six modes, on the free dofs (3 n^3 - 3, 6)."""
        F = np.zeros((3 * self.n ** 3, 6))
        for mode in range(6):
            g = self.Ke @ (self.local @ strain_mode(mode).T).ravel()        # one element, E = 1
            F[:, mode] = np.bincount(self.dofs.ravel(), weights=-(self.E[:, None] * g[None]).ravel(), minlength=F.shape[0])
        return F[3:]

    def recover(self, W: np.ndarray, K, F) -> dict:
        """Tensor and the checks of run_constant_fraction_case.py from the six periodic fields."""
        full = np.vstack([np.zeros((3, 6)), W])
        D1 = elasticity(1.0, NU)
        C = np.empty((6, 6))
        rows = []
        for mode in range(6):
            H = strain_mode(mode)
            macro_strain = np.array([H[0, 0], H[1, 1], H[2, 2], 2 * H[0, 1], 2 * H[0, 2], 2 * H[1, 2]])
            we = full[self.dofs, mode]                                      # (cells, 24)
            eps = macro_strain[None, None] + np.einsum("qaj,cj->cqa", self.B, we)
            sig = self.E[:, None, None] * np.einsum("ab,cqb->cqa", D1, eps)
            average = sig.reshape(-1, 6).mean(0)
            C[:, mode] = average / AMPLITUDE
            internal = float(0.5 * np.einsum("cqa,cqa->", sig, eps) / sig.shape[0] / 8)
            macro = 0.5 * average[mode] * AMPLITUDE
            u_aff = (self.local @ H.T).ravel()
            ue = we + u_aff[None]
            assembled = float(0.5 * np.sum(self.E * np.einsum("ci,ij,cj->c", ue, self.Ke, ue)))   # cube volume 1
            residual = float(np.linalg.norm(K @ W[:, mode] - F[:, mode]) / np.linalg.norm(F[:, mode]))
            rows.append(dict(mode=mode, periodicity="exact by construction: u = H x + w, w periodic",
                             independent_internal_energy=internal, macro_energy=macro,
                             assembled_energy=assembled, relative_algebraic_residual=residual,
                             relative_energy_residual=abs(internal - macro) / macro))
            assert abs(internal - macro) / macro <= 1e-4 and abs(assembled - macro) / macro <= 1e-4, rows[-1]
        G = E_MPA / (2 * (1 + NU))
        lam = E_MPA * NU / ((1 + NU) * (1 - 2 * NU))
        expected = np.zeros((6, 6))
        expected[:3, :3] = lam
        expected[np.arange(3), np.arange(3)] += 2 * G
        expected[3:, 3:] = np.eye(3) * G
        symmetry = float(np.linalg.norm(C - C.T) / np.linalg.norm(C))
        assert symmetry <= 1e-4
        values, vectors = np.linalg.eigh(expected)
        inverse = (vectors * (1 / np.sqrt(values))) @ vectors.T
        eig = np.linalg.eigvalsh(inverse @ ((C + C.T) / 2) @ inverse)
        voigt_upper = self.rho + (1 - self.rho) * self.floor
        assert eig.min() > 0 and eig.max() <= voigt_upper + 1e-4
        return dict(effective_C_MPa=C.tolist(), relative_antisymmetry=symmetry,
                    normalized_stiffness_eigenvalues=eig.tolist(), minimum_tensor_stiffness_ratio=float(eig.min()),
                    solid_fraction=self.rho, target_solid_fraction=self.target,
                    solid_fraction_error_relative=float((self.rho - self.target) / self.target),
                    solid_periodic_components=self.components, void_relative_stiffness=self.floor,
                    gyroid_threshold=self.threshold, resolution=self.n, voigt_upper_ratio=voigt_upper, cases=rows)


def solve(K, F, backend: str):
    t = time.time()
    if backend == "scipy":
        from scipy.sparse.linalg import splu
        lu = splu(K.tocsc(), permc_spec="COLAMD")
        W = lu.solve(F)
        info = {"backend": "scipy SuperLU (CPU)"}
    elif backend == "cudss":
        import cupy as cp
        import cupyx.scipy.sparse as csp
        import nvmath
        from nvmath.sparse.advanced import DirectSolver, DirectSolverMatrixType, DirectSolverOptions

        A = csp.csr_matrix(K)
        B = cp.asfortranarray(cp.asarray(F))
        options = DirectSolverOptions(sparse_system_type=DirectSolverMatrixType.SPD)
        with DirectSolver(A, B, options=options) as solver:
            solver.plan()
            solver.factorize()
            X = solver.solve()
        cp.cuda.Device().synchronize()
        W = cp.asnumpy(X)
        props = cp.cuda.runtime.getDeviceProperties(0)
        info = {"backend": "NVIDIA cuDSS through nvmath-python (GPU)", "nvmath": nvmath.__version__,
                "gpu": props["name"].decode(), "gpu_memory_GiB": round(props["totalGlobalMem"] / 2 ** 30, 1)}
    else:
        raise SystemExit(f"unknown backend {backend}")
    info["solve_s"] = round(time.time() - t, 2)
    return W, info


def run(n: int, floor: float, target: float, backend: str, out: Path) -> dict:
    out.mkdir(parents=True, exist_ok=False)
    t0 = time.time()
    cell = Cell(n, floor, target)
    K = cell.assemble()
    F = cell.rhs()
    W, info = solve(K, F, backend)
    report = cell.recover(W, K, F)
    report.update(status="constant_fraction_periodic_gyroid_six_strain_energy_checks_passed",
                  formulation="C3D8 2x2x2, periodic w with u = H x + w, node 0 held, one factorisation for six modes",
                  dofs=int(K.shape[0]), nonzeros=int(K.nnz), assembly_s=round(cell.assembly_s, 2), solver=info,
                  wall_s=round(time.time() - t0, 2), source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  geometry_source_sha256=hashlib.sha256(CASE.read_bytes()).hexdigest(),
                  carrier_convergence_demonstrated=False, cellular_part_generated=False)
    (out / "assessment.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    import sys
    n, floor, target, backend, out = int(sys.argv[1]), float(sys.argv[2]), float(sys.argv[3]), sys.argv[4], Path(sys.argv[5])
    r = run(n, floor, target, backend, out)
    print(n, floor, r["solid_fraction"], r["minimum_tensor_stiffness_ratio"], r["solver"], r["wall_s"])
