# Translation to English

The repository was written in French. It is being translated to English in
phases, without breaking a single SHA-256 digest along the way. This page is the
contract every translation change follows, and the glossary that keeps the
vocabulary consistent.

Progress is measured, not declared:

```bash
make translation-status      # lists Markdown files still written in French
```

## What is translated, and what is not

| scope | rule |
|---|---|
| top-level documents (`README.md`, `SAFETY.md`, …) | translated |
| `docs/**` outside `docs/reports/` | translated, phase by phase |
| generated pages (`docs/parts/`, the README parts table, `make help`) | translated **in the generator**, then regenerated — never by hand |
| catalogue prose (`name`, `description`, limitations) | translated in the record; schema field names were already English |
| code comments, docstrings, identifiers | later phase; identifiers stay stable until then |
| `docs/reports/**` | dated execution reports — translated last, content unchanged |
| **`**/evidence/**`** | **never edited.** Evidence files are pinned by digest; a translation would break provenance and `make check` would fail |
| **`archive/**`** | **never edited.** 2,014 digests pin the archived 917 line (see [ARCHIVE.md](ARCHIVE.md)) |
| `containers/*.lock.json` and their recipe inputs | **never edited**, same reason |
| file and directory names (`M64_AVANCEMENT_20260907.md`, …) | renamed in phase 5, group by group, each Markdown page with a redirect stub left at the old path. An image cannot hold a stub, so it is moved and every reference updated. A name that is pinned or frozen is kept: renaming breaks inbound links and pinned paths |

Before editing any file, check that its digest is not pinned:

```bash
h=$(sha256sum FILE | cut -c1-64); git grep -F "$h" && echo "PINNED — do not edit"
```

## Style

- British English spelling with `-ise` (`centre`, `modelling`, `fibre`,
  `aluminium`, `colour`, `licence` as a noun, `optimise`). Identifiers, schema
  fields, status enums, filenames, URLs, code and named licences (`MIT License`)
  keep their original spelling.
- Keep the house voice: short declarative sentences, claims tied to evidence,
  explicit about what is **not** claimed. Do not soften "prohibited" or
  "not validated" into friendlier words.
- Numbers use English notation: `3.77`, `3,000`, `1.1 GB`.
- Keep Porsche part numbers, manual plate references (`planche 50-013` →
  `plate 50-013`), status enums (`prohibited_pending_engineering`) and field
  names verbatim.
- A quoted French source stays in French, with a translation next to it.

## Glossary

