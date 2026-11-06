"""Draw the actual two-triangle edit and its exact lift correspondence."""
from pathlib import Path
from fractions import Fraction
import json
import hashlib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

r=Path(__file__).resolve().parent
z=np.load(r/"decoded-001/candidate.npz")
v=z["vertices"]
proof=json.loads((r/"fidelity.json").read_text())
names=[7330,7060,7398,7187]
points=v[names][:,[0,2]]
points=(points-points.mean(axis=0))*1000
s=float(Fraction(proof["exact_diagonal_parameters"][0]))
q=float(Fraction(proof["exact_diagonal_parameters"][1]))
gap=1000*float(Fraction(proof["exact_gap_mm"]))
with plt.style.context("seaborn-v0_8-whitegrid"):
    fig,ax=plt.subplots(1,2,figsize=(12,4.8),layout="constrained")
    ring=points[[0,3,1,2,0]]
    ax[0].plot(ring[:,0],ring[:,1],color="#526273",linewidth=1.5)
    ax[0].plot(points[[0,1],0],points[[0,1],1],"--",color="#cc6b24",label="Former diagonal / 46.29° patch turn")
    ax[0].plot(points[[2,3],0],points[[2,3],1],color="#168454",label="New diagonal / 29.59° patch turn")
    ax[0].scatter(points[:,0],points[:,1],color="#263847",s=28,zorder=4)
    for point,name,offset in zip(points,names,[(5,-14),(-35,8),(5,5),(-45,-14)]):
        ax[0].annotate(str(name),point,xytext=offset,textcoords="offset points",fontsize=9)
    hit=points[0]+s*(points[1]-points[0])
    ax[0].scatter(*hit,color="#168454",marker="D",s=24,zorder=5)
    ax[0].set(xlabel="Local x offset (µm)",ylabel="Local z offset (µm)",title="Actual convex projected patch")
    ax[0].set_aspect("equal")
    ax[0].legend(fontsize=8,loc="upper left")
    ax[1].plot([0,s,1],[0,gap,0],color="#168454",marker="o",label="Common-refinement lift gap")
    ax[1].axhline(0,color="#526273",linewidth=1)
    ax[1].axhline(5,color="#a74139",linestyle="--",label="Frozen edit budget: 5 µm")
    ax[1].set(xlabel="Position along the former diagonal",ylabel="Correspondence separation in y (µm)",ylim=(-.2,5.5),title="Complete two-sided surface bound ≤ 2.714 µm")
    ax[1].legend(fontsize=9)
    fig.suptitle("Two changed triangles; all 3,890,532 vertices unchanged\nGlobal material-side maximum: 46.29° → 41.76°; no edge above 45°")
    target=r/"bounded-edge-flip.png"
    assert not target.exists()
    fig.savefig(target,dpi=160)
    plt.close(fig)
(r/"figure-provenance.json").write_text(json.dumps(dict(image_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),renderer_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),geometry_sha256=hashlib.sha256((r/"decoded-001/candidate.npz").read_bytes()).hexdigest(),fidelity_sha256=hashlib.sha256((r/"fidelity.json").read_bytes()).hexdigest(),scope="Actual mesh patch and exact common-refinement correspondence, not a stress plot"),indent=2)+"\n")
