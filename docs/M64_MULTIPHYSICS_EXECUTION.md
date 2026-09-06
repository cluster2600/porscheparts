# M64 — périmètre de simulation multiphysique

## Décision utilisateur

Base M64 964/993, objectif turbo, quatre soupapes par cylindre et comparaison
deux soupapes. La variante précise reste ouverte. Conserver la silhouette
Porsche issue des références pertinentes : aucune enveloppe ovale de substitution.
Les anciens modèles 917/935 ne sont pas des interfaces M64 validées.

## Ordre d'exécution et preuves attendues

1. **Interfaces** : établir un tableau sourcé des goujons, registres de cylindre,
   plans de joint, distribution, admission/échappement et lubrification. Séparer
   cotes publiées, déductions et inconnues ; conserver variantes et tolérances.
2. **CAO d'assemblage** : reconstruire les surfaces fonctionnelles, sièges,
   guides, distribution, fixations et surépaisseurs d'usinage. Corriger les
   défauts de parois et de maillage. Vérifier les jeux à froid avant simulation.
3. **Charges turbo** : définir régime, charge, carburant, suralimentation,
   pression cylindre et états thermiques comme scénarios traçables. Employer
   Cantera pour les études thermochimiques appropriées ; aucun mécanisme ni
   résultat zéro dimension ne constitue une validation CFD tridimensionnelle.
4. **Thermique complète** : CFD/CHT OpenFOAM sur gaz, solide et air de
   refroidissement ; comparer air seul et assistance huile. Inclure pertes de
   charge et puissance auxiliaire. Contrôler conservation d'énergie, convergence
   temporelle et spatiale sur trois niveaux, puis contre-calcul indépendant.
5. **Résistance complète** : éléments finis avec propriétés à chaud, pression
   cylindre, précharges, contacts siège/guide et champs thermiques transférés.
   Évaluer déplacements, étanchéité, plastification et fatigue thermomécanique
   selon les données disponibles. Contrôler convergence et équilibre des efforts.
6. **Distribution** : jeux piston/soupapes et soupapes/soupapes sur le cycle,
   dilatation, ressorts, contacts et dynamique selon loi de came documentée.
   Une animation prescrite n'établit ni absence d'affolement ni durée de vie.
7. **Fabrication LPBF** : matériau-machine-recette identifiés, orientation,
   supports accessibles, dépoudrage, surépaisseurs, distorsions, traitement
   thermique et usinage. AdditiveFOAM local ne remplace pas un calcul complet
   de déformation de construction ; corriger les échecs numériques existants.
8. **Omniverse** : inspecter l'assemblage, les mouvements et les interférences ;
   afficher les champs calculés avec unités, légendes, cas et provenance.
   Distinguer résultats importés, animation et dynamique réellement résolue.

## Contrôle initial du 6 septembre 2026, avant les tentatives Vast

- Kali 192.168.2.3 répond en SSH ; architecture x86_64 et Docker accessibles.
- Le prévol local du skill `omniverse-cad-to-simready` a échoué : OpenUSD et
  Asset Validator absents du runtime interrogé, checkouts requis absents et
  services OVRTX/Material/Physics non prêts. Aucun calcul Omniverse exécuté.
- Rapport local : `/private/tmp/m64-omniverse-preflight-20260906/report.json`.
- Aucune location Vast effectuée lors de ce contrôle initial. Deux tentatives
  ultérieures et leur suppression sont consignées dans
  `M64_VAST_EXECUTION_20260906.md` ; aucune instance ne reste active après celles-ci.
- Le workflow du skill est arrêté au prévol ; ce blocage logiciel ne suspend
  pas la recherche documentaire des interfaces M64.

## Critère de livraison

Publier les preuves et les échecs pour chaque cas, sans transférer les anciens
résultats 917 à M64. La comparaison deux/quatre soupapes utilise les mêmes
conditions imposées et tient compte des incertitudes. Aucun résultat virtuel
ne remplace la qualification matière/procédé, l'inspection de la pièce et la
corrélation au banc ; aucune autorisation de fabrication moteur n'est acquise.

## Intégration de la pile demandée dans les photos

Les logiciels ne sont pas interchangeables ni tous des solveurs. La sélection
suivante définit leur rôle, pas une déclaration d'installation ou de réussite.

| Fonction | Briques demandées et rôle |
| --- | --- |
| Interfaces exactes et CAO | OCCT/OCP avec build123d, CadQuery ou FreeCAD ; conserver un maître fonctionnel éditable |
| Géométrie de refroidissement | PicoGK/ShapeKernel ; HelixHeatX comme exemple de construction, pas modèle thermique de culasse |
| Scan et maillage | Open3D/Trimesh/PyMeshLab/MeshFix selon défaut, Gmsh/meshio ; chaque réparation comparée à la source |
| Gaz moteur et chaleur | OpenFOAM/ICengines et Cantera ; loi Wiebe explicitement distincte d'une combustion CFD résolue |
| Contre-calcul | FluidX3D seulement sur un problème physique effectivement couvert et comparable ; licence d'usage à vérifier avant usage commercial |
| Thermomécanique | CalculiX ; Code_Aster ou Elmer comme candidat indépendant selon contacts et lois matière nécessaires |
| Fabrication | AdditiveFOAM pour le procédé local, complété par un modèle de distorsion de construction entière |
| Inspection et rendu | OpenUSD, Omniverse/SimReady/OVRTX, ParaView/PyVista/Blender ; aucun rendu n'est une preuve de résistance |
| Modèles réduits | PhysicsNeMo/PyTorch après obtention d'un jeu de calculs éligibles ; Qwen/vLLM n'est pas un solveur ni une autorité de validation |
| Exécution | Docker/CI/GHCR, Kali et Vast via le wrapper OpenBao autorisé |

Avancement de cette reprise : voir `M64_INTERFACE_SOURCE_REGISTER.md`,
`M64_LEAP71_STACK.md`, `M64_CHT_RUNTIME_SMOKE.md` et
`M64_VAST_EXECUTION_20260906.md`. Les preuves de l'ancien projet 917 restent
historiques ; elles ne sont pas renommées en preuves M64.

Vérifications de cette reprise : `make check` complet réussi, puis sept tests
ciblés du contrat M64 réussis après ajout des pistes du manuel. Le test natif
PicoGK linux/amd64 a été répété indépendamment sur Kali. Ces contrôles de
logiciel et de dossier ne constituent pas une validation de la pièce.
