# Porsche 917 — checkpoint d'ingénierie F38

## Décision

Le rendu parallélépipédique présenté au début de F38 est rejeté. Il s'agissait
d'un volume de mise au point des booléens et non d'une culasse crédible. Aucun
résultat dérivé de cette géométrie n'est retenu.

La géométrie F38 retenue conserve la connectivité de la peau F37 issue du scan
et applique un offset construit de 0,45 mm. Cette opération conserve la
morphologie extérieure, mais ne produit pas les surfaces fonctionnelles
paramétriques nécessaires à une CAO de production.

Le verdict est donc **NON IMPRIMABLE / NON DÉMARRABLE**. Ce refus est un
résultat d'ingénierie, pas un manque de calcul.

## Ce qui existe réellement

- peau locale étanche de 857 330 triangles, liée par SHA-256 et non publiée
  avec le dépôt ;
- proxy B-Rep OCCT facetté, un seul solide valide au round-trip, mais non
  maillable dans Gmsh ;
- distribution conditionnelle : quatre soupapes, quatre guides, quatre sièges,
  huit ressorts, quatre culbuteurs et deux axes, tous en composants analytiques
  séparés ;
- dix STEP analytiques séparés représentant 35 solides fermés et valides au
  réimport OCCT ;
- refroidissement recalculé avec deux maillages OpenFOAM et une corrélation
  indépendante de Gnielinski ;
- plan physique de qualification matière de 168 coupons ;
- film technique de 24 secondes construit uniquement avec les artefacts F38
  retenus.

## Résultats qui ferment la libération

| Domaine | Résultat F38 | Critère | Décision |
|---|---:|---:|---|
| Épaisseur minimale échantillonnée | 0,00497 mm | au moins 1,5 mm | échec |
| Volume piégé, voxel 1 mm | 106 mm³, étude non convergée | 0 mm³ à toutes les résolutions | échec |
| Surface à supporter à 45 degrés | 10,3707 % | moins de 0,5 % | échec |
| Maillage volumique du STEP | intersection segment/facette PLC | domaine 3D valide | échec |
| OpenFOAM, coefficient d'échange | 202,09 / 201,84 W/m²K | étude de grille | accord 0,122 % |
| Gnielinski et rendement d'ailette | 193,94 W/m²K | écart inférieur à 20 % sur h | accord 4,08 % |
| Perte de charge entre méthodes | écart 61,72 % | moins de 20 % | échec |
| Température de pont projetée | 375,8–381,2 degrés C | au plus 260 degrés C | échec |
| CHT de culasse complète | non exécutée | complète et convergée | échec |
| CalculiX porte-axes, max brut fin | 137,03 MPa | convergence de grille inférieure à 10 % | échec, variation 16,54 % |
| CalculiX porte-axes, p99 fin | 31,63 MPa | convergence de grille inférieure à 10 % | passe, variation 0,055 % |
| Carte matière CP1 à chaud | 168 coupons planifiés, 0 exécuté | carte qualifiée | échec |

Le canal OpenFOAM comporte 17 280 puis 138 240 cellules. Son bilan énergétique
fin ferme à 1,77 %. L'accord sur le coefficient d'échange ne suffit pas à
valider la culasse : la perte de charge diverge, la surface thermique globale
reste la peau parente du scan et la conduction 3D solide-air n'est pas résolue.

Le calcul CalculiX du porte-axes emploie trois maillages C3D4, de 191 984 à
736 856 éléments. Le percentile 99 et le déplacement convergent, mais le
maximum nodal brut ne converge pas. Les directions de charge, les contacts
non linéaires, la matière à chaud et la fatigue restent non validés : ce calcul
est un écran linéaire et non une preuve structurelle.

## Matière

Le candidat reste **EOS Aluminium Constellium CP1**, processus LPBF EOS M 290
à couche nominale de 60 micromètres. Il s'agit d'un choix conditionnel et non
d'une matière libérée. Les données fournisseur ne sont pas promues en
contraintes admissibles de calcul. La campagne prévoit traction à chaud, LCF,
HCF, fluage, conductivité, dilatation, densité, métallographie et CT, avec
orientations et lots séparés.

Sources officielles :

- <https://www.eos.info/metal-solutions/data-sheets/all-processes-and-materials?id=eos-aluminium-constellium-cp1>
- <https://www.constellium.com/news/aheadd-r-cp1-constelliums-high-performance-aluminium-additive-manufacturing-powder-approved-for-use-on-formula1-racing-cars>

## OpenFOAM, ICEengineFoam et Cantera

F38 exécute OpenFOAM 14 sur le passage canonique entre ailettes. Le rapport F37
reste la frontière de preuve pour ICEengineFoam : aucun exécutable portant ce
nom n'était disponible. Le seul cas moteur mobile réellement exécuté est le
tutoriel officiel OpenFOAM 13 XiFluid/engine2Valve2D, générique, 2D et à deux
soupapes ; il ne contient pas la géométrie F38.

Cantera 3.2.0 a été exécuté en 0D dans F33. Sa pression reste une charge
conservatrice non corrélée : elle n'est couplée ni au tutoriel XiFluid ni à la
culasse F38. Ces deux références ne constituent donc pas une validation de
combustion ou de puissance.

## Chemin reproductible

    make 917-f38-brep-lpbf-evidence-check
    make 917-f38-cooling-evidence-check
    make 917-f38-material-coupon-plan-check
    make 917-f38-valvetrain-package-evidence-check
    make 917-f38-engineering-check

Le film source se trouve sous videos/917-head-f38-functional. Son contrôle
HyperFrames doit être vert avant tout nouvel export :

    cd videos/917-head-f38-functional
    npm run check
    npm run render

## Conditions minimales avant impression

1. produire un B-Rep paramétrique de production à partir des surfaces
   fonctionnelles du scan ;
2. corriger toutes les zones sous 1,5 mm et prouver l'absence de volume fermé ;
3. ramener les supports sous le seuil ou définir une stratégie de retrait
   accessible ;
4. obtenir un maillage volumique indépendant puis une CHT et une fatigue
   thermomécanique convergées ;
5. qualifier CP1 à chaud sur la machine, le lot, l'orientation, le traitement
   et les témoins réellement utilisés ;
6. vérifier l'échelle, les interfaces 917, l'usinage, CT/CND, CMM, banc de flux
   et banc moteur.

Tant qu'un seul de ces points reste ouvert, le dépôt doit conserver les portes
d'impression métal et de démarrage moteur à faux.
