# F46 — cycle 0D angle-vilebrequin des culasses turbo 2V et 4V

## Résultat et limite d'autorité

F46 exécute un premier calcul moteur ouvert, résolu en angle vilebrequin, pour
comparer les hypothèses de distribution 2V et 4V de F45. Il fournit les traces
de pression, température, dégagement de chaleur, levée, section effective,
débits admission/échappement/carburant, flux thermique global et bilans du
dernier cycle.

Il ferme donc le manque historique `GAP-G4-01` de l'audit F43 **uniquement pour
la voie 0D angle-vilebrequin**. Il ne ferme pas le cas OpenFOAM/ICengines à
maillage mobile, lequel attend toujours les deux domaines fluides étanches.

Ce sous-lot n'est **pas** une validation Porsche, une prédiction de cliquetis,
une CFD 3D, une CHT ou une autorisation d'impression. Les Cd ne viennent pas
d'un banc de flux, les lois de levée ne viennent pas d'une came mesurée, le
carburant n'est pas le carburant historique qualifié du 917/30 et les pressions
collecteur ne viennent pas d'un banc moteur. L'écart entre les deux modèles de
combustion est donc une incertitude bloquante, pas un résultat à moyenner.

F46 ne crée ni enveloppe, ni ailette, ni surface extérieure de culasse. Le seul
alésage employé est un cercle de 90 mm. Le contrat porte explicitement
`oval_or_ellipse_created=false`.

## Comparabilité 2V / 4V

Les deux architectures partagent exactement :

- alésage × course : 90,0 × 70,4 mm ;
- bielle : 132 mm, cote de projet classée comme hypothèse et non métrologie
  917/30 ;
- rapport volumétrique : 9,5:1 ;
- régime : 9 000 tr/min ;
- admission : 283 700 Pa absolus et 325 K ;
- échappement : 296 000 Pa absolus ;
- paroi uniforme : 475 K ;
- équivalence : `phi=1,0` ;
- carburant thermochimique : n-dodécane ;
- séquence injection et modèles thermiques ;
- trois Cd hypothétiques : 0,62 / 0,72 / 0,82 ;
- trois pas : 1,0° / 0,5° / 0,25° vilebrequin.

Seuls le nombre de soupapes, leur diamètre, leur levée maximale et la section
de col issue du criblage F45 changent. La loi de levée est une demi-cosinus
symétrique, explicitement **pas** une loi de came :

\[
L(\theta)=\frac{L_{max}}{2}\left[1-\cos\left(2\pi
\frac{\theta-\theta_o}{\Delta\theta}\right)\right].
\]

L'admission est ouverte de −10° à 230° et l'échappement de 500° à 20° dans une
convention où 0° est le PMH de croisement et 360° le PMH combustion.

## Cinématique et débits

Le volume suit le mécanisme bielle-manivelle complet, sans approximation
sinusoïdale du piston :

\[
x=r(1-\cos\theta)+l-\sqrt{l^2-r^2\sin^2\theta},\qquad
V=V_c+A_p x.
\]

La section effective instantanée vaut :

\[
A_{eff}=C_d\min(N\pi D L(\theta), A_{col}).
\]

Le débit est calculé dans les deux sens par l'équation quasi-stationnaire d'un
orifice compressible isentropique. Le passage étranglé est activé lorsque le
rapport de pression aval/amont descend sous :

\[
\left(\frac{2}{\gamma+1}\right)^{\gamma/(\gamma-1)}.
\]

Le caractère quasi-stationnaire et l'absence de volumes de conduits signifient
qu'aucune onde, résonance, répartition de ports, tumble ou swirl n'est résolue.
Ces sorties appartiennent aux cas OpenFOAM/ICengines 3D après disponibilité de
domaines fluides étanches.

## Deux modèles de combustion réellement distincts

### Cantera 3.2.0 — cinétique homogène

