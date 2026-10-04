from pathlib import Path
import json,gmsh
p=json.load(open('targeted-refinement-symmetric.json'));gmsh.initialize();gmsh.option.setNumber('General.Terminal',0)
gmsh.model.occ.importShapes('private-V2/rotor.step');gmsh.model.occ.synchronize();balls=[]
for dim,tag in gmsh.model.getEntities(1):
 length=gmsh.model.occ.getMass(1,tag)
 if length<.5:
  xyz=gmsh.model.occ.getCenterOfMass(1,tag)
  balls.append({'center_m':[x*.001 for x in xyz],'radius_m':.0004,'transition_m':.003,'size_inside_m':.00004,'source_edge_length_mm':length,'source_edge_tag':tag})
gmsh.finalize()
if len(balls)!=9:raise ValueError('Expected the 9 measured short CAD edges')
p['additional_balls']=balls;p['trigger']='Previous localized field plus 40um sizing at the 9 native V2 short CAD edges; exact STEP geometry unchanged';Path('V2-edge-resolution-refinement.json').write_text(json.dumps(p,indent=2)+'\n');print(json.dumps(balls))
