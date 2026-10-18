"""Prepared UNRUN stdlib/Decimal and selected-AST guards; no native/scientific use."""
from pathlib import Path
import ast,copy,hashlib,itertools,json,math,unittest
from decimal import Decimal,localcontext

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
SOURCE=HERE/'assess.py'
SOURCE_SHA='0548fcbf6eba737aaaf816abbfbfd0511b5b8fb266aa10c34a1f5817eef0e338'
DONOR=ROOT/'twins/962-cylinder-head-f0/source/physics_witness/thermal_birth'
DONOR_SHA='41cf5f8f027b8ce44dab9808b52ef6b6432ccaaa9b50e3136da54cbef0d55c88'
if hashlib.sha256(SOURCE.read_bytes()).hexdigest()!=SOURCE_SHA or hashlib.sha256((DONOR/'assess.py').read_bytes()).hexdigest()!=DONOR_SHA:
    raise ValueError('Exact separately reviewed assessor and immutable donor required')
TREE=ast.parse(SOURCE.read_text())
FUNCTIONS={n.name:n for n in TREE.body if isinstance(n,ast.FunctionDef)}
NAMES=['grid','centered_enthalpy_increment','source_value','box_power','gaussian_cell_average']
NS={'math':math,'itertools':itertools}
exec(compile(ast.Module(body=[FUNCTIONS[k] for k in NAMES],type_ignores=[]),str(SOURCE), 'exec'),NS)
CARD=json.loads((HERE/'card.json').read_text())
def field(xmax,fn):
    result={}
    for lo,h,corners in NS['grid'](CARD,xmax):
        for p in corners:result[p]=fn(p)
    return result
def decimal_increment(begin,end,xmax):
    with localcontext() as ctx:
        ctx.prec=80
        value=Decimal(0)
        for lo,h,corners in NS['grid'](CARD,xmax):
            volume=math.prod(h)
            value+=Decimal.from_float(volume)/8*sum((Decimal.from_float(end[p])-Decimal.from_float(begin[p]) for p in corners),Decimal(0))
        return float(Decimal.from_float(CARD['density_kg_m3'])*Decimal.from_float(CARD['cp_at_300K_J_kgK'])*value)

