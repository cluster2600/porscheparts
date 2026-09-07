# Diagrammes du projet M64

Ces diagrammes décrivent l'architecture cible, les décisions de validation et
la traçabilité des locations. Ce ne sont pas des rendus de la culasse ni des
résultats de calcul physique. Les états réellement atteints sont dans les
reçus datés, liés depuis les documents.

| Sujet | Source de référence | Document avec rendu Mermaid GitHub |
|---|---|---|
| Chaîne logicielle | [m64-stack.mmd](m64-stack.mmd) | [Périmètre multiphysique](../docs/M64_MULTIPHYSICS_EXECUTION.md) |
| Parcours de validation | [m64-validation.mmd](m64-validation.mmd) | [Périmètre multiphysique](../docs/M64_MULTIPHYSICS_EXECUTION.md) |
| Location et collecte | [m64-vast-run.mmd](m64-vast-run.mmd) | [Exécution PicoGK](../docs/M64_PICOGK_EXECUTION.md) |

Chaque source est accompagnée de `.svg`, `.png` et `.excalidraw` au même nom.
Les scènes Excalidraw restent éditables via **File → Open** dans Excalidraw.
Le `.mmd` reste la référence ; maintenir le bloc Mermaid du document identique
après modification, puis régénérer et inspecter les exports.

## Contrôles du rendu du 7 septembre 2026

- Trois sources Mermaid rendues hors réseau par le bundle local de diagrammes.
- Trois SVG contrôlés avec `xmllint --noout` et trois PNG inspectés visuellement.
- Trois scènes Excalidraw générées ; aucune capture ou géométrie privée incluse.
- Empreinte du bundle de rendu :
  `e59f8839cd0d42acb2b21bbde0825a1806c45ca8cbbcfc4367f7be27640b120d`.

Le premier enchaînement de plusieurs exports a rencontré un SVG avec balises
HTML `br` non fermées après la conversion Excalidraw. La reprise recharge une
page de rendu fraîche avant chaque diagramme, puis produit SVG/PNG avant la
scène éditable. Les trois SVG finalement livrés passent le parseur XML. Les
sources des diagrammes n'ont pas été remplacées par des images génératives.
