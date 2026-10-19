"""Exact Fraction restriction of the stored post-Build spline; no native operation."""
from fractions import Fraction as Q
import hashlib,json,math,os,time,unittest
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
def require(ok,message):
    if not ok:raise ValueError(message)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def add(a,b):return [(a[i]if i<len(a)else Q(0))+(b[i]if i<len(b)else Q(0))for i in range(max(len(a),len(b)))]
def affine(a,b,p):
    out=[Q(0)]*(len(p)+1)
    for i,x in enumerate(p):out[i]+=a*x;out[i+1]+=b*x
    return out
def restrict(poles,knots,mults,degree,lo,hi):
    require(type(degree)is int and degree>=0 and len(knots)==len(mults)and len(knots)>=2,'Spline sizes/degree differ')
    require(all(type(m)is int and m>0 for m in mults)and all(a<b for a,b in zip(knots,knots[1:])),'Invalid ordered knots/multiplicities')
    require(knots[0]<=lo<hi<=knots[-1]and not any(lo<k<hi for k in knots),'One physical knot span required')
    expanded=[k for k,m in zip(knots,mults)for _ in range(m)];require(len(expanded)==len(poles)+degree+1,'Expanded knot/pole sizes differ');mid=(lo+hi)/2
    def basis(i,p):
        if p==0:return [Q(int(expanded[i]<=mid<expanded[i+1]))]
        out=[Q(0)];left=expanded[i+p]-expanded[i];right=expanded[i+p+1]-expanded[i+1]
        if left:out=add(out,affine((lo-expanded[i])/left,(hi-lo)/left,basis(i,p-1)))
        if right:out=add(out,affine((expanded[i+p+1]-lo)/right,-(hi-lo)/right,basis(i+1,p-1)))
        return out
    bs=[basis(i,degree)for i in range(len(poles))];partition=[Q(0)];result=[Q(0)]
    for pole,b in zip(poles,bs):partition=add(partition,b);result=add(result,[pole*x for x in b])
    require(partition==[Q(1)]+[Q(0)]*degree,'Exact basis partition is not unity')
    return result+[Q(0)]*(degree+1-len(result))
def cubic_bernstein(c):return [c[0],c[0]+c[1]/3,c[0]+2*c[1]/3+c[2]/3,sum(c)]
class Tests(unittest.TestCase):
    def test_smoothstep(self):self.assertEqual(restrict(list(map(Q,[0,0,1,1])),list(map(Q,[0,1])),[4,4],3,Q(0),Q(1)),list(map(Q,[0,0,3,-2])))
    def test_extended_constant(self):self.assertEqual(restrict([Q(1)]*5,list(map(Q,[-2,0,1])),[4,1,4],3,Q(0),Q(1)),list(map(Q,[1,0,0,0])))
    def test_extended_linear_Greville(self):
        k=list(map(Q,[-2,0,1]));full=[k[0]]*4+[k[1]]+[k[2]]*4;pol=[sum(full[i+1:i+4])/3 for i in range(5)];self.assertEqual(restrict(pol,k,[4,1,4],3,Q(0),Q(1)),list(map(Q,[0,1,0,0])))
    def test_rational_physical_subspan(self):self.assertEqual(restrict(list(map(Q,[0,0,1,1])),list(map(Q,[0,1])),[4,4],3,Q(1,3),Q(2,3)),[Q(7,27),Q(4,9),Q(1,9),Q(-2,27)])
    def test_crosses_knot(self):
        with self.assertRaises(ValueError):restrict([Q(1)]*5,list(map(Q,[-2,0,1])),[4,1,4],3,Q(-1),Q(1))
    def test_wrong_sizes(self):
        with self.assertRaises(ValueError):restrict([Q(0)]*4,list(map(Q,[0,1])),[4,3],3,Q(0),Q(1))
