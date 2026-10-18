"""Six focused source/stdlib fake guards; prepared UNRUN."""
import ast
import copy
import csv
from decimal import Decimal
import hashlib
import json
import math
from pathlib import Path
import struct
import tempfile
import unittest

SOURCE = Path(__file__).with_name('compare_saved.py')
SOURCE_SHA256 = '8b2eb2f27492e8b12747d884af7c7f7eb1823643e60f3faae93cfdd7865eafd5'
ROOT = SOURCE.resolve().parents[3]
DONORS = [ROOT/'work/962-engineering/cp1-oneway-thermoelastic-level1-assessor-prep-001/assess.py',
          ROOT/'work/962-engineering/cp1-oneway-thermoelastic-assessor-prep-003/assess.py']
REUSED = ('need', 'sha', 'bits', 'number', 'integer', 'rows', 'tensor', 'node_sample')

def functions():
    text = SOURCE.read_text(); tree = ast.parse(text)
    selected = set(REUSED) | {'schedule', 'require_same_maps', 'qp_rows', 'add_difference', 'reference_pairs'}
    ns = dict(csv=csv, Decimal=Decimal, hashlib=hashlib, json=json, math=math, Path=Path, struct=struct,
              DISP=('disp_x','disp_y','disp_z'), FORCE=('rx','ry','rz'),
              TENSORS=('stress','elastic_strain','mechanical_strain','total_strain','thermal_eigenstrain'),
              COMP=((0,0),(1,1),(2,2),(0,1),(0,2),(1,2)), SUFFIX=('xx','yy','zz','xy','xz','yz'))
    ns['QP_FIELDS'] = tuple(x+'_'+y for x in ns['TENSORS'] for y in ns['SUFFIX'])
    body = [x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name in selected]
    if {x.name for x in body} != selected: raise AssertionError('Exact finite pure guard namespace required')
    exec(compile(ast.Module(body=body,type_ignores=[]), str(SOURCE), 'exec'), ns)
    return ns


def write_csv(path, fields, records):
    with path.open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader();writer.writerows(records)


