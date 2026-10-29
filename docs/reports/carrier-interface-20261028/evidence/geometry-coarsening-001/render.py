"""Draw sections of the actual rounded-cube control meshes, without invented geometry."""
from pathlib import Path
import numpy as np,matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
import struct,json,hashlib
root=Path.cwd();r=root/'work/geometry-coarsening-report-001'
paths=[root/'work/qualified-dilation-001/cube-control-001/decoded-001/candidate.meshbin',root/'work/cgal-exact-planar-001/rounded-cube-001/decoded-001/candidate.meshbin',root/'work/cgal-bounded-coarsen-001/cube-planar-fast-001/decoded-001/candidate.meshbin']
colors=['#64748b','#087f8c','#bd5824'];titles=['Rounded input','Exact planar reduction','Bounded reduction'];counts=[];rows=[]
fig=plt.figure(figsize=(13.5,7.6),facecolor='#f7f9fc');gs=fig.add_gridspec(2,3,height_ratios=[2.7,1],hspace=.52,wspace=.25)
for i,p in enumerate(paths):
 raw=p.read_bytes();nv,nf=struct.unpack('<QQ',raw[:16]);v=np.frombuffer(raw,dtype='<f8',offset=16,count=nv*3).reshape(-1,3);f=np.frombuffer(raw,dtype='<u8',offset=16+nv*24,count=nf*3).reshape(-1,3);counts.append(nf)
 # An off-grid section avoids coincident triangle edges and exposes actual faceting.
 t=v[f];z=t[:,:,2]-.1234567;chosen=t[(z.min(1)<0)&(z.max(1)>0)];segments=[]
 for tri in chosen:
  points=[]
  for j in range(3):
   a,b=tri[j],tri[(j+1)%3]
   if(a[2]-.1234567)*(b[2]-.1234567)<0:
    q=a+((.1234567-a[2])/(b[2]-a[2]))*(b-a);points.append(q[:2])
  if len(points)==2:segments.append(points)
 segments=np.array(segments);ax=fig.add_subplot(gs[0,i]);ax.add_collection(LineCollection(segments,colors=colors[i],linewidths=2));points=segments.reshape(-1,2);ax.scatter(points[:,0],points[:,1],s=8,color=colors[i],alpha=.6)
 ax.set(xlim=(.84,1.125),ylim=(.84,1.125),xlabel='x (mm)',ylabel='y (mm)');ax.set_aspect('equal');ax.grid(alpha=.18);ax.set_facecolor('white');ax.set_title(titles[i]+'\n'+f'{nf:,} triangles',fontsize=13,fontweight='bold',pad=13);ax.spines[['top','right']].set_visible(False)
 rows.append(dict(path=str(p.relative_to(root)),sha256=hashlib.sha256(raw).hexdigest(),faces=nf,section_segments=len(segments)))
ax=fig.add_subplot(gs[1,:]);ax.barh([2,1,0],counts,color=colors,height=.62);ax.set_xscale('log');ax.set_yticks([2,1,0],['Rounded input','Exact planar','Bounded']);ax.set_xlabel('Complete mesh triangle count — logarithmic scale');ax.grid(axis='x',alpha=.2);ax.set_axisbelow(True);ax.spines[['top','right','left']].set_visible(False)
for y,n in zip([2,1,0],counts):ax.text(n*1.12,y,f'{n:,}',va='center',fontsize=10)
ax.set_xlim(100,2e6)
fig.suptitle('Fewer triangles, with a measured geometry budget',x=.08,ha='left',y=.985,fontsize=20,fontweight='bold',color='#152337')
fig.text(.08,.924,'Actual rounded-cube control · section z = 0.1234567 mm · points show triangle intersections',fontsize=11,color='#475569')
fig.text(.08,.025,'Stage 1: exact surface identity.  Stage 2: complete symmetric EPECK envelope ≤ 0.002 mm.\nThis control qualifies the geometry route; carrier coarsening and mechanics have separate checks.',fontsize=10,color='#334155')
fig.subplots_adjust(top=.79,bottom=.14,left=.12,right=.95)
out=root/'docs/media/carrier-interface-20261028/coarsening-control.png';fig.savefig(out,dpi=150,facecolor=fig.get_facecolor());plt.close(fig)
(r/'image.json').write_text(json.dumps(dict(inputs=rows,image=str(out.relative_to(root)),image_sha256=hashlib.sha256(out.read_bytes()).hexdigest(),method='Unsmoothed intersections of actual mesh triangles with fixed plane; no generated geometry'),indent=2)+'\n')
print(out)
