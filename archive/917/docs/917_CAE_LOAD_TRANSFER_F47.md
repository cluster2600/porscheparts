# F47 — chargements comparables 2V/4V pour les futurs calculs CAE

## Résultat livré

F47 transforme les **36 traces réellement calculées par F46** en tables de
chargement bornées et comparables pour les culasses turbo 2V et 4V. Chaque
trace source est relue, contrôlée par SHA-256 contre le manifeste F46 et
échantillonnée aux 720 angles entiers déjà présents. Il n'y a donc ni
interpolation, ni extrapolation, ni nouveau calcul de combustion.

Le lot livre pour chaque architecture et chaque angle vilebrequin :

- la pression absolue du gaz et la pression différentielle de criblage ;
- la température moyenne du gaz 0D ;
- le coefficient global de transfert thermique `h_gas` ;
- le flux thermique signé du gaz vers le solide ;
- les bornes Cantera et Wiebe séparées ;
- une borne extérieure commune aux deux modèles ;
- la conversion angle-temps à 9 000 tr/min.

![Enveloppes F47](../twins/reference-917-engine/evidence/f47-cae-loads/figures/f47-cae-load-envelopes.png)

Cette image montre des **chargements 0D non corrélés**. Ce n'est pas un champ
CFD, une CHT, une contrainte EF ou une preuve de fonctionnement.

## Intégrité de la source

Le contrat
[`cae-load-transfer-f47.json`](../twins/reference-917-engine/cae-load-transfer-f47.json)
verrouille par empreinte :

- le contrat cycle F46 ;
- le rapport des 36 cas ;
- le manifeste F46, qui verrouille à son tour chaque CSV gzip brut ;
- le contrat d'autorité des solveurs.

La matrice est exactement :

`2 architectures × 2 modèles de combustion × 3 Cd × 3 pas = 36 cas`.

À chaque angle, une enveloppe par modèle contient neuf contributeurs : trois
Cd (`0,62`, `0,72`, `0,82`) et trois pas (`1°`, `0,5°`, `0,25°`). Les valeurs
Cantera et Wiebe restent séparées parce que leur écart était déjà bloquant en
F46. La borne extérieure est utile pour dimensionner une campagne, mais elle
ne doit jamais être imposée comme une trajectoire : son minimum et son maximum
peuvent provenir de cas différents.

## Équations de transfert

Le temps du cycle quatre temps est reconstruit sans nouvelle hypothèse :

\[
t(\theta)=\frac{\theta}{6N},
\]

avec l'angle en degrés, le régime `N` en tr/min et `t` en secondes. À
9 000 tr/min, 720° correspondent à `13,333 ms`.

La vitesse moyenne du piston vaut :

\[
U_p=\frac{2SN}{60}=21,12\ \mathrm{m/s}.
\]

F47 réévalue exactement la corrélation de criblage F46 :

\[
h=130\left(\frac{\max(p,10^4)}{10^5}\right)^{0,8}
\left(\frac{\max(T,200)}{300}\right)^{-0,53}
\left(\frac{\max(U_p,1)}{10}\right)^{0,8}.
\]

La fermeture contrôlée ligne par ligne est :

\[
q''_{gaz\rightarrow solide}=h(T_{gaz}-T_{paroi}),
\qquad T_{paroi}=475\ \mathrm{K}.
\]

L'erreur relative maximale de reconstruction sur les 36 fichiers est
`1,61×10⁻⁸`, sous la limite numérique de `10⁻⁶`. Ce contrôle prouve la
transformation des données, pas la justesse physique de la corrélation : son
coefficient et la température de paroi n'ont pas été corrélés au moteur.

Pour préparer une charge mécanique différentielle, F47 publie également :

\[
p_{jauge}=p_{abs}-p_{référence},
\qquad p_{référence}=101\,325\ \mathrm{Pa}.
\]

Cette référence atmosphérique est une hypothèse de criblage. La pression
réelle sur le dos de la chambre, le carter, les conduits et les interfaces doit
être mesurée ou spécifiée avant une analyse structurale autoritaire.

## Bornes numériques globales

Les extrema suivants sont les bornes extérieures des modèles, Cd et pas. Ils
ne se produisent pas nécessairement simultanément.

| Architecture | Pression absolue | Température gaz | `h_gas` global | Flux paroi signé |
|---|---:|---:|---:|---:|
| 2V | 1,805 à 215,179 bar | 385,4 à 2 959,4 K | 238,7 à 5 165,1 W/m²/K | −0,039 à 12,832 MW/m² |
| 4V | 1,921 à 224,959 bar | 375,9 à 2 964,6 K | 241,1 à 5 347,0 W/m²/K | −0,045 à 13,312 MW/m² |

