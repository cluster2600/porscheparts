"""Plot the actual saved water mesh and the independently located deficient cells."""
import argparse
import json
from pathlib import Path

from mesh_surface import sha


if __name__=='__main__':
    import gmsh
    import numpy as np
    import trimesh
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('surface',type=Path);parser.add_argument('case',type=Path);parser.add_argument('output',type=Path)
    args=parser.parse_args();s=args.surface;c=args.case;o=args.output
    record=json.loads((c/'saved-readback.json').read_text())
    surface_record=json.loads((s/'surface-report.json').read_text())
    if sha(c/'coolant.msh')!=record['mesh_sha256'] or sha(s/'coolant.stl')!=surface_record['candidate_sha256']:
        raise ValueError('Plot input changed')
    if o.exists():raise ValueError('Plot must be new')
    water=trimesh.load_mesh(s/'coolant.stl',process=True)
    gmsh.initialize([])
    try:
        gmsh.option.setNumber('General.Terminal',0);gmsh.open(str(c/'coolant.msh'))
        tags=gmsh.model.mesh.getElements(3)[1][0]
        q=gmsh.model.mesh.getElementQualities(tags,'minSICN')
    finally:gmsh.finalize()
    assert len(q)==record['cells'] and np.count_nonzero(q<.1)==record['below_sicn_01']
    fig=plt.figure(figsize=(14,7),layout='constrained')
    ax=fig.add_subplot(121,projection='3d')
    ax.add_collection3d(Poly3DCollection(water.triangles,facecolors='#228bc5',edgecolors='none',alpha=.09,rasterized=True))
    poor=np.array([r['centre_mm'] for r in record['poor_cells']])
    if len(poor):ax.scatter(*poor.T,color='#d92332',s=38,depthshade=False,label=f"{len(poor)} cellules SICN < 0,1")
    bounds=water.bounds;ax.set_xlim(bounds[:,0]);ax.set_ylim(bounds[:,1]);ax.set_zlim(bounds[:,2])
    ax.set_box_aspect(bounds[1]-bounds[0]);ax.view_init(elev=25,azim=-60)
    ax.set_xlabel('X (mm)');ax.set_ylabel('Y (mm)');ax.set_zlabel('Z (mm)')
    ax.set_title("Volume d'eau et cellules déficientes")
    if len(poor):ax.legend(loc='lower left')
    hist=fig.add_subplot(122);hist.hist(q,bins=np.linspace(0,1,51),color='#228bc5',edgecolor='white',log=True)
    hist.axvline(.1,color='#d92332',label='Seuil SICN : 0,1');hist.legend()
    hist.set_xlabel('Qualité SICN (sans unité)');hist.set_ylabel('Nombre de tétraèdres (échelle logarithmique)')
    hist.set_title(f"{record['cells']:,} cellules — minimum {min(q):.5f}".replace(',',' '))
    fig.suptitle("Culasse 4 L — contrôle du maillage d'eau\nGéométrie d'étude ; aucun écoulement résolu",fontsize=15)
    o.parent.mkdir(parents=True,exist_ok=True);fig.savefig(o,dpi=150);plt.close(fig)
    from PIL import Image
    with Image.open(o) as image:image.verify()
    print(json.dumps(dict(image=str(o),sha256=sha(o),source_sha256=sha(Path(__file__)),mesh_sha256=record['mesh_sha256'])))
