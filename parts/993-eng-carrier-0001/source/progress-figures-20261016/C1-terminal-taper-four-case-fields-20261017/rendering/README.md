# Four closed taper cases: coarse and raw refined diagnostic

This separate English figure preparation compares four actual closed CalculiX cases on the same native BREP `dde710a2…`: rigid/coarse, rigid/raw-refined diagnostic, K1000/coarse and K1000/raw-refined diagnostic. Figure27 and its published source/evidence remain unchanged.

| Case | Global IP von Mises (MPa) | All-node displacement (mm) | Relative energy closure error |
| --- | ---: | ---: | ---: |
| Rigid / coarse | 697.312504283443 | 2.7940146926593 | 4.35143698851448e-09 |
| Rigid / raw refined diagnostic | 1218.07201448292 | 2.79438777963836 | 3.33820171505295e-09 |
| K1000 / coarse | 1977.80995060341 | 18.1702011842863 | 1.98886085378547e-09 |
| K1000 / raw refined diagnostic | 3716.03897959036 | 18.1727012456233 | 7.31804616904697e-09 |

The original whole coarse ROOT15c76 and raw-refined diagnostic ROOT9e0dd are separate checked authorities. Each case retains its complete closed assessment, native receipt, mesh/field identity, load/support record, energy report and every global IP tie. Both meshes use the same full load/support records: Fz=−4000 N, My=+850000 N·mm, E=107000 MPa, ν=0.31; K1000 is 1000 N/mm total per eye and axis, distributed over the retained 2274/2278 node sets.

The new source derives from the actual Figure27 renderer5be01. Five functions are byte-literal/AST unchanged: `maxima_record`, `boundary_values`, `camera_basis`, `project`, `elements`. The four field-loading/identity/IP blocks retain the original calculations. The declared source delta changes the two-context proof joins and presentation: two rows by four columns, one common stress scale and one common displacement scale, common millimetre axes/camera and true deformation ×1. All boundary corner facets are drawn. Stress colours are the maximum of the four actual IP values in the adjoining boundary element; the global IP peak remains a separate all-element measurement. Displacement colours use the largest facet-corner magnitude; the global displacement maximum includes all nodes and midsides.

Each display-only inset uses the same 50×25 mm window centred on that actual case's peak. In particular, the rigid peak migrates from negative X in the coarse result to positive X in the raw-refined result; no assumed mirror maps one field onto the other. All global peak markers and their complete records remain present.

The refined results remain diagnostic. Their strict H2 volume refusal, the native taper's original post-Build law refusal and the independent STEP exchange refusal remain unchanged. The figure does not establish H2 qualification, stress convergence, a strength allowable, physical fit or manufacturing qualification. No CAD, mesh, field, force, moment or threshold changes.

This freeze is source-only and NON-ARMED. The stdlib fixtures read only closed JSON metadata. No NumPy/Matplotlib import, field-array read or image rendering occurred. Existing closed receipts supply the large-file hashes in the pending pin map; preparation does not claim a new full hash pass over those fields or runtime files. Future execution must freshly verify every pin under a separate ROOT GO.

Proposed execution: original attested Python3.10/219-file plotting runtime, existing4d18 supervisor, 180 seconds outer with10+10cleanup, 150-second child alarm, CPU140–141, child nice10 once, BLAS1 and0workers. Four cases are held for common scales; actual RSS must be reported and no hard RSS guarantee is claimed. Planned PNG/SVG/PDF names are `carrier-terminal-taper-four-case-comparison.*`. No image export hashes exist yet. The figure archive should reference raw evidence rather than duplicate the full fields.
