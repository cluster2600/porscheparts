# M64 — G1, jumeaux 4 soupapes / double allumage, assemblage et itération

14 septembre 2026. Code : [`fourvalve/`](../../twins/m64-cylinder-head/source/fourvalve/run.py) ;
paramètres par composant : [`params/`](../../twins/m64-cylinder-head/source/fourvalve/params/design_space.json) ;
preuves : [`evidence/g1-four-valve-20260914/`](../../twins/m64-cylinder-head/evidence/g1-four-valve-20260914/manifest.json) ;
tests : [`test_m64_g1_four_valve_twins.py`](../../tests/test_m64_g1_four_valve_twins.py).

**Ce n'est ni une géométrie maître ni une autorisation de fabrication**
(`master_geometry: false`, `manufacturing_authorized: false`). La géométrie est
synthétique : aucun maillage de scan n'est importé. Les cotes 935 sont des nombres
du JSON d'interfaces (niveau C, unités ≈ mm non étalonnées). Le squelette G1
précédent (`parametric/`) reste en place, inchangé. Ce travail le prolonge sans le
remplacer.

## Ce qui est construit

Il y a dix jumeaux de composants. Chacun a son fichier de paramètres typés, son
module CAO (`cad/<composant>.py`) et son STEP :

- culasse ;
- soupapes d'admission ×2 et d'échappement ×2 ;
- guides, sièges rapportés, coupelles et demi-lunes ;
- ressort GSC5092 (enveloppe) ;
- arbres à cames et commande ;
- chemise ;
- piston à bol et 4 poches ;
- joint ;
- goujons.

Le repère commun est le plan d'étanchéité : Z vers les arbres, X admission < 0.
Il est lié au repère du scan par x = −y_scan, y = −x_scan, z = −z_scan. Le côté 1
du scan (axe 26,6°, bride haute, gorge 45,7) est **attribué** à l'admission : c'est
un choix de modèle.

Le calcul (`provenance`, `layout`, `kinematics`, `checks`, `iterate`) ne dépend que
de numpy et tourne dans la CI. La CAO et le contre-contrôle BRep demandent
CadQuery.

## Provenance (fail-closed)

Chaque valeur est revérifiée contre sa source à chaque exécution :

- `sourced_m64` : chemin dans le contrat ;
- `candidate_935_scan_C` : chemin JSON, réduction et changement de signe explicites, statut C ;
- `stock_993_2v_manual` : fiche `page_checked` ;
- `supplier_swindon` : citation présente dans la fiche et contenant la valeur ;
- `supplier_gsc5092` : champ de `spring_candidates.json`.

Une valeur modifiée ou une source retirée entraîne un refus. Un `unsourced` doit
porter une hypothèse et ne peut citer aucune source. Un `derived` porte une formule
et ses entrées, mais pas de valeur. Seule l'itération peut produire
`derived_by_iteration`, avec le numéro de l'essai.

| Provenance | Nombre | Paramètres |
|---|---:|---|
| `sourced_m64` | 2 | alésage 100 ; course 76,4 (P3) |
| `candidate_935_scan_C` | 21 | centrage Ø113,423 × 2,21 ; goujons 85,824 × 86,581, trou Ø10,879 (max) ; angles 935 26,576 / 29,162 ; face porte-arbre 86,461 ; brides x −107,217 / +82,533, hauteurs 47,53 / 35,54, conduit éch. Ø39,99 ; bougies : angles 61,68 / 60,26 et vecteurs d'axe |
| `stock_993_2v_manual` | 9 | guides (alésage culasse 13,0, Ø ext 13,06, alésage 8, dépassement 16,5, longueurs E 55,4 / A 56,4) ; longueurs soupapes 110,1 / 109 ; portée 45° — **témoins 2V** |
| `supplier_swindon` | 4 | têtes 40 / 33 ; levées 11,5 / 9,6 |
| `supplier_gsc5092` | 3 | hauteur montée 40 ; levée max publiée 14,25 ; longueur jointive 24,18 |
| `derived` | 8 | entraxes y des paires, hauteur d'arête du toit, gorges (0,85·Ø), Ø logement ressort, appuis ressort sur l'axe |
| `derived_by_iteration` | 17 | voir « Configuration retenue » |
| `unsourced` | 38 | marges de conception (pont 3, paroi 3, retrait 1, jeux piston 1,5 / 2, réserve spires 1), Ø ext ressort 30, bielle 127 (V1), puits de bougie Ø14, épaisseur de tête 6, bloc, came, piston, joint, tige de goujon Ø10 |

