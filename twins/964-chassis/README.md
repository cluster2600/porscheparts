# Jumeau numerique du chassis de Porsche 911 (964)

Niveau atteint : **`F1_envelope`** (ADR 0003). Enveloppe a l'echelle et repere
documente. Ni `F2_interface`, ni geometrie de piece liberable.

## Reprise monocoque — 2026-09-25

Le contrat [monocoque-interface.json](derived/monocoque-interface.json) reprend
maintenant les noms et les neuf ecartements transversaux du
[registre documentaire](../../catalog/measurements/MEAS-MANUAL-964-BODY-CONTROL.json),
avec les identifiants de chaque valeur. Corrections de l'audit :

- **P12 est un support de traverse de boite**, pas une fixation d'essieu arriere.
  L'ecart de travail P5–P12 (1724,3 mm, derive et non verifie) ne definit donc
  pas l'empattement. Les ancrages de suspension arriere restent a relever.
- **P6 est un support de traverse interieure d'essieu avant**. Il reste dans le
  rapport avec X `null`, statut `MANQUANT`, au lieu d'etre omis.
- Les tolerances documentaires portent sur les **ecartements de paires**.
  Les demi-ecartements supposent la symetrie ; ils ne certifient pas la
  tolerance de chaque coordonnee Y. P21 reste `INVALIDE`.

Ces corrections ne recalculent ni la CAO ni les anciens resultats FEA.
L'etiquette historique `rear_axle_crossmember` de `floor_assembly.py` designe
encore sa traverse a P12 ; elle ne prouve pas une interface d'essieu arriere.
Le contrat couvre les paires cotees du manuel, pas tous les ancrages du vehicule.

