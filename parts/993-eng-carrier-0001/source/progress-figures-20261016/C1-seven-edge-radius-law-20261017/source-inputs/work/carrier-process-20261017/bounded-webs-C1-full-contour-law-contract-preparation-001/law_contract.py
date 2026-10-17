"""Exact full-contour polynomial law contract; no OCP import or native operation."""
import importlib.util,math
from fractions import Fraction as Q
from pathlib import Path
HERE=Path(__file__).resolve().parent
AUTHORITY=HERE.with_name('bounded-webs-C1-terminal-law-restriction-analysis-001')/'analyze.py'
spec=importlib.util.spec_from_file_location('_original_exact_spline_restriction',AUTHORITY)
EXACT=importlib.util.module_from_spec(spec);spec.loader.exec_module(EXACT)
IDS=[431,293,292,291,290,289,161]
VERTICES=[302,210,214,213,212,211,124,125]
def require(ok,message):
    if not ok:raise ValueError(message)
def intervals(physical):
    require([r['edge_index_zero_based']for r in physical]==IDS,'Complete ordered seven-edge source table required')
    result=[]
    for i,row in enumerate(physical):
        require('unavailable_reason'not in row and len(row['endpoints'])==2,'Complete fresh native endpoint observations required')
        require([r['vertex_index_zero_based']for r in row['endpoints']]==VERTICES[i:i+2],'Original complete physical endpoint chain required')
        values=[r['native_contour_abscissa_mm']for r in row['endpoints']]
        require(all(type(x)is float and math.isfinite(x)for x in values)and values[0]<values[1],'Finite ordered actual abscissae required')
        result.append(values)
    require(result[0][0]==0. and all(a[1]==b[0]for a,b in zip(result,result[1:])),'Whole native contour must be covered without gaps or overlaps')
    require(physical[0]['endpoints'][0]['vertex_index_zero_based']==302 and physical[-1]['endpoints'][-1]['vertex_index_zero_based']==125,'Original zero and opposite endpoint identities required')
    return result
def requested_spec(physical):
    spans=intervals(physical);a,b=spans[0];last=spans[-1][1]
    result=dict(degree=3,poles=[0.,0.,1.,1.,1.,1.],knots=[a,b,last],multiplicities=[4,2,4],periodic=False,rational=False)
    p=list(map(Q,result['poles']));k=list(map(Q,result['knots']))
    for i,(lo,hi)in enumerate(spans):
        actual=EXACT.restrict(p,k,result['multiplicities'],3,Q(lo),Q(hi));require(actual==list(map(Q,[0,0,3,-2]if i==0 else[1,0,0,0])),'Requested complete spline does not equal the specified piecewise polynomial')
    return result
def expected_subspan(lo,hi,target):
    a,b=target;alpha=(lo-a)/(b-a);beta=(hi-lo)/(b-a);out=[Q(0)]
    for coefficient in reversed([Q(0),Q(0),Q(3),Q(-2)]):out=EXACT.affine(alpha,beta,out);out[0]+=coefficient
    require(all(x==0 for x in out[4:]),'Unexpected higher-degree coefficient')
    return out[:4]
def validate_native(rows,physical):
    spans=intervals(physical);require([r['edge_index_zero_based']for r in rows]==IDS,'Every native edge law must be retained')
    target=list(map(Q,spans[0]));proof=[]
    for i,(row,(lower,upper))in enumerate(zip(rows,spans)):
        require('unavailable_reason'not in row and type(row['native_degree'])is int and row['native_degree']==3 and row['native_rational']is False and row['native_periodic']is False,'Complete nonrational nonperiodic cubic law records required')
        values=row['native_poles']+row['native_knots']+row['native_law_bounds'];require(all(type(x)is float and math.isfinite(x)for x in values),'Finite native encoded coefficients required')
        poles=list(map(Q,row['native_poles']));knots=list(map(Q,row['native_knots']));lo,hi=map(Q,[lower,upper]);bounds=list(map(Q,row['native_law_bounds']))
        require(knots[0]<=bounds[0]<=lo<hi<=bounds[1]<=knots[-1],'Native law domain must cover its complete fresh physical edge')
        cuts=[lo]+[k for k in knots if lo<k<hi]+[hi];pieces=[]
        for a,b in zip(cuts,cuts[1:]):
            got=EXACT.restrict(poles,knots,row['native_multiplicities'],3,a,b);wanted=expected_subspan(a,b,target)if i==0 else list(map(Q,[1,0,0,0]));require(got==wanted,'Exact native polynomial restriction differs from the complete requested function')
            pieces.append(dict(interval_Q=list(map(str,[a,b])),normalized_power_coefficients_Q=list(map(str,got))))
        proof.append(dict(edge_index_zero_based=IDS[i],physical_interval_Q=list(map(str,[lo,hi])),native_full_record=row,all_actual_knot_spans=pieces,restriction='cubic_smoothstep'if i==0 else'exact_constant_R1'))
    return dict(method='exact_Fraction_full_contour_cubic_smoothstep_then_six_R1_restrictions_1',edges=proof,whole_physical_contour_covered=True,zero_vertex302_value_Q='0',opposite_vertex125_value_Q='1',terminal_and_transition_first_derivatives_Q=['0','0'],global_physical_radius_bounds_Q=['0','1'],IsConstant_flags_not_used_as_functional_proof=True,geometry_qualified=False)
def make_native(physical,Law_BSpline,Law_BSpFunc,RealArray,IntegerArray):
    """Future native seam only; callers must first prove their isolated runtime."""
    s=requested_spec(physical)
    def array(cls,values):
        a=cls(1,len(values))
        for i,v in enumerate(values,1):a.SetValue(i,v)
        return a
    curve=Law_BSpline(array(RealArray,s['poles']),array(RealArray,s['knots']),array(IntegerArray,s['multiplicities']),3,False)
    return Law_BSpFunc(curve,s['knots'][0],s['knots'][-1]),s
