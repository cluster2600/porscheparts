"""Separate exact-P2 CAD-reference nonregression; never rewrite historical volume verdicts."""
from fractions import Fraction
import math,struct

def require(value,message):
    if not value:raise ValueError(message)

def exact(record):
    require(set(record)=={'numerator','denominator','binary64_observation'},'Complete exact volume record required')
    require(type(record['numerator'])is type(record['denominator'])is str,'Exact integer strings required')
    n,d=int(record['numerator']),int(record['denominator']);require(d>0,'Positive denominator required');q=Fraction(n,d)
    require(str(q.numerator)==record['numerator']and str(q.denominator)==record['denominator'],'Canonical reduced exact ratio required')
    require(type(record['binary64_observation'])is float and math.isfinite(record['binary64_observation'])and float(q)==record['binary64_observation'],'Stored approximate display differs')
    return q

def record(q):
    q=Fraction(q);return dict(numerator=str(q.numerator),denominator=str(q.denominator),binary64_observation=float(q))

def evaluate(certificates,CAD_reference):
    require(type(CAD_reference)is float and math.isfinite(CAD_reference)and CAD_reference>0,'Original finite positive binary64 CAD reference required')
    require(set(certificates)=={'coarse-INP','refined-INP','coarse-NPZ','refined-NPZ'},'Both complete INP and NPZ coordinate representations required')
    reference=Fraction.from_float(CAD_reference);rows={}
    for representation in ['INP','NPZ']:
        values=[]
        for role in ['coarse','refined']:
            cert=certificates[role+'-'+representation]
            require(cert['identifier']==role+'-'+representation and cert['coordinate_representation']==representation,'Coordinate certificate identity differs')
            require(cert['complete_quadratic_certificate']['cell_boundary_integrals_exactly_equal']is True,'Complete signed T10/T6 identity required')
            q=exact(cert['exact_signed_T10_T6_volume_mm3']);require(q>0,'Positive whole signed P2 volume required');values.append(q)
        coarse,refined=values;left,right=abs(coarse-reference),abs(refined-reference)
        rows[representation]=dict(coarse_exact_P2_mm3=record(coarse),refined_exact_P2_mm3=record(refined),coarse_signed_error_to_closed_CAD_reference_mm3=record(coarse-reference),refined_signed_error_to_closed_CAD_reference_mm3=record(refined-reference),coarse_absolute_error_mm3=record(left),refined_absolute_error_mm3=record(right),change_in_absolute_error_mm3=record(right-left),exact_P2_CAD_nonregression_passed=right<=left)
    return dict(schema='current24af-exact-P2-CAD-reference-nonregression-1',metric='abs(refined exact signed P2 volume minus original closed CAD binary64 reference) <= abs(coarse exact signed P2 volume minus the same reference)',reference=dict(original_binary64_mm3=CAD_reference,float_hex=CAD_reference.hex(),binary64_big_endian_hex=struct.pack('>d',CAD_reference).hex(),exact_ratio_of_observation=record(reference),mathematically_exact_true_CAD_volume_claimed=False),coordinate_representations=rows,both_exact_P2_CAD_nonregression_passed=all(row['exact_P2_CAD_nonregression_passed']for row in rows.values()),epsilon=None,original_generated_and_saved_zero_refusals_unchanged=True,exact_geometry_invariance_claimed=False,compiler_error_bound_claimed=False,physical_injectivity_claimed=False,qualification_by_volume_alone=False)