La première voie utilise la phase idéale `nDodecane_IG` du fichier
`nDodecane_Reitz.yaml`, verrouillé par SHA-256. L'air est admis, puis une masse
de n-dodécane correspondant à `phi=1,0` est injectée sous forme **gazeuse,
homogène**, entre 330° et 350°. La cinétique est active et le dégagement
thermique est calculé par :

\[
\dot Q_{chim}=-V\sum_k \dot\omega_k\bar h_k.
\]

Cette voie est un écran d'auto-inflammation à compression. Elle ne contient ni
atomisation, ni film, ni turbulence de flamme, ni bougie. Le n-dodécane public
est un substitut cinétique pratique ; il ne représente pas un carburant course
917/30 corrélé. Il serait incorrect d'appeler sa phasage une marge au
cliquetis.

### Contre-modèle Wiebe

La seconde voie désactive toutes les réactions Cantera et impose une source
thermique indépendante :

\[
x_b=1-\exp\left[-a\left(\frac{\theta-\theta_0}{\Delta\theta}
\right)^{m+1}\right],
\]

avec `theta0=350°`, `Delta theta=65°`, `a=6,908`, `m=2,0` et un rendement de
dégagement de 0,94. Ces coefficients ne sont pas calibrés sur une pression
cylindre. Les deux voies partagent uniquement le harness thermodynamique et
les frontières, ce qui isole l'incertitude liée à la combustion.

## Transfert thermique et bilans

Le transfert global vers une paroi à température fixe utilise une corrélation
de criblage de type Woschni :

\[
h=130\left(\frac{p}{10^5}\right)^{0.8}
\left(\frac{T}{300}\right)^{-0.53}
\left(\frac{\max(U_p,1)}{10}\right)^{0.8}.
\]

Son coefficient n'est pas calibré. La surface est composée de deux surfaces de
piston plus la chemise exposée. Ce terme fournit une charge thermique globale
pour comparer les variantes ; il ne fournit pas de carte locale d'ailettes.

Les fermetures numériques publiées sont :

\[
\Delta m=m_{in}-m_{out}
\]

et

\[
\Delta U=H_{in}-H_{out}-W_{p\,dV}-Q_{paroi}+Q_{Wiebe}.
\]

La chaleur chimique Cantera est interne au bilan d'énergie absolue et n'est
donc pas ajoutée une seconde fois.

## Matrice, données brutes et reproduction

La campagne contient 36 cas :

`2 architectures × 2 combustions × 3 Cd × 3 pas angulaires`.

Chaque cas possède un CSV gzip déterministe du dernier cycle, avec 720 à 2 880
lignes selon le pas. Le rapport lie chaque fichier par SHA-256 :

- `twins/reference-917-engine/evidence/f46-cantera-cycle/cycle-report.json` ;
- `twins/reference-917-engine/evidence/f46-cantera-cycle/summary.json` ;
- `twins/reference-917-engine/evidence/f46-cantera-cycle/raw/*.csv.gz` ;
- `twins/reference-917-engine/evidence/f46-cantera-cycle/figures/f46-2v-4v-cycle.svg` ;
- `twins/reference-917-engine/evidence/f46-cantera-cycle/manifest.json`.

## Résultats numériques du point central

Le tableau suivant reprend le dernier cycle au Cd central de 0,72 et au pas fin
de 0,25°. La puissance est **indiquée** par le modèle 0D sur douze cylindres ;
ce n'est ni une puissance freinée, ni une mesure, ni la preuve de la cible
1 600 ch.

| Modèle | Architecture | Remplissage écran | Pmax | Tmax | IMEP | Travail/cyl/cycle | Puissance indiquée écran | Chaleur paroi/cyl/cycle |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Cantera cinétique | 2V | 0,7879 | 201,39 bar | 2 940,6 K | 25,14 bar | 1 125,8 J | 1 358,7 hp | 254,5 J |
| Cantera cinétique | 4V | 0,8695 | 219,02 bar | 2 964,0 K | 28,99 bar | 1 298,4 J | 1 567,0 hp | 268,0 J |
| Wiebe imposé | 2V | 0,7774 | 87,45 bar | 2 426,2 K | 18,54 bar | 830,6 J | 1 002,4 hp | 191,7 J |
| Wiebe imposé | 4V | 0,8613 | 94,91 bar | 2 450,1 K | 21,88 bar | 979,9 J | 1 182,7 hp | 196,4 J |

