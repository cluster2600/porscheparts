# Jumeau numerique du chassis de Porsche 911 (964)

Niveau atteint : **`F1_envelope`** (ADR 0003). Enveloppe a l'echelle et repere
documente. Ni `F2_interface`, ni geometrie de piece liberable.

## Entrees

| Entree | Nature | Role |
|---|---|---|
| `964widebodyunderside2poin13.obj` | scan de dessous, 2 400 031 sommets, 4 684 929 triangles, 210 Mo | enveloppe et repere |
| Manuel d'atelier 964, volume V « Body » | planches 50-02, 50-03, 50-05, 50-05a, 50-013 | cotes de controle et matiere |

Le scan n'est pas verse au depot : `raw-scans/` est ignore par git et sa
provenance n'est pas documentee. Le manuel non plus, conformement au precedent
de `SRC-PORSCHE-WORKSHOP-MANUAL-993`. Seules les valeurs sont reportees.

## Ce qui est etabli

**L'echelle du scan est verifiee.** Les quatre pneus ont ete isoles comme
composants connexes puis ajustes par cercle robuste dans le plan YZ, ce qui donne
les centres d'essieu. L'empattement mesure vaut **2278.1 mm** contre **2272 mm**
d'usine, soit **+0.27 %**. Le maillage est donc en millimetres a l'echelle 1:1.

**Le repere vehicule est etabli.** Le plan de symetrie a ete ajuste sur 250 000
points du soubassement par miroir et plus proche voisin, avec perte tronquee a
85 % pour absorber la couverture asymetrique du scan. Il en sort un **lacet de
-2.236 deg**, un **roulis de -0.451 deg** et un axe median a **X_scan +112.0 mm**.

Ce resultat se verifie tout seul : les roues n'entrent pas dans l'ajustement,
pourtant apres correction leur ecart gauche/droite tombe de **66.7 a 12.7 mm** a
l'avant et de **51.1 a 5.3 mm** a l'arriere.

**Le schema de cotation du manuel est decode.** Les cotes A a I sont des
ecartements gauche-droite, K a S des diagonales ou des longitudinales. La
diagonale M se recalcule depuis trois cotes publiees independantes :

    M = hypot(R, E/2 + F/2) = hypot(1245, 665 + 618) = 1787.8 mm

contre **1788 +/- 3 mm** au manuel, soit **0.2 mm d'ecart**. M relie donc le
point 17 gauche au point 18 droit. Cette verification est purement documentaire
et ne depend pas du scan.

## Ce qui n'est pas etabli

**Le calage longitudinal du reseau de datums est non resolu.** Un recalage du
reseau sur le scan donnait 16 points sur 16 a moins de 2.8 mm de structure, ce
qui semblait excellent. Un controle l'a invalide : **68 % de points tires au
hasard** sous la voiture tombent eux aussi a moins de 2.8 mm de structure, la
mediane aleatoire etant de 1.7 mm contre 1.0 mm pour les datums. L'empreinte du
plancher couvre presque tout le plan, donc « tomber sur de la structure » ne
prouve a peu pres rien.

La consequence se voit sur `evidence/overlay.png` : place selon la diagonale O,
le point **P21, palier moteur, tombe a X = -3112 mm**, dans la zone du
pare-chocs arriere, alors que le scan montre la structure moteur entre -2300 et
-2800 mm. L'autre appariement possible le place plus en arriere encore. **Aucun
des deux ne tient.**

Seuls les X de **P17, P18 et P19** viennent d'une cote publiee en vue de cote
(R = 1245 +/- 2 et S = 1328 +/- 2). Les X de P20, P3, P5, P12 et P21 sont
derives sous une hypothese de diagonale croisee qui n'est verifiee que pour M.

**Le scan est une carrosserie large.** Voie arriere mesuree autour de 1459 mm
contre 1374 mm d'usine ; voie avant 1388 mm contre 1380 mm, donc proche de
l'origine. Les ailes et bas de caisse elargis ne sont pas de la geometrie 964 de
serie. Seuls le plancher et la structure centrale servent de reference.

**Le plan de sol est le datum le plus faible.** Deduit du contact des quatre
pneus, il presente une dispersion de 55 mm. Toute cote en Z porte cette
incertitude.

## Matiere

La planche 50-013 nomme les six panneaux en **acier haute resistance (HS)** :
logement de roue avant, longeron interieur, traverse de plancher avant, assise de
siege, traverse d'essieu arriere, traverse avec palier moteur. La planche 50-014
ajoute que le soudage ne fait pas perdre de resistance, mais qu'un panneau
fortement deforme ne se redresse pas et se remplace.

Le volume V **ne publie ni nuance ni epaisseur**. Le modele porte donc une
epaisseur de travail de 1.0 mm declaree `ASSUMED`, et la masse de 36.8 kg ne vaut
que pour les solides modelises : ce n'est pas une masse de caisse 964.

## Reproduire

    source twins/964-chassis/source/env.sh
    pymesh source/symmetry.py      # ajuste le plan de symetrie
    pymesh source/align.py         # passe dans le repere vehicule
    pymesh source/wheels.py        # empattement et diametres
    pymesh source/datum_solve.py   # resout la chaine de datums
    pymesh source/control.py       # controle de significativite du recalage
    pycad  source/floor_assembly.py  # modele acier -> STEP

## Prochaine donnee utile

Localiser **un seul** point de datum publie sur un vehicule ou un scan de
serie, a mieux que sa tolerance, suffirait a caler la chaine longitudinale et a
faire passer ce jumeau en `F2_interface`. Le point 17, trou de reprise du cric
avant, est le meilleur candidat : il est publie a +/- 1 mm et visible de dessous.
