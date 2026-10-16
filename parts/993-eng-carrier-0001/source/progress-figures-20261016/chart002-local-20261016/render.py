"""Render retained chart polygons and redundancy certificates; no generation."""
import argparse,hashlib,json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import PathPatch,Rectangle
from matplotlib.path import Path as PlotPath
from matplotlib.ticker import FuncFormatter
import shapely
HERE=Path(__file__).resolve().parent
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('output',type=Path,help='Fresh output directory; an existing path is refused')
OUTPUT=parser.parse_args().output.resolve()
BASE=HERE/'inputs'
INPUTS={BASE/'chart-0000-input.json':'019259b25d64c66a0d03f07098ad482f5b48f32a4100c577fe64e4d8c286c2c5',
 BASE/'chart-0000-completed.json':'1d103422848afc5d09ca3c867cce9540dc3ec53a973f0bebcb41e7db127220dc',
 BASE/'assessment.json':'691e78aea645eab9a64cbcbc5326e555c0b89cba6f30a2c87f7954d8722200e4'}
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert all(sha(p)==h for p,h in INPUTS.items())
a,b,assessment=[json.loads(p.read_text()) for p in INPUTS]
assert b['captured_input_unchanged'] and b['input_sha256']==sha(next(iter(INPUTS)))
assert assessment['chart_progress_full_result_roundtrip_verified'] and assessment['source_files_unchanged']
infill=b['native_infill'];row=infill['continuous_interface_reconstruction']['intervals'][0]
def polygon(value,identity):
 p=shapely.from_wkb(bytes.fromhex(value));assert hashlib.sha256(p.wkb).hexdigest()==identity
 assert p.geom_type=='Polygon' and p.is_valid and not p.is_empty
 return p
D=polygon(a['source_domain_geometry_wkb_hex'],a['source_domain_geometry_sha256'])
R=polygon(b['generated_material_geometry_wkb_hex'],b['generated_material_geometry_sha256'])
assert a['source_domain_geometry_sha256']==assessment['source_domain_geometry_sha256']==row['source_domain_geometry_sha256']
assert R.wkb_hex==row['generated_material_geometry_wkb_hex']
assert row['exact_free_domain_coverage']['passed'] and row['exact_intended_band_union_confinement']['passed']
assert len(infill['interface_contacts'])==2 and all(c['passed'] for c in infill['interface_contacts'])
certificates=[r for r in row['combinatorial_construction']['whole_edge_interfaces']
 if r.get('strip_status')=='excluded_redundant_inside_source_domain']
assert [r['edge'] for r in certificates]==[2,3,4,5,6]
strips=[]
for r in certificates:
 c=r['redundancy_certificate'];assert c['exact_redundancy_coverage']['passed']
 assert c['contact_role_unchanged'] and c['source_trace_unchanged']
 strips.append(polygon(c['proposed_strip_geometry_wkb_hex'],c['proposed_strip_geometry_sha256']))
OUTPUT.mkdir(parents=True,exist_ok=False)
blue,green,orange,ink='#205f86','#17735d','#d97722','#1e2c39'
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'axes.labelcolor':ink,
 'text.color':ink,'axes.edgecolor':'#9ba8b3','xtick.color':ink,'ytick.color':ink,
 'svg.fonttype':'none','pdf.fonttype':42})
fig=plt.figure(figsize=(14.5,9),facecolor='#fbfcfd')
fig.text(.055,.965,'Cinq extensions redondantes, une feuille conservée',fontsize=22,weight='bold')
fig.text(.055,.925,'Support moteur 993  /  source 002  /  peau 2  /  coordonnées dépliées réelles',fontsize=12,color='#536574')
fig.text(.055,.875,'Cas local admis — région complète en cours',fontsize=14,weight='bold',color=green,
 bbox=dict(boxstyle='round,pad=.5',facecolor='#e7f2ed',edgecolor='none'))
source=fig.add_axes([.065,.18,.13,.59]);final=fig.add_axes([.265,.18,.13,.59]);zoom=fig.add_axes([.49,.55,.455,.25])
fmt=FuncFormatter(lambda x,_:f'{x:g}'.replace('.',','))
def draw(ax,p,face,edge,alpha=1,hatch=None,zorder=1,linestyle='-'):
 vertices=[];codes=[]
 for ring in [p.exterior,*p.interiors]:
  points=list(ring.coords);vertices.extend(points)
  codes.extend([PlotPath.MOVETO]+[PlotPath.LINETO]*(len(points)-2)+[PlotPath.CLOSEPOLY])
 patch=PathPatch(PlotPath(vertices,codes),facecolor=face,edgecolor=edge,lw=1.25,
   alpha=alpha,hatch=hatch,zorder=zorder,linestyle=linestyle)
 ax.add_patch(patch)
def style(ax):
 ax.set_aspect('equal',adjustable='box');ax.set_facecolor('white');ax.grid(color='#e5ebef',lw=.7,zorder=0)
 ax.xaxis.set_major_formatter(fmt);ax.yaxis.set_major_formatter(fmt)
 ax.set_xlabel('t (mm)');ax.set_ylabel('Z (mm)')
 for side in ('top','right'):ax.spines[side].set_visible(False)