Le maximum extérieur 4V dépasse celui du 2V de `4,55 %` en pression, `0,18 %`
en température, `3,52 %` en `h` et `3,74 %` en flux. Ce sont des accroissements
de **charge de criblage**, pas des marges ni une preuve d'amélioration.

Le faible flux négatif pendant une partie de l'admission n'est pas tronqué :
avec la paroi hypothétique à 475 K, le gaz calculé devient momentanément plus
froid que la paroi. Le signe positif signifie toujours « gaz vers solide ».

Les maxima Cantera de pression, température, `h` et flux se situent autour de
360° dans cette convention. Les maxima Wiebe sont plus tardifs et beaucoup
plus faibles. Cette divergence est conservée dans les CSV/JSON au lieu d'être
moyennée.

## Handoff OpenFOAM, AATE et engineFoam

Le fichier
[`openfoam-aate-enginefoam-patches.json`](../twins/reference-917-engine/evidence/f47-cae-loads/mappings/openfoam-aate-enginefoam-patches.json)
décrit les noms sémantiques attendus : zone gaz cylindre, chambre, calotte de
piston, faces de soupapes et limites de conduits. Toutes les correspondances
géométriques valent `null`, car aucun domaine fluide étanche 2V/4V n'est
disponible.

Règles de transfert :

1. `p(θ)` et `T(θ)` sont des **cibles de comparaison moyennes** pour la
   solution CFD, pas des conditions à imposer sur la chambre ;
2. pour une future CHT, employer soit la paire Robin `h(θ), T_gaz(θ)`, soit le
   flux direct `q''(θ)` pour une sensibilité ;
3. ne jamais appliquer simultanément Robin et flux direct ;
4. sélectionner une trace F46 complète et conserver son `case_id` ;
5. ne jamais transformer l'enveloppe point par point en historique solveur.

Aucun dictionnaire OpenFOAM, maillage mobile ou champ CFD n'est généré. La
cartographie restera bloquée jusqu'à la présence des domaines étanches, des
patches vérifiés et de trois niveaux de maillage.

## Handoff CalculiX

Le fichier
[`calculix-loads.json`](../twins/reference-917-engine/evidence/f47-cae-loads/mappings/calculix-loads.json)
prépare deux voies, sans produire de deck `.inp` :

- pression mécanique : `p_jauge(θ)` vers un futur `*DLOAD, P`, après revue du
  sens des normales et des surfaces de chambre ;
- thermique recommandée : `h(θ), T_gaz(θ)` vers un futur `*FILM` transitoire ;
- thermique de sensibilité : `q''(θ)` vers un futur `*DFLUX`, jamais en même
  temps que le film.

Les ensembles chambre, refroidissement extérieur, deck et goujons sont tous
non résolus. Les contacts, précharges, appuis, cartes matériau à chaud et
inerties ne sont pas inventés. F47 fournit donc des **données candidates de
chargement**, pas un calcul de résistance.

## Géométrie et autorité

F47 ne crée et ne charge aucune CAO, aucun maillage, aucune enveloppe externe
et aucun domaine solveur. La peau du scan n'est pas modifiée. Les noms de
patches sont seulement des emplacements sémantiques futurs. Les fichiers de
preuve ne contiennent ni STEP, ni STL, ni OBJ, ni MSH, ni deck CalculiX.

Toutes les gates restent fermées : domaine fluide 2V/4V, correspondance des
patches, CFD 3D, CHT, analyses CalculiX, corrélation Cd/pression/transfert
thermique, fabrication, impression métallique et démarrage moteur.

## Fichiers et reproduction

- rapport complet :
  `twins/reference-917-engine/evidence/f47-cae-loads/load-report.json` ;
- résumé : `.../summary.json` ;
- enveloppes CSV 2V/4V : `.../envelopes/f47-*-load-envelope.csv` ;
- enveloppes JSON : `.../envelopes/f47-load-envelopes.json` ;
- mappings solveurs : `.../mappings/*.json` ;
- figure 1 920 × 1 080 : `.../figures/f47-cae-load-envelopes.{png,svg}` ;
- empreintes : `.../manifest.json`.

Reconstruction :

```bash
python3 twins/reference-917-engine/source/build_cae_load_transfer_f47.py \
  --project-root .
```

Contrôle non destructif :

```bash
python3 twins/reference-917-engine/source/build_cae_load_transfer_f47.py \
  --project-root . --check
python3 tests/test_917_cae_load_transfer_f47.py -v
```

L'étape suivante défendable consiste à construire deux domaines fluides
étanches conformes aux interfaces mesurées, résoudre la CFD sur trois mailles,
faire une CHT couplée sur un solide muni de cartes matériau à chaud, puis
corréler pression cylindre, Cd et flux sur banc. F47 n'ouvre aucune de ces
autorisations.
