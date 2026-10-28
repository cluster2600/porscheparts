"""Prepared source-only level/contract/callback guards. No module/science/native import."""
import ast
import hashlib
import json
from pathlib import Path
from unittest import TestCase,main

PREP=Path(__file__).resolve().parent
ROOT=PREP.parents[2]
ENGINEERING=PREP.parent
DONOR=ENGINEERING/'cp1-assumed-thermal-birth-linear-prep-001'
MAC_DONOR=ENGINEERING/'cp1-assumed-thermal-birth-linear-macos-prep-001'
EXPECTED=[{'level': 0, 'dt_s': 0.01, 'expected_native_steps': 40, 'birth_step': 20, 'case': 'work/962-engineering/cp1-assumed-thermal-birth-linear-level0-prep-001', 'Mac': 'work/962-engineering/cp1-assumed-thermal-birth-linear-level0-macos-prep-001', 'planned_native_output': 'work/962-engineering/cp1-assumed-thermal-birth-linear-level0-001', 'time_input_sha256': 'efa207979d8df59060209e7d6673a7630bc3f9cf8fe7356700d7ed85de190ac6', 'case_contract_sha256': '7607afa5fd41e7df2b867aa4f2d6342e9adf03e2ee81b84085dedfed3e972535', 'source_sha256': 'f9593bd23433485966e25eef2a3a4c1c0206ce6f0dcc02d6de151eb1fc8065d6', 'mock_sha256': 'fabf8aa3e0e6c3f1701a96f7d7ec1c9a136d2bba322a48bd859f99d14965731e', 'eight_function_ASTs_exact': ['need', 'sha', 'same', 'check_pins', 'runtime_unchanged', 'commands', 'registry_features', 'checked_contract'], 'run_AST_receipt_literal_only': True, 'owned_control_command_runtime_checks_exact_after_receipt_normalization': True, 'card_sha256': '4e07cbb997c831bac2c0abd43092148c5518b6c7aa04d7b3d287779f9e700986', 'deck_sha256': 'ffe9b19786d534a8b4ad60e78290c7d3698a2dcb6b7ddf183f100321b02df1aa', 'assessor_sha256': '0548fcbf6eba737aaaf816abbfbfd0511b5b8fb266aa10c34a1f5817eef0e338'}, {'level': 1, 'dt_s': 0.005, 'expected_native_steps': 80, 'birth_step': 40, 'case': 'work/962-engineering/cp1-assumed-thermal-birth-linear-level1-prep-001', 'Mac': 'work/962-engineering/cp1-assumed-thermal-birth-linear-level1-macos-prep-001', 'planned_native_output': 'work/962-engineering/cp1-assumed-thermal-birth-linear-level1-001', 'time_input_sha256': '65a7d5bf03d5f3cc7ae5620edab2bc591b597cdfd035de3de1c859b4944583cc', 'case_contract_sha256': '047471049c96bfb3c28fd74395998748eb5ca5c91feb24495449ce78f9f5ad47', 'source_sha256': '7f6d51f52dd69373ca3dad5aad4390ed27900db8c8aad76fd02bece32a2c23c0', 'mock_sha256': 'fcbe8425fd8a6556b9e5088c7993206625071abc00d238f1c71c50d9b2293ebe', 'eight_function_ASTs_exact': ['need', 'sha', 'same', 'check_pins', 'runtime_unchanged', 'commands', 'registry_features', 'checked_contract'], 'run_AST_receipt_literal_only': True, 'owned_control_command_runtime_checks_exact_after_receipt_normalization': True, 'card_sha256': '4e07cbb997c831bac2c0abd43092148c5518b6c7aa04d7b3d287779f9e700986', 'deck_sha256': 'ffe9b19786d534a8b4ad60e78290c7d3698a2dcb6b7ddf183f100321b02df1aa', 'assessor_sha256': '0548fcbf6eba737aaaf816abbfbfd0511b5b8fb266aa10c34a1f5817eef0e338'}]

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

