#!/usr/bin/env python3
"""Derive a conditional BOM and blank physical measurement sheet from contracts."""
import argparse,csv,hashlib,json
from pathlib import Path


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def build(root):
    p=json.loads((root/'parameters/assembly-study-S1.json').read_text());c=json.loads((root/'parameters/assembly-interface-contract.json').read_text())
    g=json.loads((root/'results/assembly/S1/geometry-report.json').read_text())
    stock=json.loads((root/'results/lpbf/V2-stock-scenario/stock-report.json').read_text())
    density=p['sizing_scenario']['density_kg_m3'];bom=[]
    for name,record in g['components'].items():
        if name=='V2_original_assembly':continue
        route='conventional_or_sheet_forming_candidate'
        mass=record['volume_mm3']*density*1e-9
        if 'pulley' in name or 'belt' in name or 'shaft' in name:route='commercial_component_selection_pending';mass=None
        bom.append({'id':name,'quantity':record['solids'],'geometry_role':record['role'],
                    'analytic_solid_volume_mm3':record['volume_mm3'],
                    'conditional_mass_kg_at_assumed_aluminium_density':mass,
                    'candidate_route':route,'released_drawing_available':False,'procurement_or_build_allowed':False})
    bom.insert(0,{'id':'V2_rotor_stock_scenario','quantity':1,'candidate_route':'LPBF_AlSi10Mg_then_reviewed_machining',
                  'analytic_solid_volume_mm3':stock['stock_blank_volume_mm3'],
                  'conditional_mass_kg_at_assumed_aluminium_density':stock['stock_blank_mass_kg_at_assumed_density'],
                  'released_drawing_available':False,'procurement_or_build_allowed':False})
    for name in ['bevel_pair','output_bearings','input_bearings','seals','retention','mount_fasteners','tensioner','head_outlet_adapters']:
        bom.append({'id':name,'quantity':None,'candidate_route':'engineering_definition_pending',
                    'analytic_solid_volume_mm3':None,'conditional_mass_kg_at_assumed_aluminium_density':None,
                    'released_drawing_available':False,'procurement_or_build_allowed':False})
    path=root/'results/assembly/S1-interface-measurement-sheet.csv'
    with path.open('w',newline='') as stream:
        writer=csv.writer(stream,lineterminator='\n');writer.writerow(['interface','feature','value','units','uncertainty','instrument','calibration','datum_definition','reference_id','evidence_uri','reviewed_by'])
        for interface,features in c['required_interfaces'].items():
            for feature in features:writer.writerow([interface,feature]+['']*9)
    result={'status':'conditional_review_BOM_and_unfilled_physical_measurement_sheet','script_sha256':sha(Path(__file__)),
            'input_sha256':{name:sha(root/name) for name in ['parameters/assembly-study-S1.json','parameters/assembly-interface-contract.json','results/assembly/S1/geometry-report.json','results/lpbf/V2-stock-scenario/stock-report.json']},
            'BOM':bom,'measurement_sheet_sha256':sha(path),'measurement_rows':sum(map(len,c['required_interfaces'].values())),
            'physical_measurements_or_vendor_selection_invented':False,
            'manufacturing_authorized':False,'functional_interfaces_verified':False,'physical_validation_established':False}
    (root/'results/assembly/S1-review-packet.json').write_text(json.dumps(result,indent=2)+'\n');print('Conditional S1 review packet written')


if __name__=='__main__':
    cli=argparse.ArgumentParser(description=__doc__);cli.add_argument('root',type=Path);build(cli.parse_args().root)
