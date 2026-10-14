# Poids de faces avec centres natifs

Les deux évaluateurs encadrent les poids mathématiques natifs sur les 153boîtes fermées
conservées, avec seuil source 0.05 inchangé. Il trouve 15 344 faces positives sur
l'enveloppe et 3 216 indécises ; les 492 048 contrôles locaux de ces dernières sont
tous positifs. La lecture indépendante confirme toutes les bornes et tous les signes positifs.

Le domaine reste u=q_m source et v dans
[18685771944522017155/18446744073709551616,
9345323731508729405/9223372036854775808]. Aucun ratio ponctuel, subdivision,
centre libre, aplanissement, candidat, dictionnaire, natif ou solveur.
Quinze manifestes parents et 357 entrées sont vérifiés, ancrés PR247
`efc7b2488dde73e5a1ae21b86fe2347f40d0ab0f`.

## Expression et représentation

polyMeshTools::faceWeights utilise min(dOwn,dNei)/(dOwn+dNei+VSMALL), avec
les valeurs absolues de S·(Cf-Co) et S·(Cn-Cf). Les centres Cf et C viennent
des moments natifs signés PR236 épinglés. Les projections signées demeurent
dans chaque enregistrement ; leurs valeurs absolues pour ce critère ne
remplacent pas les signes des critères angulaires ou de plans distincts.

VSMALL et le seuil sont les valeurs rationnelles des littéraux binary64 sous
hypothèse WM_DP ; cela ne qualifie pas un binaire. L'additif est conservé en
Fraction exacte dans les quotients finaux avant arrondi externe à 160 bits.
method.md démontre l'inclusion par monotonie de chaque fraction et explique
le plafond mathématique 1/2. Aucun nouvel opérateur de noyau n'est introduit.

Les 13 696 faces internes sont distinguées des 4 864 parois non couplées, initialisées
à 1. Les 384 faces MRF sont internes. Déclarations wall et héritage coupled=false
proviennent de PR247, vérifiés par sa chaîne de sources. Pas de faux patch
couplé ni mur ajouté à des expressions qui demandent seulement les faces internes.

## Calcul et lecture

weight-bounds.jsonl.gz conserve 510 608 enregistrements, y compris les 3 216
indécisions sur l'enveloppe. Les reprises utilisent exactement les 153boîtes
sources. La plus petite borne basse positive employée vaut environ
0.05014088805473799 ; ce n'est pas un poids évalué à un ratio géométrique choisi.

Le primaire utilise les moments centrés PR236/noyau 160 PR233. Le lecteur indépendant
reconstruit séparément les six gabarits hex réduits, cycles opposés et domaines ;
il utilise les moments indépendants PR236 et dyadic192 PR238. Le quotient est
encadré via son expression complémentaire. Douze références par programme
précèdent l'application, dont deux références exactes à l'échelle VSMALL et
des cubes adjacents à trois échelles. Aucune ancienne dérivation n'est rejouée.

Les 1 522 096 intervalles des 510 608 enregistrements sont inclus dans les
bornes primaires ; tous les signes positifs sont confirmés. Aucun dénominateur
de moment ne reste indécis. Calcul : 747,461 s ; lecture : 657,778 s. Le primaire
chevauchait les tests ; ces durées ne sont pas des benchmarks CFD.

read_summary.py est une relecture structurelle de couverture et minima, pas
une troisième reconstruction géométrique. Le minimum annoncé concerne
seulement les certificats positifs employés ; les indécisions sur l'enveloppe
restent présentes et ne sont pas transformées en refus physiques.

## Limites

Les 113 boîtes aux prédicats nécessaires passants demeurent NON admises. Les 153
boîtes, toutes extrémités et les deux indécisions de déterminants sont conservées.
L'admission native, skewness, orthogonalité additive, checkFaceTets, contacts
internes de dimension inférieure, bilan flottant et conversion writePrecision 16
restent ouverts. Les moments ne sont pas remplacés par ceux des tétraèdres de
preuve. Cette restriction synthétique ne qualifie ni le système entier ni les
surfaces physiques 086/091. Couches, repos, convergence, stabilité, indépendance,
CFD et calibration restent distincts. 084 jamais relancé. Aucun débit/puissance
ou calibration validé.