class Guards(unittest.TestCase):
    def test_source_exact_helper_reuse_and_finite_unrun_index(self):
        self.assertEqual(hashlib.sha256(SOURCE.read_bytes()).hexdigest(),SOURCE_SHA256)
        tree=ast.parse(SOURCE.read_text())
        for donor in DONORS:
            old=ast.parse(donor.read_text())
            for name in REUSED:
                a=next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name==name)
                b=next(x for x in old.body if isinstance(x,ast.FunctionDef) and x.name==name)
                self.assertEqual(ast.dump(a,include_attributes=False),ast.dump(b,include_attributes=False))
        imports=[x.names[0].name for x in tree.body if isinstance(x,ast.Import)]
        self.assertFalse(set(imports)&{'numpy','scipy','gmsh'})
        index=json.loads(SOURCE.with_name('input-index.json').read_text())
        self.assertEqual(len(index['inputs']),342)
        self.assertEqual(sum(x['role']=='native-CSV' for x in index['inputs'].values()),328)
        self.assertIsNone(index['observed_differences']);self.assertIsNone(index['cross_level_difference_limit'])
        self.assertIs(index['execution_authorized'],False)

    def test_exact_prescribed_step_pair_schedule_and_birth_split(self):
        ns=functions();pairs=ns['schedule']()
        self.assertEqual(len(pairs),81)
        self.assertEqual([(r['coarse_step'],r['fine_step']) for r in pairs],[(k,2*k) for k in range(81)])
        self.assertEqual(pairs[39]['regime'],'pre_birth');self.assertEqual(pairs[40]['regime'],'post_birth')
        self.assertEqual(pairs[40]['nominal_common_time_decimal_s'],'0.200')
        self.assertEqual(pairs[80]['nominal_common_time_decimal_s'],'0.400')

    def test_exact_ID_corner_QP_and_signed_zero_map_refusals(self):
        fn=functions()['require_same_maps'];left=({3:(0.,0.,0.)},{7:[3,4,5,6,8,9,10,11]},{(7,0):(0.,0.,0.)})
        fn(left,copy.deepcopy(left))
        for changed in [({3:(-0.,0.,0.)},left[1],left[2]),
                        (left[0],{7:[4,3,5,6,8,9,10,11]},left[2]),
                        (left[0],left[1],{(7,1):(0.,0.,0.)}),
                        (left[0],left[1],{(7,0):(0.,0.,-0.)})]:
            with self.assertRaises(ValueError):fn(left,changed)

    def test_unchanged_native_doublet_protocol_rejects_missing_triple_and_token_drift(self):
        ns=functions();fields=('id','x','y','z',*ns['DISP'],'temperature',*ns['FORCE'])
        geometry={t:(1.,float(t),0.) for t in range(25)}
        records=[]
        for tag,point in geometry.items():
            row=dict(zip(fields,[str(tag),*map(str,point),'0','0','0','350','0','0','0']))
            records.extend([dict(row),dict(row)])
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'nodes.csv';write_csv(path,fields,records)
            _,storage=ns['node_sample'](path,geometry,set(geometry),(*ns['DISP'],'temperature',*ns['FORCE']),list(geometry))
            self.assertEqual(storage['raw_row_count'],50);self.assertEqual(len(storage['verified_doublets']),25)
            self.assertIs(storage['raw_rows_rewritten_or_averaged'],False)
            changes=[records[:-1],records+[dict(records[0])],copy.deepcopy(records),copy.deepcopy(records)]
            changes[2][1]['rx']='-0.0';changes[3][1]['temperature']='350.0'
            for changed in changes:
                write_csv(path,fields,changed)
                with self.assertRaises(ValueError):ns['node_sample'](path,geometry,set(geometry),(*ns['DISP'],'temperature',*ns['FORCE']),list(geometry))
            write_csv(path,fields,records)
            with self.assertRaises(ValueError):ns['node_sample'](path,geometry,set(geometry),(*ns['DISP'],'temperature',*ns['FORCE']))

    def test_saved_QP_glue_joins_all30_fields_and_refuses_missing_duplicate_or_word_drift(self):
        ns=functions();fields=('elem_id','qp_id','x','y','z',*ns['QP_FIELDS'])
        coords={(11,q):(float(q),0.,0.) for q in range(8)};records=[]
        for (tag,q),xyz in coords.items():
            records.append(dict(zip(fields,[str(tag),str(q),*map(str,xyz),*(['0']*30)])))
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'qp.csv';write_csv(path,fields,records)
            data=ns['qp_rows'](path,{11},coords)
            self.assertEqual(set(data),set(coords));self.assertTrue(all(len(row)==30 for row in data.values()))
            changed=copy.deepcopy(records);changed[0]['z']='-0.0'
            for bad in [records[:-1],records+[dict(records[0])],changed]:
                write_csv(path,fields,bad)
                with self.assertRaises(ValueError):ns['qp_rows'](path,{11},coords)

    def test_absolute_diagnostic_and_separate_birth_references_no_acceptance_gate(self):
        ns=functions();metrics={}
        ns['add_difference'](metrics,'stress_Pa',1.,4.,dict(elem_id=8))
        ns['add_difference'](metrics,'stress_Pa',2.,5.,dict(elem_id=9))
        self.assertEqual(metrics['stress_Pa']['count'],2)
        self.assertEqual(metrics['stress_Pa']['maximum_absolute_difference'],3.)
        self.assertEqual(metrics['stress_Pa']['witness']['elem_id'],8)
        with self.assertRaises(ValueError):ns['add_difference']({},'T',math.inf,0.,{})
        a={7:dict(disp_x=1.,disp_y=0.,disp_z=0.,temperature=351.,born_reference_temperature=350.)}
        b={7:dict(disp_x=2.,disp_y=0.,disp_z=0.,temperature=352.,born_reference_temperature=349.)}
        pair=ns['reference_pairs'](a,b,{7:(1.,0.,0.)},{7},{7})[0]
        self.assertIs(pair['shared'],True)
        self.assertEqual(pair['fields']['disp_x']['absolute_difference'],1.)
        self.assertEqual(pair['fields']['born_reference_temperature']['coarse'],350.)
        self.assertEqual(pair['fields']['born_reference_temperature']['fine'],349.)
        self.assertNotIn('passed',pair)


if __name__=='__main__':unittest.main()
