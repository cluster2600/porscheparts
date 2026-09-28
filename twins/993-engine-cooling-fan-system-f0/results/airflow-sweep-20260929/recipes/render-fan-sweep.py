from pathlib import Path
import numpy as np
import trimesh
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
root=Path('/workspace/jobs/fan-airflow-sweep-20260929')
fig=plt.figure(figsize=(14,12),facecolor='#edf1f5')
items=[('e-control','E — baseline'),('pitch42','Pitch 42° — higher blade angle'),('camber55','Camber −5.5 mm — stronger curvature'),('chord80','Tip chord 80 mm — wider blade')]
for i,(name,title) in enumerate(items,1):
 m=trimesh.load_mesh(root/'geometry'/name/'rotor-mm.stl',process=True)
 m=m.simplify_quadric_decimation(face_count=40000)
 tri=m.triangles
 normal=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]);normal/=np.maximum(np.linalg.norm(normal,axis=1)[:,None],1e-12)
 light=np.array([.3,-.4,-.866]);shade=.35+.65*np.abs(normal@light)
 ax=fig.add_subplot(2,2,i,projection='3d',facecolor='#edf1f5')
 ax.add_collection3d(Poly3DCollection(tri,facecolors=shade[:,None]*np.array([.57,.68,.78]),linewidths=0,rasterized=True))
 ax.set(xlim=(-132,132),ylim=(-132,132),zlim=(-80,60));ax.set_box_aspect((264,264,140));ax.view_init(elev=-48,azim=-70);ax.set_axis_off();ax.set_title(title,fontsize=15,pad=0)
fig.suptitle('Porsche 993 fan — new organic blade experiments',fontsize=23,y=.98)
fig.text(.5,.025,'Actual PicoGK meshes • 245 mm nominal diameter • 11 blades\nExperimental geometry — airflow and fitment not validated',ha='center',fontsize=12,color='#344255')
fig.subplots_adjust(left=0,right=1,bottom=.07,top=.92,wspace=0,hspace=.03)
fig.savefig(root/'geometry-comparison.png',dpi=150,facecolor=fig.get_facecolor())
print('Rendered',root/'geometry-comparison.png')
