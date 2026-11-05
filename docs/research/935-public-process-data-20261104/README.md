# 935 public process references and nominal machine-envelope screen

Date: 2026-11-04. Requirement: advance the faithful replica using sourced process
inputs while retaining the [local CADAM/Qwen branch](../../architecture/cadam-local-qwen.md)
and independent engineering admission. This is a bounded review of **eight
retrieved primary PDFs**, with three isolated experimental process references.
It is not a complete manufacturer-publication survey or a supplier selection.
No supplier message, form, scan upload, order or paid computation occurred.

## Public process references obtained

The [source ledger](sources.json) records snapshot hashes, revisions and visually
reviewed pages. PDFs remain private reference copies; none are redistributed in
Git. The [machine-readable cards](process-cards.json) keep each experiment
separate. AlSi10Mg is only the literature material, not the identified or
selected head alloy. The table reports operating power, not installed capacity.

| Primary reference | Machine / supplier role | Power W; speed mm/s; hatch mm; layer mm | Interpretation |
|---|---|---|---|
| [FS121M thin-wall study](https://www.mdpi.com/1996-1944/16/23/7326), methods pp. 3-4 | Farsoon FS121M | 340; 1500; 0.15; 0.03 | Subsequent furnace exposures at 260-440 C concern heat treatment, not temperature-dependent service allowables |
| [BLT defect/tension study](https://www.nature.com/articles/s41598-023-39948-z), pp. 2, 7 | BLT S310 | approximately 380; 1300; 0.15; 0.05 | 67-degree layer rotation; stress relief 300 C / 2 h / air cooling; raw datasets require an author request |
| [FalconTech-powder study](https://www.mdpi.com/2075-4701/11/8/1274), p. 3 | Hanbang 280; FalconTech supplied powder | 300; 1200; 0.14; 0.03 | Ar, substrate preheat 100 C; **not a Falcontech/Farsoon printer recipe** |

Arithmetic P/(speed x hatch x layer) gives about 50.4, 39.0 and 59.5 J/mm3,
respectively. Those scalar values neither identify a unique scan program nor
calibrate a heat source. No recipe transfers between machine models by matching
this scalar. No Adamantine head build was admitted from these cards.

The [Farsoon material sheet](https://www.farsoon-gl.com/wp-content/uploads/2021/07/AlSi10Mg-1.pdf)
(2024-09, p. 1) supplies heat-treated property minima and directs treatment
questions to the manufacturer. The [BLT brochure](https://www.xa-blt.com/en/wp-content/uploads/2023/04/BLT-Engine-Solutions-2023.4.13.pdf)
(PDF metadata 2025.08, p. 7) supplies generic mechanical-property ranges.
Neither inspected table supplies a complete machine/unit-specific hot material
law and held-out build-validation dataset. Catalogue properties are not engine
allowables.

## Coverage and missing inputs

Coverage denominator: three experimental cards and eight primary PDFs, not all
Farsoon/BLT publications. Across these cards, **zero complete head-build input
packages** were obtained. This does not prove that the missing data cannot be
published elsewhere or provided by a supplier.

| Input package | Farsoon FS121M card | BLT S310 card | FalconTech powder / Hanbang card |
|---|---|---|---|
| Named experimental machine and four scalar settings | Obtained | Obtained, approximate | Obtained; different printer brand |
| Exact production unit/profile, powder lot/reuse history | Incomplete | Incomplete | Incomplete |
| Full time-stamped exposure vectors, contours, recoat/dwell | Not obtained | Not obtained | Not obtained |
| Temperature-dependent thermal/phase/optical material model | Not obtained | Not obtained | Not obtained |
| Temperature/orientation/treatment-dependent mechanical laws | Not obtained as a complete model | Not obtained as a complete model | Not obtained as a complete model |
| Support, plate, clamping and release/contact conditions | Incomplete | Incomplete | Incomplete |
| Independently measured thermal/distortion calibration and held-out validation | Not obtained | Not obtained | Not obtained |
| Head duty/fatigue acceptance, machining, cleanliness and final inspection | Not established | Not established | Not established |

The earlier [technical requests](../935-readiness-20261104/PROCESS_DATA.md)
remain unsent. They enumerate the missing packages without authorising a paid
test or scan disclosure. Specimen identity, internal geometry and interface
metrology remain separate from manufacturer-process research.

## Machine-envelope necessary conditions

The [fixed method](method.json) was written before the computation. It consumes
the checksum-bound original arrays and owner-confirmed 1 mm/OBJ unit. Only
vertices incident to nonzero-area original triangles enter the metric domain;
the eight degenerate faces are retained in the source. No reconstruction,
smoothing, rescaling, hardware separation or inferred gallery is performed.

The [producer](source/build_envelope_audit.py) selects the farthest pair among
six coordinate-extreme vertices, a **diameter lower bound**, not the global
diameter. The [separate verifier](source/verify_envelope_audit.py) reads the
private witness, checks original vertex membership and exact coordinates, then
recomputes distance and box diagonals without reusing that search. It verifies
the exclusion proof, not the producer's extremum ranking or bounding spans.

Any point pair contained in a rectangular box is at most its diagonal apart.
Rigid transformations preserve the acquired pair distance. Here the witness is
**245.692798581 mm** apart. With a fixed 0.000001 mm numerical margin:

| Nominal reference box | Published dimensions mm | Recorded result for the current unseparated source |
|---|---|---|
| FS121M, optimistic envelope | 120 x 120 x 100 | Diagonal 196.977156036 mm: every single rigid placement excluded |
| FS350M effective envelope | 425 x 350 x 400 | Original-pose spans fit this nominal box; no manufacturing acceptance |
| S310, research-machine description | 250 x 250 x 400 | Original-pose spans fit this nominal box; no manufacturing acceptance |

The [FS121M 2022 sheet](https://www.farsoon-gl.com/wp-content/uploads/2021/07/FS121M.pdf)
and [2023 sheet](https://www.farsoon-gl.com/wp-content/uploads/2021/07/FS121M-1.pdf),
both p. 2, differ: 2022 excludes plate thickness from its height, whereas 2023
includes it. Laser/scanner configurations also differ. Preserve both revisions;
the optimistic box suffices for this exclusion even if real usable space is
smaller. The [FS350M sheet](https://www.farsoon-gl.com/wp-content/uploads/2023/09/FS350M-1.pdf)
(footer 2025-03, p. 2) distinguishes effective space from cylinder dimensions;
its height includes the plate. Do not transfer an FS121M research recipe to it.

This excludes **only the complete current acquired input** on FS121M, not a
future separately identified bare head. A length exceeding one box side alone
would not prove exclusion: diagonal placement may work. The larger-box results
omit plate clearance, supports, keepouts, powder removal and qualified process
constraints; they do not select a printer or issue a fabrication file.

## Executed verification and reproduction

[Aggregate results](box-results.json), [independent checks](box-verification.json)
and [eight controls](controls.json) passed on the Mac's existing Python 3.12.11 /
NumPy 2.5.4 runtime. Controls include a contained cube, an excluded segment,
known rotated rectangle and forged coordinates/distance/source hash refusals.
The exact private source-pair IDs and coordinates never enter Git.

```sh
# Use the qualified Python environment with NumPy; output directories must be new.
python source/build_envelope_audit.py method.json /private/exact-source-arrays.npz /private/new-box-trial
python source/verify_envelope_audit.py method.json /private/exact-source-arrays.npz /private/new-box-trial
python source/check_controls.py method.json /private/exact-source-arrays.npz /private/new-box-trial /private/new-controls
```

Private root: `~/Developer/PorschePartsArtifacts/935-public-process-data-20261104`.
Frozen files and source snapshots are indexed in the [private-manifest receipt](private-receipt.json).
No acquired geometry or previously frozen evidence was modified. All head,
process, physical-validation and manufacturing-release gates remain open.
