"""Analysis-only local point proposals; complete independent certification remains required."""
import numpy as np
from scipy.optimize import minimize

# shortcut: the averaged tangent plane has no feature semantics; add measured-interface constraints before using it on fitting surfaces.

def qualities(t):
    normal = np.cross(t[:, 1] - t[:, 0], t[:, 2] - t[:, 0])
    return 2 * np.sqrt(3) * np.linalg.norm(normal, axis=1) / np.sum((t[:, [1, 2, 0]] - t) ** 2, axis=(1, 2)), normal

def proposal(points, faces, vertex, radius):
    assert 0 < radius <= .05 and len(faces)
    old = points[faces]; old_q, old_n = qualities(old)
    n = old_n.sum(axis=0); length = np.linalg.norm(n)
    if length <= 1e-14: return None
    n /= length; axis = np.eye(3)[np.argmin(np.abs(n))]
    u = np.cross(n, axis); u /= np.linalg.norm(u); basis = np.column_stack([u, np.cross(n, u)])
    local = faces == vertex; floor = np.minimum(old_q, .0501)

    def evaluate(x):
        t = old.copy(); t[local] = points[vertex] + radius * (basis @ x[:2])
        q, normals = qualities(t)
        alignment = np.einsum('ij,ij->i', normals, old_n) / (np.linalg.norm(normals, axis=1) * np.linalg.norm(old_n, axis=1))
        return q, alignment

    def constraints(x):
        q, alignment = evaluate(x)
        return np.r_[q-floor, q-x[2], alignment-.25, 1-np.dot(x[:2], x[:2])]

    result = minimize(lambda x: -x[2], [0., 0., float(old_q.min())], method='SLSQP', bounds=[(-1,1),(-1,1),(0,1)], constraints={'type':'ineq','fun':constraints}, options={'maxiter':60,'ftol':1e-10})
    point = (points[vertex] + radius * (basis @ result.x[:2])).astype(np.float32).astype(float)
    t = old.copy(); t[local] = point; q, normals = qualities(t)
    alignment = np.einsum('ij,ij->i', normals, old_n)
    if not result.success or not np.isfinite(point).all() or np.linalg.norm(point-points[vertex]) > radius+1e-5*radius or np.any(q<floor-1e-10) or np.any(alignment<=0) or q.min()<=old_q.min()+1e-6: return None
    return point