À frontières communes, la 4V donne dans cet écran :

- Cantera : +10,36 % de remplissage et +15,33 % de travail indiqué ;
- Wiebe : +10,79 % de remplissage et +17,99 % de travail indiqué ;
- environ +8,5 à +8,8 % de pression de pointe selon la voie combustion ;
- +2,48 à +5,34 % de chaleur globale extraite par la paroi.

Cette tendance n'est pas encore un choix de conception : l'avantage dépend
directement des sections F45, de la levée hypothétique et de Cd. Le DOE montre
par exemple, pour la voie Cantera au pas fin, une plage de remplissage 2V de
0,6984 à 0,8508 et 4V de 0,8047 à 0,8967 lorsque Cd passe de 0,62 à 0,82.

Les contrôles numériques donnent :

- 36/36 cas calculés avec Cantera 3.2.0 ;
- résidu de masse maximal : inférieur à la précision publiée (`0,0` après
  arrondi à neuf décimales) ;
- résidu énergétique maximal : 1,126 %, sous le seuil de criblage de 3 % ;
- variation maximale pas 0,5° vers 0,25° : 1,021 %, sous le seuil de 5 % ;
- variation cyclique maximale du dernier cycle : 0,469 %, sous le seuil écran
  de 1 % ;
- **désaccord combustion maximal : 56,67 %**, très au-dessus du seuil de 5 %.

Le dernier point fait échouer la comparaison inter-modèle et maintient la
validation combustion à `false`. La voie cinétique auto-enflamme très vite le
mélange homogène et prédit CA50 autour de 354–356°, alors que la loi Wiebe fixe
CA50 autour de 380°. Une trace de pression mesurée et un modèle d'allumage SI
sont nécessaires avant toute décision sur la pression de calcul de la culasse.

Exécution avec l'environnement local qualifié :

```sh
F46_PYTHON=/private/tmp/917-f46-cantera-venv/bin/python \
  make 917-cantera-2v-4v-f46
make 917-cantera-2v-4v-f46-check
```

Le script exige Cantera 3.2.0 et vérifie le hash du mécanisme installé avant de
calculer. Le contrôle normal ne relance pas les 36 cas : il vérifie contrat,
matrice, liens SHA-256, données brutes, bilans, comparaisons et frontière de
preuve.

## Gates restant obligatoires

Même si les bilans et la convergence de pas passent, les gates physiques
restent fermés. Pour les ouvrir, il faut au minimum :

1. lois de came/levée réellement mesurées ;
2. `CdA(lift, pressure ratio)` des ports 2V et 4V sur banc de flux ;
3. carburant réel et mécanisme corrélé ;
4. pressions cylindre instrumentées pour calibrer combustion et transfert ;
5. CFD OpenFOAM/ICengines sur trois maillages étanches ;
6. CHT avec carte matière à chaud ;
7. corrélation banc moteur, puis seulement décision de fabrication.

La valeur de 1 600 ch reste une exigence documentaire et n'est jamais injectée
dans le solveur comme résultat à atteindre.

## Références de méthode

- [Cantera 3.2 — exemple officiel de moteur à combustion interne](https://cantera.org/stable/examples/python/reactors/ic_engine.html), base API pour piston, réservoirs, injecteur et réseau de réacteurs ;
- mécanisme intégré `nDodecane_Reitz.yaml`, attribué dans son en-tête à Wang,
  Ra, Jia et Reitz, *Fuel* 136 (2014), DOI
  [10.1016/j.fuel.2014.07.028](https://doi.org/10.1016/j.fuel.2014.07.028) ;
- contrat F45 local pour les dimensions de soupapes et sections de col ;
- contrat F46 local pour l'identité et la frontière d'autorité des solveurs.
