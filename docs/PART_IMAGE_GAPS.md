# Part image gaps — 6 November 2026

Re-counted on 6 November 2026 (issue #438) from `catalog/parts/*.json` and each
`parts/<id>/media/preview.json`: the 45 catalogue records have 43 CAD image sets
(`kind: geometry_render`, with `views.png`), 41 separately labelled AI studio
illustrations and two status cards (`kind: status_card`). A status card depicts no part. An AI studio
illustration is a presentation of a concept, not a photograph or exact OEM geometry.

| Catalogue record | Remaining image gap | Required source |
| --- | --- | --- |
| `993-ENG-CYLINDER-HEAD-4V-F0-0001` | No geometry linked to the current head creation record. Separate prior M64/935-derived study geometry is not the exact current 993 Turbo part. | Correctly identified catalogue-linked geometry with independent interface evidence, or an exact-part photograph with recorded reuse rights. |
| `993-ENG-COOLING-IMPELLER-ALSI10MG-F0-0001` | The synthetic generic Carrera F0 rotor views remain deliberately withdrawn because they could be mistaken for the Turbo fan. | An owner-approved archival presentation or correctly identified replacement imagery; do not restore the withdrawn generic views. |

Two records have CAD views but no AI studio illustration. That isn't a gap:
the required public images (`preview.png`, `views.png`, `preview.json`) exist,
and a studio illustration is an optional presentation.

| Catalogue record | Images | Note |
| --- | --- | --- |
| `964-CENTRAL-CELL-ASSUMED-F1` | CAD preview and views | Assumed-geometry study (PR #525). An illustration would have to say "assumed" as plainly as the record does. |
| `993-ENG-INTERCOOLER-BRACKET-TI-F1-0001` | CAD preview and views | F1 study; the F0 bracket record keeps its illustration. |

Both gaps in the first table stay **blocked**. The head needs catalogue-linked
geometry with interface evidence (#484). The AlSi10Mg impeller needs an owner
decision on archival imagery, and its withdrawn generic views must not return.

Five former status-card records now have catalogue-linked PicoGK concepts and
studio illustrations: the charge-pipe set, turbo intake tract, titanium chain-case
lid, catalytic-converter pair and heat-exchanger pair. Their images depict the
existing concept models. They do not establish OEM shape, measured interfaces,
fit, material qualification or functional completion. Their original CAD views
remain available alongside the AI presentation images.

No third-party photographs or PET illustrations were copied. The commercial and
reference-only sources in these records do not grant image republication rights.
Never close an exact-part evidence gap using a different variant, a generic proxy
or an AI-generated photograph. Creating functional geometry still requires the
interfaces and independent evidence specified by AGENTS.md.
