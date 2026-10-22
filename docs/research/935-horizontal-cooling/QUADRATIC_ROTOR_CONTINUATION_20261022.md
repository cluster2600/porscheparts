# 935 rotor: preserved boundary and first complete quadratic calculation

The root README's order is retained observations → reviewed PicoGK master →
independent geometry and assembly checks → calculation meshes → reference
solvers → convergence and measurements. This continuation advances the rotor's
calculation mesh and structural diagnostics on the Mac and Kali1 over Thunderbolt.
No additional paid instance is created.

The [machine-readable receipt](quadratic-rotor-20261022.json) binds source hashes,
native executions and [private evidence](https://github.com/cluster2600/porscheparts-935-private/releases/tag/analysis-mesh-935-20261022).
The earlier [surface correction and refused volumes](ANALYSIS_MESH_CONTINUATION_20261022.md)
remain unchanged.

## Surface and volume

The [source patch](../../../twins/935-horizontal-cooling-system-f0/source/analysis-simplification/protected-input-patches-20261022.patch)
protects three topological rings around inherited input facets below mean ratio
0.05 before simplifying elsewhere. Native controls exercise the poor facet,
its neighbour and a disconnected good facet; the closed cube remains on its
original planes with unit volume. The preceding implementation and its receipts
are retained.

The actual float32 surface contains **436,712 vertices and 873,444 triangles**.
The unchanged independent checker verifies both directions against every original
PicoGK triangle, including topology and self-intersections, at the original
**0.0225 uncalibrated-unit bound**, retaining its 0.0025-unit reserve.

Unmodified upstream TetGen **1.5.1** completes in **13.31 seconds**, after its
analytic tetrahedron control. The independent audit checks **436,838 nodes and
1,426,554 tetrahedra**: zero inverted or exactly flat cells, one connected body,
exact boundary-coordinate/triangle bijection and relative volume difference
2.22e-16 from the analysis surface. TetGen 1.6 still aborts; that attempt is
preserved separately.

All-cell diagnostics nevertheless find a minimum tetrahedron mean ratio of
**3.62237e-6** and a maximum Jacobian condition number of **8.32013e7**.
Positive volume does not establish suitable mechanical element quality.

An additional 1.5.1 refinement finishes with 685,514 nodes and 2,952,749 cells.
All parent node coordinates remain exact, but **124,915 boundary triangles are
replaced**, despite the requested `-Y` option. The exact boundary gate refuses
reuse of the surface certificate. No solver is run on that proposal.
[TetGen refinement and preservation options](https://www.wias-berlin.de/software/tetgen/1.5/doc/manual/manual005.html).
The separate Mac Netgen hybrid-volume control passes, but its rotor trial
segfaults after 40.24 seconds and supplies no accepted mesh.

## Matched structural calculations

The retained preparer produces C3D4 and straight-sided C3D10 decks from the
unchanged-boundary volume. It verifies the whole-simplex Jacobian for every
quadratic cell. No cell is refused; the complete numerical-coordinate transport
bound is **2.79846e-14 native units**, below the existing 1e-9 budget.

These are linear-elastic centrifugal hypotheses: AlSi10Mg, 6,000 rpm, Poisson
ratio 0.33, **assumed** 1 mm per scan unit and a rigid numerical bore band.
Neither scale nor the support/contact model is measured. Air pressure, thermal
loads, transmission loads, fatigue and plasticity are absent.

| Quantity | C3D4, Mac | C3D10, Mac |
|---|---:|---:|
| Nodes | 436,838 | 2,736,957 |
| Elements | 1,426,554 | 1,426,554 |
| Audited integration points | 1,426,554 | 5,706,216 |
| Maximum displacement, assumed mm | 0.092667 | 0.309288 |
| Peak elastic von Mises, assumed MPa | 2,240.96 | 1,643.10 |
| Element-peak stress p95 outside assumed r=25 mm | 26.6108 | 36.5515 |

The quadratic solve completes in **676 seconds**, peaking at **37.77 GiB** under
a 48 GiB limit. Every requested displacement, support reaction and integration
point is present and finite. Relative force and discrete-moment balance errors
are 7.06536e-10 and 5.17547e-9. The independent equilibrium checks pass.

The repeated C3D4 calculation on Kali agrees with the Mac: the largest global
normalized field difference is **6.435e-7**, below the declared 1e-5 numerical
comparison limit. The formulation comparison also uses one Mac binary for both
element types. The quadratic maximum displacement is **3.3376 times** the linear
value. The outside-bore stress statistic differs by **27.20%** relative to the
quadratic result. Both peak stresses occur in the worst-quality tetrahedron.

This is a numerical sensitivity finding, not a converged stress, strength or
usable-speed result. Agreement between computers and force balance cannot
establish mesh convergence. The previous material/speed projections remain
historical conditional studies; this calculation does not qualify those alloys
for manufacture.

## Next steps in the README chain

1. Improve local analysis-mesh quality while preserving or independently
   recertifying the complete boundary. Retain rejected meshes and every repair.
2. Run a quadratic spatial-refinement series on at least three meshes with the
   same declared geometry, loads and support rule. Check non-singular stresses,
   displacements and subsequent prestressed modes against their convergence
   criteria. A P1/P2 comparison is not an h-refinement series.
3. Prepare the MRF/k–omega SST pilot for the qualified OpenFOAM runtime. The
   existing generator targets OpenCFD v2406; it cannot simply be relabelled for
   the qualified rootless Foundation 13 environment. The Poiseuille witness is
   not accepted rotor CFD.
4. Continue the 17-interface and hidden-transmission definition alongside
   conditional studies. The observed drive exterior and six-cylinder engine
   packaging placeholder do not define a complete historical mechanism.
5. Use accepted reference results for SciPy/OpenMDAO optimization; evaluate
   PhysicsNeMo only after a suitable independently tested dataset exists.

The USD/Omniverse assembly remains a presentation and inspection branch.
Historical fit, full-mechanism function, process qualification, fatigue,
balancing and bench validation remain open. Manufacturing is not authorized.
