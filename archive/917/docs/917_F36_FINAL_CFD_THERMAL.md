# Culasse 917 F36 — recoupement CFD et thermique final

## Objet et niveau de preuve

Cette campagne compare deux discrétisations indépendantes de l'écoulement d'air
externe autour de la peau F36 :

- FluidX3D, méthode de Boltzmann sur réseau D3Q19/TRT, paroi isotherme ;
- OpenFOAM 13, volumes finis RANS compressibles, paroi isotherme.

Le candidat LBM alimente ensuite un écran de conduction stationnaire CalculiX.
Ce chaînage est un **recoupement numérique**, pas une CHT
conjuguée : les températures solides ne sont pas réinjectées dans le fluide et
le coefficient d'échange FluidX3D repose sur une diffusivité turbulente
effective constante. Il ne constitue donc ni une corrélation physique, ni une
autorisation d'impression ou de démarrage moteur.

## Conditions communes

| Paramètre | Valeur |
|---|---:|
| Débit massique nominal | 0,85 kg/s |
| Température d'air amont | 308,15 K |
| Température de paroi CFD | 533,15 K |
| Domaine externe non caréné | 0,36 × 0,20 × 0,15 m |
| Carénage 20 mm, domaine court | 0,36 × 0,16525 × 0,13675 m |
| Carénage 20 mm, domaine long essayé | 0,72 × 0,16525 × 0,13675 m |
| Surface externe si 1 unité OBJ = 1 mm | 0,18487 m² |
| Flux moyen chambre de l'écran solide | 0,45 W/mm² |
| Limite de service utilisée comme écran | 260 °C |

Le coefficient effectif est calculé par :

```text
h_eff = Q_air / [A_ext × (T_wall - T_inlet)]
```

La perte de charge FluidX3D est une estimation issue de la traînée :

```text
Delta_p_drag = F_drag / A_domain
P_air = Delta_p_drag × m_dot / rho_air
```

Ce n'est pas une mesure de pression statique entre deux prises corrélées.

## FluidX3D — indépendance de grille

| Grille | Pas | Débit | Rejet thermique | h effectif | Delta p traînée |
|---|---:|---:|---:|---:|---:|
| 96 × 54 × 40 | 3,750 mm | 0,7825 kg/s | 39,99 kW | 961 W/m²K | 2,274 kPa |
| 192 × 107 × 80 | 1,875 mm | 0,8144 kg/s | 29,49 kW | 709 W/m²K | 2,852 kPa |
| 288 × 160 × 120 | 1,250 mm | 0,8257 kg/s | 23,99 kW | 577 W/m²K | 2,072 kPa |
| 384 × 213 × 160 | 0,938 mm | 0,8311 kg/s | 22,28 kW | 536 W/m²K | 1,587 kPa |

Chaque cas atteint son critère temporel interne. Entre les deux grilles les
plus fines, le débit change de 0,65 %, mais le rejet thermique de 7,11 % et la
perte de charge de 23,43 %. Le critère spatial de 5 % échoue donc. Les valeurs
absolues restent des écrans de conception.

## Balayage du carénage

| Jeu | Débit | h effectif | Delta p traînée | Décision virtuelle |
|---|---:|---:|---:|---|
| 5 mm | 0,728 kg/s | 985 W/m²K | 44,73 kPa | rejeté, perte élevée |
| 10 mm | 0,775 kg/s | 1 181 W/m²K | 46,38 kPa | rejeté, perte élevée |
| 15 mm | 0,816 kg/s | 811 W/m²K | 7,85 kPa | admissible écran |
| **20 mm** | **0,813 kg/s** | **1 108 W/m²K** | **8,025 kPa — candidat LBM, non sélectionné** |
| 25 mm | 0,827 kg/s | 1 050 W/m²K | 7,97 kPa | admissible écran |
| 30 mm | 0,833 kg/s | 550 W/m²K | 1,46 kPa | échange insuffisant |

