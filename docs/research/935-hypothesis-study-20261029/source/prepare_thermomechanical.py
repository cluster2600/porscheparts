"""Apply an independently solved steady temperature field to the pressure deck."""
import argparse
import json
from pathlib import Path
import numpy as np
p=argparse.ArgumentParser();p.add_argument('case',type=Path)
a=p.parse_args();d=np.load(a.case/'thermal-direct-fields.npz');t=d['NDTEMP'][:,0]
assert np.isfinite(t).all() and t.min()>75 and t.max()<255
with (a.case/'temperature-field.inp').open('x') as out:
    out.write('*TEMPERATURE\n')
    for i,v in enumerate(t,1):out.write(f'{i},{v:.12g}\n')
base=(a.case/'pressure-direct.inp').read_text()
base=base.replace('*BOUNDARY\n','*INITIAL CONDITIONS,TYPE=TEMPERATURE\nALL,80.\n*BOUNDARY\n',1)
base=base.replace('*NODE FILE\n','*INCLUDE,INPUT=temperature-field.inp\n*NODE FILE\n',1)
(a.case/'thermomechanical.inp').write_text(base)
(a.case/'thermomechanical-assumptions.json').write_text(json.dumps({'stress_free_temperature_C':80,'material_properties':'same constant hypothetical aluminium card as pressure and thermal cases','temperature_field':'thermal-direct-fields.npz:NDTEMP','pressure_MPa':10,'plasticity':False,'contact_or_bolt_preload':False,'scope':'linear thermoelastic sensitivity study; stress above a real alloy allowable would invalidate elastic service interpretation'},indent=2)+'\n')
