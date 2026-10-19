"""Plot the actual four-rail construction ledger and its exact coordinate-width law."""
from fractions import Fraction as Q
import hashlib
import json
import math
import os
from pathlib import Path
import resource
import signal
import sys

H = Path(__file__).resolve().parent
R = H.parents[1]
T = R / 'work/carrier-process-20261017/bounded-webs-stock-rib-C2-width-trial-preparation-002'
B = T.with_name('bounded-webs-stock-rib-body-inspection-preparation-001')
F = R / 'work/carrier-first-window-stock-FEA-figure-preparation-002/pending-plan.json'

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def bezier(points, t):
    degree = len(points) - 1
    return tuple(sum(Q(math.comb(degree, i)) * (1-t)**(degree-i) * t**i * p[k]
                     for i, p in enumerate(points)) for k in (0, 1))

def main():
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError('90 s drawing limit')))
    signal.alarm(90)
    resource.setrlimit(resource.RLIMIT_CPU, (60, 70))
    os.nice(10)
    assert os.getpriority(os.PRIO_PROCESS, 0) == 10
    read = lambda p: json.loads(p.read_bytes())
    trial, body = read(T/'root-terminal-review-001.json'), read(B/'root-terminal-review-001.json')
    assert sha(T/'root-terminal-review-001.json') == 'e37d778f94894ae3cc9a34a8094d73ffd5688845b74be474a20843fffca10e20'
    assert sha(B/'root-terminal-review-001.json') == '3f5313d65f0206aa0141a7334ac5c9c901de296d9d63186856a4fdaf85d7bb0c'
    assessment = read(T/'output-001/assessment.json')
    ledger = T/'output-001'/assessment['actual_modified_rail_branch_ledger']['path']
    assert sha(ledger) == assessment['actual_modified_rail_branch_ledger']['sha256']
    rows = [json.loads(line) for line in ledger.read_text().splitlines()]
    assert rows == assessment['actual_modified_rail_branch_ledger']['rows']
    assert {(r['X_side'], r['Y_side']) for r in rows} == {(-1,-1), (-1,1), (1,-1), (1,1)}
    row = next(r for r in rows if r['X_side'] == r['Y_side'] == 1)
    new = [tuple(Q(v) for v in p) for p in row['control_points_Q']]
    old = [(Q(22),Q(87,5)), (Q(27),Q(87,5)), (Q(29),Q(32,5)), (Q(35),Q(32,5))]
    inner = [(x,y-Q(14,5)) for x,y in old]
    # shortcut: 401 samples draw the exact source curves; this is an illustration, not a distance gate.
    ts = [Q(i,400) for i in range(401)]
    curves = [[bezier(points,t) for t in ts] for points in (inner,old,new)]
    for t,a,b in zip(ts,curves[1],curves[2]):
        assert b[0] == a[0] and b[1]-a[1] == Q(14,5)*64*t**3*(1-t)**3
    assert trial['candidate_BREP_sha256'] == body['candidate_BREP_sha256'] == assessment['outputs_sha256']['candidate-native.brep']
    assert body['measured_mass_kg'] == 1.2747979975709924
    pins = {str(p.relative_to(R)):sha(p) for p in [Path(__file__),ledger,T/'root-terminal-review-001.json',B/'root-terminal-review-001.json',T/'output-001/assessment.json',F]}
    runtime = read(F)['runtime_sha256']
    assert all(sha(Path(p)) == v for p,v in runtime.items())
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    matplotlib.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'svg.fonttype':'none','axes.spines.top':False,'axes.spines.right':False})
    out = H/'output-001'
    out.mkdir()
    fig,(ax,bx) = plt.subplots(1,2,figsize=(12,6),gridspec_kw={'width_ratios':[1.15,1]})
    fig.patch.set_facecolor('#f6f8fa')
    for panel in (ax,bx): panel.set_facecolor('#f6f8fa');panel.grid(alpha=.18)
    xy = [[list(map(float, p)) for p in curve] for curve in curves]
    for data,label,color,style in zip(xy,['Unchanged inner rail','Previous outer rail','New outer rail'],['#677989','#1679a7','#df7a22'],['-','--','-']):
        ax.plot([p[0]for p in data],[p[1]for p in data],style,color=color,label=label,lw=2.3)
    ax.fill_between([p[0]for p in xy[2]],[p[1]for p in xy[1]],[p[1]for p in xy[2]],color='#df7a22',alpha=.22,label='Added material')
    ax.set(title='One of four mirrored transitions',xlabel='X (mm)',ylabel='Y (mm)',aspect='equal');ax.legend(loc='lower left',fontsize=9,framealpha=.96)
    widths = [Q(14,5)*(1+64*t**3*(1-t)**3) for t in ts]
    bx.plot([float(t)for t in ts],[float(w)for w in widths],color='#df7a22',lw=3)
    bx.axhline(2.8,color='#1679a7',ls='--',label='Previous 2.8 mm width')
    bx.scatter([.5],[5.6],color='#df7a22',zorder=5)
    bx.annotate('5.6 mm at the centre',(.5,5.6),xytext=(.53,5.87),fontsize=10)
    bx.set(title='Smooth width increase',xlabel='Transition parameter t',ylabel='Y-coordinate width (mm)',ylim=(2.4,6.2),xlim=(0,1));bx.legend(loc='lower center',fontsize=9)
    bx.text(.5,.24,r'$\Delta y=2.8\,64t^3(1-t)^3$',transform=bx.transAxes,ha='center',fontsize=15)
    bx.text(.5,.15,'C2 endpoint continuity preserved',transform=bx.transAxes,ha='center',fontsize=10)
    fig.suptitle('993 Turbo carrier | targeted rib reinforcement',fontsize=19,fontweight='bold',y=.97)
    fig.text(.5,.88,'Actual d64a7faf construction ledger | mass 1.274798 kg | limit 1.30 kg',ha='center',fontsize=12)
    fig.text(.5,.035,'Added mass: 6.96 g across four transitions   •   Remaining mass allowance: 25.20 g\nGeometry drawing; new surface and mechanical calculations are separate stages.',ha='center',fontsize=10,color='#445767')
    fig.subplots_adjust(top=.79,bottom=.21,wspace=.32)
    for suffix in ('png','svg'): fig.savefig(out/('carrier-rib-C2-geometry.'+suffix),dpi=180,facecolor=fig.get_facecolor())
    plt.close(fig)
    loaded = {str(Path(m.__file__).resolve()) for n,m in list(sys.modules.items()) if n.split('.')[0] in ['numpy','matplotlib','PIL'] and getattr(m,'__file__',None) and Path(m.__file__).is_file()}
    assert loaded <= set(runtime)
    assert all(sha(Path(p)) == v for p,v in runtime.items())
    assert all(sha(R/p)==v for p,v in pins.items())
    receipt = dict(schema='actual-rib-source-geometry-drawing-1',language='English',candidate_BREP_sha256=body['candidate_BREP_sha256'],inputs_sha256=pins,runtime_sha256=runtime,actual_loaded_runtime_files=sorted(loaded),sample_count=401,exact_sample_law_assertions=True,source_ledger_four_mirrors_verified=True,geometry_or_FEA_modified=False,outputs={p.name:dict(bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(out.iterdir())})
    with(out/'receipt.json').open('x')as f:json.dump(receipt,f,indent=2);f.write('\n')
    print(json.dumps(dict(status='actual_source_geometry_drawing_complete',outputs=receipt['outputs'])))

if __name__ == '__main__': main()
