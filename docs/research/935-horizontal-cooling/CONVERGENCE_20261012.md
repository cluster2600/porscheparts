# 935 — comparaison au scan et raffinement numérique

[Dossier](README.md) · [Candidat et solveurs](CONTINUATION_20261012.md) ·
[Plan](RECONSTRUCTION_PLAN.md) · [Banc](BENCH_PROTOCOL.md)

La livraison précédente est fusionnée par la
[PR #173](https://github.com/cluster2600/porscheparts/pull/173).
Cette campagne révèle deux limites : la répétition d'une pale ne reproduit
pas encore toutes les surfaces acquises ; les contraintes maximales restent
sensibles au maillage. Elle caractérise le candidat sous hypothèses, sans
qualifier une réplique de montage ni sa fabrication.

## Comparaison géométrique

Les fonctions existantes de `review_reconstruction.py` échantillonnent les
surfaces uniformément par aire et calculent les distances aux triangles.
Chaque pale fournit **2 000 points acquis vers le candidat** et **1 000 points
du candidat vers la région acquise**, avec graines enregistrées.
Les plages radiales sont 98–136 unités source pour le scan, 100–134 pour le
candidat. Cette garde réduit l'effet des bords artificiels de découpe.
Les phases acquises définissent les secteurs. Pieds, extrémités et moyeu
ne sont pas évalués ; leurs lacunes ne deviennent pas des observations.

| Pale | RMS scan → candidat | P95 scan → candidat | RMS candidat → zone acquise |
|---|---:|---:|---:|
| 00, utilisée pour la construction | 0,386 | 0,881 | 0,225 |
| 01 | 0,954 | 1,595 | 0,838 |
| 02 | 1,562 | 2,099 | 1,608 |
| 03 | 1,721 | 2,763 | 1,674 |
| 04 | 1,142 | 2,184 | 1,157 |
| 05 | 1,049 | 1,344 | 0,423 |
| 06 | 0,971 | 1,925 | 0,979 |
| 07 | 0,883 | 1,775 | 0,679 |
| 08 | 0,818 | 1,539 | 0,735 |

Les distances sont en **unités source non calibrées**. Le scénario suppose
1 mm par unité ; cette hypothèse ne certifie pas la métrologie. Les huit
autres pales n'ont pas servi à l'ajustement périodique, mais appartiennent
à la même acquisition : elles ne vérifient pas indépendamment l'échelle.

La carte multivue est inspectée visuellement et conservée en privé avec les
points, distances et empreintes. Les écarts s'étendent sur les surfaces
acquises. Ils justifient de reprendre le recalage des acquisitions et
l'ajustement commun des pales avant de retenir la périodicité pour une
réplique exacte. Aucun recalage arbitraire ne masque ces écarts.

Une première comparaison par secteur incluait de petits fragments non
classifiés et donnait jusqu'à 2,251 unités RMS. Elle est conservée séparément.
Le tableau ci-dessus utilise les neuf composantes significatives identifiées
par la segmentation existante : coupure radiale à 94 et au moins 5 000 sommets.
Les trois petits groupes de 433, 196 et 22 sommets restent dans le scan et
sont explicitement exclus de cette comparaison des pales ; aucun trou
ou fragment n'est modifié. Leurs fonctions mécaniques restent inconnues.

## Raffinement centrifuge

Ces trois grilles utilisent le **même champ signé PicoGK à 0,2 mm**, le
même STL, AlSi10Mg isotrope, 6 000 tr/min et Poisson supposé de 0,33.
Elles sont connectées, conservent le bore nominal, passent les Jacobiennes
Gmsh et restent à moins de 5 % du volume CAO. CalculiX 2.21 s'exécute en série,
dans un nouveau dossier par deck.

| Pas, mm | C3D8 | Volume, mm³ | Contrainte maximale, MPa | P95, MPa | Déplacement maximal, mm |
|---|---:|---:|---:|---:|---:|
| 1,40 | 155 702 | 427 246 | 150,60 | 28,92 | 0,13991 |
| 1,25 | 215 328 | 420 563 | 133,83 | 28,80 | 0,13845 |
| 1,20 | 241 327 | 417 013 | 147,18 | 29,03 | 0,13437 |

Entre les deux grilles finales, les variations relatives à la grille fine
sont **9,07 % pour le maximum**, **0,81 % pour le P95** et **3,04 % pour le
déplacement**. Le P95 décrit tous les points d'intégration ; il ne remplace
pas un contrôle des contraintes locales non singulières ou de fatigue.
Le maximum et sa localisation varient aux jonctions non qualifiées.
La convergence complète reste ouverte.

Les réactions du bore sont confrontées à la résultante centrifuge calculée
indépendamment depuis les centres et volumes des cellules. L'erreur relative
reste sous **6 × 10⁻⁸** pour ces trois cas. Cet équilibre vérifie les efforts
appliqués, sans qualifier les contacts ou appuis du système réel.

La tolérance de sélection de l'encastrement égale le pas de grille : la
frontière et la sélection nodale changent au raffinement. Interfaces
analytiques et raccordements définis restent nécessaires. Pression, thermique,
modes précontraints, fatigue, transmission et vitesse admissible restent ouverts.

Un calcul à 1,4 mm sur le champ de 0,4 mm donne 131,45 MPa et 0,14395 mm.
Ce diagnostic de sensibilité est séparé de la comparaison à champ commun.
Les rejets sont conservés : dépassement de volume à 1,3 mm et éléments
déconnectés à 1,2 mm sur le champ de 0,4 mm.

Le plafond d'échantillonnage PicoGK passe de deux à quatre millions de
cellules candidates après contrôle des **64 Go du Mac**. Cette grille est
parcourue sans allouer un solide par hypothèse. La limite de 300 000 éléments
conservés et les contrôles géométriques restent inchangés.

## Contrôle du calcul d'air

Le cas reste un conduit carré hypothétique : débit imposé de 0,6 m³/s,
6 000 tr/min. La préparation utilise désormais `relTol 0`, `tolerance 1e-9`
pour pression/vitesse/turbulence et deux corrections non orthogonales.
La campagne stationnaire est prolongée à 1 800 itérations.

`assess_candidate_cfd.py` contrôle les empreintes des entrées préparées,
le maillage, la fin du solveur et les historiques synchronisés. Il calcule
la pression totale moyenne surfacique en Pa depuis la pression cinématique
et `|U|²`, puis le couple résistant depuis le moment fluide.
Deux fenêtres successives de 100 itérations sont exigées : étendue finale
et écart des moyennes sous 1 % pour pression/couple, déséquilibre volumique
et écart au débit imposé sous 0,1 %.

Oscillation, dérive, fuite, données incomplètes/non finies ou entrées modifiées
empêchent l'acceptation. Un point accepté sur un maillage ne devient jamais
une courbe 935 validée : trois maillages, parois, carter et conditions réelles
restent nécessaires.

```sh
python twins/935-horizontal-cooling-system-f0/source/assess_candidate_cfd.py \
  work/new-cfd/artifacts/coarse work/new-cfd-assessment
```

La sortie doit être neuve et privée sous `work/`. Le rapport conserve séries
et empreintes. Les fichiers d'entrée de cette exécution ont été confrontés
octet par octet à une préparation indépendante pendant le calcul ; cette
chronologie est enregistrée dans les métadonnées.

## Conservation, vérification et suite

Scripts d'analyse, paramètres, résultats bruts, cartes et rejets sont conservés
dans le [dépôt privé](https://github.com/cluster2600/porscheparts-935-private).
Les scans originaux, transformations et anciennes preuves sont préservés.
Le Git public reçoit les contrôles numériques et leur documentation.
Les contrôles 935 passent : **78 tests**, dont **18 tests du candidat et de
l'analyse CFD**. `make check` est exécuté par la CI Linux avant fusion.

La priorité géométrique est le recalage du dos et des pales, puis leurs
raccordements mesurés. Un calcul transitoire doit être évalué si le pilote
stationnaire reste instable. Les 17 interfaces de montage, le mécanisme,
les procédés et le banc restent à établir. Les contrats et autorisations de
fabrication/validation physique restent inchangés à `false`. Aucun Vast
n'est lancé pour ce lot.