Le Ø14 des puits de bougie est un perçage lisse. Il suppose M14 × 1,25, fait
partiel du contrat pour la 993 Carrera. L'alésage apparent de la 935 (11,2–11,4)
est plus petit que le mineur M14.

## Centrage et chemise

Avec le centrage 935 (Ø113,42) et l'alésage M64 (100), il reste une paroi
d'épaulement de 6,71 mm. Les trous de goujon 935 empiètent de 1,2 mm sur le
centrage : le Ø utile tombe à 111,03. Il reste alors 5,42 mm de paroi, jeu 0,1
déduit, au-dessus de l'hypothèse de 4 mm. C'est **compatible sous hypothèse**. Le
Ø extérieur réel d'une chemise M64 n'est pas sourcé. Le lamage 935 (arête Ø94,3)
correspond à un alésage d'environ 95. Avec 100, sa portée intérieure n'existe plus
dans ce modèle.

## Contrôles

Il y a 36 contrôles, dont 34 bloquants. Les distances piston et soupape–soupape
sont calculées sur 720° : pas de 2° pendant la recherche, 1° pour le résultat.
Chaque échec est rapporté tel quel : la position de départ 935 est évaluée sans
retouche. Les poches de goujon, de conduit, de logement, de guide et de puits sont
des capsules, ce qui est conservatif pour des cylindres finis. Les ponts sont
calculés en projection sur le plan d'étanchéité. Le jeu piston–soupape est vertical
et prend en compte bol et poches. La loi de levée est la `CamLaw` du modèle V1, avec
la levée Swindon et les centres V1 supposés (105° / 612°).

| Contrôle | Seuil | Départ 935 | Retenu | Marge |
|---|---|---:|---:|---:|
| têtes dans l'alésage (retrait) | ≥ 1,0 | 1,90 | 1,66 | 0,66 |
| pont adm/adm · éch/éch | ≥ 3,0 | 3,00 · 3,00 | 3,19 · 3,19 | **0,19** |
| pont adm/éch | ≥ 3,0 | 3,14 | 15,93 | 12,9 |
| tête de son côté de l'arête | ≥ 0 | 1,50 | 3,42 | 3,4 |
| puits de bougie dans l'alésage | ≥ 1,0 | 16,59 | 8,51 | 7,5 |
| pont bougie 1 / sièges | ≥ 3,0 | **−3,67 échec** | 4,14 | 1,14 |
| pont bougie 2 / sièges | ≥ 3,0 | **−7,36 échec** | 4,14 | 1,14 |
| pont bougie / bougie · paroi des puits | ≥ 3,0 | 33,7 · 35,5 | 53,9 · 53,9 | 50,9 |
| puits / conduits | ≥ 3,0 | **−7,10 échec** | 8,50 | 5,5 |
| puits / goujons | ≥ 3,0 | **−8,24 échec** | 18,49 | 15,5 |
| puits / logements de ressort | ≥ 3,0 | **2,38 échec** | 25,09 | 22,1 |
| puits / guides | ≥ 3,0 | 5,94 | 22,11 | 19,1 |
| goujon / alésage | ≥ 3,0 | 5,52 | 5,52 | 2,5 |
| goujon / conduits | ≥ 3,0 | 3,61 | 3,20 | **0,20** |
| goujon / logements de ressort | ≥ 3,0 | **0,61 échec** | 4,58 | 1,58 |
| logements éch/éch · adm/adm · adm/éch | ≥ 3,0 | 4,0 · 11,0 · 59,0 | 4,19 · 11,19 · 80,5 | 1,19 |
| fond de logement / conduits | ≥ 3,0 | 4,79 | 5,93 | 2,9 |
| appui ressort sous la face porte-arbre | ≤ 86,46 | 65,9 | 75,3 | 11,2 |
| levée ≤ levée publiée GSC5092 | ≤ 14,25 | 11,5 | 11,5 | 2,75 |
| réserve à spires jointives (40 − 11,5 − 24,18) | ≥ 1,0 | 4,32 | 4,32 | 3,3 |
| épaulement de chemise · Ø utile goujons | ≥ 4,0 | 6,71 · 5,42 | idem | 1,42 |
| poches dans la calotte · profondeur ≤ 5 | ≥ 3,0 | sans objet | 4,01 · 3,92 | 1,01 |
| cames : écart entre lobes · au-dessus de la face | ≥ 3 · ≥ 86,46 | 121 · 116 | 146 · 117 | 30 |
| soupape–soupape sur le cycle | ≥ 1,0 | 2,68 | 11,48 (φ = 111°) | 10,5 |
| soupape adm.–piston | ≥ 1,5 | **1,48 échec** | 1,76 (φ = 2°) | **0,26** |
| soupape éch.–piston | ≥ 2,0 | 3,51 | 6,62 | 4,6 |
| tête / haut de chemise à pleine levée | ≥ 1,0 | 3,42 | 4,04 | 3,0 |
| *indicatif* : 11,5 et 9,6 simultanées | ≥ 1,0 | 0 (contact) | 6,23 | — |
| *indicatif* : contact dans un poussoir à coupelle | rayon ≥ 18,8 | 15 échec | 15 échec | −3,8 |

