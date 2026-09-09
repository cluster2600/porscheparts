# F33 — campagne virtuelle intégrée de la culasse 917 2V/4V

## Décision d'ingénierie

F33 exécute la campagne virtuelle la plus complète possible avec la contrainte
suivante : le scan 3D existant restera l'unique source de mesure. Le programme
ne prévoit donc ni nouvelle métrologie, ni tomographie d'une pièce fabriquée,
ni banc physique. Le résultat maximal est un **concept solveur feuille blanche
borné par le scan**, pas une réplique dimensionnellement certifiée.

Le criblage désigne l'architecture **4 soupapes** comme meilleure base de
performance : +20,45 % de débit CFD sur le maillage fin, +4,27 % de puissance
0D à 9 000 tr/min et une paroi de chambre estimée 21,1 °C plus froide. Elle
atteint 1 644,9 ch dans le modèle 0D, contre 1 577,6 ch pour la 2V.

Cette victoire aérodynamique n'est pas une libération de définition. Les deux
architectures échouent le criblage fatigue/thermomécanique : dommage de Miner
supposé de 7,36 en 2V et de 34,81 en 4V, pour une limite de 1. La 4V augmente
aussi la pression cylindre maximale du point 9 000 tr/min de 17,21 à
18,80 MPa. La conclusion de F33 est donc : **poursuivre la 4V comme architecture
de développement, mais ne pas imprimer et ne pas démarrer ce moteur**.

![Concept produit 4V issu du STL solveur](../twins/reference-917-engine/evidence/f33/figures/product-4v-functional-cad.png)

![Comparaison virtuelle 2V/4V](../twins/reference-917-engine/evidence/f33/figures/integrated-2v-4v.png)

## Autorité géométrique et remplacement des essais indisponibles

Le scan ne contient pas les culasses et son échelle absolue n'est pas
confirmée. L'alésage de 90 mm reste une graine documentaire/de conception, pas
une mesure extraite du scan. F33 ne transforme pas des données synthétiques en
preuves physiques :

| Suite industrielle demandée | Exécution F33 | Limite permanente en mode scan seul |
|---|---|---|
| Métrologie F27/F30 | 30 répétitions synthétiques sur 8 caractéristiques, biais d'échelle injecté puis estimé | aucune mesure CMM/CT réelle; portes F27/F30 fermées |
| CAO complète | B-rep solveur étanche 2V et 4V avec chambre, conduits, sièges, guides, bougie, fixations, jacket et galerie d'huile | pas de filetages, états de surface, tolérances, contacts de sièges, porte-arbres ou manifolds complets |
| Carte matériau à chaud | courbe AlF357 supposée de 20 à 300 °C pour sensibilité | ni fiche fournisseur à chaud, ni éprouvette, ni lot poudre/machine qualifié |
| CFD admission | 6 cas OpenFOAM 13 compressibles, gaz parfait, RANS k-ω SST | conduits équivalents fixes; pas des runners 3D complets ni des soupapes mobiles |
| CHT | réseau conjugué de résistances thermiques avec bilan énergétique fermé | pas de CHT 3D conjuguée |
| Fatigue/TMF | Basquin-Miner sur contraintes élastiques F31 et température F33 | pas de plasticité, fluage, contrainte moyenne, défauts de surface ou courbe TMF qualifiée |
| CT/CND | Monte-Carlo de 20 000 défauts et étude POD synthétique | aucune pièce réelle inspectée |
| Banc de flux | modèle quasi-stationnaire à 6,95 kPa | aucune mesure corrélée |
| Banc moteur | cycle 0D Wiebe à sept régimes | aucun dynamomètre ni jeu de validation tenu à l'écart |

Le maximum de |z| de l'exercice métrologique est 0,365 et la correction
retrouve le biais d'échelle injecté à 6,14 ppm près. Cela valide seulement la
chaîne de calcul synthétique, pas les dimensions d'une culasse réelle.

## CAO fonctionnelle solveur

Gmsh/OpenCASCADE produit un volume B-rep unique par architecture et les dérivés
STEP/STL de travail. Les fichiers géométriques restent sous `work/` et ne sont
pas publiés comme pièces fabricables; le dépôt ne versionne que le manifeste et
les empreintes SHA-256.

| Architecture | Volume solveur | Nœuds surface | Éléments surface | Classement |
|---|---:|---:|---:|---|
| 2V | 802 923 mm³ | 5 487 | 11 022 | substitut solveur, pas CAO de fabrication |
| 4V | 779 628 mm³ | 6 343 | 12 758 | substitut solveur, pas CAO de fabrication |

## Résultats aérodynamiques et thermiques

Le premier essai CFD incompressible a été refusé : il ne convergait pas en
maille et produisait un régime supersonique incompatible avec son hypothèse.
F33 conserve ce run dans `work/` comme diagnostic et publie uniquement la
relance compressible stabilisée.

