# Figure 31: current complete-law coarse FEA fields

Source-only proposal. No extraction, graphics import, plot or solver is executed
by this preparation. The two current 07b354 cases have their own closed owner
and ROOT evidence; no old C1 or terminal-taper result is transferred.

The plot keeps the existing actual-field renderer and its literal boundary-value,
camera, projection, connectivity and all-tie functions. Two columns compare rigid
and K1000 ends; stress and true displacement ×1 use common scales, camera and
millimetre axes. Every actual boundary corner facet is submitted without
decimation. The stress colour is the largest of four integration-point values
in each boundary-adjacent element, with no nodal extrapolation. The global table
and markers retain every global IP tie, including any larger interior value.
Displacement colours use each facet's largest corner value; the separate global
maximum and markers include every mesh node, including midsides.

The current mesh has 166,263 nodes and 89,485 C3D10 elements. The four applied-load
bolt groups each contain 528 nodes. End groups each contain 2,274 nodes. Rigid
ends constrain 13,644 DOFs; K1000 has 13,644 SPRING1 elements and means exactly
1,000 N/mm total per eye and axis, not per node. Fz = −4,000 N and
My = +850,000 N·mm, E = 107,000 MPa and ν = 0.31 are retained. All whole load,
case, energy and global-peak reports remain joined to their own native results.

The two 50 mm XY inset windows are display crops around the actual negative-X
rigid and positive-X K1000 peaks. They do not remove any field or global peak.
The table shows global IP von Mises and all-node displacement maxima separately
from the rendered boundary maximum. These are coarse-mesh support-model results;
stress convergence has not been established.

The installed 219-file plotting runtime and SYSTEM Python 3.10 −B command are
reused. The child keeps OS user-site behaviour, then sets cwd=/ before plotting.
Resources are 180 seconds outer, a 150-second child alarm, CPU 140/141, nice 10
once, BLAS 1 and zero Python workers. Three exports and a full render receipt
are proposed. ROOT must review the source/pins/tests and issue a separate render
GO. Publication and repository edits are outside this preparation.