for ax in [source,final,zoom]:style(ax)
for ax in [source,final]:
 ax.set_xlim(-2.55,.65);ax.set_ylim(35.6,53.05);ax.set_xticks([-2,0]);ax.set_yticks([36,40,44,48,52])
 ax.add_patch(Rectangle((-2.5,35.9),3.15,.49,facecolor='none',edgecolor=orange,lw=1.3,ls='--',zorder=5))
draw(source,D,'#d8e9f4',blue);source.set_title('Domaine source D',fontsize=13,weight='bold',pad=13)
draw(final,R,'#dcefe7',green);draw(final,D,'none',blue,linestyle='--',zorder=2)
final.set_title('Surface calculée R',fontsize=13,weight='bold',pad=13)
fig.text(.13,.095,f'{D.area:.4f}'.replace('.',',')+' mm²',ha='center',fontsize=12,color=blue,weight='bold')
fig.text(.33,.095,f'{R.area:.4f}'.replace('.',',')+' mm²',ha='center',fontsize=12,color=green,weight='bold')
zoom.set_xlim(-2.5,.75);zoom.set_ylim(35.9,36.39);zoom.set_anchor('N')
zoom.set_xlabel('Abscisse dépliée t (mm)');zoom.set_yticks([36,36.2]);zoom.set_xticks([-2,-1,0])
draw(zoom,D,'#d8e9f4',blue)
for i,p in enumerate(strips,1):
 draw(zoom,p,'#f8d7aa',orange,alpha=.95,hatch='///',zorder=3)
 zoom.text((p.bounds[0]+p.bounds[2])/2,36.09,str(i),ha='center',va='center',weight='bold',fontsize=11,zorder=4)
zoom.annotate('',xy=(.59,36.19),xytext=(.59,35.99),arrowprops=dict(arrowstyle='<->',lw=1.2,color=orange))
zoom.text(.66,36.09,'0,20\nmm',color=orange,fontsize=10,ha='left',va='center')
zoom.set_title('Zoom — les cinq emprises sont déjà dans D',fontsize=14,weight='bold',pad=13,loc='left')
fig.text(.49,.53,'Zones hachurées : quadrilatères réellement conservés dans les certificats.',fontsize=11,color='#536574')
fig.text(.49,.465,'5 / 5 entièrement contenus dans D',fontsize=19,weight='bold',color=orange)
fig.text(.49,.405,'D est intégralement conservé.',fontsize=15,weight='bold',va='top')
fig.text(.49,.355,'Rôles et traces de contact conservés.\nLes ajouts redondants sont omis ; les autres raccords\ncalculés restent dans la surface finale R.',fontsize=13,linespacing=1.6,va='top')
fig.text(.49,.235,'Preuves locales conservées',fontsize=12,weight='bold',color=green,va='top')
fig.text(.49,.195,'D dans R : PASS   •   R dans la bande autorisée : PASS\nContacts haut / bas du cas local : PASS',fontsize=12,color=green,linespacing=1.6,va='top')
fig.text(.055,.045,'Contours issus du calcul retenu, sans recalcul de génération.  |  Entrées et exports liés par SHA-256 dans render-receipt.json.',fontsize=10,color='#657582')
outputs=[]
for suffix in ['png','svg','pdf']:
 path=OUTPUT/('chart002-local-review.'+suffix)
 fig.savefig(path,dpi=230,facecolor=fig.get_facecolor(),metadata={'Title':'Support 993 — correction locale de la peau 2'})
 outputs.append(path)
plt.close(fig)
assert all(sha(p)==h for p,h in INPUTS.items())
receipt=dict(status='rendered_retained_local_chart_no_global_admission',
 visible_status='Cas local admis — région complète en cours',source_index=2,original_chart_index=2,
 scope='One 2D chart from retained full-repair003; no native_infill, remapping or support generation was executed',
 inputs_sha256={str(p.relative_to(HERE)):h for p,h in INPUTS.items()},
 render_source='render.py',source_sha256=sha(Path(__file__)),
 source_domain_geometry_sha256=a['source_domain_geometry_sha256'],generated_material_geometry_sha256=b['generated_material_geometry_sha256'],
 redundant_edge_ids=[r['edge'] for r in certificates],redundant_polygon_sha256=[r['redundancy_certificate']['proposed_strip_geometry_sha256'] for r in certificates],
 data_coordinates='Retained chart t,Z in mm; equal axis scale, no deformation amplification',
 source_area_mm2=D.area,result_area_mm2=R.area,matplotlib_version=matplotlib.__version__,shapely_version=shapely.__version__,
 input_files_unchanged=True,outputs_sha256={p.name:sha(p) for p in outputs})
(OUTPUT/'render-receipt.json').write_text(json.dumps(receipt,indent=2,ensure_ascii=False)+'\n')
print(json.dumps({'status':receipt['status'],'outputs':list(receipt['outputs_sha256'])}))
