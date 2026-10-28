"""Plot the actual, assessed native histories; never infer a carrier deformation."""
import argparse,csv,hashlib,json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

def main(folder,output):
    folder=Path(folder);output=Path(output);assert not output.exists();assessment=json.loads((folder/'assessment.json').read_text());assert assessment['passed'];output.mkdir()
    fig,axes=plt.subplots(3,1,figsize=(9,8),sharex=True);colors={'plastic':'#205a81','elastic':'#ba4d00'}
    for label,name,description in [('plastic','birth-cycle-release_out.csv','J2 plastique'),('elastic','elastic-control_out.csv','Contre-calcul élastique')]:
        rows=list(csv.DictReader((folder/label/name).open()))[1:];t=[float(x['time']) for x in rows];stress=[float(x['stress_bar']) for x in rows];u0=float(rows[0]['u_right']);u=[float(x['u_right'])-u0 for x in rows];p=[float(x['plastic_xx_bar']) for x in rows]
        axes[0].plot(t,stress,'o-',label=description,color=colors[label]);axes[1].plot(t,u,'o-',color=colors[label]);axes[2].plot(t,p,'o-',color=colors[label])
    for axis in axes:
        axis.grid(alpha=.2);axis.axvline(4.5,color='#666',linestyle='--');axis.ticklabel_format(axis='y',style='plain',useOffset=False)
    axes[0].legend(frameon=False,loc='upper left');axes[0].set_ylabel('Contrainte σxx (MPa)');axes[1].set_ylabel('Déplacement relatif\nà la naissance (mm)');axes[2].set_ylabel('Déformation plastique εp,xx');axes[2].set_xlabel('Temps du témoin synthétique (s)')
    axes[0].annotate('Débridage',xy=(4.5,190),xytext=(4.65,270),arrowprops={'arrowstyle':'->','color':'#666'},color='#444')
    axes[0].set_ylim(-650,330);fig.suptitle('Contrôle du solveur MOOSE',fontsize=16,y=.985);fig.text(.5,.93,'Température prescrite 300 → 600 → 300 K · barre synthétique 10 × 1 × 1 mm\nAucune prédiction de déformation du support moteur',ha='center',va='top',fontsize=9.5)
    fig.subplots_adjust(top=.83,hspace=.15,bottom=.09,left=.16,right=.97)
    for ext in ['png','svg']:fig.savefig(output/('moose-history.'+ext),dpi=180,facecolor='white')
    plt.close(fig);(output/'figures.json').write_text(json.dumps({'assessment_sha256':hashlib.sha256((folder/'assessment.json').read_bytes()).hexdigest(),'renderer_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'images_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in output.iterdir() if p.is_file()}},indent=2)+'\n')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('folder',type=Path);p.add_argument('output',type=Path);a=p.parse_args();main(a.folder,a.output)
