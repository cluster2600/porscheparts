# 935 — correction of the blade 03 tip

The tip previously extended at constant profile now uses its own
acquired contours. The observed arcs of the incomplete sections are
kept; only their gaps are closed by local chords.
**The scan → candidate RMS deviation falls from 1.174 to 0.181 source units** over the
inspected zone. This correction concerns one blade, not the whole set of
historical interfaces nor the other eight tips.

The [numerical receipt](tip-correction-20261013.json) contains the digests,
checks and results. Geometries, sections, deviation maps, images, cases,
fields and rejected trials stay in the [private archive](https://github.com/cluster2600/porscheparts-935-private/releases/tag/tip-correction-20261013).
The computation runs on the Mac: native PicoGK `osx-arm64`, Gmsh in local Docker
under amd64 emulation, native Linux aarch64 CalculiX in local Docker.
No Vast rental and no 993/917 geometry are used.

## Why correct this zone

The displacement maximum of the three previous computations lay near
the extrapolated tip, beyond the last acquired profile at station 122.
Its association with blade 03 was angular, without exact segmentation of the
mechanical field. This signal justifies an inspection of the scan; it does not justify
thickening a blade to lower the displacement artificially.

The segmentation uses the connected components of the scan beyond radius
94 source units. Nine significant components are identified. Their
phases are compared with those of the existing profiles; only the component
corresponding to blade 03 supplies the new sections.

Two closed contours are recovered at stations 134 and 136. The observed
apex projected on the radial axis reaches 136.410. A closed section at
136.160 leaves a guard of 0.25 source unit. **Its terminal closure
remains artificial**, and this guard is not a machining tolerance.
File names do not fix the units; all results in mm
still assume 1 mm per source unit.

## Limited repair and rejected trial

A first trial interpolated contours 122 and 134 at stations
124…132. Its median was better, but its scan → candidate RMS rose
to 1.978 units and its maximum to 9.009: this interpolation cut through a
zone that is still observed. The candidate, its sources and its three computations are
kept as a rejected trial; they are not the retained correction.

The retained correction keeps all the end points of the acquired segments
of the five open sections: 124, 126, 128, 130 and 132. The seven missing
links measure 0.171 to 8.709 source units and remain bounded by an
explicit limit of 9. Additional points on each chord prevent
a free spline from curving the gap. Smoothing keeps the earlier
parameter of 0.025 and the 128 points per profile. The closed sections
receive no added link. The profiles are registered cyclically
between stations of this same blade.

Provenance distinguishes acquired closed contours, acquired arcs with
repair chords, and the artificial terminal closure. A chord
is not a measured surface. Interpolation between sections remains a
reconstruction; the original scan is never modified.

The other eight blades and all earlier profiles of blade 03 up to
122 are kept exactly. An independent audit of the 0.6 STLs compares
the triangles whose three vertices project before station 120:
**1,294,915 triangles have exactly the same coordinates and orientations**.
This local guard is not a global self-intersection audit.

## Geometry and deviations

PicoGK builds the profiles, the rotor and the fields at assumed resolutions
1.2, 0.6 and 0.3 mm. The three STLs have one component, are closed,
consistently oriented and contain no zero-area face.
Between the last two: volume +0.0724 %, maximum variation of the principal
inertias 0.1185 %. The 1 % numerical threshold is met for these
quantities; it does not qualify the scale or the historical dimensions.

The comparison uses 6,000 independent points, drawn by triangle
area, and the distance to the candidate's triangles. The observed zone is
the blade 03 component whose vertices all project beyond
124. The same points and seeds are used before/after.

| Direction and indicator, in source units | Old tip | Correction |
|---|---:|---:|
| Scan → candidate, RMS | 1.1745 | 0.1814 |
| Scan → candidate, median | 0.5117 | 0.0284 |
| Scan → candidate, P95 | 2.8048 | 0.3696 |
| Scan → candidate, sampled maximum | 5.3398 | 2.1017 |
| Candidate → open scan, RMS | 3.0160 | 0.3385 |
| Candidate → open scan, P95 | 6.4371 | 0.4417 |
| Candidate → open scan, sampled maximum | 8.1796 | 3.6653 |

The second direction includes the gaps in the scan: it does not measure
the accuracy of an absent surface. The extrema stay in the private
files; no general tolerance is inferred from the RMS alone. Views of the
rotor and its tip as well as six sections were inspected visually.

## Mechanical comparison

Three AlSi10Mg computations at 6,000 rpm reuse exactly the previous material law,
the assumed fixed support of the bore and the centrifugal loading.
The scale, the process and the real supports remain unqualified. Each
audit covers all nodes, the eight integration points of each C3D8
and the reactions of the fixed nodes. The force and moment balances pass.

| Assumed step, mm | Corrected elements | Old displacement, mm | Corrected displacement, mm | Reduction | Corrected max. von Mises, MPa |
|---|---:|---:|---:|---:|---:|
| 1.50 | 131,084 | 0.8156 | 0.5249 | 35.6 % | 144.38 |
| 1.35 | 177,185 | 0.9410 | 0.6036 | 35.9 % | 188.37 |
| 1.20 | 244,240 | 1.1604 | 0.7598 | 34.5 % | 197.46 |

The reduction is consistent at identical step, but the displacement still varies
by **25.9 % between the two finest meshes**: mechanical convergence is
refused. The maximum stress varies by 4.82 %, and the P95 of per-element peaks
outside r = 25 mm by 2.81 %. These two indicators do not offset
the displacement failure. No admissible speed is inferred from these values.
The fine-mesh results are also exported as discrete PicoGK VDB fields,
with their digests and a read-back check.

On the fine mesh, the maximum is now associated angularly with
blade 02, at station 128.9, within its acquired range. This association
is not an exact segmentation of the field; it does not justify
modifying this measured profile to make the computation pass.

## Reproduction

The [recovery program](../../../twins/935-horizontal-cooling-system-f0/source/recover_tip_sections.py)
takes a private case and a new output directory:

```sh
python recover_tip_sections.py tip-local-repair-case.json work/new-tip-sections
dotnet SectionLoft.dll work/new-tip-sections/sections.json SHA256 1 0.6 work/new-lofts
dotnet Assembly935.dll final-rotor-case.json SHA256 work/new-rotor
dotnet CandidateRotor.dll work/new-rotor/rotor_candidate.stl SHA256 0.6 work/new-grid 1.5,1.35,1.2
python prepare_candidate_fea.py final-fea-case.json work/new-fea
bash run_candidate_fea.sh work/new-fea/rotor.inp SHA256 work/new-solve
python assess_mac_fea.py work/new-fea work/new-solve work/new-assessment
dotnet MacStudy935.dll fea-fields fields-case.json work/new-fields
```

Each SHA256 is that of the immediately preceding argument; the cases
also fix and verify the digests of the dependencies. The C# sources and the
earlier preparation and audit tools remain unchanged. The executed cases and
scripts are archived with the necessary private inputs. For
the existing mechanical parser, `log.rotor` is a verified copy of
`ccx.log`, not a new run. The targeted tests cover
preservation, provenance and the rejection of invalid profiles.

## Next steps in qualification

The correction provides neither the real hub clamping, nor the shaft
interfaces, nor the thermal and aerodynamic conditions of the 935.
The other eight extrapolated tips must be inspected with the same
discipline. The next batch can then replace the assumed fixed support
of the bore with a documented support and resume mechanical convergence.
The old CFD values are not attributed to this new geometry.
Manufacturing, fatigue strength, admissible speed and physical operation
remain not validated.