**Départ 935 : refusé**, avec 7 échecs bloquants. Les bougies 935 viennent d'une
culasse 2 soupapes : elles tombent sur les sièges d'une implantation 4 soupapes
(pont jusqu'à −7,4 mm) et traversent conduits et goujons. Le logement de ressort
d'admission passe à 0,6 mm du goujon. Le jeu piston d'admission est de 1,48 mm.

**Contre-contrôle BRep** (`BRepExtrema_DistShapeShape`) aux pires angles, sur la
configuration retenue :

- soupape adm.–piston : 1,755 / 1,757 / 1,765 / 1,770, identiques au calcul analytique ;
- soupape éch.–piston : 6,616 à 6,629, identiques ;
- soupape–soupape à φ = 111° : BRep 11,424 contre 11,478 analytique.

L'échantillonnage surestime donc la distance d'environ 0,05 mm ; la BRep fait foi et
reste bloquante. `BRepCheck_Analyzer` valide les 31 pièces. La culasse est un solide
unique de 1 651 403 mm³, sans signification physique puisque le bloc n'est pas
sourcé.

## Itération

La recherche est déterministe. La graine 935 fixe 160 tirages dans les bornes, puis
240 évaluations de recherche par coordonnées avec pas divisé par deux. Les 402
essais sont journalisés dans `iteration-history.json`. Deux exécutions donnent le
même historique.

L'étape 1 n'utilise que des variables non sourcées : angles et entraxes des
soupapes, position et inclinaison des bougies (miroir en y), profondeur des poches,
calage des cames ±10°, longueur de soupape. **L'étape 1 a suffi** : 104 essais
acceptés, le premier à l'essai 260. L'alésage (étape 2) et les diamètres de
soupape (étape 3) n'ont pas été ouverts. Aucune valeur M64, manuel ou fournisseur
n'a été modifiée.

Les contraintes limitantes les plus fréquentes parmi les essais refusés sont :

- pont bougie–sièges (64) ;
- puits–conduits (48) ;
- paroi entre puits (26) ;
- goujon–conduits (26) ;
- bougies ou têtes hors alésage (23 chacun).

### Configuration retenue (essai 385, marge minimale 0,19 mm)

| Variable | Départ | Retenu |
|---|---:|---:|
| angle axe admission | 26,58° (935) | 33,38° |
| angle axe échappement | 29,16° (935) | 24,62° |
| x centre tête adm. / éch. | −19,39 / +15,91 | −20,12 / +27,40 |
| écart supplémentaire dans une paire | 0 | 0,19 |
| bougies au plan (x, ±y) | (15,94 ; 20,27) et (−8,66 ; −20,38) | (2,88 ; ±32,49) |
| inclinaison / azimut des bougies | 28,3° / 154,5° et 29,7° / −23,6° | 6,9° / ±30,1° |
| profondeur des poches piston | 0 | 3,92 |
| avance came adm. / éch. | 0 / 0 | −5,71° (retard) / +0,73° |
| écart de longueur de soupape vs 993 | 0 | +7,44 |

Les deux bougies sont presque verticales, près de l'arête du toit, entre les têtes
de chaque paire, à y = ±32,5. L'échappement a été écarté vers l'extérieur.

## Balayage d'alésage (« il faut un alésage plus grand »)

[`bore_sweep.py`](../../twins/m64-cylinder-head/source/fourvalve/bore_sweep.py) →
[`bore-sweep.json`](../../twins/m64-cylinder-head/evidence/g1-four-valve-20260914/bore-sweep.json).
Le balayage couvre 13 alésages de 95 à 106 mm, avec 5 535 essais journalisés.

Pour chaque alésage, la recherche d'étape 1 est relancée : 80 tirages et 200
évaluations locales, alésage fixé, démarrage à chaud depuis le voisin accepté.
Le motif de goujons 935 est essayé d'abord. Si l'alésage échoue, l'entraxe des
goujons est libéré (`derived_by_iteration`). Conséquence signalée : **carter et
cylindres non compatibles M64**.

La bande 95–102,7 est la plage documentée du kit Swindon. Au-delà, jusqu'à 106,
chaque essai est marqué `exploratory_beyond_sources`. La cylindrée se calcule sur
6 cylindres avec la course de 76,4 (P3).

De nouveaux contrôles deviennent limitants avec un grand alésage :

- **Ø centrage vs Ø extérieur de chemise requis** : Ø centrage 113,42 (candidat 935)
  ≥ alésage + 2 × 4 (paroi supposée) + 2 × 0,1.
- **Ø extérieur de chemise requis vs trous de goujon** : le Ø libre entre les trous
  de goujon est 2 × (60,95 − 5,44) = 111,03 avec le motif 935.
- **Pont entre cylindres voisins** : `not_computable`. Aucun entraxe de cylindres
  M64 n'est sourcé ; le seul entraxe du dépôt est 917/Type 912 à 118 mm, niveau C,
  non transférable.

| Alésage | Bande | Cylindrée cm³ | Goujons 935 | Marge / contrainte limitante | Goujons libres (non M64) |
|---:|---|---:|---|---|---|
| 95 | doc. | 3 249 | refus | −0,35 têtes hors alésage | refus −0,52 têtes hors alésage |
| 96 | doc. | 3 318 | refus | −0,20 jeu soupape éch.–piston | refus −0,38 |
| 97 | doc. | 3 388 | refus | −0,13 jeu soupape éch.–piston | refus −0,14 |
| 98 | doc. | 3 458 | refus | −0,13 jeu soupape éch.–piston | refus −0,13 |
| **99** | doc. | 3 529 | **passe** | +0,19 pont adm/adm | — |
| 100 | doc. (M64) | 3 600 | passe | +0,19 pont adm/adm | — |
| 101 | doc. | 3 673 | passe | +0,19 pont adm/adm | — |
| 102 | doc. | 3 746 | passe | +0,19 pont adm/adm | — |
| **102,7** | doc. | 3 797 | **passe** | +0,13 chemise / trous de goujon | — |
| 103 | **exploratoire** | 3 820 | refus | −0,17 chemise / trous de goujon | passe +0,32 (goujons 85,8 × 94,1) |
| 104 | **exploratoire** | 3 894 | refus | −1,17 chemise / trous de goujon | passe +0,32 (93,3 × 94,1) |
| **105** | **exploratoire** | 3 969 | refus | −2,17 chemise / trous de goujon | **passe** +0,22 (93,3 × 94,1) |
| 106 | **exploratoire** | 4 045 | refus | −3,17 chemise / trous de goujon | refus −0,78 Ø centrage < Ø chemise requis |

**Plages d'alésage qui passent :**

- **Motif de goujons 935** : de **99 à 102,7 mm**, soit 3 529 à 3 797 cm³.
  - Côté bas : premier refus à 98 mm, limité par le jeu soupape d'échappement–piston
    (−0,13). À 95 mm, ce sont les têtes hors alésage.
  - Côté haut : premier refus à 103 mm, limité par la paroi de chemise vers les trous
    de goujon (−0,17). Limite analytique : alésage ≤ 111,03 − 8,2 = 102,83.
- **Goujons écartés** (hors M64, exploratoire) : jusqu'à **105 mm**, soit 3 969 cm³.
  - À 106 mm, le centrage 935 de Ø113,42 devient plus petit que la chemise requise
    (114,2).
  - Aller au-delà impose aussi d'abandonner le centrage candidat 935.

Le plus petit alésage qui passe est **99 mm**. Le plus grand qui reste dans la bande
documentée et le motif 935 est **102,7 mm**, soit 3 797 cm³ (+5,5 % sur 100). La
marge de 0,13 mm y repose sur les hypothèses de paroi 4 mm et de jeu 0,1. Le pont
entre cylindres reste non calculable faute d'entraxe M64 sourcé ; c'est **le
contrôle qui manque pour valider un grand alésage sur un vrai bloc**.

## Ce qui est bloquant ou reste hypothétique

1. **Les marges retenues sont minces et reposent sur des hypothèses.** Pont 3,0
   entre sièges (marge 0,19), paroi goujon–conduit 3,0 (marge 0,20), jeu piston
   1,5 (marge 0,26) : tous `unsourced`. Réévaluée sans nouvelle itération, la
   configuration passe encore avec un pont de 3,25 mm (marge 0,10). À 3,5 mm, elle
   échoue sur la paroi goujon–conduit (−0,007), car les paires s'écartent.
2. Le Ø extérieur du GSC5092 n'est pas publié (30 supposé). Il fixe le Ø des
   logements, donc les parois goujon/logement (1,58) et éch./éch. (1,19).
3. La commande est un **culbuteur** ramené à un empilement axial. Un poussoir à
   coupelle demanderait Ø ≥ 39,7 pour la loi V1 (valeur cohérente avec le Ø39,2 du
   935). Il n'est pas logeable ici entre les goujons et dans la paire
   d'échappement.
4. La loi et le calage V1 sont supposés (durées, centres, rampes). Le calage
   retenu retarde l'admission de 5,7° pour gagner du jeu au piston.
5. Plusieurs cotes ne sont que des candidats C d'une 935 2 soupapes, non
   transférables à une M64 : goujons, centrage, face porte-arbre, brides. Entraxe
   des cylindres, bloc, passages d'huile, sortie latérale des puits de bougie et
   refroidissement ne sont pas modélisés.
6. Les ponts sont projetés et les conduits sont des cylindres droits. Le taux de
   compression, les efforts et la thermique ne sont pas calculés.

## Sorties

STEP de moins de 1 Mo versés dans le dépôt : culasse (640 Ko), soupapes, guides,
sièges et coupelles, ressorts, chemise, piston, joint, goujons. S'y ajoutent une
coupe XZ en SVG, les paramètres résolus, les contrôles, l'historique et le
manifeste avec SHA-256 (entrées, sources, générateurs, sorties).

Deux fichiers dépassent 1 Mo et restent **hors dépôt**, dans
`/home/maxime/m64-local-artifacts/g1-four-valve-20260914/` : arbres à cames (1,01 Mo)
et assemblage à φ = 0 (2,0 Mo). Leurs empreintes figurent dans le manifeste. Les
en-têtes STEP sont horodatés, donc les empreintes STEP changent à chaque
régénération.

Reproduction :
`uv run --no-project --with cadquery --with numpy python twins/m64-cylinder-head/source/fourvalve/run.py twins/m64-cylinder-head/evidence/g1-four-valve-20260914 --external-dir <hors dépôt>`
(code de sortie 2 si la configuration est refusée ; `--no-cad` pour le calcul seul).
