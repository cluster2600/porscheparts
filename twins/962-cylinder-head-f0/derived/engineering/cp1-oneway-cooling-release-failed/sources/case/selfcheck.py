"""UNRUN finite source/data guards; no MOOSE, runtime query or actual solve."""
import ast,copy,hashlib,json,math
from decimal import Decimal,localcontext
from pathlib import Path
import tempfile,unittest

PREP=Path(__file__).resolve().parent
SOURCE=PREP/"prepare_continuation.py"
SOURCE_SHA="a2b61fde2968229861145ce1c99d22896ac15284843b3843760ae1702241e218"
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==SOURCE_SHA
TEXT=SOURCE.read_text();TREE=ast.parse(TEXT);DEFS={n.name:n for n in TREE.body if isinstance(n,ast.FunctionDef)}
NS={"math":math,"Decimal":Decimal,"localcontext":localcontext,"Path":Path,"hashlib":hashlib}
exec(compile(ast.Module(body=[DEFS[n] for n in ["need","read_fixed_grid","extend_cooling","table_text"]],type_ignores=[]),
             "<fixed-table-guard-only>","exec"),NS)

class Guards(unittest.TestCase):
    def test_exact_temporal_schedule_and_own_birth_reference(self):
        c=json.loads((PREP/"card.json").read_text())
        self.assertEqual((c["time"]["dt_s"],c["time"]["steps"],c["time"]["birth_step"]),(.0025,182,80))
        self.assertEqual((c["prescribed_cooling"]["starts_after_END_step"],c["prescribed_cooling"]["ends_at_END_step"]),(160,180))
        self.assertEqual(c["loading"]["temporary_build_clamp"]["release_BEGIN_step"],181)
        self.assertFalse(c["prescribed_cooling"]["is_heat_equation_solution"])
        self.assertEqual(c["birth"]["old_constant_stress_free_temperature_K"],400)
        self.assertIn("BEGIN80",c["birth"]["born_stress_free_temperature"])
        self.assertEqual(c["birth"]["restore_overridden_dofs"],[True,True,True,True,False])

    def test_complete_original_prefix_and_cooling_endpoint(self):
        tokens=[format(350+(i%225)/225,".17g") for i in range(161*225)]
        result=NS["extend_cooling"](tokens,161)
        self.assertEqual(result[:len(tokens)],tokens);self.assertEqual(len(result),41175)
        self.assertEqual(result[-675:],["300"]*675)
        for j in range(20):
            values=list(map(float,result[len(tokens)+j*225:len(tokens)+(j+1)*225]))
            self.assertTrue(all(300<=v<=351 for v in values))
        with self.assertRaises(ValueError):NS["extend_cooling"](tokens[:-1],161)
        with self.assertRaises(ValueError):NS["extend_cooling"](tokens,160)

    def test_grid_header_axes_counts_and_raw_tokens_remain_strict(self):
        axes=(("X",(0.,)),("Y",(0.,)),("Z",(0.,)),("T",(0.,.0025)))
        tokens=["-0","3.0000000000000001e2"]
        body=NS["table_text"](axes,tokens)
        self.assertEqual(NS["read_fixed_grid"](body,axes,2),tokens)
        for bad in [body.replace("AXIS X","AXIS Q"),body+"300\n",body.replace("-0\n","nan\n"),body.replace("DATA\n","DATA\n\n")]:
            with self.assertRaises(ValueError):NS["read_fixed_grid"](bad,axes,2)

    def test_no_original_CSV_conversion_or_padded_cooling_reference(self):
        source=SOURCE.read_text()
        self.assertNotIn("csv.DictReader",source)
        self.assertIn('"born-begin80.grid":reference',source)
        self.assertIn('"original_tokens_preserved":54675',source)
        self.assertIn('"new_assumed_cooling_hold_values":9900',source)
        self.assertIn('range(183)',source);self.assertIn('range(80,183)',source)
        self.assertIn('reference=(SOURCE/"born-begin80.grid").read_bytes()',source)

    def test_temporary_clamp_and_rigid_constraints_do_not_overlap(self):
        deck=(PREP/"thermoelastic-birth.i").read_text()
        self.assertEqual(deck.count("type = TimePeriod"),1)
        self.assertIn("start_time = 0.4525",deck)
        self.assertIn("reverse_on_false = true",deck)
        self.assertIn("set_sync_times = true",deck)
        self.assertIn("disable_objects = 'BCs/build_x BCs/build_y BCs/build_z'",deck)
        for name in ["origin_x","origin_y","origin_z","axis_x_y","axis_x_z","axis_y_z"]:
            block=deck.split("  ["+name+"]",1)[1].split("  []",1)[0]
            self.assertIn("enable = false",block)
        self.assertIn("new_boundary = build_clamp",deck)
        self.assertIn("input = axis_y",deck)
        self.assertIn("end_time = 0.455",deck)

    def test_material_IC_and_full_tensor_capture_unchanged(self):
        old=(PREP.parent/"cp1-oneway-thermoelastic-transfer-prep-002/thermoelastic-birth.i").read_text()
        new=(PREP/"thermoelastic-birth.i").read_text()
        self.assertEqual(old[old.index("[Materials]"):old.index("[Preconditioning/full]")],
                         new[new.index("[Materials]"):new.index("[Preconditioning/full]")])
        for marker in ["[ICs]","[AuxKernels]","[MeshModifiers/birth]"]:
            following={"[ICs]":"[AuxKernels]","[AuxKernels]":"[MeshModifiers/birth]","[MeshModifiers/birth]":"[BCs]"}[marker]
            self.assertEqual(old[old.index(marker):old.index(following)],new[new.index(marker):new.index(following)])
        self.assertNotIn("type = IsotropicPlasticityStressUpdate",new)

    def test_resources_and_honest_held_authorities(self):
        h=json.loads((PREP/"held-preparation.json").read_text())
        self.assertEqual(h["coupon_resources"],{"wall_seconds":100,"sampled_RSS_stop_bytes":2147483648,"sampled_output_stop_bytes":536870912})
        self.assertIsNone(h["native_actual"]);self.assertIsNone(h["completed_continuation_data"])
        self.assertIsNone(h["independent_3D_assessment"]["source"])
        for k in ["data_preparation_authorized","native_launch_authorized","coupon_solve_authorized","guard_execution_authorized",
                  "head_authorized","engineering_accepted","physics_qualified","material_qualified","process_calibrated",
                  "manufacturing_authorized","automatic_retry"]:
            self.assertIs(h[k],False)
        self.assertEqual(h["required_selected_runtime_features"][-1],"TimePeriod")

    def test_data_authority_fails_before_any_output(self):
        source=ast.unparse(DEFS["prepare"])
        self.assertIn("data_preparation_authorized",source)
        self.assertIn("root_and_peer_review_complete",source)
        self.assertLess(source.index("checked_pins(pins)"),source.index("OUTPUT.mkdir()"))
        self.assertNotIn("subprocess",TEXT);self.assertNotIn("numpy",TEXT)
        self.assertIn('pins.get(str((PREP / \'held-preparation.json\').relative_to(ROOT)))',source)

if __name__=="__main__":unittest.main()
