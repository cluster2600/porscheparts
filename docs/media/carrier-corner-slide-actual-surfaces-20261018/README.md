# Reinforcing the window root

![Actual d64 and new corner-slide surfaces](carrier-corner-slide-actual-surfaces.png)

[Editable SVG](carrier-corner-slide-actual-surfaces.svg) · [render record](render-receipt.json) · [independent review](evidence/root-terminal-review.json) · [file inventory](archive.json)

The latest **24af0584** design shifts the first main-window corner **1.5 mm
in X along its original AB edge** on both mirrored arms. The preceding d64
shape and new design are the complete actual **597,720 / 598,372-triangle**
STLs, shown unchanged with the same camera and scale. Nominal CAD mass moves
from **1.274797998 kg** to **1.275991674 kg**: **+1.194 g**, leaving **24.01 g**
below **1.30 kg**, using **4,420 kg/m³**.

The lower panels are tessellated STL intersections at
**X = 83.39717404347466 mm**, the **prior R1 coarse reference plane**. This is
not a stress peak calculated for 24af. Both panels share the same YZ crop and
equal axis scale. All segments are computed before the display crop; **full
profile counts and coordinate hashes** are retained. The pinned source STLs,
plane and helper reproduce these sections. The picture does not supply all
segment coordinates, a sampled native section, normal-chord dimensions or a
global thickness measurement.

The [current construction, body and surface records](../../reports/carrier-rib-20261018/README.md#reinforcing-the-window-root--new-24af-design-trial)
keep their own geometry identities. Local construction, strict original-baseline
and d64 retention, mass, bounds and four tool-column predicates pass. At image
creation, complete surface audits, protected comparison, volume mesh and new
mechanics remain pending. Any later results belong in that checkpoint. The
separate R1 fillet is not inherited, and no d64/R1 stress or native face identity
is transferred to this design.

The actual PNG and SVG are byte copies of the one completed render. The ROOT
review independently verifies the complete retained owner record and output
hashes; PNG visual review passes. No PDF or new CAD/FEA run was made for this
publication. [The frozen source clarification](source/README-clarification.md)
corrects an earlier README phrase about section-coordinate retention.

The [render source](source/render.py), literal derivation, controls and complete
[external identity map](external-inputs.json) retain the original work paths,
source STLs, helper sources and **5,259 runtime files**. The external full meshes
and runtime binaries are not copied. These review snapshots require their
recorded local environment; this folder makes no portable replay claim.