| Résultat | 2V | 4V | Lecture |
|---|---:|---:|---|
| Banc de flux virtuel, pic | 174,8 cfm | 201,5 cfm | +15,28 % 4V |
| CFD fin, débit massique | 0,11334 kg/s | 0,13652 kg/s | +20,45 % 4V |
| Mach moyen CFD fin | 0,463 | 0,467 | modèle compressible requis |
| Variation maille moyenne→fine | 7,53 % | 7,77 % | sous le seuil F33 de 8 %, marge faible |
| Température paroi chambre, CHT réduit | 234,4 °C | 213,3 °C | −21,1 °C 4V |
| Puissance 0D à 9 000 tr/min | 1 577,6 ch | 1 644,9 ch | cible 1 600 ch franchie seulement par le modèle 4V |
| Pression cylindre max à 9 000 tr/min | 17,21 MPa | 18,80 MPa | charge structurelle supérieure en 4V |

La cible 1 600 ch reste une exigence. L'atteindre dans le modèle 0D ne prouve
ni la puissance réelle, ni la tenue, ni le refroidissement d'un moteur.

## Matériau, soupapes et ressorts

Le choix de criblage reste l'AlF357 LPBF pour la culasse, devant l'AlSi10Mg
dans F29. La référence [EOS Aluminium AlF357](https://www.eos.info/metal-solutions/metal-materials/data-sheets/mds-eos-aluminum-alf357)
documente le matériau et les procédés compatibles; elle ne qualifie pas la
courbe à chaud supposée par F33. Cette courbe ne peut donc pas ouvrir la porte
matériau.

La distribution retenue au niveau conceptuel reste achetée et non imprimée :

- admission : soupape Ti-6Al-4V forgée ou usinée ;
- échappement : soupape INCONEL 751 ;
- ressort : acier silicium-chrome trempé à l'huile, nitruré et grenaillé en
  plusieurs étapes.

Les revêtements, couples siège/tige, diamètre de fil, géométrie de spire,
hauteur montée et spécification fournisseur ne sont pas définis. Il s'agit
d'une sélection de technologie, pas d'une nomenclature achetable validée.

## Fatigue/TMF et CND virtuel

L'AlF357 supposé donne une marge de limite élastique à chaud de 0,738 pour la
2V et de 0,720 pour la 4V. Les deux valeurs sont inférieures à 1 et concordent
avec l'échec Miner. Le prochain cycle numérique doit réduire la contrainte des
ponts de sièges et du deck 4V, renforcer localement les ligaments et améliorer
le chemin de refroidissement avant toute nouvelle optimisation de débit.

L'étude CND synthétique indique qu'un voxel de 60 µm dépasserait la cible POD
virtuelle de 90 % sur les défauts critiques. Les voxels de 100 et 200 µm
échouent avec 84,9 % et 10,7 %. Cette résolution de 60 µm devient une
spécification de simulation; elle n'est pas une démonstration de détection
réelle.

![POD CND virtuel](../twins/reference-917-engine/evidence/f33/figures/virtual-ndt-pod.png)

## Reproductibilité, PhysicsNeMo et Omniverse

L'image CAE est construite nativement sur ARM64 et sur la machine Kali
`testmachineit` en x86_64. Le cas représentatif `2v/coarse` donne exactement
0,1420326827536 kg/s sur les deux architectures avec OpenFOAM 13. Le répertoire
temporaire distant a été supprimé après le test.

La forme de données PhysicsNeMo est un ensemble de champs de maillages surface
et volume non structurés. Les candidats vérifiés sont DoMINO, Transolver,
FIGConvUNet et MeshGraphNet. F33 ne fournit que 6 cas classiques, contre le
minimum contractuel de 200, et aucun jeu physique tenu à l'écart : aucun
entraînement de substitut n'est donc autorisé.

Le préflight NVIDIA CAD-to-SimReady accepte les chemins d'entrée/sortie, puis
se bloque avant conversion : OpenUSD Python, Asset Validator,
`usd-convert-cad`, SimReady Foundation et Content Agents ne sont pas prêts, et
les services material/OVRTX/physics ne répondent pas. Aucun USD n'a été créé et
aucune validation SimReady n'est revendiquée.

## Reproduction

```sh
make 917-integrated-virtual-f33-image
make 917-integrated-virtual-f33
# exécuter le préflight NVIDIA officiel sur le STEP 4V sous work/
make 917-integrated-virtual-f33-publish
make check
```

Les preuves publiées sont :

- [rapport intégré F33](../twins/reference-917-engine/evidence/f33/report.json) ;
- [manifestes et empreintes de CAO](../twins/reference-917-engine/evidence/f33/functional-cad/geometry-report.json) ;
- [préflight Omniverse bloqué](../twins/reference-917-engine/evidence/f33/omniverse/preflight.md) ;
- [validation croisée x86/ARM](../twins/reference-917-engine/evidence/f33/toolchain/x86-cross-check.json) ;
- [manifeste de publication](../twins/reference-917-engine/evidence/f33/publication.json).

Toutes les portes de libération restent à `false`, notamment métrologie
physique, CAO de fabrication complète, carte matériau à chaud, CFD/CHT 3D,
fatigue/TMF, CT/CND, corrélation banc de flux, corrélation banc moteur, revue
professionnelle, impression métal et démarrage moteur.
