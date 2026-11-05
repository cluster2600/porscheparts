# Compliant-support case

This figure reads back the fields of the real elastic computation
`combined-spring-1000-static`, 7 mm mesh, from pass `run-001`.
The solver was not rerun. The ten inputs, including the five computation
files and the three graphical outputs, are bound by their SHAs in
`provenance.json`; their identities were cross-checked against the executed steps
of the original workflow.

Both views and their legends were inspected. The deformed shape is amplified
×10; the stresses in MPa and the displacement colours in mm remain
real. The 1,000 N/mm is the total stiffness per eyelet and per axis, distributed
among the nodes, not a stiffness applied in full to each node.

The elastic peak of 1,676.55 MPa and the displacement of 18.2486 mm describe this
comparison case. The figure does not replace a material strength decision.
The SVG keeps the original Matplotlib bytes, including their trailing
whitespace, in order to preserve its identity.