| French | English |
|---|---|
| dépôt | repository |
| fiche (de pièce, de source) | (part, source) record |
| pièce | part |
| dossier de conception | design dossier |
| jumeau numérique | digital twin |
| preuve | evidence |
| empreinte SHA-256 | SHA-256 digest |
| échoue fermé / fail-closed | fails closed |
| libéré, libération | released, release |
| interdit en l'état | prohibited pending engineering |
| critique pour la sécurité | safety-critical |
| fonctionnel / non critique | functional / non-critical |
| à décider | undecided |
| matière candidate | candidate material |
| nuance | grade |
| procédé | process |
| fabrication additive (FA) | additive manufacturing (AM) |
| criblage | screening |
| porte (d'entrée, de qualité) | gate (entry gate, quality gate) |
| réfutable | falsifiable |
| relevé (du manuel) | transcription (from the manual) |
| manuel d'atelier | workshop manual |
| planche (du manuel) | plate |
| cote | dimension |
| jeu | clearance |
| caisse | body shell |
| cellule (complète, fermée) | (full, closed) cell |
| plancher (nu) | (bare) floor pan |
| longeron | side rail |
| cloison | bulkhead |
| tunnel central | centre tunnel |
| passage de roue | wheel arch |
| pied milieu | B-pillar |
| pavillon | roof |
| cadre de pare-brise / de baie | windscreen frame |
| raideur en torsion | torsional stiffness |
| coques linéaires / quadratiques | linear / quadratic shells |
| substitut (de conception) | (design) surrogate model |
| culasse | cylinder head |
| soupape (d'admission, d'échappement) | (intake, exhaust) valve |
| bielle | connecting rod |
| carter | case, housing |
| couvre-culasse | valve cover |
| suralimentation | forced induction |
| habitacle | interior |
| carrosserie | body |
| éclairage | lighting |
| échappement | exhaust |
| moteur, admission et refroidissement | engine, intake and cooling |

## Diagrams and images

Readers understand a pipeline faster from a picture than from a paragraph. Every
translated page should earn at least one visual when its content has a shape — a
flow, a hierarchy, a sequence of gates, a timeline, a comparison.

- **Mermaid first.** GitHub renders ```` ```mermaid ```` blocks natively, in both
  light and dark themes. Use `flowchart` for pipelines and dependencies,
  `stateDiagram-v2` for status and gate progressions, `timeline` or `gantt` for
  dated sequences, `pie` for shares, `xychart-beta` for small numeric series,
  `mindmap` for inventories.
- **Only what the page already says.** A diagram restates sourced content; it
  never adds a claim, a number or a relationship that the text does not carry.
  Numbers in a chart must be copied from the page or from a record.
- **Show the stop signs.** Where a flow ends in "prohibited", "failed closed" or
  "not validated", draw that end explicitly. Suggested classes:
  `classDef stop fill:#fde2e1,stroke:#c0392b,color:#1a1a1a;`
  `classDef ok fill:#e3f1e6,stroke:#2e7d32,color:#1a1a1a;`
  `classDef open fill:#fff4d6,stroke:#b7791f,color:#1a1a1a;`
  Never name a class `root` (it collides with Mermaid internals).
- **Keep diagrams small**: about 12 nodes at most; split rather than cram. Put
  `<br/>` in labels instead of long lines, and quote labels containing
  punctuation: `A["Ti-6Al-4V (LPBF)"]`.
- **Images: existing files only.** Embed PNG/SVG/GIF already in the repository
  (renders, screens, figures under `evidence/` may be *linked or embedded*, never
  edited), with a relative path, a descriptive alt text and a one-line italic
  caption saying what it shows and what it does not prove. Never generate an
  image that looks like a photograph or a rendering of a real part.
- Check the page still renders: balanced code fences, and each Mermaid block
  parses (if `npx -y @mermaid-js/mermaid-cli` is available, render it once).

## Phases

| phase | scope | state |
|---|---|---|
| 1 | README, top-level documents, generators (parts table, part pages, `make help`), catalogue part names and descriptions, core `docs/*.md`, README figures | done |
| 2 | remaining `docs/*.md`, `docs/993/` (with the generated print-screen sections), `docs/research/`, `docs/decisions/`, `docs/media/`, catalogue READMEs and templates, CHANGELOG | done |
| 3 | `docs/reports/`, twin, container, deploy and simulation READMEs outside `evidence/`, catalogue twin records; diagrams and images across the docs | done |
| 4 | code comments, docstrings and command-line messages in `scripts/` and `tests/` | done (exceptions below) |
| 5 | file and directory renames, with redirects | done (exceptions below) |

Phase 5 progress ([#430](https://github.com/cluster2600/porscheparts/issues/430)).
Renamed so far, each with a redirect stub at the old path:

- 2026-11-06: decisions 0005 to 0008, four `docs/993/` pages (chain cover,
  chain case lid, titanium exhaust tip, titanium backlog),
  `docs/MONOCOQUE_964_993_COMPUTATION_CHAIN.md` and three `docs/research/` pages.
- 2026-11-12: `docs/pieces/` became `docs/parts/`, through the generator. Each
  page kept its file name; one stub, `docs/pieces/README.md`, redirects the
  directory.
- 2026-11-17: two more `docs/993/` pages (turbo oil circuit, LPBF sourcing in
  China) and four `docs/research/` pages (964 carbon/Kevlar chassis, carbon
  panels, phase 2 CAD forums, phase 2 German braking research).
- 2026-11-18, after the owner's decision "all in British English": the 13
  French-named `docs/reports/M64_*` reports, each with a stub at its old name,
  and the five French-named diagrams in `docs/media/diagrams/`, moved without
  a stub:

  | old name | new name |
  |---|---|
  | `M64_700CH_ENGINE_RESEARCH.md` | `M64_700PS_ENGINE_RESEARCH.md` |
  | `M64_700CH_MATERIAL_COOLING_LPBF.md` | `M64_700PS_MATERIAL_COOLING_LPBF.md` |
  | `M64_ADMISSION_CHAMBRE_20260908.md` | `M64_INTAKE_CHAMBER_20260908.md` |
  | `M64_AGGLOMERATION_LOCALE_20260908.md` | `M64_LOCAL_AGGLOMERATION_20260908.md` |
  | `M64_AVANCEMENT_20260907.md` | `M64_PROGRESS_20260907.md` |
  | `M64_CORPS_ADMISSION_MAILLAGE_20260908.md` | `M64_BODY_INTAKE_MESH_20260908.md` |
  | `M64_CORRECTIONS_NATIVES_20260908.md` | `M64_NATIVE_CORRECTIONS_20260908.md` |
  | `M64_DOMAINE_GAZ_OPENFOAM_20260908.md` | `M64_GAS_DOMAIN_OPENFOAM_20260908.md` |
  | `M64_LOCALISATION_ET_HXT_20260908.md` | `M64_LOCALISATION_AND_HXT_20260908.md` |
  | `M64_MAILLAGE_PARTITION_UNIFIEE_20260908.md` | `M64_UNIFIED_PARTITION_MESH_20260908.md` |
  | `M64_NETGEN_CONTRECONTROLE_20260908.md` | `M64_NETGEN_CROSS_CHECK_20260908.md` |
  | `M64_REMAILLAGE_NATIF_20260908.md` | `M64_NATIVE_REMESH_20260908.md` |
  | `M64_VOLUME_REEL_CONTROLES_20260908.md` | `M64_REAL_VOLUME_CHECKS_20260908.md` |
  | `964-chemin-effort.svg` | `964-load-path.svg` |
  | `964-echelle-architectures.svg` | `964-architecture-ladder.svg` |
  | `964-mecanisme-architecture.svg` | `964-architecture-mechanism.svg` |
  | `964-modele-coque.svg` | `964-shell-model.svg` |
  | `digital-twin-993-etat.{excalidraw,mmd,png,svg}` | `digital-twin-993-state.*` |

  `700PS` follows the existing `M64_700PS_*` reports. Each report keeps its
  content and title; only links to the renamed files changed. No pinned or
  frozen file referenced a diagram path, so no copy was kept at an old image
  path; the docs, the gallery and `twins/964-chassis/fea/figures.py`, which
  draws the four 964 figures, use the new names. Two consequences are
  accepted. External links to an old image path break. And the reports index
  generator, `scripts/render_reports_index.py`, is pinned by digest in
  `containers/stack-20261105/recon-native-validation.json`, so it cannot learn
  to skip stubs: `docs/reports/README.md` lists the 13 stubs as `Moved` rows
  and counts them as reports.

Still French-named on 2026-11-18, with the reason:

| path | why it keeps its name |
|---|---|
| `outils/` | frozen in place ([#425](https://github.com/cluster2600/porscheparts/issues/425)); run records pin its files by path and digest |
| `catalog/sources/src-*.json` | the file name is the source identifier |
| `docs/research/993-turbo-20261002/exports/fr/` | the French export, pinned by its publication manifest |
| `parts/993-eng-carrier-0001/source/progress-figures-20261016/**` | figures pinned by their manifests and receipts |
| `twins/964-chassis/derived/scan-recalage-20260925.json` | its digest is pinned in five run records, three of which also record its path |
| `training/qwen-metal-additive-20261002/input/glossaire_7_langues.csv` | pinned by the training manifest |
| French report names cited inside `twins/m64-cylinder-head/evidence/*.json` | frozen evidence, never edited. Three records cite `docs/M64_AGGLOMERATION_LOCALE_20260908.md` or `docs/M64_MAILLAGE_PARTITION_UNIFIEE_20260908.md`. That `docs/` path has not existed since 2026-09-14, when the reports moved into `docs/reports/` without a stub. The stubs now at `docs/reports/` under those names lead to the English reports |
| the redirect stubs left by every batch, including the 13 in `docs/reports/` | they exist to keep the old names working |

A scan of tracked file names for French words on 2026-11-18 found no other
French name. The French code and generated content that stay on purpose are the
phase 4 exceptions below.

Phase 4 exceptions (2026-11-06, issue #429). These stay French on purpose:

- **Lock-pinned sources.** `scripts/export_917_air_oil_seeds_f34b.py`,
  `scripts/run_917_doe_f34.py`, `tests/test_917_air_oil_seeds_f34b.py` and
  `tests/test_air_oil_cycle_f34b_image.py` are recipe inputs of
  `containers/air-oil-cycle-f34b.lock.json` or are pinned elsewhere by
  digest. Editing them breaks the lock.

  **Owner decision, 2026-11-06 ([#581](https://github.com/cluster2600/porscheparts/issues/581)):**
  create a new English image/lock generation while preserving the old one.
  [Follow-up #607](https://github.com/cluster2600/porscheparts/issues/607)
  tracks new source/recipe/output revisions, equivalence tests, build and runtime
  receipts, coordinated with #404–#406. The four historical files and their
  existing lock remain frozen; this decision does not claim that the English
  image has been built, published or qualified.
- **Generated document content (audited 2026-11-06, issue #580).** The French
  page content these generators write stays French, because translating it
  would change frozen outputs:
  - `build_turning_route_card.py` and `build_process_route_card.py` write their
    route cards and quotation requests into `evidence/` directories
    (`twins/*/evidence/route-*`, `turning-f1`), and `make check` regenerates
    them with `--check` against those frozen files.
  - `build_carrier_workshop_guide.py` to `_v6.py`, `build_part_workflow_guide.py`
    and `render_carrier_{fields,progress,region,workshop_drawing}.py` are
    themselves pinned by SHA-256, in `manufacturing/workflows/993-carrier-lpbf-v*.json`,
    `manufacturing/runtimes/pdf/results.json` and the carrier figure receipts.
  - `build_carrier_workshop_guide_v7.py` is unpinned, but it builds on the pinned v6
    and writes only into private run directories.

  English versions are possible only as **new** evidence revisions, for example
  an English quotation request for a supplier, written beside the frozen French
  ones. That is a deliverable choice for the owner, not a translation fix.
- **Data strings.** Strings in `tests/` that must equal French values written in
  records, evidence or script output (for example
  `tests/test_vast_simready_native.py`) change only when their source does.