class ConstantThermalGuards(unittest.TestCase):
    def test_constant_card_deck_time_and_tolerances(self):
        old=json.loads((DONOR/'card.json').read_text())
        self.assertEqual(CARD['predeclared_tolerances'],old['predeclared_tolerances'])
        for k in ['bounds_m','mesh_intervals','old_region_xmax_m','birth_time_s','end_time_s','time_steps_s','initial_temperature_K','birth_temperature_K','enthalpy_reference_K','laser_power_W','efficiency','factor','radii_m','source_start_m','velocity_m_s']:
            self.assertEqual(CARD[k],old[k],k)
        self.assertEqual([CARD[k] for k in ['density_kg_m3','cp_at_300K_J_kgK','cp_slope_J_kgK2','k_at_300K_W_mK','k_slope_W_mK2']],[2700.,900.,0.,187.,0.])
        self.assertEqual(CARD['selected_time_level'],2)
        self.assertEqual((HERE/'time-level.i').read_text(),'[Executioner]\n  dt = 0.0025\n[]\n')
        self.assertEqual(round(CARD['end_time_s']/CARD['time_steps_s'][2]),160)
        deck=(HERE/'thermal-birth.i').read_text()
        for text in ["expression = '900+0*(t-300)'","expression = '187+0*(t-300)'",'prop_values = 2700','precision = 17','type = ADMatHeatSource','times = 0.2','restore_overridden_dofs = true']:
            self.assertEqual(deck.count(text),1,text)

    def test_exact_case_guard_refuses_changed_binding(self):
        gate=next(n for n in FUNCTIONS['assess'].body if isinstance(n,ast.If) and 'Only the separately frozen assumed constant thermal card' in ast.unparse(n))
        code=compile(ast.Module(body=[gate],type_ignores=[]),str(SOURCE),'exec')
        exec(code,{'card':copy.deepcopy(CARD)})
        for key,value in [('density_kg_m3',1),('cp_at_300K_J_kgK',901),('cp_slope_J_kgK2',.01),('k_at_300K_W_mK',186),('id','wrong')]:
            bad=copy.deepcopy(CARD);bad[key]=value
            with self.assertRaises(ValueError):exec(code,{'card':bad})

    def test_centered_uniform_small_increment_decimal(self):
        begin=field(2.,lambda p:400.)
        end={p:v+2**-25 for p,v in begin.items()}
        actual=NS['centered_enthalpy_increment'](CARD,end,begin,2.)
        self.assertEqual(actual,decimal_increment(begin,end,2.))
        self.assertGreater(actual,CARD['predeclared_tolerances']['corrected_step_energy_absolute_J'])
        self.assertEqual(actual,2700*900*2*2**-25)

    def test_nonuniform_increment_decimal_and_curved_cp_refusal(self):
        begin=field(2.,lambda p:400.+p[0]/8)
        end={p:v+(1+round(p[0]*8)+round(p[1]*4)+round(p[2]*4))*2**-30 for p,v in begin.items()}
        actual=NS['centered_enthalpy_increment'](CARD,end,begin,2.)
        reference=decimal_increment(begin,end,2.)
        self.assertLessEqual(abs(actual-reference),2*math.ulp(reference))
        bad=copy.deepcopy(CARD);bad['cp_slope_J_kgK2']=.01
        with self.assertRaises(ValueError):NS['centered_enthalpy_increment'](bad,end,begin,2.)

    def test_birth_shared_field_has_no_fictitious_step_heat(self):
        begin=field(2.,lambda p:400. if p[0]<=1 else 350.)
        self.assertTrue(all(v==400 for p,v in begin.items() if p[0]==1))
        self.assertEqual(NS['centered_enthalpy_increment'](CARD,dict(begin),begin,2.),0.)
        donor=ast.parse((DONOR/'assess.py').read_text())
        old_assess=next(n for n in donor.body if isinstance(n,ast.FunctionDef) and n.name=='assess')
        old_birth=next(n for n in ast.walk(old_assess) if isinstance(n,ast.If) and ast.unparse(n.test)=='step == birth_step')
        new_birth=next(n for n in ast.walk(FUNCTIONS['assess']) if isinstance(n,ast.If) and ast.unparse(n.test)=='step == birth_step')
        self.assertEqual(ast.dump(new_birth,include_attributes=False),ast.dump(old_birth,include_attributes=False))

    def test_source_normalization_and_omitted_PDE_source_refused(self):
        self.assertEqual(2*CARD['factor']*CARD['efficiency']*CARD['laser_power_W'],40.)
        time=CARD['time_steps_s'][2]
        power=NS['box_power'](CARD,time,1.)
        qh=math.fsum(NS['gaussian_cell_average'](CARD,lo,h,time)*math.prod(h) for lo,h,corners in NS['grid'](CARD,1.))
        self.assertTrue(0<power<40 and 0<qh<40)
        call=next(n for n in ast.walk(FUNCTIONS['assess']) if isinstance(n,ast.Call) and n.args and isinstance(n.args[0],ast.Constant) and n.args[0].value=='nonlinear_BE_enthalpy_identity')
        expression=compile(ast.Expression(body=call.args[1]),str(SOURCE),'eval')
        defect=eval(expression,{'delta_h':0.,'dt':time,'qh':qh,'correction':0.})
        self.assertGreater(abs(defect),CARD['predeclared_tolerances']['corrected_step_energy_absolute_J'])

    def test_continuous_error_cannot_be_hidden_by_birth_inventory(self):
        assignment=next(n for n in ast.walk(FUNCTIONS['assess']) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='relative' for t in n.targets))
        code=compile(ast.Expression(body=assignment.value),str(SOURCE),'eval')
        relative=eval(code,{'defect':-3.,'incoming':3.,'birth_energy':1e8})
        self.assertEqual(relative,-1.)
        self.assertGreater(abs(relative),CARD['predeclared_tolerances']['finest_continuous_energy_relative'])

    def test_all_eleven_other_oracle_functions_are_unchanged(self):
        donor={n.name:n for n in ast.parse((DONOR/'assess.py').read_text()).body if isinstance(n,ast.FunctionDef)}
        names=set(donor)-{'assess'}
        self.assertEqual(len(names),11)
        for name in names:self.assertEqual(ast.dump(FUNCTIONS[name],include_attributes=False),ast.dump(donor[name],include_attributes=False),name)

if __name__=='__main__':unittest.main()
