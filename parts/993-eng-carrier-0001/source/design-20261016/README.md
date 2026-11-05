# 993 Turbo carrier — geometric rework of 16 October 2026

The `bounded-webs` candidate keeps the attachments of the V6f study and brings the
computed dense mass to **1.262213 kg**, under the **1.30 kg** ceiling authorised by
Maxime. It is built from parameters and contours before the
Boolean operations, then exported and re-imported as STEP.

The [complete chain](../../../../docs/manufacturing/PART_WORKFLOW.md) links this
source to the inspected surface, the computations, the supports, the layers and the
shop-floor guide. The recipe is
[`manufacturing/workflows/993-carrier.json`](../../../../manufacturing/workflows/993-carrier.json).

## Retained geometry

- [`build_bounded_webs.py`](build_bounded_webs.py) builds the part with
  [`bounded-webs.json`](bounded-webs.json) and the
  [construction plan](bounded-webs-plan.json).
- The upper skin and the lower skin are nominally 1.5 mm; the
  2.8 mm ribs and their height are kept.
- The windows are reduced before cutting. The peripheral wall is defined
  by a contour offset of 1.61 mm. The
  [geometric bound](bounded-webs-wall-proof.json) proves a minimum
  separation of 1.59588 mm over this family of curves; it does not certify
  every edge of the part.
- Two local bosses of 4 mm outer radius surround the secondary
  holes of 2 mm radius, keeping their axes.
- The model stays within the 592 × 73 × 52 mm study envelope. The 8 mm
  central plate, its four axes at 100 × 40 mm centres and the end
  axes 560 mm apart are kept.

These dimensions are the explicit parameters of the study. The revisions do not
turn the V6f assumptions into measured Porsche dimensions.

## Checks and selection

[`inspect_protected.py`](inspect_protected.py) compares the solids of the protected
regions: zero symmetric difference on the plate and the six end
regions. The independent V6f check also verifies the axes, the
tool clearances and the F0 model pair.

[`compare.py`](compare.py) reruns and compares the same cases on
C3D10 meshes of nominal sizes 9 and 7 mm. Selection requires all of:

1. mass ≤ 1.30 kg and passing protected-region checks;
2. displacement and maximum von Mises below V6f in all four
   comparisons combined load / two meshes / rigid or spring supports;
3. independent energy balance and superposition passing at the declared thresholds.

The [criteria](normal-webs-selection-criteria.json) explicitly distinguish
this comparative selection from a material allowable. The combined cases
apply 4,000 N and 850 N·m. The compliant-support model uses a total
of 1,000 N/mm per eye and per direction, distributed among its nodes.

The candidate passes these comparisons. The elastic maximum of the compliant case remains
above the limit used in the plastic diagnosis; the nonlinear
computations and local reinforcements therefore have their own revisions
and decisions. A successful comparative pass does not replace them.

## Reproduction

The [macOS ARM64 / Python 3.10 CAD base](cad-base-macos-arm64-python310.lock.txt)
pins the 45 wheels of the verified standalone installation, including build123d
0.11.1, OCCT without VTK, and NumPy. The procedure describes its installation; it
avoids depending on the historical environment of the main checkout.
The [installer](setup_cad_base.py) was run on a second, fresh directory:
installation with digests, dependency check and six native checks
of the drilled solid and of the STEP re-import pass. The
[compact receipt](cad-base-standalone-validation.json) keeps the versions,
digests and witness results.

```sh
work/part-workflow/runtimes/design/bin/python -B \
  parts/993-eng-carrier-0001/source/design-20261016/build_bounded_webs.py \
  work/NOUVEAU_CANDIDAT
```

To reproduce the whole dossier, use the launcher and runtimes of the
[procedure](../../../../docs/manufacturing/PART_WORKFLOW.md).

`normal-builder/cad.py` is a traceable copy of the historical builder,
with only the changes needed before cutting and in the volume
computation. The earlier trials remain present with their parameters: thick
skin, thinned rib, tangent root and offsets of finished surfaces.
The mass, mechanical or STEP re-import rejections are not erased.
