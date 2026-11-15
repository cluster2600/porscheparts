"""Build test cases outside the authors' training scenes, in their NPZ layout.

cloth-plane    the validation cloth (sheet, material, topology) over the ground plane only
cloth-tunnel   the same sheet over a half-cylinder of radius 0.3 m lying on the ground, axis along z
fluid-still    a level slab of fluid at rest in a tank 2.4 x 1.6 m, another size than the training tank
fluid-dam      the same number of particles in the same tank as a column at one end: a dam break that
               must end as the still slab
fluid-still-training-tank   the control: the same level slab in a tank of the training size, 4 x 2 m,
               without the boat and the island of the training scenes
Usage: make_cases.py HF_DIR OUT_DIR
"""
import sys
from pathlib import Path
import numpy as np

hf, out = Path(sys.argv[1]), Path(sys.argv[2])
rng = np.random.default_rng(20261113)
cloth = np.load(hf / "cloth_on_ball/dataset/10/10.npz")
frames = cloth["position"].shape[0]
start = 10                                                   # frame_start of the checkpoint's configuration


def save_cloth(name, box, normals):
    d = out / name
    d.mkdir(parents=True, exist_ok=True)
    pos = np.repeat(cloth["position"][start][None], frames, axis=0)       # no reference: the initial state repeated
    vel = np.repeat(cloth["velocity"][start][None], frames, axis=0)
    np.savez(d / f"{name}.npz", position=pos, velocity=vel, feats=cloth["feats"], box=box.astype(np.float32),
             box_feats=normals.astype(np.float32), neighbors_index=cloth["neighbors_index"],
             neighbors_row_splits=cloth["neighbors_row_splits"])


ground, ground_n = cloth["ground_points"], cloth["ground_normals"]
# plane only: the 5,000 sphere points are replaced by 5,000 more ground points, so the count stays at 10,000
extra = np.column_stack([rng.uniform(-0.9, 0.9, 5000), np.full(5000, ground[0, 1]), rng.uniform(-0.9, 0.9, 5000)])
save_cloth("cloth-plane", np.vstack([extra, ground]), np.vstack([np.tile([0.0, 1.0, 0.0], (5000, 1)), ground_n]))
# tunnel: half-cylinder x^2 + (y - y0)^2 = R^2, y >= y0, with its axis on the ground plane
R, y0 = 0.3, float(ground[0, 1])
theta, z = rng.uniform(0.0, np.pi, 5000), rng.uniform(-0.9, 0.9, 5000)
tunnel = np.column_stack([R * np.cos(theta), y0 + R * np.sin(theta), z])
tunnel_n = np.column_stack([np.cos(theta), np.sin(theta), np.zeros(5000)])
save_cloth("cloth-tunnel", np.vstack([tunnel, ground]), np.vstack([tunnel_n, ground_n]))

# fluid: tank x in [-1.2, 1.2], y in [0, 2], z in [-0.8, 0.8]; walls sampled at the training density, normals pointing out
fluid = np.load(hf / "fancy_fluid/dataset/66/66.npz")
lo, hi = np.array([-1.2, 0.0, -0.8]), np.array([1.2, 2.0, 0.8])
density = 54000 / 40.0                                        # training: 54,000 samples on 40 m2 of walls
pts, nrm = [], []
for axis in range(3):
    others = [a for a in range(3) if a != axis]
    area = float(np.prod((hi - lo)[others]))
    for side, sign in ((lo[axis], -1.0), (hi[axis], 1.0)):
        m = int(round(area * density))
        p = np.empty((m, 3))
        p[:, axis] = side
        for a in others:
            p[:, a] = rng.uniform(lo[a], hi[a], m)
        n = np.zeros((m, 3))
        n[:, axis] = sign
        pts.append(p)
        nrm.append(n)
box, box_n = np.vstack(pts), np.vstack(nrm)
s, floor_gap, depth_layers = 0.06, 0.078, 6                   # lattice spacing; first layer as far from the floor as in the training scenes
xs = np.arange(lo[0] + floor_gap, hi[0] - floor_gap + 1e-9, s)
zs = np.arange(lo[2] + floor_gap, hi[2] - floor_gap + 1e-9, s)
ys = floor_gap + s * np.arange(depth_layers)
grid = np.stack(np.meshgrid(xs, ys, zs, indexing="ij"), axis=-1).reshape(-1, 3)
T = 301
d = out / "fluid-still"
d.mkdir(parents=True, exist_ok=True)
np.savez(d / "fluid-still.npz", position=np.repeat(grid[None].astype(np.float32), T, axis=0),
         velocity=np.zeros((T, len(grid), 3), dtype=np.float32), feats=np.tile(fluid["feats"][0], (len(grid), 1)).astype(np.float32),
         box=box.astype(np.float32), box_feats=box_n.astype(np.float32))
# dam break: the same 5,700 particles as a column 12 wide and 19 high against the wall at -x
columns, layers = 12, 19
assert columns * layers * len(zs) == len(grid), "the column must hold the particles of the slab"
dam = np.stack(np.meshgrid(xs[:columns], floor_gap + s * np.arange(layers), zs, indexing="ij"), axis=-1).reshape(-1, 3)
T = 501
d = out / "fluid-dam"
d.mkdir(parents=True, exist_ok=True)
np.savez(d / "fluid-dam.npz", position=np.repeat(dam[None].astype(np.float32), T, axis=0),
         velocity=np.zeros((T, len(dam), 3), dtype=np.float32), feats=np.tile(fluid["feats"][0], (len(dam), 1)).astype(np.float32),
         box=box.astype(np.float32), box_feats=box_n.astype(np.float32))
# control: a level slab in a tank of the training size
lo2, hi2 = np.array([-2.0, 0.0, -1.0]), np.array([2.0, 2.0, 1.0])
pts, nrm = [], []
for axis in range(3):
    others = [a for a in range(3) if a != axis]
    area = float(np.prod((hi2 - lo2)[others]))
    for side, sign in ((lo2[axis], -1.0), (hi2[axis], 1.0)):
        m = int(round(area * density))
        p = np.empty((m, 3))
        p[:, axis] = side
        for a in others:
            p[:, a] = rng.uniform(lo2[a], hi2[a], m)
        n = np.zeros((m, 3))
        n[:, axis] = sign
        pts.append(p)
        nrm.append(n)
box2, box2_n = np.vstack(pts), np.vstack(nrm)
xs2 = np.arange(lo2[0] + floor_gap, hi2[0] - floor_gap + 1e-9, s)
zs2 = np.arange(lo2[2] + floor_gap, hi2[2] - floor_gap + 1e-9, s)
grid2 = np.stack(np.meshgrid(xs2, ys, zs2, indexing="ij"), axis=-1).reshape(-1, 3)
T = 301
d = out / "fluid-still-training-tank"
d.mkdir(parents=True, exist_ok=True)
np.savez(d / "fluid-still-training-tank.npz", position=np.repeat(grid2[None].astype(np.float32), T, axis=0),
         velocity=np.zeros((T, len(grid2), 3), dtype=np.float32), feats=np.tile(fluid["feats"][0], (len(grid2), 1)).astype(np.float32),
         box=box2.astype(np.float32), box_feats=box2_n.astype(np.float32))
print({"control_particles": int(len(grid2)), "control_wall_points": int(len(box2))})
print({"cloth_particles": int(cloth["position"].shape[1]), "fluid_particles": int(len(grid)), "fluid_wall_points": int(len(box)),
       "fluid_slab_top_m": float(ys[-1]), "lattice_m": s})
