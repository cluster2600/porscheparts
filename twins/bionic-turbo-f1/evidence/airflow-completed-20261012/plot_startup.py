from pathlib import Path
import sys
import math
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
sys.path.insert(0,'twins/bionic-turbo-f1/cfd')
from audit_case import table

fig,axes=plt.subplots(2,2,figsize=(11,7),constrained_layout=True)
for variant,label,color in [('baseline','Référence','#1768ac'),('candidate','Volute F1','#c24b21')]:
 p=Path('work/bionic-airflow-20261012')/(variant+'-transient-010')
 minima=table(p/'postProcessing/scalarMinima/0/volFieldValue.dat',3)
 flow=table(p/'postProcessing/mass_outlet/0/surfaceFieldValue.dat',2)
 torque=table(p/'postProcessing/rotorForces/0/moment.dat',10)
 for ax,rows,column,scale in [(axes[0,0],minima,2,1),(axes[0,1],minima,1,.001),(axes[1,0],flow,1,1),(axes[1,1],torque,3,-100000*math.pi/30/1000)]:
  ax.plot([r[0]*1e6 for r in rows],[r[column]*scale for r in rows],label=label,color=color,lw=1.8)
for ax,title,ylabel in [(axes[0,0],'Température minimale','K'),(axes[0,1],'Pression absolue minimale','kPa'),(axes[1,0],'Débit signé à la sortie','kg/s — négatif : retour dans le domaine'),(axes[1,1],'Puissance instantanée transmise au fluide','kW — couple natif × vitesse de rotation')]:
 ax.set(title=title,xlabel='Temps physique (µs)',ylabel=ylabel)
 ax.grid(alpha=.25)
 ax.legend(frameon=False)
axes[1,0].axhline(0,color='#555',lw=.7)
fig.suptitle('Turbo à 100 000 tr/min — démarrage de 20 µs\nCalculs terminés, écoulement non établi : aucun gain de performance validé',fontsize=13)
fig.savefig('twins/bionic-turbo-f1/evidence/airflow-completed-20261012/startup-histories.png',dpi=160)
