# Porsche 993 cooling impeller program

[Repository home](../../README.md) · [Program record](program/program.json) · [Reproduction commands](program/REPRODUCE.md) · [Validation and missing inputs](program/VALIDATION_PLAN.md)

[Multilingual 911 / 935 / 993 research: sources, parameters and contradictions](program/research/README.md)

**Status on October 3, 2026: exploratory studies; no validated part.** The scan
supplied as a “935” has been located and audited privately. Its identity, units,
calibration and derivative rights remain unresolved; private purchase evidence
supports the reported Wolfe Classics acquisition. Equivalence to a 993 impeller
remains a hypothesis. Neither the raw scan nor its geometry derivatives is public.

**Terminology:** *impeller* means the rotating bladed wheel; *cooling fan assembly*
means the complete impeller, fan housing and drive arrangement; *fan housing*
means the surrounding housing. Original source titles, quotations, part numbers,
filenames and machine identifiers retain their original wording.

## Work by stage

| Stage | Deliverables and evidence | Actual status |
|---|---|---|
| Identification / scan | [Intake and privacy boundary](program/SCAN_INTAKE.md), [sources and part identification](REFERENCE_REBUILD.md), [earlier research record](reference-research.json) | Open scan; two components; scale and specimen identity not established |
| Reference model | [Editable PicoGK source](source/picogk-reference/Program.cs), [parameters](source/picogk-reference/reference.json), [checks](results/reference/validation.json), [model-derived views](results/reference/reference-review.png) | Hypothetical Turbo reconstruction, separate from the scan |
| Variants | [A–E study](ORGANIC_BLADE_STUDY.md), [sweep plans](results/airflow-sweep-20260929/configs/plan.json), [Qwen candidate / PR105](https://github.com/cluster2600/porscheparts/pull/105) | Traceable variants; no established optimum |
| Rotation / structure / modes | [Centrifugal calculations](results/organic/structure/), [new modal calculation](program/EXECUTION_20261003.md) | Executed; assumed supports/material, unqualified fatigue and convergence |
| Aerodynamics | [PR103 / diagnostics](MESH_RECOVERY_20261001.md), [PR105 recovery](https://github.com/cluster2600/porscheparts/pull/105), [final-output audit](program/EXECUTION_20261003.md) | Two accepted meshes; runs ended at 2,000 iterations; convergence rejected |
| Additive manufacturing | [Geometric screening](PRINT_RELEASE.md), [machine/material scenario](zrapid-print-process.json), [thermal code](source/simulate_zrapid_print.py) | Exploratory AlSi10Mg LPBF; no qualified distortion/residual-stress prediction |
| Omniverse / OpenUSD | [Organized asset](program/fan-program.usda), [checks and scope](program/EXECUTION_20261003.md), [earlier demonstrators](OMNIVERSE_DIGITAL_TWIN.md) | Composition and units checked; geometry and physical digital twin not validated |

![Views generated from the parametric reference impeller; no dimensional qualification](results/reference/reference-review.png)

*These views show the existing parametric model, not a dimensionally validated physical impeller.*

## Three distinct identities

The [archived Carrera F0 catalog record](../../catalog/parts/993-eng-cooling-impeller-alsi10mg-f0-0001.json)
remains the source of truth for that earlier concept: part number 96410601531,
synthetic 280 mm geometry, twelve blades and status
`prohibited_pending_engineering`. Its earlier [fan housing](../../catalog/parts/993-eng-fan-housing-alsi10mg-f0-0001.json)
does not become the Turbo fan housing.

The September 28 reconstruction targets **993 Turbo M64.60 / 96410601522**, with
an assumed working diameter of 245 mm and eleven blades. Interfaces for the hub,
fan housing 99310666750, rear cone, spacers, pulleys and alternator still require
measurement. The user has selected no alternator: 175 A / 240 A remain research
alternatives with different drive requirements. AS-PL alternator dimensions do
not describe the PMB unit. No validated functional catalog record exists for
this reconstruction.

The **“935” scan** is a third investigation branch. Visual resemblance does not
replace either earlier identity. Porsche distinguishes Turbo and Carrera
impellers in [ORIGINALE 05, PDF page 7](https://assets-v2.porsche.com/int/-/media/Project/PCOM/SharedSite/PorscheClassic/ORIGINALE/Editions---EN/originale-05-ww.pdf).
That source does not identify the scanned specimen.

## Next work

The [validation criteria](program/VALIDATION_PLAN.md) order the remaining work.
Auditing and model preparation can continue, but functional geometry derived
from the scan first requires specimen identity, independent dimensional
references, measured interfaces and permitted reuse scope. Earlier CFD/thermal
fields are not transferred to the scan or a different reference model. This
program authorizes no manufacturing, purchase, physical spin test or installation.
