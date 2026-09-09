# Porsche 917 — F49, réparation topologique interne 2V / 4V

## Verdict

F49 est **refusée en mode fail-closed**. Les tentatives non déformantes
conservent un solide unique, une coque unique, zéro arête libre et zéro arête
non-manifold selon OCCT, mais le round-trip STEP conserve des p-courbes
invalides. Aucun candidat ne remplit donc la condition préalable
`BOPAlgo = 0`; conformément au contrat, aucun nouveau maillage volumique Gmsh
n'a été accepté et aucune impression métal n'est autorisée.

La bonne décision d'ingénierie est de conserver la peau extérieure F43 comme
autorité géométrique privée et de refuser un « soin » global qui déplacerait la
forme. La reconstruction locale des faces fautives doit être traitée dans un
lot ultérieur avec une comparaison de peau complète.

## Enveloppe verrouillée

Les variantes 2V et 4V chargent exactement la même source privée F43,
d'empreinte SHA-256
`38f8ed3071005e5f64156d8670b5a755c98599d8702ef030ff132b7a034f0f24`.
Le dépôt ne contient pas cette géométrie. Les opérations suivantes sont
interdites par contrat : modification de surface externe, mise à l'échelle
anisotrope, ellipse ou ovale global, proxy global et couture globale.

Les seuls cercles autorisés restent fonctionnels : alésage, sièges, cols,
guides, puits de bougie, sections circulaires de conduits et galeries d'huile.
La bbox exacte et quelques échantillons OCCT sont restés invariants à la
précision numérique; cette observation ne remplace pas une signature exhaustive
des faces extérieures.

![Quatre vues de l'enveloppe dérivée du scan](../twins/reference-917-engine/evidence/f49-solid/917-head-f49-scan-derived-exterior-four-views.png)

## Essais exécutés

| Variante / méthode | BRepCheck | Topologie | BOPAlgo après STEP | Gmsh 3D | Décision |
|---|---:|---|---:|---|---|
| 2V F47 de référence | valide | 1 solide, 1 coque, 0 libre, 0 non-manifold | 8 | échec PLC F47 | rejet |
| 2V booléens séquentiels | valide | identique | 8 | non lancé par fail-fast | rejet |
| 2V booléens individuels | valide | identique | 8, sur 5 faces / 8 arêtes | non lancé | rejet |
| 2V reprojection p-curve, surface curves mode 1 | valide | identique | 0 avant export, 8 après round-trip | non lancé | rejet |
| 2V STEP sans surface curves, mode 0 | valide | identique | 131, sur 61 faces / 69 arêtes | non lancé | rejet |
| 4V F47 de référence | valide | 1 solide, 1 coque, 0 libre, 0 non-manifold | 32 | échec PLC F47 | rejet |
| 4V reprojection p-curve, surface curves mode 1 | valide | identique | 0 avant export, 32 après round-trip | non lancé | rejet |

Deux pistes ont également été rejetées : la conversion globale NURBS changeait
le volume et l'aire du noyau gaz tout en créant 22 défauts BOP; le sweep
circulaire tangent créait 27 défauts dont 21 auto-intersections. Elles ne sont
pas utilisées dans le résultat.

![Coupes 2V et 4V des candidats rejetés](../twins/reference-917-engine/evidence/f49-solid/917-head-f49-2v-4v-sections.png)

## Huile, épaisseur et physique

Le circuit d'huile reste un composant séparé, inchangé depuis F47 et propre au
contrôle BOP pour les deux variantes. Il n'est pas une chemise de liquide de
refroidissement. Pression, retour d'huile et accès poudre ne sont pas validés.

Les ligaments analytiques nominaux hérités de F47 sont 1,5 unité pour la 2V et
3,159837414 unité pour la 4V. Ce sont des écrans géométriques conditionnels à
la convention « une unité de scan = un millimètre »; ils ne constituent pas une
carte exhaustive d'épaisseur. L'échelle absolue du scan et le montage Porsche
ne sont pas certifiés. La porte `épaisseur >= 1,5 mm` reste donc fermée.

F49 ne valide ni thermique, ni structure, ni fatigue, ni matériau à chaud, ni
fabrication LPBF, ni montage, ni démarrage moteur.

## Fichiers et vérification

- contrat :
  [`internal-solid-repair-f49.json`](../twins/reference-917-engine/internal-solid-repair-f49.json) ;
- rapport public :
  [`f49-solid-public-report.json`](../twins/reference-917-engine/evidence/f49-solid/f49-solid-public-report.json) ;
- manifeste :
  [`publication.json`](../twins/reference-917-engine/evidence/f49-solid/publication.json).

```bash
python3 twins/reference-917-engine/source/publish_internal_solid_repair_f49.py \
  --project-root . --check
python3 tests/test_917_f49_internal_solid_repair.py -v
```

Les STEP, STL, BREP, OBJ et MSH dérivés du scan sont volontairement absents du
dépôt. Le rapport publie seulement des empreintes et métriques assainies.
