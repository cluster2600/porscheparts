from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import trimesh

paths=[('low_B', Path('/workspace/work/993-cylinder-head-fast/cfd-improved/low_B/fluid-domain.stl')),
       ('high_B', Path('/workspace/work/993-cylinder-head-fast/cfd-improved/high_B/fluid-domain.stl'))]
fig=plt.figure(figsize=(14,6))
for i,(name,p) in enumerate(paths, start=1):
    mesh=trimesh.load_mesh(str(p), process=True)
    ax=fig.add_subplot(1,2,i,projection='3d')
    verts=mesh.vertices
    faces=mesh.faces
    x=verts[:,0]; y=verts[:,1]; z=verts[:,2]
    ax.plot_trisurf(x,y,z,triangles=faces,alpha=0.45,linewidth=0.2,edgecolor='k',cmap='viridis')
    ax.set_title(f'{name} cavity')
    ax.set_axis_off()
    ax.view_init(elev=20, azim=30)
plt.tight_layout()
out=Path('/workspace/work/993-cylinder-head-fast/reports/cfd_stub_preview_continuation.png')
plt.savefig(out,dpi=180)
print(out)
