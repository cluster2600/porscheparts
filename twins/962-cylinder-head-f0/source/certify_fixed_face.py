"""Exact rational necessary SICN screen for one binary64 fixed linear triangle."""
import argparse
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path

FAMILY=Path(__file__).resolve().parents[1]
ROOT=FAMILY.parents[1]


def rational(value):
    return dict(numerator=str(value.numerator),denominator=str(value.denominator))


def certificate(coordinates):
    if len(coordinates)!=3 or any(len(row)!=3 for row in coordinates):
        raise ValueError("Exactly three 3D binary64 coordinates required")
    if not all(math.isfinite(float(x)) for row in coordinates for x in row):
        raise ValueError("Finite binary64 coordinates required")
    p=[[Fraction.from_float(float(x)) for x in row] for row in coordinates]
    u=[p[1][k]-p[0][k] for k in range(3)]
    v=[p[2][k]-p[0][k] for k in range(3)]
    cross=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]]
    cross_squared=sum(x*x for x in cross)
    edge_sum=sum((p[a][k]-p[b][k])**2 for a,b in [(0,1),(1,2),(2,0)] for k in range(3))
    if cross_squared<=0 or edge_sum<=0:
        raise ValueError("Nondegenerate linear triangle required")
    left,right=2700*cross_squared,edge_sum**2
    return dict(arithmetic="Fraction.from_float preserves each input binary64 value exactly; all following operations are rational.",
        cross_squared_mm4=rational(cross_squared),sum_squared_edge_lengths_mm2=rational(edge_sum),
        exact_triangle_SICN_squared=rational(12*cross_squared/right),
        exact_loose_tetra_SICN_squared_upper_bound=rational(27*cross_squared/right),
        inequality_left_2700_cross_squared=rational(left),inequality_right_edge_sum_squared=rational(right),
        exact_strict_inequality_2700_cross_squared_lt_edge_sum_squared=bool(left<right),
        no_positive_linear_tetrahedron_with_this_fixed_face_can_reach_SICN_point1=bool(left<right),
        no_square_root_or_floating_tolerance_used=True)


def run(output):
    import numpy as np
    if output.exists() or output.is_symlink():raise ValueError("Output directory must be new")
    output.mkdir(parents=True);(output/"source-executed.py").write_bytes(Path(__file__).read_bytes())
    source=ROOT/"work/962-engineering/analysis-envelope-025-002/checkpoint-audit-001/analysis-surface.npz"
    sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
    before=sha(source);data=np.load(source);p,f=data["points_mm"],data["triangles"]
    xyz=p[f];u=xyz[:,1]-xyz[:,0];v=xyz[:,2]-xyz[:,0]
    cross_squared=np.einsum("ij,ij->i",np.cross(u,v),np.cross(u,v))
    length_sum=np.einsum("ij,ij->i",u,u)+np.einsum("ij,ij->i",v,v)+np.einsum("ij,ij->i",v-u,v-u)
    # This floating search chooses one face only. The acceptance decision below is exact.
    index=int(np.argmin(cross_squared/length_sum**2));nodes=f[index];coords=p[nodes]
    proof=certificate(coords.tolist())
    report=dict(schema="962-fixed-face-rational-certificate/v1",status="exact_fixed_face_tetra_SICN_point1_impossibility_proved" if proof["no_positive_linear_tetrahedron_with_this_fixed_face_can_reach_SICN_point1"] else "no_impossibility_certificate_for_selected_face",
        source_npz_path=str(source.relative_to(ROOT)),source_npz_sha256=before,
        selected_face_index_zero_based=index,selected_node_indices_zero_based=nodes.tolist(),
        coordinates_mm=coords.tolist(),coordinate_binary64_hex=[[float(x).hex() for x in row] for row in coords],
        coordinate_bytes_sha256=hashlib.sha256(np.asarray(coords,dtype="<f8").tobytes()).hexdigest(),
        certificate=proof,metric_definition_reference= json.loads((FAMILY/"source/gmsh_sicn_reference.json").read_text()),
        metric_definition_reference_sha256=sha(FAMILY/"source/gmsh_sicn_reference.json"),
        source_sha256=sha(Path(__file__)),all_source_inputs_unchanged=sha(source)==before,
        scope="One selected fixed linear triangle in the bound recovered8GiB checkpoint only. This does not apply after surface remeshing or to another head/analysis representation.",
        full_native_facet_coverage="The separately bound recovery receipt evaluated native minSICN on all1753570 imported fixed linear triangles, without facet subsampling. Its938 count is a floating diagnostic, not this exact certificate.",
        native_recovery_receipt_sha256=sha(source.parent/"receipt.json"),
        no_head_tetrahedra_generated=True,engineering_accepted=False,manufacturing_authorized=False)
    if not report["all_source_inputs_unchanged"]:raise ValueError("Bound candidate changed during exact proof")
    (output/"receipt.json").write_text(json.dumps(report,indent=2,allow_nan=False)+"\n")
    print(json.dumps({k:report[k] for k in ["status","selected_face_index_zero_based","coordinates_mm","certificate"]}))


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args();run(args.output)