La [feuille de route monocoque](https://github.com/cluster2600/porscheparts/blob/135dcc8ef6e71ac483e1ed3036217536562c80a1/twins/993-carbon-safety-cell/roadmap-to-release.md)
reste sur une branche distincte, non fusionnee a la base `7fe668b` de cette
reprise. Ses calculs de treillis et de cuisson sont des etudes F1, pas des
validations de coque composite. Ses conventions d'axes doivent etre rapprochees
avant toute superposition avec ce jumeau (X vers l'arriere contre X vers l'avant ici).

Le scan brut a depuis ete recupere (voir ci-dessous). Prochaine etape : identifier des
datums avec XYZ, reperes et incertitudes, et relever les interfaces arriere et
les enveloppes de transmission C2/C4 (tringlerie, arbre, debattements, acces).
Les ecarts 964/993 doivent etre qualifies par variante. Ni un scan de dessous,
ni les cotes documentaires seules ne permettent de figer les moules ou de
declarer la coque apte a la route, au circuit ou homologuee.

Verification du contrat :

```sh
(cd twins/964-chassis/source && python3 monocoque_interface.py)
python3 -m unittest discover -s tests -p 'test_964_monocoque_interface.py'
```

## Scan recupere et diagnostic du tunnel — 2026-09-25

Le fichier utilisateur `964widebodyunderside2poin13.obj` est conserve localement,
en lecture seule, hors Git : 210 972 101 octets, 2 400 031 sommets et
4 684 929 triangles. SHA-256 :
`f397909141e5af2529db961641c7699d39d40c355e05245cfb1573a2974c8dc5`.
L'audit d'entree retrouve 118 411 aretes ouvertes. Les comptages concordent avec
l'etude historique ; ils ne certifient ni l'identite du vehicule, ni la variante,
ni la precision du scanner. Les droits de redistribution restent non confirmes.

Les scripts existants de symetrie, recalage, transformation et sensibilite des
roues ont ete reexecutes sur cet original. Le
[rapport de recalage](derived/scan-recalage-20260925.json) lie le scan, les scripts,
les versions et les tableaux produits par SHA-256. Resultats de cette execution :

- lacet −2,236 deg, roulis −0,451 deg, residu de symetrie tronque 7,54 mm ;
- empattement par ajustement des roues : 2277,9 mm, contre 2272 mm documentaire ;
  sensibilite au diametre suppose : 2270,4 a 2278,8 mm ;
- dispersion du sol deduit des pneus : 55,1 mm ;
- coherence numerique transformation/tableau : erreur maximale 0,000128 mm sur
  200 000 sommets. **Ce dernier chiffre n'est pas la precision physique du scan.**

Le [diagnostic de visibilite](derived/tunnel-visibility-20260925.json) couvre huit
stations, dont **six** dans la plage habitacle X = −1400 a −400 mm. Leur relief
median centre/flancs va de −3,123 a −0,696 mm. Les coupes et la vue en plan sont
produites localement, sans rebouchage ni reconstruction de surfaces cachees.

**L'ancienne conclusion « pas de tunnel, pas d'arbre longitudinal » est retiree.**
Ces bandes ne montrent que la peau visible. Elles ne disent pas ce qui passe
au-dessus, derriere un carenage, ni quels jeux restent disponibles. Le diagnostic
ne reconnait pas C2/C4. La
[source Porsche allemande](../../catalog/sources/src-porsche-964-993-all-wheel-drive-history.json)
confirme l'architecture de transmission C4, mais n'en fournit aucune cote.

| Zone a integrer | Donnee encore necessaire, separement pour 964 et 993 |
|---|---|
| Tringlerie C2/C4 | axes, articulations, supports, enveloppe balayee sur tous les rapports |
| Tube/arbre vers l'avant C4 | axe XYZ, diametre exterieur, brides, supports et mouvements du groupe |
| Interfaces boite / differentiel avant | plans et points d'ancrage, volumes reels, tolerances |
| Tunnel de coque et entretien | deux faces de paroi, epaisseurs, passages voisins, volumes de depose |

Il faut notamment un releve de l'habitacle/tunnel et du soubassement avec les
organes et carenages identifies. Un vide dans le nuage n'est jamais traite comme
un volume libre. Le recalage des datums structurels et la compatibilite C2/C4/993
restent non valides ; aucun moule ni drapage n'est libere.

### Rejouer

L'execution locale utilise Python 3.10.11, NumPy 2.2.6, SciPy 1.14.1 et
trimesh 5.1.0 ; Matplotlib sert aux figures. SciPy 1.15.3 ne se chargeait pas
sur cet hote macOS ; le remplacement est reste dans un environnement isole.
Verifier d'abord le SHA-256 de l'original ci-dessus. Dans un repertoire de
travail prive, creer `raw/964widebodyunderside2poin13.obj` comme lien vers cet
original, puis executer avec cet environnement, dans cet ordre :

```sh
python /chemin/du/depot/twins/964-chassis/source/symmetry.py
python /chemin/du/depot/twins/964-chassis/source/align.py
python /chemin/du/depot/twins/964-chassis/source/vehicle_transform.py
python /chemin/du/depot/twins/964-chassis/source/wheelbase_robust.py
python /chemin/du/depot/twins/964-chassis/source/tunnel_probe.py \
  --vertices verts_vehicle.npy --scan raw/964widebodyunderside2poin13.obj \
  --registration-report /chemin/du/depot/twins/964-chassis/derived/scan-recalage-20260925.json \
  --output tunnel
```

Le dossier de sortie doit etre nouveau. Le diagnostic refuse un scan ou un
tableau de sommets dont l'empreinte differe du rapport ; un autre environnement
peut necessiter une nouvelle attestation de recalage, sans ecraser celle-ci.
Sorties locales : `scan-plan.png`, `visible-sections.png`, `tunnel-visibility.json`.

## Vue annotee et fiche de releve des interfaces — 2026-09-25

Le [plan de mesure](interface-measurement-plan.md) et la
[fiche CSV](derived/interface-measurements-20260925.csv) couvrent les **18 identites**
du registre documentaire, dont neuf absentes du contrat XY initial. Le
[rapport de generation](derived/interface-review-20260925.json) lie les entrees
et les sorties numeriques par SHA-256. Les vues 3D et en plan restent locales.

Sept paires sont projetees comme **hypotheses XY**, pas comme ancrages reconnus.
Les hauteurs restent inconnues (`null`, pas zero) ; le plan graphique et les pointilles ne sont pas
de la geometrie de piece. P6, P21 et les identites sans XY restent visibles dans
la fiche. Aucun point XYZ n'est valide, aucune CAO de fixation n'est creee.

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

Ce resultat a ete mis a l'epreuve. Les composants de roue sont couverts sur
360 degres et non sur un arc partiel, et en imposant au rayon des valeurs allant
de 560 a 680 mm de diametre, l'empattement deduit reste entre **2270,4 et
2278,9 mm**. La verification d'echelle ne depend donc pas de l'estimation du
rayon des pneus, qui est elle instable d'un pneu a l'autre.

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

## Le repere est desormais exploitable par machine

La fiche de jumeau ne decrivait le passage scan -> vehicule qu'en prose. Il porte
maintenant la **matrice homogene 4x4** correspondante, dans
`coordinate_system.vehicle_transform`, composee par `source/vehicle_transform.py`
depuis `frame_params.npy` : recentrage lateral, annulation du lacet, annulation du
roulis, puis permutation d'axes et mise a l'origine.

Elle est verifiee, et pas seulement relue. Sa partie rotation est orthonormee a
2,5e-18 pres pour un determinant de 1,000000000, et appliquee a **200 000 sommets
tires au hasard dans le scan** elle reproduit `verts_vehicle.npy` a **1,3e-4 mm**
au maximum. La verification n'est pas cosmetique : la chaine enchaine une
translation, deux rotations et une permutation d'axes, ou une convention de signe
ou un ordre de composition se trompent facilement.

La prose d'origine est conservee dans `vehicle_transform_note`.

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

## Ce que le volume IV ajoute

Le volume IV « Chassis » couvre le train roulant, pas la caisse, mais il porte
deux cotes qui interessent directement le repere du jumeau, parce qu'elles sont
prises **du sol jusqu'a un point de caisse** :

| cote | Carrera 2/4 | RS | definition |
|---|---|---|---|
| hauteur avant | **165 +/- 10 mm** | 125 +/- 5 | du contact roue-sol au boulon exterieur « Crossmember to body » |
| hauteur arriere | **270 +/- 5 mm** | 235 +/- 5 | du contact roue-sol a la fixation exterieure de bras, cote caisse |

Le point avant est le **P5 du volume V**, « Mount - outer cross member FA »,
d'ecartement transversal 770 +/- 2 mm. Le volume IV lui donne donc une cote en
Z rattachee au plan de sol, la ou le volume V ne donnait qu'un ecartement.
C'est la premiere cote verticale de datum du dossier.

Elle n'est pas encore exploitee. Le faire suppose de localiser cette fixation
sur le maillage, et de savoir a quelle hauteur de caisse roule le vehicule
scanne : ces valeurs valent au poids a vide DIN 70020, suspension chargee, et le
scan est une carrosserie large probablement modifiee. Un ecart mesure
indiquerait un rabaissement, pas une erreur de repere.

Geometrie utile par ailleurs : carrossage arriere -40' +/- 10' et pincement
+10' par roue. Le plan de roue n'est donc pas parallele au plan YZ du vehicule,
ce qui explique une part de la dispersion des ajustements de cercle sur les
pneus.

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

## Recherche du point 17 sur le scan : resultat negatif

Le point 17 a ete cherche comme il doit l'etre : un trou de reprise est une
boucle de bord dans le maillage. Les 118 411 aretes de bord du scan donnent
1 521 boucles, dont 248 ressemblent a un trou (8 points ou plus, diametre 10 a
80 mm, circularite inferieure a 0,25).

Une paire de datums doit satisfaire quatre criteres simultanement : meme station
longitudinale, meme hauteur, meme diametre, et un ecartement egal a la cote
publiee. Le filtrage successif donne :

| critere cumule | paires |
|---|---|
| meme X a 25 mm, ecartement a 4 mm d'une cote publiee | 14 |
| + meme hauteur, dZ < 20 mm | 1 |
| + meme diametre, a 8 mm | 0 |
| + ecartement a 1 mm, tolerance publiee | **0** |

Les 14 premieres correspondances ne valent rien : le tirage aleatoire en prevoit
**17,1**. Il y a donc moins de correspondances que le hasard n'en produit.

Aucune paire d'ecartement voisin de 1330 mm ne tient : toutes sont soit a des
stations longitudinales sans rapport, jusqu'a 3478 mm d'ecart, soit a des
hauteurs differentes. La moins mauvaise, ecartement 1324,7 mm a dX = -23 mm,
manque la cote de 5,3 mm sur une tolerance de +/- 1 mm, et se trouve en avant de
l'essieu avant, ou le cric avant ne peut pas etre.

Les boucles de bord du scan sont des trous d'occlusion, pas des percages. Le
scan ne resout pas les trous de reprise, et la carrosserie large masque
probablement les bas de caisse d'origine. **La chaine longitudinale reste non
calee.**

## Prochaine donnee utile

Le diagnostic a evolue le 2026-09-04. Ce qui manque n'est pas une entite a
trouver sur le scan mais **une cote a trouver dans une publication** : le scan ne
resout pas les percages, alors qu'il localise les centres de roue a +/- 7 mm. Il
suffirait donc d'**une seule cote longitudinale publiee entre un point de datum
et une ligne d'essieu**. Le volume IV ne la donne pas, il donne des hauteurs au
sol. L'etat complet des pistes, avec leurs priorites, est dans
`docs/research/964-combler-le-gap-de-donnees.md`.

La piste documentaire `SRC-RENNLIST-993-BODY-DIMENSIONS-PDF` signale un tableau
de points en millimetres, non obtenu. Un fil 993 rapporte 1245 mm entre points
de levage, comme la cote R du manuel 964 : c'est une piste de recoupement,
pas une preuve de transferabilite des interfaces entre generations.

Localiser un point de datum pourrait ancrer longitudinalement le sous-reseau
dont les distances relatives sont etablies. **Cela ne suffit pas a atteindre
`F2_interface`** : les X derives restent a verifier, P6 manque, P21 est invalide,
les Z et les incertitudes de recalage restent a qualifier. P17 est un candidat,
mais la tolerance publiee de +/- 1 mm porte sur l'ecartement de sa paire, pas
sur sa position absolue par rapport a l'essieu.

La quatrieme priorite du dossier, etendre le modele coque, est faite : voir
« Ce que la caisse ajoute au plancher » ci-dessous. Il ne reste donc plus, dans
les pistes qui dependent de nous seuls, que des travaux de second rang. Les
items decisifs — un releve de marbre, un scan de carrosserie de serie, un
tableau de points publie — dependent tous d'un tiers.

## Piste composite

Une etude de materiau a ete menee sur l'essai de torsion existant, sans en
changer ni la geometrie ni le chargement, pour repondre a la question du
monocoque carbone de type ZESAD. A raideur en torsion egale, le carbone
quasi-isotrope monolithique ne gagne que 18 % de masse surfacique et l'aramide
en perd 30 % : ce caisson travaille en cisaillement de membrane, donc le critere
est `G/rho` et non `E/rho`, et une ame de sandwich n'y change rien. Le levier
d'un monocoque est architectural, pas materiel, et ne se demontre pas sur un
plancher seul.

Voir `docs/research/964-chassis-carbone-kevlar.md`. Cette piste ne produit
aucune geometrie liberable : une structure autoportante porte la retenue des
occupants et reste `prohibited_pending_engineering`.

## Ce que la caisse ajoute au plancher

Le modele coque a ete prolonge du plancher seul jusqu'a une cellule fermee —
passages de roue, pieds milieu, brancards, pavillon, cadre de pare-brise. C'etait
la seule piste du dossier a ne dependre d'aucune donnee exterieure : elle ne
demande que des sections `ASSUMED` de plus.

Deux resultats en sortent, tous deux relatifs et donc exploitables malgre les
sections supposees.

**Le classement des elements ne suit pas leur masse.** Du plancher nu a la
cellule fermee, la raideur en torsion est multipliee par 3,7 pour une masse
multipliee par 2,3. Mais le pavillon, 10,5 kg, n'apporte que +1 % ; le cadre de
pare-brise, 1,1 kg, apporte le plus gros increment de toute l'echelle. Le
rapport de rendement au kilo entre les deux est de **deux ordres de grandeur**,
et il tient a trois finesses de maillage alors que la raideur absolue, elle,
derive de 11 %. Ce qui compte en haut de caisse n'est pas la matiere, c'est la
**fermeture de l'anneau** : pieds milieu et brancards ajoutes seuls, sans rien
pour fermer a l'avant, apportent exactement zero pour 7,5 kg.

**Une traverse du modele ne portait rien.** Un controle de connexite ajoute au
constructeur a montre que la traverse arriere, placee a x = -1703 par la chaine
de datums, tombait derriere le bord du plancher modelise : elle comptait pour
5,7 % de la masse et pour rien dans la raideur. Les raideurs deja publiees
etaient justes — retirer cette traverse redonne exactement les 2442 N.m/deg
publies — mais les masses, donc les raideurs specifiques, etaient minorees.
Detail et consequences dans `fea/README.md`.

Aucun de ces chiffres n'est une raideur de 964, et le fait que le modele ignore
vitrage colle, portes et ouvertures de panneaux joue precisement dans le sens
qui flatte l'anneau ferme.
