<div align="center">

![Full 964 cell rotating, colored by von Mises stress under a torsion load](docs/media/diagrams/964-hero.gif)

# porscheparts

**Reverse engineering for the Porsche 911 964 and 993**<br>
*Sourced data, falsifiable calculations, no part manufactured.*

[![Validate catalogue](https://github.com/cluster2600/porscheparts/actions/workflows/validate.yml/badge.svg)](https://github.com/cluster2600/porscheparts/actions/workflows/validate.yml)
[![License: all rights reserved](https://img.shields.io/badge/license-all%20rights%20reserved-lightgrey)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/)
[![Active phase](https://img.shields.io/badge/active%20phase-manufactures%20nothing-critical)](SAFETY.md)
[![Docs](https://img.shields.io/badge/docs-English-brightgreen)](docs/TRANSLATION.md)

[**Browse the parts**](#2-993-parts-for-additive-manufacturing) ·
[**See the structural results**](#1-structural-analysis-of-the-964-body-shell) ·
[**Run the checks**](#quick-start) ·
[**Gallery**](docs/GALLERY.md) ·
[**993 cooling impeller program: models, calculations and evidence**](twins/993-engine-cooling-fan-system-f0/README.md) ·
[**935 horizontal cooling system: 40-language evidence, engine inputs and gaps**](twins/935-horizontal-cooling-system/README.md) ·
[**Horizontal fan: CAD, mechanics, CFD gates, LPBF screening and OpenUSD studies**](models/horizontal-fan-reconstruction/README.md) ·
[**Latest impeller engineering results and open gates**](twins/993-engine-cooling-fan-system-f0/program/ENGINEERING_RESULTS_20261003.md) ·
[**Four-valve cylinder head: air + oil study**](docs/studies/993-air-oil-20261002/README.md) ·
[**Contribute**](CONTRIBUTING.md) ·
[**Safety first**](SAFETY.md)

</div>

---

This repository does not publish a library of files to print. It publishes
**sourced data** and **falsifiable calculations**: every claim of fit, mass or
stiffness is tied to a measurement, to a verifiable source or to a calculation
anyone can rerun — and **withdrawn when it no longer holds**. The repository has
withdrawn several, listed [further down this page](#what-the-repository-withdrew-from-its-own-results).

> [!IMPORTANT]
> **No part is validated.** All 34 part records are at status `concept`, 18 of
> them `prohibited_pending_engineering`. Read [SAFETY.md](SAFETY.md).

> [!TIP]
> **Printable today:**
> - 🖨️ the **[switch trim ring, F1](parts/993-int-switch-trim-ring-f1-0001/print/README.md)** — a part
>   the repository designed, printed as designed: 17 minutes of PETG or ASA, no supports. Fit on
>   the car not checked yet ([decision 0010](docs/decisions/0010-print-the-trim-ring-f1-in-polymer.md)).
> - a **[fit-test kit for the dashboard switch blank](parts/993-int-switch-blank-0001/print/README.md)** —
>   three sizes to find the real opening ([decision 0009](docs/decisions/0009-first-fit-test-print-switch-blank.md)).
>
> - 🧩 a **[1:1 display mock-up of the F0 connecting rod](parts/993-eng-connecting-rod-ti64-f0-0001/print/README.md)** —
>   the most complex design, rod and cap that bolt together, about 5 hours; "MOCK-UP / NOT FOR USE"
>   is engraved in it, and the rod itself stays prohibited ([decision 0011](docs/decisions/0011-printable-display-mockups-of-prohibited-parts.md)).
>
> - 🧩 a **[K16 wheel pair on a display stand](parts/993-eng-k16-compressor-wheel-al2139-f1-0001/print/README.md)** —
>   the compressor and turbine wheel designs side by side on an engraved stand, about 9.5 hours; both
>   wheels stay prohibited and carry "MOCK-UP / NOT FOR USE" on their backs.
>
> None of them is validated.

> [!NOTE]
> The project was written in French. Its documentation is now in English; code
> comments and a few command-line messages are next. Pinned evidence files stay
> in their original language on purpose — see [docs/TRANSLATION.md](docs/TRANSLATION.md).

<table>
<tr>
<td align="center"><h3>521</h3>qualified source records</td>
<td align="center"><h3>34</h3>part records<br><sub>18 prohibited as they stand</sub></td>
<td align="center"><h3>24</h3>993 design dossiers<br><sub>for additive manufacturing</sub></td>
</tr>
<tr>
<td align="center"><h3>9</h3>digital twins<br><sub>none at <code>F2_interface</code></sub></td>
<td align="center"><h3>3,000</h3>CalculiX cases<br><sub>on the 964 body shell</sub></td>
<td align="center"><h3>2,800+</h3>tests run by<br><code>make check</code></td>
</tr>
</table>

## How the repository works

Every artifact climbs the same ladder, and every rung is checked by `make check`.
Nothing leaves the last rung: manufacturing is suspended by design.

```mermaid
flowchart LR
    S["Sources<br/><sub>catalog/sources/</sub>"] --> R["Part records<br/><sub>catalog/parts/</sub>"]
    R --> D["Design dossiers<br/><sub>docs/993/</sub>"]
    D --> T["Digital twins<br/><sub>twins/</sub>"]
    T --> C["FEA · CFD · print simulation<br/><sub>CalculiX · OpenFOAM · LPBF</sub>"]
    C --> G{"Quality gates<br/><sub>docs/QUALITY_GATES.md</sub>"}
    G -- "claim fails" --> W["Withdrawn, and said so"]
    G -- "claim holds" --> E["Evidence<br/><sub>pinned by SHA-256</sub>"]
    E -. "suspended in the active phase" .-> M["Manufacturing"]
    classDef stop fill:#fde2e1,stroke:#c0392b,color:#1a1a1a;
    classDef ok fill:#e3f1e6,stroke:#2e7d32,color:#1a1a1a;
    class M,W stop
    class E ok
```

### Where to start

[M64 local-compute architecture](docs/architecture/README.md) — TOGAF,
ArchiMate and UML/Mermaid; [local Qwen training](training/m64-qwen/README.md)
before the next engineering deployment.

| I want to… | go to |
|---|---|
| print something today | [the F1 switch trim ring](parts/993-int-switch-trim-ring-f1-0001/print/README.md) · [the connecting rod display mock-up](parts/993-eng-connecting-rod-ti64-f0-0001/print/README.md) · [the switch blank fit-test kit](parts/993-int-switch-blank-0001/print/README.md) |
| see which 993 parts exist and their status | [the parts table](#2-993-parts-for-additive-manufacturing) → one page per part in [`docs/pieces/`](docs/pieces/) |
| understand the 964 structural model and its results | [section 1](#1-structural-analysis-of-the-964-body-shell) → [`twins/964-chassis/fea/`](twins/964-chassis/fea/) |
| know what may and may not be built | [SAFETY.md](SAFETY.md) · [docs/QUALITY_GATES.md](docs/QUALITY_GATES.md) |
| add a part or a source | [CONTRIBUTING.md](CONTRIBUTING.md) · [docs/WORKFLOW.md](docs/WORKFLOW.md) · [docs/SOURCE_POLICY.md](docs/SOURCE_POLICY.md) |
| find any document | [the documentation index](docs/README.md) |
| see the figures, renders and print screens | [the gallery](docs/GALLERY.md) |
| browse the digital twins | [twins/README.md](twins/README.md) |
| read what was run, day by day | [the dated reports index](docs/reports/README.md) |
| run the checks locally | [Quick start](#quick-start) |

### Contents

1. [Structural analysis of the 964 body shell](#1-structural-analysis-of-the-964-body-shell)
2. [993 parts for additive manufacturing](#2-993-parts-for-additive-manufacturing)
3. [Body and interior](#3-body-and-interior)
4. [The catalogue and its data contract](#4-the-catalogue-and-its-data-contract)
5. [The rules](#the-rules) · [What the repository withdrew](#what-the-repository-withdrew-from-its-own-results) · [What it does not claim](#what-the-project-does-not-claim)
6. [Quick start](#quick-start) · [Layout](#repository-layout) · [Status](#status)

---

## 1. Structural analysis of the 964 body shell

The main workstream. A finite-element shell model of the floor pan, the box
section and the full cell answers **relative** questions: between changing the
material and closing the body shell, which pays off more? What is a
superstructure member worth per kilogram? Where does the load go in torsion?

![The shell model, bare floor pan and full cell](docs/media/diagrams/964-modele-coque.svg)

**Results that hold** — see [`twins/964-chassis/fea/`](twins/964-chassis/fea/):

- the **side rail** carries torsion, not the floor pan, which agrees with plate
  50-013 of the workshop manual that places high-strength steel there;
- **closing a ring does not just add stiffness, it changes the mechanism that
  carries it** — bending on the bare floor pan, shear on the closed cell;
- from bare floor pan to closed cell, **K × 3.77 for mass × 2.3**;
- roof and windshield frame together are worth **1.63 times** the sum of their
  separate contributions: the roof only works once the ring is closed.

![von Mises stress on the bare floor pan](docs/media/diagrams/964-chemin-effort.svg)

![Share of shear in stiffness, by architecture](docs/media/diagrams/964-mecanisme-architecture.svg)

A **corpus of 3,000 CalculiX cases**, in quadratic shells, is being built to
train a design surrogate model later, with its validation set frozen before any
model exists. Chain and status:
[docs/MONOCOQUE_964_993_CHAINE_CALCUL.md](docs/MONOCOQUE_964_993_CHAINE_CALCUL.md).

The [monocoque program](docs/MONOCOQUE_964_993_PROGRAMME.md) defines what would
have to be established to compete with an existing offer on the one axis where
it is bare: published data. It **contradicts the written scope** of
[ROADMAP.md](ROADMAP.md), and says so.

## 2. 993 parts for additive manufacturing

The richest line of the repository: **24 design dossiers** `993_*_F0` and
`_F1`, and **34 part records**, from the headlamp spring hook to the K16 turbine
wheel in Inconel 718, by way of the Ti-6Al-4V connecting rod, the AlSi10Mg
compressor wheel and the IN625 exhaust manifold.

Each dossier starts from dimensions **published by a supplier**, separates what
is sourced from what is assumed, and states what it does not contain. Nothing is
released: every record is **at status `concept`**. The
[metal printing and Omniverse pipeline](docs/AM_VALIDATION_PIPELINE.md) is
mandatory before any manufacturing.

The table below is generated from `catalog/parts/` on every `make check`. The
"status" column is the record's, not an intention: a part **prohibited pending
engineering** stays so until an engineering review lifts it.

<!-- parts:start - generated by scripts/render_parts_table.py -->

> [!CAUTION]
> These are concept models for studying parts in software, not validated parts. 🖨️ marks a printable design, 🧩 an engraved display mock-up (never for use).

<table>
<tr>
<td align="center" width="16%"><a href="parts/993-body-front-impact-support-alsi10mg-f0-0001/"><img src="parts/993-body-front-impact-support-alsi10mg-f0-0001/media/preview.png" alt="993 front impact support" width="130"><br><sub>993 front impact support</sub></a></td>
<td align="center" width="16%"><a href="parts/993-body-front-lid-0001/"><img src="parts/993-body-front-lid-0001/media/preview.png" alt="Front lid" width="130"><br><sub>Front lid</sub></a></td>
<td align="center" width="16%"><a href="parts/993-elec-headlamp-spring-hook-f0-0001/"><img src="parts/993-elec-headlamp-spring-hook-f0-0001/media/preview.png" alt="Headlamp spring hook repair" width="130"><br><sub>Headlamp spring hook repair</sub></a></td>
<td align="center" width="16%"><a href="parts/993-eng-carrier-0001/"><img src="parts/993-eng-carrier-0001/media/preview.png" alt="Turbo engine carrier (Motortraege…" width="130"><br><sub>Turbo engine carrier (Motortraege…</sub></a></td>
<td align="center" width="16%"><a href="parts/993-eng-chain-case-0001/"><img src="parts/993-eng-chain-case-0001/media/preview.png" alt="993 timing chain case and its lids" width="130"><br><sub>993 timing chain case and its lids</sub></a></td>
<td align="center" width="16%"><a href="parts/993-eng-connecting-rod-ti64-f0-0001/"><img src="parts/993-eng-connecting-rod-ti64-f0-0001/media/preview.png" alt="🧩 993/993 Turbo connecting rod" width="130"><br><sub>🧩 993/993 Turbo connecting rod</sub></a></td>
</tr>
<tr>
<td align="center" width="16%"><a href="parts/993-eng-exhaust-manifold-in625-f0-0001/"><img src="parts/993-eng-exhaust-manifold-in625-f0-0001/media/preview.png" alt="993 Turbo three-into-one exhaust…" width="130"><br><sub>993 Turbo three-into-one exhaust…</sub></a></td>
<td align="center" width="16%"><a href="parts/993-eng-exhaust-valve-f1-0001/"><img src="parts/993-eng-exhaust-valve-f1-0001/media/preview.png" alt="993 exhaust valves - F1 proxies" width="130"><br><sub>993 exhaust valves - F1 proxies</sub></a></td>
<td align="center" width="16%"><a href="parts/993-eng-fan-housing-alsi10mg-f0-0001/"><img src="parts/993-eng-fan-housing-alsi10mg-f0-0001/media/preview.png" alt="Stationary engine fan housing" width="130"><br><sub>Stationary engine fan housing</sub></a></td>
<td align="center" width="16%"><a href="parts/993-eng-intake-valve-f1-0001/"><img src="parts/993-eng-intake-valve-f1-0001/media/preview.png" alt="993 intake valve - F1 proxy and t…" width="130"><br><sub>993 intake valve - F1 proxy and t…</sub></a></td>
<td align="center" width="16%"><a href="parts/993-eng-intake-valve-ti64-hollow-f0-0001/"><img src="parts/993-eng-intake-valve-ti64-hollow-f0-0001/media/preview.png" alt="993 hollow Ti64 intake valve" width="130"><br><sub>993 hollow Ti64 intake valve</sub></a></td>
<td align="center" width="16%"><a href="parts/993-eng-intercooler-bracket-ti-f0-0001/"><img src="parts/993-eng-intercooler-bracket-ti-f0-0001/media/preview.png" alt="993 Turbo/GT2 intercooler bracket" width="130"><br><sub>993 Turbo/GT2 intercooler bracket</sub></a></td>
</tr>
<tr>
<td align="center" width="16%"><a href="parts/993-eng-intercooler-end-tank-alsi10mg-f0-0001/"><img src="parts/993-eng-intercooler-end-tank-alsi10mg-f0-0001/media/preview.png" alt="993 Turbo intercooler end tank" width="130"><br><sub>993 Turbo intercooler end tank</sub></a></td>
<td align="center" width="16%"><a href="parts/993-eng-k16-compressor-wheel-al2139-f1-0001/"><img src="parts/993-eng-k16-compressor-wheel-al2139-f1-0001/media/preview.png" alt="🧩 K16 compressor wheel" width="130"><br><sub>🧩 K16 compressor wheel</sub></a></td>
<td align="center" width="16%"><a href="parts/993-eng-k16-compressor-wheel-alsi10mg-f0-0001/"><img src="parts/993-eng-k16-compressor-wheel-alsi10mg-f0-0001/media/preview.png" alt="993 K16 compressor wheel" width="130"><br><sub>993 K16 compressor wheel</sub></a></td>
<td align="center" width="16%"><a href="parts/993-eng-k16-turbine-wheel-in718-f0-0001/"><img src="parts/993-eng-k16-turbine-wheel-in718-f0-0001/media/preview.png" alt="🧩 K16 turbine wheel" width="130"><br><sub>🧩 K16 turbine wheel</sub></a></td>
<td align="center" width="16%"><a href="parts/993-eng-oil-filter-console-alsi10mg-f0-0001/"><img src="parts/993-eng-oil-filter-console-alsi10mg-f0-0001/media/preview.png" alt="Engine oil filter console with in…" width="130"><br><sub>Engine oil filter console with in…</sub></a></td>
<td align="center" width="16%"><a href="parts/993-eng-piston-cp1-gallery-f0-0001/"><img src="parts/993-eng-piston-cp1-gallery-f0-0001/media/preview.png" alt="M64/60 piston with cooling gallery" width="130"><br><sub>M64/60 piston with cooling gallery</sub></a></td>
</tr>
<tr>
<td align="center" width="16%"><a href="parts/993-eng-three-runner-intake-alsi10mg-f0-0001/"><img src="parts/993-eng-three-runner-intake-alsi10mg-f0-0001/media/preview.png" alt="993 three-runner intake manifold" width="130"><br><sub>993 three-runner intake manifold</sub></a></td>
<td align="center" width="16%"><a href="parts/993-eng-turbo-heat-shield-in625-f0-0001/"><img src="parts/993-eng-turbo-heat-shield-in625-f0-0001/media/preview.png" alt="993 left turbo heat shield cover" width="130"><br><sub>993 left turbo heat shield cover</sub></a></td>
<td align="center" width="16%"><a href="parts/993-eng-turbo-oil-return-line-in625-f0-0001/"><img src="parts/993-eng-turbo-oil-return-line-in625-f0-0001/media/preview.png" alt="Turbo oil return line" width="130"><br><sub>Turbo oil return line</sub></a></td>
<td align="center" width="16%"><a href="parts/993-eng-upper-valve-cover-alsi10mg-f0-0001/"><img src="parts/993-eng-upper-valve-cover-alsi10mg-f0-0001/media/preview.png" alt="Upper valve cover with COP towers" width="130"><br><sub>Upper valve cover with COP towers</sub></a></td>
<td align="center" width="16%"><a href="parts/993-exh-oval-tip-in625-f0-0001/"><img src="parts/993-exh-oval-tip-in625-f0-0001/media/preview.png" alt="993 oval exhaust tip" width="130"><br><sub>993 oval exhaust tip</sub></a></td>
<td align="center" width="16%"><a href="parts/993-exh-oval-tip-ti-f1-0001/"><img src="parts/993-exh-oval-tip-ti-f1-0001/media/preview.png" alt="Oval exhaust tip" width="130"><br><sub>Oval exhaust tip</sub></a></td>
</tr>
<tr>
<td align="center" width="16%"><a href="parts/993-int-dashboard-trim-0001/"><img src="parts/993-int-dashboard-trim-0001/media/preview.png" alt="Dashboard trim" width="130"><br><sub>Dashboard trim</sub></a></td>
<td align="center" width="16%"><a href="parts/993-int-door-opener-lever-f0-0001/"><img src="parts/993-int-door-opener-lever-f0-0001/media/preview.png" alt="993 interior door opener lever" width="130"><br><sub>993 interior door opener lever</sub></a></td>
<td align="center" width="16%"><a href="parts/993-int-door-pull-0001/"><img src="parts/993-int-door-pull-0001/media/preview.png" alt="Interior door pull handle" width="130"><br><sub>Interior door pull handle</sub></a></td>
<td align="center" width="16%"><a href="parts/993-int-seat-rail-cover-0001/"><img src="parts/993-int-seat-rail-cover-0001/media/preview.png" alt="Seat rail cover" width="130"><br><sub>Seat rail cover</sub></a></td>
<td align="center" width="16%"><a href="parts/993-int-switch-blank-0001/"><img src="parts/993-int-switch-blank-0001/media/preview.png" alt="Switch blank" width="130"><br><sub>Switch blank</sub></a></td>
<td align="center" width="16%"><a href="parts/993-int-switch-trim-ring-f1-0001/"><img src="parts/993-int-switch-trim-ring-f1-0001/media/preview.png" alt="🖨️ Aluminum switch trim ring" width="130"><br><sub>🖨️ Aluminum switch trim ring</sub></a></td>
</tr>
<tr>
<td align="center" width="16%"><a href="parts/993-turbocharger-k16-pair-0001/"><img src="parts/993-turbocharger-k16-pair-0001/media/preview.png" alt="Pair of K16 turbochargers of the…" width="130"><br><sub>Pair of K16 turbochargers of the…</sub></a></td>
<td align="center" width="16%"><a href="parts/993-whl-center-cap-alsi10mg-f0-0001/"><img src="parts/993-whl-center-cap-alsi10mg-f0-0001/media/preview.png" alt="993 center cap" width="130"><br><sub>993 center cap</sub></a></td>
</tr>
</table>

*Concept CAD blocks rendered from each part's own CAD by `scripts/render_part_previews.py`. **None of these is the original part, and none is validated**: 39 of 39 records are at `concept`, and 0 of 39 have measured geometry. 🖨️ Printable as designed, fit unchecked: Aluminum switch trim ring. 🧩 Printable as an engraved display mock-up, never for use: 993/993 Turbo connecting rod, K16 compressor wheel, K16 turbine wheel. Click a part to see it next to the original.*

```mermaid
pie showData title 39 part records by safety class
    "prohibited pending engineering" : 21
    "safety-critical" : 1
    "functional" : 12
    "non-critical" : 5
```

```mermaid
flowchart LR
    L0["concept<br/><b>39</b> records"]
    L1["dimensionally_reviewed<br/><b>0</b> records"]
    L2["prototype_fitted<br/><b>0</b> records"]
    L3["functionally_tested<br/><b>0</b> records"]
    L4["engineering_reviewed<br/><b>0</b> records"]
    L5["released<br/><b>0</b> records"]
    L0 --> L1 --> L2 --> L3 --> L4 --> L5
    classDef here fill:#fff4d6,stroke:#b7791f,color:#1a1a1a;
    classDef empty fill:#f4f4f4,stroke:#9e9e9e,color:#6b6b6b;
    class L0 here
    class L1 empty
    class L2 empty
    class L3 empty
    class L4 empty
    class L5 empty
```

*The validation ladder of `catalog/schemas/part.schema.json`, with the number of records whose `validation.status` names each step. Both charts are computed from the records.*

**Engine, intake and cooling**

| part | candidate material | process | status |
|---|---|---|---|
| [Turbo engine carrier (Motortraeger)](docs/pieces/993-eng-carrier-0001.md) | unknown | undecided | **safety-critical** |
| [993 timing chain case and its lids](docs/pieces/993-eng-chain-case-0001.md) | unidentified | undecided | **prohibited pending engineering** |
| [Left chain case lid 964 105 107 01](docs/pieces/993-eng-chain-case-lid-ti-f0-0001.md) | Ti-6Al-4V Grade 5, plate — deliberate c… | CNC | functional |
| [993/993 Turbo connecting rod](docs/pieces/993-eng-connecting-rod-ti64-f0-0001.md) | Ti-6Al-4V Grade 5 LPBF for screening | LPBF | **prohibited pending engineering** |
| [993 engine cooling fan — archived Carrera F0…](docs/pieces/993-eng-cooling-impeller-alsi10mg-f0-0001.md) | EOS Aluminium AlSi10Mg T6 for comparison | undecided | **prohibited pending engineering** |
| [M64 four-valve cylinder head — creation prepa…](docs/pieces/993-eng-cylinder-head-4v-f0-0001.md) | not selected | undecided | **prohibited pending engineering** |
| [993 Turbo three-into-one exhaust manifold](docs/pieces/993-eng-exhaust-manifold-in625-f0-0001.md) | EOS NickelAlloy IN625 / UNS N06625 for… | undecided | **prohibited pending engineering** |
| [993 exhaust valves - F1 proxies](docs/pieces/993-eng-exhaust-valve-f1-0001.md) | INCONEL 751 / UNS N07751 candidate | CNC | **prohibited pending engineering** |
| [Stationary engine fan housing](docs/pieces/993-eng-fan-housing-alsi10mg-f0-0001.md) | EOS Aluminium AlSi10Mg T6 for comparison | undecided | **prohibited pending engineering** |
| [993 intake valve - F1 proxy and titanium vari…](docs/pieces/993-eng-intake-valve-f1-0001.md) | Ti-6Al-4V Grade 5 | DMLS | **prohibited pending engineering** |
| [993 hollow Ti64 intake valve](docs/pieces/993-eng-intake-valve-ti64-hollow-f0-0001.md) | Ti-6Al-4V Grade 5 LPBF, screening | LPBF | **prohibited pending engineering** |
| [993 Turbo/GT2 intercooler bracket](docs/pieces/993-eng-intercooler-bracket-ti-f0-0001.md) | Ti-6Al-4V Grade 5 for screening | CNC | functional |
| [993 Turbo intercooler end tank](docs/pieces/993-eng-intercooler-end-tank-alsi10mg-f0-0001.md) | EOS Aluminium AlSi10Mg for screening | LPBF | **prohibited pending engineering** |
| [K16 compressor wheel](docs/pieces/993-eng-k16-compressor-wheel-al2139-f1-0001.md) | EOS Aluminium Al2139 AM, M290 60 µm, he… | LPBF | **prohibited pending engineering** |
| [993 K16 compressor wheel](docs/pieces/993-eng-k16-compressor-wheel-alsi10mg-f0-0001.md) | EOS AlSi10Mg, screening | LPBF | **prohibited pending engineering** |
| [K16 turbine wheel](docs/pieces/993-eng-k16-turbine-wheel-in718-f0-0001.md) | EOS NickelAlloy IN718 API, M290 40 µm… | undecided | **prohibited pending engineering** |
| [Engine oil filter console with integrated gal…](docs/pieces/993-eng-oil-filter-console-alsi10mg-f0-0001.md) | EOS Aluminium AlSi10Mg T6 for comparison | undecided | **prohibited pending engineering** |
| [M64/60 piston with cooling gallery](docs/pieces/993-eng-piston-cp1-gallery-f0-0001.md) | Constellium Aheadd CP1, Velo3D Sapphire… | LPBF | **prohibited pending engineering** |
| [993 three-runner intake manifold](docs/pieces/993-eng-three-runner-intake-alsi10mg-f0-0001.md) | generic AlSi10Mg for screening | undecided | functional |
| [993 left turbo heat shield cover](docs/pieces/993-eng-turbo-heat-shield-in625-f0-0001.md) | EOS NickelAlloy IN625 / UNS N06625, scr… | undecided | functional |
| [Turbo oil return line](docs/pieces/993-eng-turbo-oil-return-line-in625-f0-0001.md) | EOS NickelAlloy IN625 / UNS N06625 for… | undecided | **prohibited pending engineering** |
| [Upper valve cover with COP towers](docs/pieces/993-eng-upper-valve-cover-alsi10mg-f0-0001.md) | EOS Aluminium AlSi10Mg T6, for comparis… | undecided | **prohibited pending engineering** |

**Charge air**

| part | candidate material | process | status |
|---|---|---|---|
| [993 Turbo charge-air tract transcribed parts…](docs/pieces/993-ca-charge-pipe-set-pet-0001.md) | unknown per line item (hoses are rubber… | undecided | non-critical |
| [993 Turbo turbocharging intake tract (group 1…](docs/pieces/993-ca-turbo-intake-manifold-pet-0001.md) | unknown | undecided | non-critical |

**Turbocharger**

| part | candidate material | process | status |
|---|---|---|---|
| [Pair of K16 turbochargers of the 993 Turbo](docs/pieces/993-turbocharger-k16-pair-0001.md) | undetermined | undecided | **prohibited pending engineering** |

**Exhaust**

| part | candidate material | process | status |
|---|---|---|---|
| [993 Turbo catalytic converters (front muffler…](docs/pieces/993-exh-cat-converter-pair-pet-0001.md) | unknown | undecided | **prohibited pending engineering** |
| [993 Turbo exhaust heat exchangers (manifolds)](docs/pieces/993-exh-heat-exchanger-pair-pet-0001.md) | unknown (an IN625 aftermarket offer exi… | undecided | **prohibited pending engineering** |
| [993 oval exhaust tip](docs/pieces/993-exh-oval-tip-in625-f0-0001.md) | EOS NickelAlloy IN625 / UNS N06625 for… | undecided | functional |
| [Oval exhaust tip](docs/pieces/993-exh-oval-tip-ti-f1-0001.md) | Ti-6Al-4V if the actual temperature all… | LPBF | functional |

**Body**

| part | candidate material | process | status |
|---|---|---|---|
| [993 front impact support](docs/pieces/993-body-front-impact-support-alsi10mg-f0-0001.md) | generic screening AlSi10Mg | undecided | **prohibited pending engineering** |
| [Front lid](docs/pieces/993-body-front-lid-0001.md) | fiber and resin to be determined | undecided | functional |

**Interior**

| part | candidate material | process | status |
|---|---|---|---|
| [Dashboard trim](docs/pieces/993-int-dashboard-trim-0001.md) | fiber and resin to be determined | undecided | functional |
| [993 interior door opener lever](docs/pieces/993-int-door-opener-lever-f0-0001.md) | AlSi10Mg, screening | LPBF | functional |
| [Interior door pull handle](docs/pieces/993-int-door-pull-0001.md) | to_be_determined_after_load_test | undecided | functional |
| [Seat rail cover](docs/pieces/993-int-seat-rail-cover-0001.md) | to_be_determined_after_fit_test | FFF | non-critical |
| [Switch blank](docs/pieces/993-int-switch-blank-0001.md) | to_be_determined_after_fit_test | FFF | non-critical |
| [Aluminum switch trim ring](docs/pieces/993-int-switch-trim-ring-f1-0001.md) | EN AW-6063 T6 retained for bright anodi… | CNC | non-critical |

**Lighting**

| part | candidate material | process | status |
|---|---|---|---|
| [Headlamp spring hook repair](docs/pieces/993-elec-headlamp-spring-hook-f0-0001.md) | EOS Aluminium AlSi10Mg / AlSi10Mg_FlexM… | LPBF | functional |

**Wheels**

| part | candidate material | process | status |
|---|---|---|---|
| [993 center cap](docs/pieces/993-whl-center-cap-alsi10mg-f0-0001.md) | AlSi10Mg for screening | undecided | functional |

*39 records, 21 of them prohibited pending engineering, none released. Each link opens the part's description page in [`docs/pieces/`](docs/pieces/), generated from its `catalog/parts/*.json` record; the design dossiers are in [`docs/993/`](docs/993/). Table generated by `scripts/render_parts_table.py`, checked by `make check`.*

<!-- parts:end -->

## 3. Body and interior

**Bolt-on** panels — fenders, lids, spoiler, doors — are a legitimate target;
the load-bearing structure is not. The factory catalogue draws the line in part
numbers:
[docs/research/993-964-panneaux-carbone.md](docs/research/993-964-panneaux-carbone.md).

But those panels can already be ordered from several tuners. The part chosen is
therefore the one nobody sells: the **dashboard trim**,
`993-INT-DASHBOARD-TRIM-0001`, restricted to vehicles **without a passenger
airbag** — on the others it carries the deployment flap, which makes it an
occupant-restraint part. Its
[measurement plan](parts/993-int-dashboard-trim-0001/evidence/measurement-plan.md)
opens with an entry gate that can stop the project.

Three simpler interior pilots are waiting for a physical measurement session:
[docs/MEASUREMENT_CAMPAIGN.md](docs/MEASUREMENT_CAMPAIGN.md).

## 4. The catalogue and its data contract

**521 source records** qualified by provenance, rights and level of evidence;
34 part records, 9 twins, 4 components, 2 assemblies. Everything is validated by
a JSON schema and by the test suite:

```bash
make check
```

A record keeps technical access, reading method and reuse rights separate. An
accessible page is not redistributable; a page read in a browser is neither an
authorized download nor a validation of accuracy.

```mermaid
flowchart TB
    subgraph catalog["catalog/ — source of truth, JSON-schema validated"]
      direction LR
      src["sources/<br/>521 records"] --- prt["parts/<br/>34 records"]
      prt --- tw["twins/<br/>9 records"]
      prt --- cmp["components/ · assemblies/"]
      prt --- mea["measurements/<br/>3 manual transcriptions"]
    end
    prt -- "render_part_pages.py" --> pages["docs/pieces/<br/>one page per part"]
    prt -- "render_parts_table.py" --> table["README parts table"]
    tw --> twins["twins/&lt;zone&gt;/<br/>CAD · analysis · evidence"]
```

---

## The rules

| rule | what it requires |
|---|---|
| **Source before STL** | FreeCAD, OpenSCAD, build123d or STEP remain the master formats |
| **Evidence before publication** | every claim of fit or accuracy is tied to a measurement or a source |
| **Digital before prototype** | the active phase manufactures nothing |
| **Interface before appearance** | a measured zone that allows a clearance check beats a full scan of unknown accuracy |
| **Explicit safety** | when in doubt, the part is lowered to `prohibited_pending_engineering` — see [SAFETY.md](SAFETY.md) |
| **No vendor harvesting** | a site closed to robots is not queried — see [decision 0003](docs/decisions/0003-no-vendor-harvesting.md) |
| **Accessible tools** | a free, open-source, local toolchain |

## What the repository withdrew from its own results

This is the most useful part of its history, and it is public.

![Stiffness by architecture in linear and quadratic shells](docs/media/diagrams/964-echelle-architectures.svg)

Above, the heaviest correction: the architecture ladder had been published with
linear elements. The four figures on this page are regenerated with
`twins/964-chassis/fea/figures.py`, the animated banner with
`twins/964-chassis/fea/hero.py` — the two charts from values frozen in
`figures-data.json`, each carrying the origin of its calculation, the model
views and the banner from a mesh and result snapshot kept in `figures-mesh/`.
None of them is a rendering: they are the calculation's data.

| withdrawn claim | what defeated it |
|---|---|
| "the structure works in membrane shear" | a test decoupling `E` and `G`: the bare floor pan works in almost pure bending |
| "stiffness follows thickness exactly linearly" | the exponent is 1.00 with linear elements and **1.10** with quadratic ones: the exactness belonged to the element |
| "the windshield frame has the best return per kilogram" | in quadratic shells, it is the center tunnel |
| a cross member counted in the model's mass | a connectivity check: it was attached to nothing |
| eleven lost analysis cases, read as a near-singular system | a defect in the solver's partitioner, whose message went to `stderr` |

Three wrong calculations in that campaign came from **resource sharing** — work
files left in place, a mesh shared by two campaigns, a shared machine. None had
left a trace in an error output.

## What the project does not claim

- **No absolute stiffness value is a 964 stiffness.** The model's sections are
  `ASSUMED` and the mesh is not converged; only ratios and rankings are usable.
- **No part is validated.** Two printable files exist — the F1 trim ring and a
  fit-test kit (decisions 0009, 0010) — and neither has been checked on a car. All 34 records are at status
  `concept`, 18 of them `prohibited_pending_engineering`. No twin reaches the
  `F2_interface` level.
- **No physical measurement is recorded yet.** The three records in
  `catalog/measurements/` are transcriptions from the workshop manual, not
  instrumented measurements: the repository has access to neither a 993, nor a
  removed part, nor an instrument.
- **A rendering is not evidence.** Neither Omniverse, nor an image, nor a photo
  demonstrates physical behavior.

## What is archived

The **917 cylinder head** dossier — 891 files, iterations F1 to F50 — is retired
as a product and kept as a numerical regression, along with the 935 cylinder
head scan. It was not moved into an archive folder, and
[ARCHIVE.md](ARCHIVE.md) explains why: it carries 2,014 SHA-256 digests that
moving it would invalidate. Evidence beats tidiness.

That page lists what can still be done with it — rerun the calculations, reuse
the test cases — and what cannot: a part.

---

## Quick start

Requirements: Python 3.11 or newer and `make`. Clone onto a native Linux file
system (on WSL, not under `/mnt/c` — see [AGENTS.md](AGENTS.md)).

```bash
git clone https://github.com/cluster2600/porscheparts.git
cd porscheparts
make help                 # active targets, grouped by theme
make check                # schemas, tests, generators and digests
make translation-status   # which pages are still in French
```

To add a part:

```bash
cp catalog/templates/part-record.json catalog/parts/993-xxx-0001.json
# fill in the record, add licensed CAD files under parts/<part_id>/
make part-pages parts-table   # regenerate its page and the README table
make check
```

Conventions in detail: [CONTRIBUTING.md](CONTRIBUTING.md). The 162 `917-*`
targets are not listed by `make help`: they drive the archived line, and
`make help-917` lists them separately. Tests that need `numpy`, `matplotlib` or
CAD kernels are skipped or fail without them; the compute images in
[`containers/`](containers/) carry the full stack.

## Repository layout

```text
catalog/            records: sources, parts, measurements, twins, components
  schemas/            the catalogue's data contract
  templates/          record, measurement and manufacturing-request templates
parts/              geometry, measurement plans and deliverables per part
components/         component geometry; assemblies/ holds their evidence
twins/              digital twins, one folder per zone — see twins/README.md
  964-chassis/        964 chassis twin: datums, CAD, analysis, corpus
  993-*/              993 functional zones
  m64-*/              M64 engine and cylinder head twins
docs/               plans, quality criteria, software chain — see docs/README.md
  993/                the 24 design dossiers of the 993 parts
  pieces/             one generated page per part record
  decisions/          numbered architecture decisions
  reports/            dated execution and audit reports, indexed by day
  research/           source research by topic
  media/              diagrams and video projects
  GALLERY.md          every figure and render on one page
simulation/         forced-induction circuit analysis cases
archive/917/docs/   the 112 written dossiers of the 917 cylinder head
outils/benchmarks/  solver verification cases
scripts/  tests/    automatic checks and guardrails
containers/ deploy/ reproducible compute images and deployment
```

## Status

| phase | state |
|---|---|
| 0 — foundation | ✅ done |
| 1 — source inventory | 🟡 past its quantitative threshold; cross-qualification and direct measurements still open |
| 2 — physical inventory and twin assembly | 🟡 run in digital mode; physical prototypes suspended, except two printable non-critical files (decisions 0009, 0010) |
| 3 — titanium engineering twin, no manufacturing | ⬜ open: candidate `993-ENG-CARRIER-0001` under study |
| 4 — public catalog | ⬜ open: only parts that clear their quality gates will be published |

Details and exit criteria: [ROADMAP.md](ROADMAP.md) ·
[docs/PROJECT_CHARTER.md](docs/PROJECT_CHARTER.md) ·
[docs/DIGITAL_TWIN.md](docs/DIGITAL_TWIN.md) ·
[docs/QUALITY_GATES.md](docs/QUALITY_GATES.md).

The first composite engine subassembly, the
[F0 cooling fan housing and impeller](docs/993/993_ENGINE_COOLING_FAN_SYSTEM_F0.md),
converts to OpenUSD but fails its clearance test on an explicit BRep collision:
it remains a research twin that cannot be manufactured.

For the M64/60 engine (993 Turbo), the master bill of materials of the whole-engine twin is indexed in
[`twins/m64-engine-system/bom/m64-bom-v1.json`](twins/m64-engine-system/bom/m64-bom-v1.json)
with its coverage summary
[`twins/m64-engine-system/bom/coverage.md`](twins/m64-engine-system/bom/coverage.md).

The [2 October 2026 engine and K16 hybrid research](docs/research/993-turbo-20261002/README.md)
adds source-qualified M64/60 data and map leads, with a separate
[CPT/SFT preparation package](training/993-turbo-20261002/README.md).
The [3 October 2026 Mezger variants and materials supplement](docs/research/mezger-turbo-materials-20261003/README.md)
adds 203 scoped records and a [separate training increment](training/mezger-turbo-materials-20261003/README.md).

The [German-source supplement](docs/research/mezger-german-sources-20261003/README.md)
adds 108 records on alloy chemistry, manufacturing, scoped hybrid-turbo wheel
data and racing variants, with [108 CPT and 108 SFT examples](training/mezger-german-sources-20261003/README.md).


![Sourced state of the 993 digital twin](docs/media/diagrams/digital-twin-993-etat.svg)

This diagram shows the sourced logical relationships, not the actual position
of the components in the car.

---

## Disclaimer

This repository provides research and manufacturing data without warranty.
Printing, fitting and road use remain the responsibility of whoever makes and
installs the part. Read [SAFETY.md](SAFETY.md) before any manufacturing.

Porsche and 911 are trademarks of their respective owners. This project is
independent and not affiliated with Porsche AG.

## License

**© 2026 Maxime Grenu. All rights reserved.** The repository is under a custom
[proprietary license](LICENSE): you may view it, but copying, modifying,
printing or manufacturing parts, redistributing, commercial use and AI training
all need prior written permission — ask by opening an issue. Third-party
sources and models keep their own license; see [LICENSES.md](LICENSES.md).
Revisions published before 2026-09-25 were under the MIT License.
