# FIA dimensions applied to the PicoGK prototype

The FIA form and its transcriptions were already in the repository. The
previous prototype did not use its piston pin axis–crown dimension: 22 mm
instead of the published 43 mm. This step of 11 October 2026 corrects that
omission and makes the provenance of the dimensions used explicit.

## Source reread and reuse of Git

The [official form no. 250](https://historicdb.fia.com/sites/default/files/car_attachment/1601078401/homologation_form_number_250_group_4.pdf)
was downloaded again, then its pages 8 and 14 were inspected visually.
Its SHA-256 matches the existing register:
`92a03ecef96a68cd227d0ef9f5f7413a7519a04ef24796330fbee4874b2226cd`.
The PDF and its captures remain private in `work/`.

The transcriptions already present are reused:
[source register](../../../catalog/sources/src-fia-917-homologation-250.json),
[F13 facts](../../../twins/reference-917-engine/classical-solver-cases-f13.json),
[F35 dimensions](../../../twins/reference-917-engine/rotating-assembly-cad-f35.json)
and [F29 measurement matrix](../../../archive/917/docs/917_GERMAN_SOURCE_AND_MEASUREMENT_MATRIX_F29.md).
The [reread record](source-review.json) fixes pages, fields, units,
variant and digests. None of these earlier contracts is modified.

| FIA reference for the 4.494 L | Page / field | Application |
|---|---|---|
| Bore 85 mm, stroke 66 mm | 8 / 133–134 | geometric parameters and kinematics |
| Piston pin axis–crown distance 43 mm | 8 / 146 | prototype crown placed at +43 mm from the axis |
| Bearing/crankpin diameter 52 mm | 8 / 158 | crankpin reference; connecting rod bore at 54 mm with a radial bearing shell of 1 mm **assumed** |
| Connecting rod 0.42 ± 0.02 kg | 8 / 163 | inertia comparison with the prototype's computed masses |
| Piston + pin + rings 0.46 ± 0.02 kg | 8 / 164 | complete reference group, never treated as the mass of the piston alone |

Field 159 at 56 mm remains excluded: its label is ambiguous in the existing
contracts. It provides neither the outside diameter of the big end nor the
dimension of the machined bore. Extension 1/1E, page 14, gives 86 × 70.4 mm
for the 4.907 L; it is recorded separately and is not applied to this
configuration. The historical label « Boxer » in field 132 does not by itself
define the crankpin pairing; the topology and phasing of the prototype remain
hypotheses to be checked against the crankshaft.

## Geometry re-executed

[The configuration](reference-assumptions.json) is checked by
[run.py](run.py), then sent to the PicoGK generator of
[the previous experiment](../hypothesis/README.md). Its sources and their
digests remain intact: a new execution and a new record are created. The four
families and the 48 instances are recomputed at the 1 and 0.5 mm grids; the
STL/VDB files and the assembly remain private.

The preserved generator represents a piston symmetric about its axis.
To apply +43 mm to the crown, this experiment also chooses **43 mm of skirt
below the axis**: an additional hypothesis, not an FIA dimension. The computed
total height of 86 mm must therefore not be attributed to the form. An
asymmetric definition waits for the skirt dimension and its profile. The big
end outside diameter of 72 mm comes from the F35 hypothesis; the 54 mm bore is
computed from 52 mm and the assumed bearing shell thickness.

This correction exposes a useful inconsistency: the provisional cylinder
remains placed from 70 to 192 mm from the crankshaft axis. With the assumed
connecting rod centre distance of 132 mm, the crown reaches 208 mm at TDC.
The conservative criterion of complete axial coverage of the skirt gives
−16 mm and **rejects this layout**. Centre distances of 120 and 144 mm give
−26 and −28 mm under the same hypotheses.
This does not prove a defect in the Porsche engine: cylinder position, skirt,
cylinder head and deck reference of the prototype are not measured. These
values are not artificially lengthened to make the check pass.

The [execution record](execution-20261011.json) keeps the audits, masses,
probes and qualification gates. A mesh screen or a sampled clearance does not
validate this layout nor its complete swept volume.

## Loads and material

The FIA masses give a nominal reciprocating mass of 0.600 kg under the
unchanged hypothesis of one third of the connecting rod in translation.
Combining the declared intervals by sum of extremes, it varies from 0.5733 to
0.6267 kg. Nine pressure/speed scenarios are recomputed for this documentary
group, alongside the eighteen scenarios based on the prototype's volumes and
densities. The FIA masses are not transferred to the new titanium/aluminium
parts: their geometry and material differ.

At an assumed 8,000 rpm and 80 bar, this group gives 45.40 kN of gas force
and 17.37 kN of nominal inertia. The sum of the independent peaks varies from
61.99 to 63.54 kN with the mass intervals. This is neither a measured
combustion cycle nor evidence of the connecting rod's strength.

The form states light alloys and a hard-chrome cylinder coating, without
qualifying AlSi10Mg or Ti6Al4V. The additive candidates of the previous
dossier remain choices to study; they are not confirmed Porsche grades.
Combustion pressure, connecting rod mass fraction, assembly tolerances,
high-temperature strength, fatigue and final process remain to be
established.

```bash
PYTHON=/chemin/vers/python-avec-dependances-scientifiques
DOTNET=/chemin/vers/dotnet-9
"$PYTHON" models/917-engine-reconstruction/fia/run.py \
  --output work/917-fia/nouvelle-execution --dotnet "$DOTNET"
"$PYTHON" tests/test_917_picogk_fia.py -v
```

The documentary dimensions are available and applied to the model. They do
not by themselves establish the identity or scale of the scan, the undescribed
interiors, the machining tolerances or a manufacturing qualification.

The 17 targeted tests of the three steps pass, including the digest check and
the rejection of mixed variants. Compilation completes with no error or
warning. `make check` runs 3,631 tests, 153 skipped, then stops on the two
exact floating-point comparisons already reproduced in the unchanged 993
impeller/stator files; the following targets are not reached locally.
Markdown links are checked separately. The zero return code of this
experiment means that the diagnostic was executed, not that its rejected
layout is accepted. Read `source-review-status.json` and the FIA report, in
addition to the status of the geometry subprogramme.
