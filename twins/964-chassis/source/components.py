import numpy as np, trimesh, time
from trimesh.graph import connected_components
m = trimesh.load('raw/964widebodyunderside2poin13.obj', process=False)
t=time.time()
cc = connected_components(m.face_adjacency, nodes=np.arange(len(m.faces)), engine='scipy')
print(f"components: {len(cc)}  ({time.time()-t:.1f}s)")
sizes = np.array(sorted((len(c) for c in cc), reverse=True))
print("top 15 component sizes:", sizes[:15])
tot=len(m.faces)
print(f"largest = {100*sizes[0]/tot:.3f}% of faces")
print(f"components with >1000 faces: {(sizes>1000).sum()}")
print(f"components with <100 faces (debris): {(sizes<100).sum()}, total faces {sizes[sizes<100].sum()}")
np.save('cc_sizes.npy', sizes)
# save the largest component index list
big = max(cc, key=len)
np.save('cc_largest.npy', big)
