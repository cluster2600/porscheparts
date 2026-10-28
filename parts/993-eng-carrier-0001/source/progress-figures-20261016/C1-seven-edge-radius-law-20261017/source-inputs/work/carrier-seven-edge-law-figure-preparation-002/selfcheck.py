"""Small stdlib trust-boundary tests; no plotting, CAD or scientific imports."""
from pathlib import Path
import copy,importlib.util,json,sys,unittest
H=Path(__file__).resolve().parent;R=H.parents[1]
def load(name,path):
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
m=load('_law_figure_source',H/'figure.py')
context=R/'work/carrier-process-20261017/bounded-webs-C1-full-contour-native-observer-preparation-001'
review=json.loads((context/'root-terminal-review-001.json').read_bytes());terminal=json.loads((context/'terminal-collection-001.json').read_bytes())
contract=load('_existing_exact_contract',R/'work/carrier-process-20261017/bounded-webs-C1-full-contour-law-contract-preparation-001/law_contract.py')
data=m.select_data(review,terminal)
class Checks(unittest.TestCase):
    def test_closed_data_whole(self):self.assertEqual(m.read(H/'law-data.json'),data)
    def test_full_native_function_proof(self):
        requested,proof=m.validate_data(data,contract);self.assertEqual(requested['poles'],[0.,0.,1.,1.,1.,1.]);self.assertEqual(len(proof['edges']),7)
    def test_foreign_owner_refuses(self):
        r=copy.deepcopy(review);r['owner_terminal_sha256']='0'*64
        with self.assertRaises(ValueError):m.select_data(r,terminal)
    def test_stock_final_curve_refuses(self):
        d=copy.deepcopy(data);d['stock']['post_Build_laws']=[]
        with self.assertRaises(ValueError):m.validate_data(d,contract)
    def test_fake_stock_native_result_refuses(self):
        t=copy.deepcopy(terminal);t['variants']['stock-rebuilt']['whole_final_native_laws']=[]
        with self.assertRaises(ValueError):m.select_data(review,t)
    def test_native_coefficient_mutation_refuses(self):
        d=copy.deepcopy(data);d['patched']['whole_final_native_laws'][0]['native_poles'][2]=.5
        with self.assertRaises(ValueError):m.validate_data(d,contract)
    def test_missing_physical_interval_refuses(self):
        d=copy.deepcopy(data);d['patched']['whole_post_Build_physical_source_edges'].pop()
        with self.assertRaises(ValueError):m.validate_data(d,contract)
    def test_forged_exact_proof_refuses(self):
        d=copy.deepcopy(data);d['patched']['whole_final_exact_function_proof']['global_physical_radius_bounds_Q']=['0','2']
        with self.assertRaises(ValueError):m.validate_data(d,contract)
    def test_foreign_raw_BREP_authority_refuses(self):
        t=copy.deepcopy(terminal);t['variants']['patched']['raw_BREP_sha256']='0'*64
        with self.assertRaises(ValueError):m.select_data(review,t)
    def test_display_samples_not_a_proof(self):
        _,p=m.validate_data(data,contract);x,y,w=m.visual_samples(p,81);self.assertEqual(len(x),7*81);self.assertEqual((x[0],y[0],y[-1]),(0.,0.,1.));self.assertEqual(y,w)
        with self.assertRaises(ValueError):m.visual_samples(p,80)
    def test_existing_pure_helpers_literal(self):
        m.literal_helpers(R,dict(pure_helpers_source='work/carrier-terminal-taper-four-case-figure-preparation-001/figure.py',literal_helper_names=['require','sha','read','write','fresh']))
    def test_no_plot_or_CAD_imports(self):
        self.assertFalse(any(n.split('.')[0]in['numpy','matplotlib','PIL','OCP','build123d']for n in sys.modules))
if __name__=='__main__':unittest.main()
