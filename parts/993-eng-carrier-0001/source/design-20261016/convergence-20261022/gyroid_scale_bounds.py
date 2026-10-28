"""Evaluate analytic opposite-level gap bounds without assigning printable wall limits."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def main():
    p=argparse.ArgumentParser(__doc__);p.add_argument('--cell-contract',type=Path,required=True);p.add_argument('--study',type=Path,required=True);p.add_argument('--budget',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();cell=json.loads(a.cell_contract.read_text());study=json.loads(a.study.read_text());budget=json.loads(a.budget.read_text());threshold=cell['threshold'];depth=study['geometry']['thickness_mm']-2*budget['parameters']['skin_mm']
    if a.output.exists()or not 0<threshold<1.5 or not depth>0:raise ValueError('Fresh output and valid fixed gyroid/pad parameters required')
    lower=threshold/(2*math.pi*math.sqrt(3));upper=math.sqrt(3)*math.asin(2*threshold/3)/(2*math.pi);u=.5*math.asin(2*threshold/3)
    assert abs(3*math.sin(u)*math.cos(u)-threshold)<1e-12 and 0<lower<=upper
    pitches=[.5,1.,2.,3.,4.,6.,8.];rows=[dict(pitch_mm=x,minimum_opposite_level_gap_lower_mm=lower*x,minimum_opposite_level_gap_upper_mm=upper*x,nominal_pad_core_periods=depth/x)for x in pitches]
    # Bound the untrimmed periodic sheet; clipping and the actual printed surface need their own audit.
    report=dict(status='analytic_untrimmed_gyroid_scale_bounds_evaluated',threshold=threshold,global_dimensionless_gradient_norm_bound=2*math.sqrt(3),lower_gap_formula='threshold * pitch / (2*pi*sqrt(3))',upper_gap_formula='sqrt(3) * asin(2*threshold/3) * pitch / (2*pi)',nominal_pad_core_depth_mm=depth,relative_density_independent_of_pitch=True,periodic_linear_elastic_tensor_independent_of_pitch=True,rows=rows,part_geometry_changed=False,printability_qualified=False,formal_interval_certificate=False,source_sha256={str(f):hashlib.sha256(f.read_bytes()).hexdigest()for f in [a.cell_contract,a.study,a.budget,Path(__file__)]})
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'figure.facecolor':'#f5f5f1','axes.facecolor':'#f5f5f1','axes.spines.top':False,'axes.spines.right':False});fig,axes=plt.subplots(1,2,figsize=(12,5.5),layout='constrained');axes[0].fill_between(pitches,[r['minimum_opposite_level_gap_lower_mm']for r in rows],[r['minimum_opposite_level_gap_upper_mm']for r in rows],color='#237a69',alpha=.22,label='Analytic bracket for minimum gap');axes[0].plot(pitches,[r['minimum_opposite_level_gap_lower_mm']for r in rows],color='#237a69');axes[0].plot(pitches,[r['minimum_opposite_level_gap_upper_mm']for r in rows],color='#237a69');axes[0].set_ylabel('Opposite-level surface gap [mm]');axes[0].set_title('Smaller cells also mean smaller features',loc='left',fontweight='bold');axes[0].legend(fontsize=9)
    axes[1].plot(pitches,[r['nominal_pad_core_periods']for r in rows],'o-',color='#b57535');axes[1].set_ylabel('Periods across nominal pad core');axes[1].set_title(f'Finite core example / {depth:g} mm depth',loc='left',fontweight='bold')
    for ax in axes:ax.set_xlabel('Cell pitch [mm]');ax.grid(axis='y',alpha=.13);ax.set_ylim(bottom=0)
    fig.suptitle('993 CARRIER / MICRO-CELL LENGTH-SCALE TRADEOFF',fontsize=17,fontweight='bold');fig.supxlabel('Fixed sheet threshold: shrinking pitch does not change ideal periodic density or elasticity\nUntrimmed analytic sheet only. No machine minimum, printable feature or finite-core stiffness is certified.',fontsize=10);a.output.mkdir();image=a.output/'gyroid-length-scale.png';fig.savefig(image,dpi=160);plt.close(fig);report['figure_sha256']=hashlib.sha256(image.read_bytes()).hexdigest();(a.output/'assessment.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':main()
