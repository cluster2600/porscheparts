# Porsche 917 — définition géométrique F38 et écran LPBF

F38 est une correction de direction, pas une libération industrielle. La peau
visible reste celle du scan F37; le précédent concept à volume rectangulaire a
été abandonné. La reconstruction applique seulement un offset normal uniforme
de 0,45 mm, conditionnel à l'échelle supposée du scan.

Le livrable sépare volontairement trois niveaux :

1. **STL maître local** — 857 330 triangles, morphologie et topologie F37
   conservées, aire 198 806,73 mm² et volume 1 146 833,25 mm³ sous l'hypothèse
   d'échelle.
2. **STEP facetté de contrôle** — 7 000 faces, un solide OCCT valide après
   réimport, mais échec de maillage volumique Gmsh. Il n'est pas CAE-ready.
3. **Noyaux fonctionnels hérités** — chambre et quatre conduits F36, galeries
   d'huile F37, plus les STEP F37 du porte-culbuteurs, des quatre enveloppes de
   culbuteurs et des deux axes. Leur intégration dimensionnelle F38 n'est pas
   prouvée.

Le rapport vérifiable est
`twins/reference-917-engine/evidence/f38-brep-lpbf/f38-brep-lpbf-report.json`.
Il consigne les trois résolutions de flood-fill voxel, l'échantillonnage réel
d'épaisseur, le calcul d'overhang sur le STL maître réouvert et l'échec Gmsh.

## Reproduction géométrique

Dans un environnement `linux/amd64` ou macOS possédant `trimesh`, `pymeshlab`,
`build123d` et OCCT :

```bash
python3 twins/reference-917-engine/source/build_f38_brep_lpbf.py \
  --contract twins/reference-917-engine/f38-brep-lpbf-contract.json \
  --f37-head-stl work/917-scan-conforming-f37/head-mesh-proof/917-head-f37-printable-proof.local.stl \
  --output work/917-scan-conforming-f38/brep-lpbf
```

L'empreinte du parent est contrôlée avant génération. Le script produit le STL
maître local, le proxy STL, le STEP facetté et un rapport de génération. Le
rapport publié reste l'autorité pour les portes de validation.

## Travaux obligatoires avant fabrication

- remplacer l'offset global par des corrections locales avec carte d'épaisseur
  exhaustive et reconstruction des sièges, guides, deck, filetages et plans;
- supprimer ou rendre accessibles toutes les cavités jusqu'à convergence de
  l'étude voxel et maillage volumique indépendant;
- revoir l'orientation et la géométrie pour descendre réellement sous 0,5 % de
  support, puis simuler le procédé avec la machine, le lot poudre et la stratégie
  de balayage retenus;
- qualifier la carte matière à chaud sur coupons imprimés, usinés et traités;
- réaliser CMM/CT, ressuage, étanchéité, banc de flux et banc moteur corrélé;
- faire approuver la définition par un ingénieur responsable.

Jusqu'à ces preuves, `metal_print_authorized` et `engine_start_authorized`
restent à `false`.
