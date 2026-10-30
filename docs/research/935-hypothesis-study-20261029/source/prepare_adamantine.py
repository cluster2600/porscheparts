"""Whole-envelope elastic cooldown study; explicitly not a laser/melt-pool build simulation."""
import argparse
import json
from pathlib import Path
import numpy as np
p=argparse.ArgumentParser();p.add_argument('input',type=Path);p.add_argument('output',type=Path);p.add_argument('--dt',type=float,default=.02)
a=p.parse_args();a.output.mkdir()
d=np.load(a.input);x=d['nodes']/1000;h=d['hexes']
faces=h[:,np.array([[0,3,2,1],[4,5,6,7],[0,1,5,4],[1,2,6,5],[2,3,7,6],[3,0,4,7]])].reshape(-1,4)
_,idx,count=np.unique(np.sort(faces,axis=1),axis=0,return_index=True,return_counts=True)
b=faces[idx[count==1]];bottom=np.isclose(x[b,:,][...,2].mean(axis=1),x[:,2].min())
assert bottom.any()
with (a.output/'head.msh').open('w') as out:
 out.write('$MeshFormat\n2.2 0 8\n$EndMeshFormat\n$Nodes\n'+str(len(x))+'\n')
 for i,q in enumerate(x,1):out.write(f'{i} {q[0]:.12g} {q[1]:.12g} {q[2]:.12g}\n')
 out.write('$EndNodes\n$Elements\n'+str(len(h)+len(b))+'\n')
 for i,c in enumerate(h+1,1):out.write(f'{i} 5 2 0 1 '+' '.join(map(str,c))+'\n')
 for i,c in enumerate(b+1,len(h)+1):out.write(f'{i} 3 2 {4 if bottom[i-len(h)-1] else 1} 1 '+' '.join(map(str,c))+'\n')
 out.write('$EndElements\n')
factor=round(5/a.dt)
text=f'''geometry
{{
 import_mesh true
 mesh_file /tmp/935/{a.output.name}/head.msh
 mesh_format gmsh
 reset_material_id true
 dim 3
 material_height 1
 material_deposition false
 use_powder false
}}
physics {{ thermal true
 mechanical true
}}
discretization
{{
 mechanical {{ fe_degree 1 }}
 thermal {{ fe_degree 1
 quadrature gauss
 }}
}}
boundary
{{
 type convective,traction_free
 boundary_4 {{ type convective,clamped }}
}}
refinement {{ n_refinements 0
 time_steps_between_refinement 100000
}}
materials
{{
 initial_temperature 500
 property_format polynomial
 n_materials 1
 material_0
 {{
  solidus 843
  convection_temperature_infty 300
  solid
  {{
   lame_first_parameter 51083591331.26935
   lame_second_parameter 26315789473.68421
   thermal_expansion_coef 2.3e-5
   density 2670
   specific_heat 900
   thermal_conductivity_x 150
   thermal_conductivity_y 150
   thermal_conductivity_z 150
   convection_heat_transfer_coef 20
  }}
 }}
}}
sources {{ n_beams 0 }}
time_stepping
{{
 method rk_fourth_order
 scan_path_for_duration false
 duration 20
 time_step {a.dt}
 mechanical_time_step_factor {factor}
}}
post_processor
{{
 filename_prefix cooldown
 time_steps_between_output {factor}
 additional_output_refinement 0
}}
memory_space host
verbose_output false
'''
(a.output/'cooldown.info').write_text(text)
(a.output/'assumptions.json').write_text(json.dumps({'scope':'first 20 seconds of an assumed fully solid, initially stress-free post-build cooldown; NOT laser melting, deposition, porosity or full build qualification','initial_temperature_K':500,'ambient_K':300,'h_W_m2_K':20,'rho_kg_m3':2670,'Cp_J_kg_K':900,'k_W_m_K':150,'E_Pa':70e9,'nu':.33,'CTE_per_K':23e-6,'dt_s':a.dt,'duration_s':20,'geometry_pitch_mm':float(d['pitch']),'clamped_boundary':'lowest voxel surface of the monolithic envelope; provisional fixture','clamped_faces':int(bottom.sum()),'native_profile':'existing solid-polynomial research build, guard unchanged','manufacturing_qualified':False},indent=2)+'\n')
