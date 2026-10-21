"""Render saved native laws and saved NURBS control nets, without rebuilding CAD."""
import argparse
import hashlib
import json
from pathlib import Path
import sys


def main():
    parser=argparse.ArgumentParser(__doc__)
    parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();root=args.root.resolve();out=args.output.resolve()
    if out.exists():raise ValueError('Use a fresh figure directory')
    out.mkdir(parents=True)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    import scipy
    from scipy.interpolate import BSpline
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False,'axes.titleweight':'bold','figure.facecolor':'#f8fafc','axes.facecolor':'#ffffff'})
    case=root/'work/carrier-resume-20261020/point-radius-001/output/assessment.json'
    patches=root/'work/carrier-resume-20261020/nurbs-root-patch-001/output/assessment.json'
    assessment=json.loads(case.read_text());saved=json.loads(patches.read_text())

    def spline(curve,coefficients=None):
        knots=np.repeat(curve.get('knots_mm',curve.get('knots')),curve['multiplicities'])
        values=coefficients if coefficients is not None else curve.get('poles',curve.get('poles_xyz_mm'))
        return BSpline(knots,np.asarray(values),curve['degree'])

    standalone=assessment['contours'][0]['standalone_interpolation_before_any_assertion']['curve']
    generated=assessment['consumed_laws'][0]['raw']['curve']
    length=assessment['contours'][0]['actual_domain_mm'][1]
    original=spline(standalone);actual=spline(generated)
    u=np.linspace(0,length,601)
    fig,axes=plt.subplots(1,2,figsize=(12.8,5.1),layout='constrained')
    fig.get_layout_engine().set(rect=(0,.12,1,.88))
    fig.suptitle('The input law and the law returned after native construction differ',fontsize=17,fontweight='bold',x=.04,ha='left')
    for ax in axes:ax.grid(color='#dce4ec',alpha=.7);ax.set_xlabel('Physical contour position  s / L')
    axes[0].plot(u/length,original(u),color='#155eab',lw=2.8,label='Standalone clamped input')
    axes[0].plot(u/length,actual(u),color='#d75b20',lw=2.4,ls='--',label='GetLaw after Compute')
    axes[0].set(title='Radius on the actual contour',ylabel='Radius (mm)',xlim=(0,1))
    axes[0].legend(frameon=False,loc='lower center')
    axes[1].plot(u/length,original.derivative()(u),color='#155eab',lw=2.8)
    axes[1].plot(u/length,actual.derivative()(u),color='#d75b20',lw=2.4,ls='--')
    axes[1].scatter([0,1],actual.derivative()([0,length]),color='#d75b20',s=50,zorder=4)
    axes[1].axhline(0,color='#4b5563',lw=.8)
    axes[1].set(title='Endpoint slopes changed',ylabel='Radius slope  dr / ds',xlim=(-.03,1.03))
    fig.text(.04,.015,'Actual saved coefficients · negative-X contour · display sampling only; exact coefficient audit is retained separately.\nNative result: two faulty vertices, no replacement carrier. The original 24af master remains unchanged.',fontsize=9,color='#475569')
    for ext in ['png','svg']:fig.savefig(out/('native-law-comparison.'+ext),dpi=170,bbox_inches='tight')
    plt.close(fig)

    patch=saved['patches'][1];arc=patch['surfaces'][0];basis=patch['aligned_curve']
    u=np.linspace(*patch['domain'],120);v=np.linspace(0,1,41)
    points=[spline(basis,arc['control_columns'][key])(u) for key in arc['column_order']]
    weights=np.asarray(arc['weights']);bernstein=np.stack([(1-v)**2,2*v*(1-v),v**2],axis=1)*weights
    surface=sum(points[j][:,None,:]*bernstein[None,:,j,None] for j in range(3))/bernstein.sum(axis=1)[None,:,None]
    base=spline(basis)(u)
    fig=plt.figure(figsize=(13.2,5.8),layout='constrained')
    fig.get_layout_engine().set(rect=(0,.12,1,.88))
    fig.suptitle('Explicit NURBS root reinforcement — actual saved construction',fontsize=17,fontweight='bold',x=.03,ha='left')
    ax=fig.add_subplot(121,projection='3d')
    ax.plot_surface(surface[:,:,0],surface[:,:,1],surface[:,:,2],color='#548bbd',edgecolor='none',alpha=.96,antialiased=True)
    ax.plot(base[:,0],base[:,1],base[:,2],color='#dc5c32',lw=1.8,label='Original arch / rib seam')
    ax.set(xlabel='X (mm)',ylabel='Y (mm)',zlabel='Z (mm)',title='Positive-X patch, in model coordinates')
    ax.set_box_aspect([35,20,18]);ax.view_init(elev=23,azim=-64);ax.legend(frameon=False,loc='upper left',fontsize=8)
    ax=fig.add_subplot(122)
    middle=(patch['domain'][0]+patch['domain'][1])/2
    p=spline(basis)(middle)
    controls=np.asarray([spline(basis,arc['control_columns'][key])(middle) for key in arc['column_order']])
    section=bernstein@controls/bernstein.sum(axis=1)[:,None]
    ax.plot(section[:,1]-p[1],section[:,2]-p[2],color='#155eab',lw=3,label='Saved rational NURBS arc')
    r=spline(patch['radius_curve'])(middle)[1]
    ax.plot([-r,.06,.06,0],[0,-.06,r,r],color='#61758b',lw=1.6,label='Overlap inside the parent solid')
    ax.scatter([0],[0],color='#dc5c32',s=36,label='Original seam')
    ax.axhline(0,color='#cbd5e1',lw=.8);ax.axvline(0,color='#cbd5e1',lw=.8)
    ax.set(aspect='equal',xlabel='Y − seam Y (mm)',ylabel='Z − seam Z (mm)',title='Section at native parameter  u = 0.5')
    ax.grid(color='#e2e8f0');ax.legend(frameon=False,fontsize=8,loc='upper left')
    fig.text(.03,.015,'Both native patches are valid single solids, about 4.098 mm³ each. This is a patch illustration, not a qualified carrier.\nThe assembly and its material-retention verdicts are separate records. No tessellation or display samples authorize acceptance.',fontsize=9,color='#475569')
    for ext in ['png','svg']:fig.savefig(out/('explicit-nurbs-root-patch.'+ext),dpi=170,bbox_inches='tight')
    plt.close(fig)
    receipt=dict(inputs={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [case,patches]},versions=dict(python=sys.version.split()[0],matplotlib=matplotlib.__version__,numpy=np.__version__,scipy=scipy.__version__),purpose='Saved-data visualization only; no CAD reconstruction or numerical acceptance',outputs={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.iterdir()})
    (out/'figure-provenance.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt))


if __name__=='__main__':main()