class SourceGuards(TestCase):
 def test_exact_dt_level_contract_and_unchanged_physics(self):
  original=json.loads((DONOR/'case-contract.json').read_text())
  for row in EXPECTED:
   with self.subTest(level=row['level']):
    level=row['level'];case=ROOT/row['case'];contract=json.loads((case/'case-contract.json').read_text())
    for name,key in [('card.json','card_sha256'),('thermal-birth.i','deck_sha256'),('assess.py','assessor_sha256')]:
     self.assertEqual((case/name).read_bytes(),(DONOR/name).read_bytes())
     self.assertEqual(sha(case/name),row[key])
    self.assertEqual(sha(case/'case-contract.json'),row['case_contract_sha256'])
    self.assertEqual(sha(case/'time-level.i'),row['time_input_sha256'])
    self.assertEqual((case/'time-level.i').read_text(),f"[Executioner]\n  dt = {row['dt_s']}\n[]\n")
    self.assertEqual(contract['selected_level_only'],level)
    self.assertEqual(contract['level_input_sha256'],{str(level):row['time_input_sha256']})
    self.assertEqual(contract['time_level_inputs'],{str(level):(case/'time-level.i').read_text()})
    self.assertEqual(contract['card'],original['card'])
    self.assertEqual(contract['card']['selected_time_level'],2)
    self.assertEqual(contract['historical_card_selected_time_level'],2)
    self.assertEqual(contract['assessor_sha256'],row['assessor_sha256'])
    self.assertEqual(round(contract['card']['end_time_s']/row['dt_s']),row['expected_native_steps'])
    self.assertEqual(round(contract['card']['birth_time_s']/row['dt_s']),row['birth_step'])
    restored=json.loads(json.dumps(contract));restored.pop('historical_card_selected_time_level')
    for key in ['scope','selected_level_only','level_input_sha256','time_level_inputs']:restored[key]=original[key]
    self.assertEqual(restored,original)
    self.assertTrue(all(contract[k] is False for k in ['native_execution_authorized','head_execution_authorized','manufacturing_authorized']))
 def test_only_CASE_and_receipt_level_change_all_callbacks_preserved(self):
  original=(MAC_DONOR/'run_mac.py').read_text()
  oldfunc={n.name:ast.dump(n,include_attributes=False) for n in ast.parse(original).body if isinstance(n,ast.FunctionDef)}
  for row in EXPECTED:
   with self.subTest(level=row['level']):
    source=ROOT/row['Mac']/'run_mac.py';body=source.read_text()
    self.assertEqual(sha(source),row['source_sha256'])
    oldcase='CASE = ENGINEERING / "cp1-assumed-thermal-birth-linear-prep-001"'
    newcase=f'CASE = ENGINEERING / "{Path(row["case"]).name}"'
    oldlevel='level=2 if stage == "coupon" else None'
    newlevel=f'level={row["level"]} if stage == "coupon" else None'
    self.assertEqual((body.count(newcase),body.count(newlevel)),(1,1))
    self.assertEqual(body.replace(newcase,oldcase).replace(newlevel,oldlevel),original)
    functions={n.name:ast.dump(n,include_attributes=False) for n in ast.parse(body).body if isinstance(n,ast.FunctionDef)}
    self.assertEqual([n for n in oldfunc if functions[n]==oldfunc[n]],row['eight_function_ASTs_exact'])
    normalized={n.name:ast.dump(n,include_attributes=False) for n in ast.parse(body.replace(newlevel,oldlevel)).body if isinstance(n,ast.FunctionDef)}
    self.assertEqual(normalized,oldfunc)
    held=json.loads((ROOT/row['Mac']/'held-preparation.json').read_text())
    oldheld=json.loads((MAC_DONOR/'held-preparation.json').read_text())
    for key in ['runtime_sha256s','runtime_symlinks','coupon_resources']:self.assertEqual(held[key],oldheld[key])
    self.assertEqual(held['case_reference_contract']['sha256'],row['case_contract_sha256'])
    self.assertEqual(held['selected_time_level'],row['level'])
    method=ROOT/row['Mac']/'METHOD.md'
    self.assertEqual(method.read_bytes(),(PREP/'METHOD.md').read_bytes())
    self.assertEqual(held['input_sha256'][str(method.relative_to(ROOT))],sha(method))
    self.assertEqual(held['planned_coupon_output'],str(ROOT/row['planned_native_output']))
    self.assertIsNone(held['actual_contract']);self.assertIsNone(held['native_output'])
    self.assertFalse(held['native_launch_authorized'] or held['coupon_solve_authorized'] or held['guard_execution_authorized'])
 def test_existing_mock_guard_two_binding_reversals_only(self):
  original=(MAC_DONOR/'selfcheck.py').read_text();oldsha=sha(MAC_DONOR/'run_mac.py')
  originalclasses={n.name:ast.dump(n,include_attributes=False) for n in ast.parse(original).body if isinstance(n,ast.ClassDef)}
  for row in EXPECTED:
   with self.subTest(level=row['level']):
    path=ROOT/row['Mac']/'selfcheck.py';body=path.read_text()
    self.assertEqual(sha(path),row['mock_sha256'])
    old='self.assertEqual(r["level"], 2)';new=f'self.assertEqual(r["level"], {row["level"]})'
    self.assertEqual((body.count(row['source_sha256']),body.count(new)),(1,1))
    restored=body.replace(row['source_sha256'],oldsha).replace(new,old)
    self.assertEqual(restored,original)
    self.assertEqual({n.name:ast.dump(n,include_attributes=False) for n in ast.parse(restored).body if isinstance(n,ast.ClassDef)},originalclasses)

if __name__=='__main__':main()
