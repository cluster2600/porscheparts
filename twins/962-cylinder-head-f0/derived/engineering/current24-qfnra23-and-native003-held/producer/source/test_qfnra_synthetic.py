"""HELD/UNRUN pure synthetic source; no solver/process/current-head evaluation."""
from fractions import Fraction
from pathlib import Path
import ast
import hashlib
import importlib.util
import unittest

ROOT = Path('/Users/maxime/.codex/worktrees/962-faithful-displacements/3dprinting993/work/962-engineering')
PREP = ROOT/'head-star-current24-coupled-qfnra-prep-001'
SOURCES = {
    'qfnra_emitter.py': ('5d76ef8218843ef92c83d64db3e5d9b0d8d1f6523d95aecdfa53b99dc569cd7b',36312),
    'qfnra_protocol.py': ('9b5885a35bfbc681c0354e937b9f57621b3d8137adc25b4e2ba455e86ce59785',12459)}
MODEL = '0'*64
COORDINATE = dict(component_ID=2,node_tag=101,axis=0,symbol='c002_n101_x')
X = COORDINATE['symbol']


def load_pure(name):
    data = (PREP/name).read_bytes()
    digest,size = SOURCES[name]
    if len(data)!=size or hashlib.sha256(data).hexdigest()!=digest:
        raise ValueError('Frozen pure source changed')
    spec = importlib.util.spec_from_file_location(name[:-3]+'_held',PREP/name)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ExactOracle:
    """Synthetic exact value only. Never owns a process or solver interface."""
    def __init__(self, protocol, value, sqrt_two=False):
        self.p=protocol;self.value=value;self.sqrt_two=sqrt_two;self.calls=[]
    def linear(self, term):
        if term==X:return (1,Fraction()) if self.sqrt_two else (0,Fraction(self.value))
        if term==['-',X]:return (-1,Fraction()) if self.sqrt_two else (0,-Fraction(self.value))
        return 0,self.p.rational_value(term)
    def __call__(self, request):
        if set(request)!={'model_id','term','command'} or request['model_id']!=MODEL:
            raise AssertionError('Wrong retained synthetic model')
        if request['command']!='(get-value ('+request['term']+'))':
            raise AssertionError('Wrong exact Boolean request')
        self.calls.append(request)
        op,left,right=self.p.parse_sexpr(request['term'])
        a,b=self.linear(left);c,d=self.linear(right)
        coefficient,constant=a-c,b-d
        if coefficient==0:
            sign=(constant>0)-(constant<0)
        else:
            if coefficient not in (-1,1):raise AssertionError('Unsupported synthetic expression')
            bound=-constant/coefficient
            if bound<=0:root_sign=1
            else:root_sign=(Fraction(2)>bound*bound)-(Fraction(2)<bound*bound)
            sign=coefficient*root_sign
        return {'<':sign<0,'<=':sign<=0,'=':sign==0,'>':sign>0,'>=':sign>=0}[op]