Le cas 20 mm maximise `h` dans ce balayage LBM parmi les points qui respectent simultanément
`h >= 800 W/m²K` et `Delta p <= 10 kPa`. Sa puissance d'air estimée est élevée,
environ 6,15 kW ; le ventilateur, les fuites du carénage et le débit disponible
restent à dimensionner sur le moteur complet. Il n'est pas sélectionné pour la
conception tant que le même carénage n'a pas franchi le recoupement OpenFOAM.

La sensibilité de fermeture testée à jeu constant donne `h = 1 067` et
`1 097 W/m²K`, soit une étendue de 2,65 % de la valeur candidate. Augmenter
le débit jusqu'à 1,15 puis 1,34 kg/s élève `h` à 1 564 puis 1 824 W/m²K, mais
la perte de charge estimée monte à 16,40 puis 22,48 kPa. Ces deux points sont
donc rejetés par la contrainte hydraulique de 10 kPa.

## Conduction solide CalculiX

Le modèle résout :

```text
div[k(T) grad(T)] = 0
-k grad(T).n = q_chamber
-k grad(T).n = h (T - T_air) sur les surfaces refroidies
```

À flux chambre 0,45 W/mm² et sur le maillage de 2,5 mm :

| h imposé | T maximum | T p95 | Écran 260 °C |
|---:|---:|---:|---|
| 800 W/m²K | 253,89 °C | 171,06 °C | passe de 6,11 °C |
| 900 W/m²K | 247,65 °C | 164,61 °C | passe |
| 1 000 W/m²K | 242,55 °C | 159,41 °C | passe |
| **1 108 W/m²K** | **237,98 °C** | **154,57 °C** | **passe de 22,02 °C** |
| 1 181 W/m²K | 235,30 °C | 151,70 °C | passe |

Le passage du maillage 3,0 à 2,5 mm modifie le maximum de 4,57 % et le p95 de
4,32 %. Ce critère numérique passe. En revanche, une baisse de 20 % de la
conductivité supposée donne 301,34 °C même avec `h = 1 600 W/m²K` sur le
maillage de sensibilité 4 mm. La carte matière à chaud issue d'éprouvettes
imprimées est donc un verrou majeur, pas une formalité documentaire.

## OpenFOAM et contrôle anti-faux-positif

Une première exécution a convergé sur le bloc de fond sans la culasse. Elle est
explicitement rejetée : le fichier `headHeatFlux` ne contenait aucune ligne de
données et le maillage de calcul ne portait que les patches `inlet`, `outlet`
et `farfield`.

Le maillage snappy réel a été récupéré séparément avec 200 305 cellules,
56 315 faces sur le patch `head` et `checkMesh` standard réussi. Le script
`run_f36_openfoam_recovered_mesh.sh` impose ces preuves avant de conserver le
calcul. Les résultats géométriquement résolus sont incorporés au rapport JSON
uniquement si le solveur termine et si le flux du patch `head` est non vide.

Le contrôle strict n'est pas vert : deux contrôles échouent, avec une cellule
de déterminant inférieur à 0,001 et 12 564 cellules concaves ; deux faces
dupliquées et quatre faces à sommets partagés non consécutifs sont également
signalées. Le maximum de non-orthogonalité (69,91°) et le maximum de skewness
(3,95) restent sous les limites du dictionnaire utilisé. Le cas est conservé
comme recoupement de sensibilité, jamais comme preuve de libération.

Le cas medium a été arrêté après 36,7 minutes et 25 itérations de raffinement :
le paramètre `minRefinementCells` avait été ajouté sous une mauvaise clé du
dictionnaire et le maillage de 1 356 021 cellules ne respectait donc pas le
contrat medium prévu. Le cas fine n'a pas été lancé. L'indépendance de grille
OpenFOAM est par conséquent explicitement non acquise.

Le cas récupéré termine à 0,850012 kg/s. Il rejette 2,949 kW, donne une perte
de charge statique de 0,684 kPa et un coefficient moyen de 81,55 W/m²K. Le
bilan énergétique calculé entre entrée et sortie ferme à 0,42 %, et la
variation du flux intégré entre les deux derniers échantillons est 0,008 %.

