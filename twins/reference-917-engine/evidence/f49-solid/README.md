# F49 — réparation du solide interne (preuve publique)

Verdict : **refus fail-closed**. Aucun STEP F49 n'a satisfait simultanément le
round-trip STEP, `BRepCheck`, `BOPAlgo = 0` et le maillage 3D Gmsh. Ces images
montrent donc les candidats F47 audités et rejetés; elles ne constituent ni une
nouvelle CAO F49, ni une preuve d'impression.

Contenu public :

- `f49-solid-public-report.json` : métriques assainies et portes de décision ;
- `publication.json` : manifeste et empreintes SHA-256 ;
- `917-head-f49-scan-derived-exterior-four-views.png` : quatre vues annotées ;
- `917-head-f49-2v-4v-sections.png` : coupes comparatives 2V / 4V annotées.

La peau extérieure F43 dérivée du scan, les STEP rejetés, les maillages privés
et les coordonnées/indices des défauts restent hors dépôt. Le rapport ne publie
que leurs empreintes et des compteurs agrégés. La forme extérieure n'a reçu ni
ellipse/ovale global, ni changement d'échelle anisotrope, ni proxy.

Reproduction des seules preuves publiques :

```bash
make 917-f49-solid-repair-check
```
