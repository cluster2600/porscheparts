# Repair-reference reader: held source revision001

This is preparation only. The new reader, pure helper and five tiny test methods
have not been imported or executed. No candidate arrays, NumPy/Gmsh/VTK/CGAL or
native geometry were loaded by this preparer. Only source/evidence text and
file hashes were inspected. Existing geometry and all earlier records remain
unchanged. Root must review sources/tests, run the tiny tests, materialize the
four exact source copies plus a separately authorized contract, verify fresh
resources and all pins, then decide whether to execute this read-only reader.

The future input is immutable d2af, 869355 vertices/1739126 faces. Existing209a
and8750 records supply the exact3112 poor-face IDs and incident-region identity.
The reader does not recalculate quality or choose a new poor threshold. It
AST-extracts only the retained `audit_quality_head.read` codec and marks loaded
point/face arrays read-only. The patch topology kernel and stopped-reader
controller are byte-identical copies856a/e0e. The pure new reference helper uses
stdlib Fraction.from_float, which represents each stored binary64 value exactly.

1. Reconstruct the exact incident mask and exterior-only fixed vertices; compare
   all mask bits with the legacy exterior-or-x=+/-76 mask and its frozen hash.
   Record every additional legacy fixed vertex. Compute the actual patch vertices
   not exterior-fixed and compare them with patch-minus-oriented-boundary IDs.
   Counts5938-2012=3926 are arithmetic expectations, not assumed mask equality.
2. Select the complete3508-face all-z=0 complex independently of the9872 repair
   region. Report every edge-connected cap component, face ownership in/out of
   the incident union, oriented boundary cycles, vertex links/Euler, point-only
   component contacts and exact rational winding signs. A bounded vectorized full
   face scan gathers both incident faces for every cap-boundary/region-boundary
   edge, including cap-component/poor/patch/plane-only ownership. Region cycles
   and cap cycles are separate records. This does not prove geometric void
   coverage, physical feature identity or permission to change the cap.
3. For each frozen poor triangle, order its three squared edge lengths using
   exact Fraction arithmetic and retain every equal minimum. Record the full
   exact numerator/denominator order and ties. Report two explicitly separate UF
   graphs: all tied minima, and exploratory lexicographic-first minimum per face.
   Neither is an accepted target policy. Every row is an existing triangle edge;
   no new length cutoff, welding, band or grid is introduced. A component has no
   necessary-only keeper candidates if any member is exterior-fixed (the old
   all-members-free quotient rule, conditional on later mask approval). Otherwise
   list every member, restricted to exact z=0 when any member belongs to the cap
   complex. No keeper is chosen. No normal, quality, link, neighbor, envelope or
   quotient admissibility is inferred from this list.

The fresh global-reference worker02c7/receipt29c2, root11a16 and peer07c3 are bound
as completed evidence: one component/Euler-208 and complete zero global
self-intersections on d2af. They do not approve this reader's mask/proposals or
remove the3112-poor-face rejection. This reader does not repeat those global
scientific checks. The fixed-mask and cap observations are descriptive only.

The proposed existing runtime is pinned ARM Python72956 with NumPy2.0.2;
no new NumPy extension-hash proof is claimed. Unchanged e0e controls are120s
wall deadline, sampled4GiB worker RSS stop and two library threads with protected
process-group kill/finally-wait. These are not hard OS memory/CPU quotas or a
certified peak. The output is JSON/log/receipt only; no geometry export, repair,
mesh generation/optimization, solver, API/network or Git operation exists.

Five prepared stdlib tests cover exact tied minima/lex separation, squared-length
underflow avoided by Fraction, all necessary keeper candidates/whole-component
fixed conflict, cap winding/plane refusal, and empty/malformed/nonfinite inputs.
They exercise the actual new pure helper, not a duplicate implementation. The
previous six topology-kernel tests are retained provenance only. Root runs tests;
this preparation reports no test pass or scientific result.
