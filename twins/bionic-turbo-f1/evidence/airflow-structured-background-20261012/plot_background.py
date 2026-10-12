import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
root=Path('twins/bionic-turbo-f1/evidence');old=json.loads((root/'airflow-rear-interface-20261012/geometry-027.json').read_text())
new=json.loads(Path('work/bionic-airflow-20261012/profile-background-030/manifest.json').read_text())
reports=[json.loads((root/'airflow-profile-interface-20261012'/(name+'-profile-023.json')).read_text()) for name in ('baseline','candidate')]
a=np.array(old['profile']['nodes_z_radius_mm']);b=np.array(new['simplified_profile_nodes_mm']);bands=reports[0]['bands'][3:]
z=np.array([r['z_low_mm'] for r in bands]+[bands[-1]['z_high_mm']]);lower=[];upper=[]
for j in range(3,359):
 lower.append(max(r['bands'][j]['rotor_upper_mm'] for r in reports));upper.append(min(r['bands'][j]['stator_lower_mm'] for r in reports))
fig,axes=plt.subplots(1,2,figsize=(12,4.6),layout='constrained')
for ax in axes:
 ax.stairs(lower,z,label='Borne rotor',color='#c44e52');ax.stairs(upper,z,label='Borne stator',color='#8172b3')
 ax.plot(a[:,0],a[:,1],label='Profil 027',color='#999999',lw=2)
 ax.plot(b[:,0],b[:,1],label='Profil contraint 030',color='#0077aa',lw=1.3,marker='.',ms=3)
 ax.set_xlabel('z (mm)');ax.set_ylabel('Rayon (mm)');ax.grid(alpha=.2)
axes[0].set(xlim=(-4,33),ylim=(17,37),title='Passage latéral des deux variantes')
axes[1].set(xlim=(-3.7,4.6),ylim=(30,34),title='Profil arrière : contraintes inchangées')
axes[0].legend(fontsize=8);fig.suptitle('Fond structuré 030 : Mesh OK ; parois physiques non encore maillées',fontsize=12)
fig.savefig(Path(__file__).with_name('profile-background.png'),dpi=160)
