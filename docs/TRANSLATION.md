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
| generated pages (`docs/pieces/`, the README parts table, `make help`) | translated **in the generator**, then regenerated — never by hand |
| catalogue prose (`name`, `description`, limitations) | translated in the record; schema field names were already English |
| code comments, docstrings, identifiers | later phase; identifiers stay stable until then |
| `docs/reports/**` | dated execution reports — translated last, content unchanged |
| **`**/evidence/**`** | **never edited.** Evidence files are pinned by digest; a translation would break provenance and `make check` would fail |
| **`archive/**`** | **never edited.** 2,014 digests pin the archived 917 line (see [ARCHIVE.md](../ARCHIVE.md)) |
| `containers/*.lock.json` and their recipe inputs | **never edited**, same reason |
| file and directory names (`docs/pieces/`, `964-chemin-effort.svg`, …) | kept for now: renaming breaks inbound links and pinned paths. A later phase renames with redirects |

Before editing any file, check that its digest is not pinned:

```bash
h=$(sha256sum FILE | cut -c1-64); git grep -F "$h" && echo "PINNED — do not edit"
```

## Style

- American English spelling (`center`, `modeling`, `fiber`).
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
| tunnel central | center tunnel |
| passage de roue | wheel arch |
| pied milieu | B-pillar |
| pavillon | roof |
| cadre de pare-brise / de baie | windshield frame |
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
| 4 | code comments, docstrings and command-line messages in `scripts/` and `tests/` | open |
| 5 | file and directory renames, with redirects | open |