class QFNRASyntheticGuards(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.e=load_pure('qfnra_emitter.py')
        cls.p=load_pure('qfnra_protocol.py')

    def roots(self,seeds=(4,),conn=(1,2,3,4)):
        dag=self.e.IntegerDAG()
        baseline={1:(0,0,0),2:(1,0,0),3:(0,1,0),4:(0,0,1)}
        points={t:[dag.variable('n%d_%d'%(t,a)) if t in seeds else dag.integer(v)
                   for a,v in enumerate(row)] for t,row in baseline.items()}
        roots=self.e.cell_roots(dag,conn,points,set(seeds))
        values=dag.evaluate({'n%d_%d'%(t,a):v for t,row in baseline.items() if t in seeds
                            for a,v in enumerate(row)})
        return dag,roots,values

    def test_01_strict_bytes_JSON_and_held_input_refusal(self):
        for data in (b'{"a":1,"a":2}',b'{"a":NaN}'):
            with self.subTest(data=data),self.assertRaises(ValueError):self.e.strict_json(data)
        with self.assertRaisesRegex(ValueError,'Exact accepted edge intake contract'):
            self.e.admit_current({},b'{}')
        held=(ROOT/'head-star-current24-edge-removal-prep-001/held-preparation.json').read_bytes()
        with self.assertRaisesRegex(ValueError,'Exactly23'):
            self.e.admit_current({},held)

    def test_02_uniform_dyadic_normalization_preserves_context_and_homogeneous_gate(self):
        context=dict(points={1:(-0.0,0.,0.),2:(.125,0.,0.),3:(0.,.125,0.),4:(0.,0.,.125)})
        norm=self.e.integer_normalization(context)
        self.assertEqual((norm['power_of_two_exponent'],norm['scale_integer']),(3,'8'))
        self.assertEqual(norm['integers'],{1:(0,0,0),2:(1,0,0),3:(0,1,0),4:(0,0,1)})
        self.assertEqual(context['points'][1][0].hex(),'-0x0.0p+0')
        _,roots,values=self.roots()
        D,S,T,P=(values[roots[n]] for n in ('D','S','T','P'))
        self.assertEqual((D,S,T,P),(1,9,6,3546))
        native_D=Fraction(1,8**3);native_S=Fraction(9,8**2);native_T=Fraction(6,8**4)
        self.assertEqual(Fraction(P,8**6),3600*native_D**2-native_S*native_T)
        self.assertEqual(Fraction(36*D*D,S*T),Fraction(2,3))

    def test_03_native_orientation_planarity_and_one_two_seed_degrees(self):
        for seeds in ((4,),(3,4)):
            with self.subTest(seeds=seeds):
                _,roots,values=self.roots(seeds)
                self.assertLessEqual(roots['maximum_total_degree'],4 if len(seeds)==1 else 6)
                self.assertEqual(values[roots['D']],1)
        _,roots,values=self.roots((4,),(4,1,2,3))
        self.assertEqual(values[roots['D']],-1)
        dag,roots,_=self.roots()
        for height,expected in ((0,0),(-1,-1)):
            values=dag.evaluate({'n4_0':0,'n4_1':0,'n4_2':height})
            self.assertEqual(values[roots['D']],expected)
            self.assertFalse(values[roots['D']]>0)

    def test_04_integer_DAG_constants_and_exact_untested_solver_plan(self):
        dag=self.e.IntegerDAG();zero=dag.integer(0)
        self.assertEqual(dag.nodes[dag.binary('*',zero,dag.integer(7))]['value'],'0')
        self.assertEqual(dag.nodes[dag.binary('-',zero,zero)]['value'],'0')
        block=dict(component_ID=2,variables=[dict(symbol=X)],nodes=[dict(op='integer',value='0')],
                   predicates=[dict(name='strict_zero',root=0,relation='>',integer_rhs='0')])
        text=self.e.smt_block(block)
        self.assertIn('(assert (! (> d_c002_0 0) :named strict_zero))',text)
        self.assertIn(':zero_accuracy 0',text);self.assertIn(':randomize false',text)
        self.assertIn('(set-logic QF_NRA)',text)
        self.assertEqual(self.e.SOLVER_PLAN['argv'],['/opt/homebrew/bin/z3','-in','-smt2'])
        self.assertFalse(self.e.SOLVER_PLAN['unique_or_cross_version_model_claim'])

    def test_05_exact_status_and_complete_rational_algebraic_projection(self):
        self.assertEqual([self.p.parse_status(x) for x in ('sat','unsat','unknown')],['sat','unsat','unknown'])
        rows=self.p.parse_projection('((a (/ (- 1.0) 2.0)) (b (root-obj (+ (^ x 2) (- 2)) 2)))',
                                     ['a','b'],'sat')
        self.assertEqual(rows[0]['value'],dict(kind='rational',numerator='-1',denominator='2'))
        self.assertEqual(rows[1]['value']['kind'],'solver_algebraic_root_term')
        for text,status,names in [('((a 1))','unknown',['a']),('((a 1) (a 2))','sat',['a','b']),
                                 ('((b 1))','sat',['a']),('((a 1.4?))','sat',['a'])]:
            with self.subTest(text=text),self.assertRaises(ValueError):self.p.parse_projection(text,names,status)

    def test_06_single_complete_response_and_error_or_approximation_refusal(self):
        for text in ('sat unsat','(sat','(error "synthetic failure")','|quoted|','a;comment'):
            with self.subTest(text=text),self.assertRaises(ValueError):self.p.parse_sexpr(text)
        for term in (['/','1','0'],['sqrt','2'],'1.2?'):
            with self.subTest(term=term),self.assertRaises(ValueError):self.p.rational_value(term)
        with self.assertRaisesRegex(ValueError,'32MiB'):
            self.p.parse_sexpr('a'*(self.p.CAP+1))

    def test_07_exact_same_model_boolean_query_association(self):
        term='(<= '+X+' (/ 1 2))'
        self.assertTrue(self.p.parse_boolean('(((<= '+X+' (/ 1.0 2.0)) true))',term,'sat'))
        for response,status in [('(((< '+X+' (/ 1 2)) true))','sat'),
            ('(((<= '+X+' (/ 1 2)) 1))','sat'),('(((<= '+X+' (/ 1 2)) true))','unknown')]:
            with self.subTest(response=response),self.assertRaises(ValueError):
                self.p.parse_boolean(response,term,status)

    def test_08_rational_ties_even_and_negative_subnormal_zero(self):
        cases=[(Fraction(1),0x3ff0000000000000),
               (Fraction(1)+Fraction(1,2**53),0x3ff0000000000000),
               (Fraction(1)+Fraction(3,2**53),0x3ff0000000000002),
               (Fraction(1,2**1075),0),(-Fraction(1,2**1075),1<<63)]
        for value,word in cases:
            with self.subTest(value=str(value)):
                oracle=ExactOracle(self.p,value)
                record=self.p.nearest_binary64(COORDINATE,1,MODEL,oracle)
                self.assertEqual(record['word_u64'],word)
                self.assertEqual(record['events'][0]['request']['model_id'],MODEL)
                self.assertLessEqual(record.get('rank_decisions',0),63)

    def test_09_subnormal_normal_and_exponent_word_boundaries(self):
        self.assertEqual(self.p.positive_word_value(1),Fraction(1,2**1074))
        self.assertEqual(self.p.positive_word_value(0x3ff0000000000000),Fraction(1))
        for lower,upper in ((0x000fffffffffffff,0x0010000000000000),
                            (0x3fefffffffffffff,0x3ff0000000000000)):
            midpoint=(self.p.positive_word_value(lower)+self.p.positive_word_value(upper))/2
            result=self.p.nearest_binary64(COORDINATE,8,MODEL,ExactOracle(self.p,8*midpoint))
            self.assertEqual(result['word_u64'],upper)
            self.assertEqual(result['bracket']['relation'],'tie_to_even')

    def test_10_algebraic_model_uses_exact_comparison_oracle_not_decimals(self):
        result=self.p.nearest_binary64(COORDINATE,1,MODEL,ExactOracle(self.p,None,sqrt_two=True))
        self.assertEqual(result['word_u64'],0x3ff6a09e667f3bcd)
        self.assertFalse(result['real_model_feasibility_implies_rounded_gate'])
        self.assertFalse(result['application_authorized'])

    def test_11_a_real_feasible_interval_does_not_validate_the_rounded_word(self):
        lower=Fraction(1)
        upper=lower+Fraction(1,2**52)
        real=(lower+upper)/2
        self.assertTrue(lower<real<upper)
        result=self.p.nearest_binary64(COORDINATE,1,MODEL,ExactOracle(self.p,real))
        actual=self.p.positive_word_value(result['word_u64'])
        self.assertEqual(actual,lower)
        self.assertFalse(lower<actual<upper)

    def test_12_unavailable_nonboolean_or_out_of_range_oracle_refuses(self):
        def missing(request):raise RuntimeError('synthetic unavailable')
        with self.assertRaises(self.p.MappingRefusal) as caught:
            self.p.nearest_binary64(COORDINATE,1,MODEL,missing)
        self.assertEqual(len(caught.exception.events),1)
        with self.assertRaises(self.p.MappingRefusal):
            self.p.nearest_binary64(COORDINATE,1,MODEL,lambda request:1)
        too_large=self.p.positive_word_value(self.p.MAX_POSITIVE_WORD)+1
        with self.assertRaises(self.p.MappingRefusal):
            self.p.nearest_binary64(COORDINATE,1,MODEL,ExactOracle(self.p,too_large))

    def test_13_incomplete_mapping_never_materializes_a_partial_subset(self):
        context=dict(points={},words={},cells={},poor=set(),seeds=set(),protected_cells=set(),
                     protected_nodes=set(),intake={},classification_rows=[])
        admitted=dict(context=context,context_before=self.e.context_snapshot(context),blocks=[])
        with self.assertRaisesRegex(ValueError,'Exactly48'):
            self.e.word_proposal(admitted,[])

    def test_14_source_reuse_and_no_process_or_implicit_execution_entrypoint(self):
        donor=(ROOT/'head-star-current24-edge-removal-prep-001/propose_saved_edge_removal.py').read_text()
        proposed=(PREP/'qfnra_emitter.py').read_text()
        a,b=ast.parse(donor),ast.parse(proposed)
        for name in ('coordinate_rows','need','typed_hash','current_faces','prepare_context','oriented_boundary','context_snapshot'):
            old=next(n for n in a.body if isinstance(n,ast.FunctionDef) and n.name==name)
            new=next(n for n in b.body if isinstance(n,ast.FunctionDef) and n.name==name)
            self.assertEqual(ast.get_source_segment(donor,old),ast.get_source_segment(proposed,new))
            self.assertEqual(ast.dump(old,include_attributes=False),ast.dump(new,include_attributes=False))
        for filename in SOURCES:
            tree=ast.parse((PREP/filename).read_text())
            self.assertFalse(any(isinstance(n,(ast.Import,ast.ImportFrom)) and 'subprocess' in ast.unparse(n)
                                 for n in ast.walk(tree)))
            self.assertFalse(any(isinstance(n,ast.If) and '__name__' in ast.unparse(n.test) for n in tree.body))
            self.assertFalse(any(isinstance(n,ast.Call) and isinstance(n.func,ast.Name)
                                 and n.func.id in ('exec','eval','compile','open') for n in ast.walk(tree)))


if __name__=='__main__':
    unittest.main(verbosity=2)