def main():
    start=time.monotonic();r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests));require(r.wasSuccessful(),'Small exact restriction fixtures failed')
    folder=HERE.with_name('bounded-webs-C1-terminal-taper-prototype-preparation-001');source=folder/'output-001/assessment.json';terminal=folder/'terminal-collection-001.json';observer=HERE.with_name('bounded-webs-C1-terminal-law-observation-preparation-001')/'output-001/assessment.json'
    pins={str(p.relative_to(ROOT)):sha(p)for p in [source,terminal,observer,Path(__file__)]};require(sha(source)=='e3ce58a25667cac0be400d90105720db9dddebbd997e501aac93c7fa4529d690'and sha(terminal)=='4e0aac4f3d64eb3d107221c71350317ca5a64276069539123f4be9f597a49ed3','Closed actual prototype authority differs')
    actual=json.loads(source.read_text());old=json.loads(observer.read_text());row=actual['post_Build_laws'][0];require(row['native_degree']==3 and row['native_rational']is False and row['native_periodic']is False,'Actual cubic polynomial spline required')
    require(all(type(x)is float and math.isfinite(x)for x in row['native_poles']+row['native_knots']+actual['physical_edge431_abscissae_mm']),'Finite stored IEEE coefficients required')
    poles=list(map(Q,row['native_poles']));knots=list(map(Q,row['native_knots']));lo,hi=map(Q,actual['physical_edge431_abscissae_mm']);c=restrict(poles,knots,row['native_multiplicities'],3,lo,hi);bern=cubic_bernstein(c);wanted=list(map(Q,[0,0,3,-2]));difference=[x-y for x,y in zip(c,wanted)]
    dstart=c[1]/(hi-lo);dend=(c[1]+2*c[2]+3*c[3])/(hi-lo);other_same=actual['post_Build_laws'][1:]==old['simulated_laws'][1:];require(other_same,'Other six actual native law records differ')
    report=dict(schema='post-Build-C1-spline-exact-physical-restriction-1',status='exact_posthoc_restriction_computed_original_refusal_unchanged',native_or_geometry_executed=False,small_stdlib_tests=r.testsRun,source_law=row,all_other_six_native_records=actual['post_Build_laws'][1:],all_other_six_equal_closed_observer=other_same,coefficient_model='Exact rationals of stored finite IEEE poles/knots, not rounded native Value/D1 evaluations',physical_interval_Q=list(map(str,[lo,hi])),extended_law_domain_Q=list(map(str,[knots[0],knots[-1]])),normalized_parameter='t=(s-lo)/(hi-lo), 0<=t<=1',physical_power_coefficients_Q=list(map(str,c)),physical_Bernstein_coefficients_Q=list(map(str,bern)),smoothstep_power_coefficients_Q=list(map(str,wanted)),difference_from_smoothstep_Q=list(map(str,difference)),identical_to_requested_smoothstep=c==wanted,physical_endpoint_values_Q=list(map(str,[c[0],sum(c)])),physical_endpoint_derivatives_per_mm_Q=list(map(str,[dstart,dend])),physical_Bernstein_hull_bounds_Q=list(map(str,[min(bern),max(bern)])),Bernstein_hull_proves_0_to_1=min(bern)>=0 and max(bern)<=1,physical_start_value_sign=(c[0]>0)-(c[0]<0),physical_start_derivative_sign=(dstart>0)-(dstart<0),native_raw_D1=row['native_endpoint_D1'],native_raw_D1_parameter_scope='Endpoints of the extended law domain, not the physical start0',candidate_qualified=False,original_RC1_and_law_gate_preserved=True,no_tolerance_or_threshold_changed=True,files_sha256=pins,elapsed_seconds=time.monotonic()-start)
    require({p:sha(ROOT/p)for p in pins}==pins,'Closed sources changed during analysis')
    out=HERE/'assessment.json'
    with out.open('x')as f:json.dump(report,f,indent=2,allow_nan=False);f.write('\n');f.flush();os.fsync(f.fileno())
    print(json.dumps(dict(status=report['status'],assessment_sha256=sha(out),identical_to_smoothstep=c==wanted,physical_power_coefficients_float=list(map(float,c)),physical_Bernstein_float=list(map(float,bern)),physical_endpoint_values_float=[float(c[0]),float(sum(c))],physical_endpoint_D1_float=[float(dstart),float(dend)],Bernstein_hull_proves_0_to_1=report['Bernstein_hull_proves_0_to_1'])))
if __name__=='__main__':main()
