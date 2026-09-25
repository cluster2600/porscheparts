# M64 project diagrams

These diagrams describe the target architecture, the validation decisions and
the traceability of the rentals. They are not renders of the cylinder head nor
results of a physical computation. The states actually reached are in the dated
receipts, linked from the documents.

| Subject | Reference source | Document with GitHub Mermaid rendering |
|---|---|---|
| Software chain | [m64-stack.mmd](m64-stack.mmd) | [Multiphysics scope](../../reports/M64_MULTIPHYSICS_EXECUTION.md) |
| Validation path | [m64-validation.mmd](m64-validation.mmd) | [Multiphysics scope](../../reports/M64_MULTIPHYSICS_EXECUTION.md) |
| Rental and collection | [m64-vast-run.mmd](m64-vast-run.mmd) | [PicoGK execution](../../reports/M64_PICOGK_EXECUTION.md) |
| 700 PS target sizing | [m64-700ps-execution.mmd](m64-700ps-execution.mmd) | [Engine research and 0D balance](../../reports/M64_700CH_ENGINE_RESEARCH.md) |

Each source comes with a `.svg`, `.png` and `.excalidraw` of the same name.
The Excalidraw scenes stay editable via **File → Open** in Excalidraw.
The `.mmd` remains the reference; keep the document's Mermaid block identical
after any change, then regenerate and inspect the exports.

## Rendering checks of September 7, 2026

- Three Mermaid sources rendered offline by the local diagram bundle.
- Three SVGs checked with `xmllint --noout` and three PNGs inspected visually.
- Three Excalidraw scenes generated; no private capture or geometry included.
- Rendering bundle digest:
  `e59f8839cd0d42acb2b21bbde0825a1806c45ca8cbbcfc4367f7be27640b120d`.

The first chained run of several exports hit an SVG with unclosed HTML `br`
tags after the Excalidraw conversion. The rerun reloads a fresh rendering page
before each diagram, then produces SVG/PNG before the editable scene. The three
SVGs finally delivered pass the XML parser. The diagram sources were not
replaced by generative images.

The 700 PS diagram was also rendered to SVG/PNG and Excalidraw with this
bundle. A PNG attempt after the Excalidraw conversion was refused by the canvas
security; reloading the page and a fresh SVG/PNG render fixed the export,
without changing the computation model.