À débit comparable, FluidX3D ultra ajusté prédit 23,148 kW et 1,696 kPa. Les
écarts relatifs à OpenFOAM sont donc respectivement 684,9 % et 147,8 %. Ils ne
peuvent pas être assimilés à un accord inter-solveurs. La principale différence
de modèle est la diffusivité turbulente effective constante du LBM, non
calibrée, contre la fermeture RANS et ses fonctions de paroi dans OpenFOAM.
Ce recoupement concerne le domaine externe non caréné commun. Le carénage
20 mm a ensuite été reproduit dans OpenFOAM, mais aucun de ses calculs ne
franchit les critères d'acceptation ci-dessous : il ne fournit donc pas une
validation croisée favorable.

Une dernière tentative a ajouté un carénage rectangulaire explicite à jeu
10 mm, avec quatre patches de paroi `noSlip` et adiabatiques. Le maillage final
de 181 243 cellules passe `checkMesh` standard, mais échoue trois contrôles stricts
(une cellule de faible déterminant, 9 693 cellules concaves et six faces de
faible poids d'interpolation). Le solveur s'arrête au temps 6 s par exception
flottante dans `omegaWallFunction`, malgré la séparation des quatre parois.
Aucun `Q`, `h`, `Delta p` ou bilan d'énergie de ce cas n'est donc accepté. Cette
tentative bornée est classée **solveur bloqué**, et non résultat défavorable ou
favorable.

Deux maillages du même carénage 20 mm ont ensuite été calculés sur le domaine
court de 0,36 m avec `kEpsilon`, parois `noSlip` et adiabatiques. Les conditions
communes sont 0,85 kg/s et 308,15 K. Le nombre de Reynolds de volume, calculé
avec le diamètre hydraulique du rectangle d'entrée complet, est voisin de
2,96 × 10^5. Il confirme qu'un modèle turbulent est nécessaire.

| Modèle / maille | Cellules | h observé | Delta p | Puissance air idéale | Erreur bilan énergie | Statut |
|---|---:|---:|---:|---:|---:|---|
| kEpsilon / 7,5 mm | 193 383 | 125,48 W/m²K | 1,831 kPa | 1,35 kW | 75,96 % | rejeté |
| kEpsilon / 5,0 mm | 460 657 | 145,88 W/m²K | 1,649 kPa | 1,22 kW | 82,04 % | rejeté |
| laminaire / 7,5 mm | 193 383 | 56,93 W/m²K | 1,830 kPa | 1,35 kW | 41,78 % | borne diagnostique rejetée |
| laminaire / 5,0 mm | 460 657 | 81,61 W/m²K | 1,612 kPa | 1,19 kW | 80,17 % | borne diagnostique rejetée |

La puissance indiquée est seulement `Delta p × débit volumique`, sans rendement
de ventilateur, fuites, pertes de distribution ni interaction entre les douze
cylindres. Elle est donc une limite idéale par domaine simulé, pas un
dimensionnement de soufflante moteur.

Les deux mailles RANS diffèrent de 16,26 % sur `h`, 22,38 % sur le flux intégré
et 9,95 % sur la perte de charge. Les deux diagnostics laminaires diffèrent de
43,35 %, 50,89 % et 11,94 %. Surtout, les erreurs de bilan énergie sont très
supérieures au seuil de 5 %. Les valeurs de cette table sont publiées comme
**observations numériques rejetées** ; elles ne sont ni des coefficients
utilisables pour concevoir, ni des bornes physiques garanties.

Le domaine axial porté à 0,72 m n'a pas corrigé ce défaut. Le cas 7,5 mm a été
relancé depuis zéro avec relaxations réduites, puis s'est arrêté au temps 153 s
sur une température initiale calculée de -66,43 K. Le cas 5 mm s'est arrêté au
temps 14 s par exception flottante du solveur de pression. Aucun résultat
thermique ou hydraulique n'est retenu pour ces deux exécutions.

La formulation laminaire a uniquement servi de diagnostic conservateur après
les instabilités des fonctions de paroi. À `Re ≈ 2,96 × 10^5`, elle n'est pas
physiquement applicable et ne constitue pas un second solveur indépendant.

Le calcul solide lié à `h = 81,55 W/m²K`, sur le même maillage de 2,5 mm et le
même flux chambre de 0,45 W/mm², atteint 617,42 °C au maximum et 525,64 °C au
p95. Cet écran échoue largement. Il rend le choix thermique dépendant du modèle
de turbulence sur le cas non caréné et interdit de retenir le seul résultat LBM
favorable du carénage comme base de fabrication avant un second calcul de ce
carénage.

Le chaînage CalculiX a également été exécuté exactement avec les deux valeurs
RANS du carénage : `h = 125,48 W/m²K` donne 501,66 °C, et
`h = 145,88 W/m²K` donne 468,09 °C. Les deux échouent l'écran à 260 °C. Même la
meilleure observation RANS rejetée reste 81,77 % sous le minimum échantillonné
de 800 W/m²K qui passe l'écran solide. Comme son bilan énergie CFD échoue, cette
distance est indicative et non une marge certifiée.

Chaque entrée OpenFOAM utilisée est publiée dans `openfoam-runs/` avec le log
solveur, les contrôles `checkMesh` standard et strict, les métadonnées, la
configuration et les cinq séries `.dat` exactes. `openfoam-run-manifest.json`
enregistre chemin, taille et SHA-256, y compris pour tous les essais rejetés.
`bundle-manifest.json` protège à son tour le rapport, la planche et ce manifeste.

## Verdict

Le carénage de 20 mm est seulement le meilleur compromis **dans l'échantillon
LBM testé** et sa valeur nominale de `h` passe l'écran de conduction. Les quatre
calculs OpenFOAM de domaine court terminés le contredisent sans toutefois être
eux-mêmes acceptables, et les deux essais de domaine long restent bloqués.
Aucune configuration de refroidissement n'est sélectionnée. La fermeture
thermique n'est pas acquise : ni indépendance de grille FluidX3D, ni bilan
énergétique et indépendance de grille du carénage OpenFOAM, ni CHT.

Les verrous de libération restent : échelle absolue du scan, CAO fonctionnelle
et interfaces mesurées, carte matière à chaud qualifiée, vraie CHT, fatigue
thermomécanique avec contacts/précharges, corrélation banc de flux et thermique,
CT/CND de la pièce, puis banc moteur instrumenté. En conséquence :

- `metal_print_authorized = false` ;
- `engine_start_authorized = false`.

## Reproduction de la synthèse

```bash
python3 twins/reference-917-engine/source/build_f36_final_cfd_thermal_evidence.py \
  --raw work/917-scan-conforming-f36/final-cross-solver-013/raw-remote \
  --openfoam-case work/917-scan-conforming-f36/final-cross-solver-013/openfoam/coarse \
  --openfoam-case work/917-scan-conforming-f36/final-cross-solver-013/openfoam/shroud-gap10-nonslip-coarse \
  --openfoam-case work/917-scan-conforming-f36/final-cross-solver-013/openfoam/shroud-gap20-kepsilon-base7p5 \
  --openfoam-case work/917-scan-conforming-f36/final-cross-solver-013/openfoam/shroud-gap20-kepsilon-base5 \
  --openfoam-case work/917-scan-conforming-f36/final-cross-solver-013/openfoam/shroud-gap20-kepsilon-long-base7p5 \
  --openfoam-case work/917-scan-conforming-f36/final-cross-solver-013/openfoam/shroud-gap20-kepsilon-long-base5 \
  --openfoam-case work/917-scan-conforming-f36/final-cross-solver-013/openfoam/shroud-gap20-laminar-base7p5 \
  --openfoam-case work/917-scan-conforming-f36/final-cross-solver-013/openfoam/shroud-gap20-laminar-base5 \
  --output work/917-scan-conforming-f36/final-cross-solver-013
```

Les livrables sont `cross-solver-report.json`,
`openfoam-run-manifest.json`, `bundle-manifest.json`, le dossier compact
`openfoam-runs/` et `917-head-f36-final-cfd-thermal.png`.
