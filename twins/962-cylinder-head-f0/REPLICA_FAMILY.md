# Culasse 962 C : référence fidèle et famille de 3,0 à 4,0 L

**Décision du 16 octobre 2026 : prendre la 962 C 3,0 L à eau comme référence,
reconstruire sa culasse le plus fidèlement possible, puis étudier plusieurs
cylindrées jusqu'à 4,0 L.** Le [registre](replica-family.json) porte cette
nouvelle priorité. Les modèles bioniques et le [scénario Mezger 4 L SP95](MEZGER_4L_SP95.md)
restent des études de dérivés ; ils ne définissent pas la géométrie originale.

La livraison présente une définition de référence, une gamme de cibles et un
calculateur de cylindrée. **Aucune CAO de réplique mesurée n'est encore
disponible.** Le changement ne transforme pas les anciens STL en répliques.

## Référence historique et niveau de preuve

Le [dossier Porsche « 40 Years Group C »](https://newsroom.porsche.com/dam/jcr:a6f33b52-c47d-47b4-98c1-7e963661f587/40%2520Years%2520Group%2520C.pdf)
documente le 3,0 L quatre soupapes entièrement refroidi par eau aux essais du
Mans 1985 (page 8), les 2 994 cm³ des types 935/79, /82 et /83 et les
3 164 cm³ des types /79 et /86 (page 18). Cela fixe une famille ; le type,
l'année et la référence physique à copier restent à identifier.

Les pages 19–20 décrivent les ensembles aluminium cylindre–culasse soudés
par faisceau d'électrons, les alésages Nikasil, les deux arbres à cames par
banc entraînés par engrenages, les poussoirs avec pastilles et les deux
circuits d'eau indépendants avec une pompe par banc. La construction précise
doit être confirmée sur l'exemplaire choisi, avant de dessiner sa liaison.

**L'alésage/course du donneur 3,0 L reste inconnu.** Le couple 92,3 × 66 mm du
dossier concerne le 956 935/76 ; il ne sera pas transféré à la 962 C. Le
couple souvent repris de 95 × 70,4 mm n'est pas confirmé ici par une source
primaire du donneur. Le nombre de bougies reste lui aussi à établir. Les
[photos déjà examinées](ORIGINAL_ARCHITECTURE.md) montrent une ouverture
centrale et un ensemble modifié par le restaurateur ; elles ne prouvent ni
une cote ni toute la spécification d'usine.

## Gamme de travail

| Désignation | Cylindrée utilisée | Statut |
| --- | ---: | --- |
| 3,0 L référence | 2 994 cm³ | Famille historique Porsche choisie |
| 3,2 L contexte de période | 3 164 cm³ | Variante historique documentée ; culasse commune non prouvée |
| 3,4 L | 3 400 cm³ | Cible de dérivé proposée |
| 3,6 L | 3 600 cm³ | Cible de dérivé proposée |
| 3,8 L | 3 800 cm³ | Cible de dérivé proposée |
| 4,0 L | 4 000 cm³ | Plafond de la famille demandée |

Les paliers intermédiaires sont une proposition de gamme, pas des recettes
moteur approuvées. Alésage, course, rapport volumétrique, pistons, soupapes et
composants disponibles restent à sélectionner. Le calculateur accepte aussi
une cible intermédiaire dans l'intervalle 2 994–4 000 cm³.

L'ancien scénario **102 × 81,6 mm donne 4 000,660 cm³**. Ses sources et
preuves sont conservées ; il ne respecte pas strictement le nouveau plafond
de 4 000 cm³. À alésage hypothétique de 102 mm, le calcul donne une course
d'environ 81,58654 mm pour 4 000 cm³ exactement. Ce résultat algébrique ne
sélectionne pas un vilebrequin et ne constitue pas une cote de fabrication.

## Ce qui reste commun et ce qui doit être revu

Le maître historique doit conserver les surfaces, axes, distribution,
interfaces, circuit d'huile et topologie d'eau réellement mesurés. Le
[dossier de métrologie 962 C](REPLICA_METROLOGY.md) prépare cette acquisition ;
le dossier M64 existant concerne une autre base. Aucun facteur d'échelle
global n'est appliqué à la culasse, aux goujons, aux filetages ou au porte-arbres.

Une variation de **course à alésage constant** ne change pas directement le
diamètre de chambre. Elle oblige à vérifier hauteur de bloc/cylindre,
compression, forme de piston, jeux piston–culasse et piston–soupape,
cinématique de distribution, charges et refroidissement. Elle ne garantit
donc pas la réutilisation de la culasse.

Une variation d'**alésage** impose de reprendre chambre, portée/liaison
cylindre–culasse, sièges et dégagement des soupapes, épaisseurs, entraxes et
chemins d'effort. Eau, huile et distribution doivent ensuite être contrôlées
sur chaque montage. On ne peut pas encore promettre un corps de culasse
unique pour toute la gamme ni affirmer que 102 mm tient dans le carter.

Le double allumage, les nervures BCC, les galeries conformes et les matériaux
LPBF restent des choix de dérivés à justifier séparément. Ils ne seront pas
ajoutés au maître historique sans preuve d'origine. Les objectifs antérieurs
de 1 000 PS et de SP95 ne deviennent pas les spécifications de la réplique,
ni une promesse pour chaque cylindrée.

## Reproduction du calcul

`V = π × alésage² × course × 6 / (4 × 1000)` avec les longueurs en mm et
la cylindrée en cm³. Une cylindrée seule ne détermine pas les deux longueurs.
Le rapport par défaut les laisse donc à `null`. Une longueur explicitement
fournie devient une hypothèse ; l'autre est seulement calculée.

```sh
python3 twins/962-cylinder-head-f0/source/displacement_family.py
python3 twins/962-cylinder-head-f0/source/displacement_family.py --check
python3 twins/962-cylinder-head-f0/source/displacement_family.py --target-cm3 4000 --bore-mm 102
python3 -m unittest discover -s tests -p 'test_962*.py' -v
```

Le [rapport conservé](derived/replica-family-report.json) est lié au registre
et au calculateur par leurs empreintes. Aucun appel au générateur PicoGK,
export STEP/STL, solveur ou achat n'est effectué par cet outil. Les sorties
ne qualifient ni compatibilité, ni puissance, ni fabrication, ni vente.

La prochaine entrée nécessaire pour reconstruire la forme est un ensemble
962 C identifié, avec droits de mesure, culasse/cylindre et porte-arbres
appariés, puis métrologie extérieure, CT des galeries et relevé des interfaces.
Les inconnues du registre restent `null` jusqu'à réception des preuves.

## Vérification du 16 octobre 2026

Les 53 tests ciblés 962 se terminent sans échec : 48 réussis et 5 ignorés
car VTK n'est pas disponible dans l'environnement Python 3.12 utilisé.
Les huit nouveaux tests vérifient les unités, les deux sens du calcul,
les bornes et entrées invalides, la conservation des inconnues, le rapport,
les liens du programme et la feuille de métrologie vide. Les empreintes des
anciens modèles passent leurs contrôles ; leurs géométries sont inchangées.
La reproduction du rapport et le contrôle strict des liens réussissent.

Le `make check` global exécute 4 040 tests en 267,189 s : trois échecs et
230 tests ignorés. Deux échecs d'égalité exacte de flottants concernent les
modules de ventilateur 993 non modifiés ; les mêmes écarts figurent dans le
journal de la précédente étude. Le troisième concerne deux caches Python
locaux dans le benchmark OpenFOAM. Ces caches créés durant les vérifications
sont supprimés ; les 17 tests du benchmark repassent avec
`PYTHONDONTWRITEBYTECODE=1`. Les autres cibles de `make check` passent
séparément avec `make -o test check`. Cela ne transforme pas le résultat du
`make check` initial en succès global.

Les journaux locaux sont conservés sous `work/962-replica/`. Aucun nouveau
calcul CFD/CHT, export natif de réplique, essai physique, CI distante ou
fusion n'est revendiqué pour cette livraison locale.
