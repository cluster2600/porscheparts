# M64 G2 — conduits, refroidissement, galerie et taux de compression

**Statut : jumeau de conception, non revu. Fabrication et démarrage moteur non autorisés.**
Aucune cote de cette page n'est mesurée sur une culasse M64 : les formes ajoutées ici sont des
hypothèses de conception, déclarées `unsourced` dans `params-g2/head_features.json`.

## Pourquoi un G2

Le jalon G1 (`docs/reports/M64_G1_FOUR_VALVE_SKELETON_20260914.md`) livrait un squelette : chambre
en toit, sièges, guides, logements de ressort, puits de bougie, goujons — mais des **conduits
droits**, **ni ailettes**, **ni galerie d'huile**, et **aucun critère de combustion**. Le lot G1
défini dans `docs/reports/M64_RESEARCH_EXECUTION_20260912.md` demandait pourtant conduits, huile et
plans. G2 comble la part réalisable sans mesure nouvelle.

G2 s'active par `--extra-params` : sans ce fichier, `layout.cylinders`, la CAO et les contrôles sont
identiques à G1, dont les preuves restent reproductibles à l'octet près.

## Ce que G2 ajoute

| Élément | Forme | Contrôles |
|---|---|---|
| Conduits | Bézier cubique de la gorge (tangent à l'axe de soupape) à la bride (perpendiculaire), en segments partagés entre numpy et CAO ; les deux conduits d'un côté se rejoignent au centre de la bride | parois conduit/goujon, conduit/puits de bougie, conduit/logement de ressort |
| Galerie d'huile | perçage traversant en y, sous la face porte-arbre | parois vers logements, guides, bougies, goujons, conduits ; distance à la face porte-arbre |
| Ailettes | plaques horizontales sur les faces ±y, entre les brides | hauteur sous la face porte-arbre ; interférence avec la culasse voisine **non calculable** (entraxe des cylindres non sourcé) |
| Taux de compression | volume mort BRep au PMH d'allumage : cylindre d'alésage moins culasse, sièges, soupapes fermées et piston | plage cible en hypothèse, **bloquant** pour l'acceptation ; proxy numpy calibré non bloquant, utilisé comme filtre de recherche |

## Découverte principale : la chambre G1 est trop volumineuse

Mesuré en BRep sur la configuration G1 acceptée (alésage 100, course 76,4) :

| Grandeur | Valeur |
|---|---|
| Angles de soupape retenus en G1 | 33,4° admission, 24,6° échappement (58° inclus) |
| Hauteur d'arête du toit | 27,5 mm |
| Volume mort | 171,8 cm³ |
| Volume balayé | 600,0 cm³ |
| **Taux de compression** | **4,49** |

Un moteur turbo se situe usuellement vers 8:1 ; aucune valeur M64 n'est sourcée dans le dépôt, la
plage 8 à 9 retenue ici est donc une hypothèse. La cause est claire : **l'itération G1 n'avait aucun
critère de combustion** et maximisait les jeux, ce qui pousse les angles vers le haut de leur borne.

## Deux calculs du volume mort, un seul juge

Le proxy numpy intègre le toit sur le disque d'alésage, moins la calotte du piston. Deux défauts
distincts le séparaient du BRep ; ils ne se traitent pas de la même façon.

**Une omission, corrigée.** Il ne comptait ni les poches de soupape ni le bol autrement que par un
cylindre : il ajoutait le bol et ignorait les poches. Il reprend désormais `crown_depression`, la
même fonction que la cinématique, recouvrements et débordements d'alésage compris. Sur la
configuration G1 (poches de 3,92 mm) cela vaut **16,8 cm³** : 116,7 cm³ avant, 133,5 après.

**Un biais résiduel, assumé et borné.** Restent les logements de sièges, les gorges et les conduits
qui débouchent dans la chambre. Mesuré en BRep sur quatre configurations, ce biais n'est ni un
facteur constant ni un décalage constant : il croît avec l'arête du toit.

| Angles | Arête | Proxy brut | BRep | Facteur |
|---|---:|---:|---:|---:|
| 16° / 16° | 14,67 | 77,15 cm³ | 82,94 cm³ | 1,075 |
| 22° / 22° | 18,80 | 89,79 | 108,52 | 1,209 |
| 28° / 28° | 22,79 | 99,70 | 132,13 | 1,325 |
| 33,4° / 24,6° (G1) | 27,47 | 133,50 | 171,81 | 1,287 |

`chamber_proxy_calibration` retient **1,075**, la valeur mesurée *au voisinage de la plage visée* —
c'est là que le filtre doit être juste, et il l'est : à 16° le proxy calibré donne 8,24 contre 8,23
en BRep. Ailleurs il dérive, et la dérive est publiée : sur la configuration retenue ici,
`observed_calibration` vaut 1,409 contre 1,075 supposé, soit un proxy annonçant 6,91 pour un taux
BRep réel de 5,51. C'est assumé : le proxy n'est qu'un filtre de recherche.
**Le taux BRep est le juge** : `run.py` refuse l'acceptation si le taux BRep sort de la plage, et
`compression_proxy_band_tolerance` (0,6 point) élargit la plage côté proxy pour qu'il n'écarte pas
un candidat que la mesure aurait retenu.

## Validité BRep des conduits : trois essais

La découpe d'un conduit courbe est la partie fragile. Mesures sur la configuration G1 :

| Construction | BRep valide | Solides | Remarque |
|---|---|---|---|
| Capsules découpées une par une | non | 10 | la culasse se fragmente |
| Loft de cercles normaux à la courbe | non | 14 | volume négatif : orientation inversée |
| Capsules fusionnées, sphères aux jonctions | oui | 3 | deux éclats parasites (129 mm³ et 0) |
| **Tronçons allongés d'un rayon, fusionnés en un outil, une seule découpe** | **oui** | **1** | retenu |

Les ailettes seules et la galerie seule restent valides et d'un seul solide.

## Le réglage des angles : trois essais, trois causes distinctes

**Essai 1 — balayage des deux seuls angles : 0 candidat.** Les quinze autres variables de G1
(bougies, poches de piston, calage, longueur de soupape) avaient été optimisées *pour* les angles de
G1 ; les déplacer seuls casse les ponts vers les puits de bougie. Le critère de combustion est donc
descendu dans la recherche elle-même (`iterate.compression_record`), qui replace toutes les
variables ensemble.

**Essai 2 — recherche complète : 1 070 essais, 0 accepté.** Deux fautes, pas une. D'abord le départ
chaud retirait les positions de tête de soupape pour les laisser se redériver, ce qui jetait dès le
premier essai le seul point admissible connu — or la configuration G1 passe bel et bien les
contrôles G2, conduits et galerie compris, avec une marge de 0,188 mm. Ensuite le classement laissait
« dans la plage » primer sur des essais **refusés** : la recherche locale a couru après la
compression en abandonnant la géométrie et s'est arrêtée sur un essai dans la plage mais avec six
contrôles en échec et une marge de −4,11 mm. Le critère ne départage désormais que des essais déjà
acceptés, et le départ conserve la configuration G1 entière.

**Essai 3 — recherche complète corrigée : accepté, mais bloquée à 6,17 côté proxy.** Partie de G1
(4,5), la descente par coordonnées remonte le taux puis ne trouve plus de voisin meilleur : aller
vers la plage coûte d'abord de la marge géométrique avant d'en rendre. D'où la méthode retenue, une
**continuation** : les deux angles sont figés à chaque palier, les quinze autres variables se
replacent librement, et chaque palier démarre à chaud du précédent — exactement ce que
`bore_sweep.py` fait pour l'alésage.

## Résultat : la plage 8–9 est hors d'atteinte, et on sait pourquoi

2 249 essais, 360 acceptés, 5 mesures BRep sur l'échelle des paliers (un candidat par palier) :

| Palier | Angles adm./éch. | Accepté | Marge | Proxy calibré | **BRep** | Contrainte limitante |
|---|---|---|---:|---:|---:|---|
| 1,00 | 33,4 / 24,6 | oui | 0,188 | 5,79 | 4,55 | pont adm/adm |
| 0,95 | 31,7 / 23,4 | oui | 0,315 | 6,00 | 4,74 | soupape–piston |
| 0,90 | 30,0 / 22,2 | oui | 0,306 | 6,81 | 5,28 | tête hors arête |
| 0,85 | 28,4 / 20,9 | oui | 0,313 | 6,92 | 5,43 | soupape–piston |
| **0,80** | **26,7 / 19,7** | **oui** | **0,080** | 6,91 | **5,51** | paroi goujon/logement |
| 0,75 | 25,0 / 18,5 | non | **−0,052** | 6,94 | — | **têtes hors alésage** |
| 0,70 | 23,4 / 17,2 | non | −0,560 | 7,13 | — | têtes hors alésage |
| 0,60 | 20,0 / 14,8 | non | −1,605 | 7,65 | — | têtes hors alésage |
| 0,55 | 18,4 / 14,0 | non | −2,138 | 8,03 | — | têtes hors alésage |

La descente **bute sur `valve_heads_within_bore`**, et le mécanisme est géométrique : l'empreinte
projetée d'une tête a pour demi-axe en x le produit `d/2 · cos θ`. Aplatir les soupapes élargit donc
leur empreinte, et deux têtes de 40 mm plus deux de 33 finissent par déborder d'un alésage de 100.
Le mur tombe entre 26,7° et 25,0° : le palier 0,75 échoue de **0,052 mm** sur une marge exigée de
1,0 mm.

Conséquence : dans les bornes de l'étape 1 — alésage M64 sourcé à 100, têtes Swindon sourcées à
40 et 33 — **le taux de 8:1 n'est pas atteignable**. Le meilleur taux BRep accepté est **5,51**
(volume mort 133,07 cm³), contre 4,49 pour G1 : +23 %, et toujours hors plage. Les seuls leviers
restants sortent de l'étape 1 et touchent des valeurs sourcées : réduire les diamètres de tête
(étape 3, pénalisée), agrandir l'alésage (étape 2), ou réviser des hypothèses non sourcées qui ne
sont pas des variables — jeu au plat de culasse (1,0 mm), jeux soupape–piston (1,5 / 2,0 mm).
Ce choix demande une décision, pas un calcul : il n'est pas pris ici.

Les preuves de `g2-head-features-20260916` sont donc produites sur la configuration du palier 0,80,
retenue par `--select-best-accepted` : la CAO est complète et valide, mais le manifeste porte
`accepted: false`, refusé **sur le seul taux de compression**. Les 44 contrôles géométriques passent
(marge minimale 0,080 mm), la culasse est un solide unique valide de 399 faces, et les neuf
contre-contrôles BRep de distance passent.

Conséquence d'exploitation : **un seul calcul lourd à la fois**. Un client `docker` tué laisse le
conteneur vivant : deux exécutions ont ainsi écrit dans le même fichier de sortie, et le code 137
observé venait du client, pas du conteneur (`OOMKilled=false`).

## Reproduire

```sh
FV=twins/m64-cylinder-head/source/fourvalve
# descente d'angle par paliers, puis mesure BRep d'un candidat par palier
python3 $FV/tune_compression.py work/m64-g2/compression-tuning.json \
  --method continuation --select-best-accepted --top 12
# refaire le choix et les mesures BRep sans relancer la recherche
python3 $FV/tune_compression.py work/m64-g2/compression-tuning.json \
  --reselect work/m64-g2/compression-tuning-ladder.json --select-best-accepted
# exécution complète avec la configuration retenue
python3 $FV/run.py twins/m64-cylinder-head/evidence/g2-head-features-20260916 \
  --extra-params $FV/params-g2/head_features.json \
  --fixed-design work/m64-g2/compression-tuning.json --external-dir work/m64-g2-external
```

`tune_compression.py` et `run.py` rendent 2 tant que le taux BRep reste hors de la plage : c'est le
cas aujourd'hui.

Tests : `tests/test_m64_g2_head_features.py` (conduits, galerie, ailettes, CAO et taux) et la
non-régression `tests/test_m64_g1_four_valve_twins.py`.

## Ce que G2 ne fait pas

- **Interfaces manquantes du contrat** (centrage, passage d'huile) et **entraxe des cylindres** :
  aucune donnée M64 dans le dépôt, donc ni pont entre cylindres, ni interférence d'ailettes.
- **Débit** : la forme des conduits n'est pas validée par un banc de flux ; aucune section, aucun
  rapport de gorge n'est justifié par un calcul de débit.
- **Refroidissement** : ailettes et galerie sont des formes, pas un bilan thermique. Ni débit de
  pompe, ni débit de ventilateur, ni propriété matériau à chaud ne sont sourcés.
- **Contradictions ouvertes** entre rapports (commande des soupapes, calage d'échappement, jeu
  piston, ressorts) : elles restent à trancher avec des sources.
