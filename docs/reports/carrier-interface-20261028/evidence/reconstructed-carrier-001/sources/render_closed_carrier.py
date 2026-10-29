"""Render real carrier sections and highlight its eight closed internal chambers."""
import argparse,hashlib,json
from pathlib import Path
import numpy as np


def main():
    import manifold3d as mf
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.path import Path as PlotPath
    from matplotlib.patches import PathPatch,Rectangle,Patch
    p=argparse.ArgumentParser(__doc__);p.add_argument('--directory',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    assert not a.output.exists();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    report=a.directory/'assessment.json';r=json.loads(report.read_text());archive=a.directory/'candidate.npz'
    assert r['status']=='complete_closed_chamber_variant_geometry_checked' and not r['manufacturing_authorized'] and not r['powder_escape_demonstrated']
    assert sha(archive)==r['output_sha256'] and r['original_external_oriented_triangles_exact']
    z=np.load(archive);body=mf.Manifold(mf.Mesh64(np.array(z['vertices']),np.array(z['triangles'],dtype=np.uint64)))
    assert body.status()==mf.Error.NoError and abs(body.volume()-r['candidate_volume_mm3'])/body.volume()<=1e-10
    voids=[]
    for shell in body.decompose():
        if shell.volume()<0:
            mesh=shell.to_mesh64();faces=np.array(mesh.tri_verts,dtype=np.uint64)
            voids.append(mf.Manifold(mf.Mesh64(np.array(mesh.vert_properties)[:,:3],np.array(faces[:,[0,2,1]],dtype=np.uint64,order='C',copy=True))))
    assert len(voids)==8 and all(v.status()==mf.Error.NoError for v in voids)
    void=mf.Manifold.batch_boolean(voids,mf.OpType.Add);assert abs(void.volume()-r['removed_volume_mm3'])/void.volume()<=1e-10
    height=.5;material_section=body.slice(height);void_section=void.slice(height)
    def plot_path(section):
        paths=[];area=0.
        for polygon in section.to_polygons():
            polygon=np.array(polygon);assert len(polygon)>=3
            area+=.5*float(np.sum(polygon[:,0]*np.roll(polygon[:,1],-1)-polygon[:,1]*np.roll(polygon[:,0],-1)))
            paths.append(PlotPath(np.vstack([polygon,polygon[0]]),[PlotPath.MOVETO]+[PlotPath.LINETO]*(len(polygon)-1)+[PlotPath.CLOSEPOLY]))
        assert paths and abs(area-section.area())/section.area()<=1e-10
        return PlotPath.make_compound_path(*paths)
    material_path=plot_path(material_section);void_path=plot_path(void_section)
    background='#f4f1e9';teal='#286c68';orange='#d18442'
    fig,axes=plt.subplots(2,1,figsize=(13,8),gridspec_kw={'height_ratios':[1,2]},layout='constrained',facecolor=background)
    for ax,xlim,title in zip(axes,[(-302,302),(-92,92)],['Complete carrier / unchanged outer surface','Central detail / orange shows new internal voids']):
        ax.set_facecolor(background);ax.add_patch(PathPatch(material_path,facecolor=teal,edgecolor='#153e3c',lw=.5));ax.add_patch(PathPatch(void_path,facecolor=orange,edgecolor='#945021',lw=.35))
        ax.set(xlim=xlim,ylim=(-40,40),xlabel='X [mm]',ylabel='Y [mm]');ax.set_aspect('equal');ax.set_title(title,loc='left',fontsize=12,color='#203b3b');ax.grid(alpha=.13)
    axes[0].add_patch(Rectangle((-92,-40),184,80,fill=False,edgecolor='#945021',linestyle='--',lw=1))
    axes[0].legend(handles=[Patch(facecolor=teal,label='Retained titanium'),Patch(facecolor=orange,label='New internal voids'),Patch(facecolor=background,edgecolor='#777',label='Existing empty space')],loc='center left',bbox_to_anchor=(.13,.5),ncol=1,frameon=False,fontsize=9)
    fig.suptitle(f"993 CARRIER / CLOSED-CHAMBER BASELINE / {r['nominal_candidate_mass_kg']:.6f} kg",fontsize=17,fontweight='bold',color='#203b3b')
    fig.supxlabel('Actual mesh sections at Z = 0.5 mm / nominal Ti density 4.42 g/cm³\nThe section opens the chambers only in this drawing; the 3D geometry still has eight closed voids.\nTransitions, powder escape and complete-carrier mechanics remain pending.',fontsize=10,color='#203b3b')
    a.output.mkdir();path=a.output/'closed-carrier-sections.png';fig.savefig(path,dpi=160);plt.close(fig)
    (a.output/'figure-provenance.json').write_text(json.dumps(dict(figure_sha256=sha(path),input_sha256={str(p):sha(p)for p in [archive,report]},source_sha256={str(Path(__file__)):sha(Path(__file__))},section_z_mm=height,material_section_area_mm2=material_section.area(),new_void_section_area_mm2=void_section.area(),candidate_geometry_generated=True,powder_escape_demonstrated=False,manufacturing_authorized=False),indent=2)+'\n')


if __name__=='__main__':main()
