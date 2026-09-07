# F50 — récupération CFD 2V/4V sans changement de géométrie

## Verdict

Cette itération explique l'arrêt numérique F49 et fournit un contrôle de débit
stationnaire indépendant sur les douze combinaisons 2V/4V, admission/échappement
et trois grilles. Elle ne valide pas une culasse, un moteur ni une impression.
Les portes énergie, accord interméthode, CHT, fabrication et démarrage restent
fermées.

Les volumes gaz natifs F48 ont été repris bit pour bit par leur SHA-256. Aucun
scan, solide de culasse ou champ brut n'est publié. Aucune surface extérieure ou
intérieure n'a été modifiée et aucun proxy ovale ou elliptique n'a été créé.

## Ce qui s'est passé dans F49

Les calculs transitoires compressibles d'échappement F49 n'ont pas atteint
l'horizon minimal de 5 ms :

| Cas | temps physique final | pas minimal | Co maximal | facteur minimal de croissance du taux local |
| --- | ---: | ---: | ---: | ---: |
| 2V grossier échappement | 2,212681 ms | 2,011e-39 s | 0,1201 | 4,765e30 |
| 4V grossier échappement | 1,915030 ms | 6,784e-47 s | 0,1214 | 1,397e38 |

Le contrôle de Courant a conservé `Co ≈ 0,1` uniquement en réduisant le pas de
temps. Lorsque `deltaT < 1e-20 s`, le temps physique n'avance plus. Sur le cas
2V, le résidu initial d'enthalpie atteint environ 1 alors que les résidus de
vitesse deviennent artificiellement minuscules. Cela caractérise une stagnation
numérique du couplage pression–énergie, pas une convergence physique. Le constat
ne permet pas d'attribuer la divergence à une forme, une paroi ou un mécanisme
physique précis.

![Effondrement du pas F49](../twins/reference-917-engine/evidence/f50-cfd-recovery/917-f50-transient-timestep-collapse.png)

## Formulation indépendante 1 — stationnaire compressible

Une formulation officielle OpenFOAM Foundation 14, `foamRun -solver fluid` avec
`ddtSchemes steadyState`, a été essayée sur le cas 2V grossier échappement. Les
conditions finales configurées restent celles de F49, mais la divergence empêche
de les atteindre. Une initialisation laminaire par
paliers a été utilisée pour éviter un choc numérique :

- le palier à 1 % atteint l'itération 250 ;
- le palier à 10 % diverge avant l'itération 500, dernière écriture complète à
  l'itération 440 ;
- l'écart massique instantané est alors 0,05584 %, mais le débit n'est pas en
  plateau (dispersion 48,03 %) ;
- l'écart énergétique stationnaire est 99,999 % et le solveur de pression finit
  par `SIGFPE` après inversion du débit.

Cette formulation échoue donc. Le faible écart massique instantané ne peut pas
être utilisé hors du contexte de divergence.

## Formulation indépendante 2 — contrôle de conductance incompressible

Le contrôle utilise `foamRun -solver incompressibleFluid`, `steadyState` et
`kOmegaSST`. Il conserve le différentiel physique de 10 kPa de F49. Pour chaque
écran, une densité constante est calculée à l'état source :

\[
\rho = \frac{p_{source}}{R_{air} T_{source}}, \qquad R_{air}=287{,}05\;J\,kg^{-1}K^{-1}
\]

La pression cinématique imposée et la viscosité cinématique sont :

\[
\Delta p_k = \frac{10\,000}{\rho}, \qquad \nu = \frac{1{,}82\times10^{-5}}{\rho}
\]

Ce modèle répond à une seule question : la conductance des mêmes domaines sous
le même différentiel de pression est-elle numériquement reproductible ? Il ne
résout pas l'équation d'énergie. Un résultat de débit vert ne peut donc pas
ouvrir une porte thermique.

Le générateur F49 hérité avait laissé `execution_status=prepared_not_run` dans
le `case.json` avant calcul. Les rapports runners ont conservé ce champ obsolète
malgré la commande `foamRun` réellement journalisée. La publication ne reprend
pas cette contradiction telle quelle : elle exige une étape `foamRun`, son code
retour, sa durée et le SHA-256 du log, puis normalise `execution_status` à
`EXECUTED` tout en conservant la valeur héritée sous
`legacy_input_execution_status` pour l'audit.

### Portes par cas

- `checkMesh` et écart de volume OpenFOAM/F48 inférieur ou égal à 1 % ;
- code retour solveur nul et 6 000 itérations atteintes ;
- déséquilibre massique inférieur ou égal à 1 % ;
- dispersion des dix derniers débits inférieure ou égale à 1 % ;
- résidus finaux : `p <= 1e-6`, `U/k/omega <= 1e-5` ;
- énergie : toujours indisponible, donc rouge pour une validation complète.

### Résultats des douze cas

Les douze rapports sélectionnés proviennent de l'exécution Vast contenue dans
`f50-cfd-final12.tar.gz`, SHA-256
`c939326b884c75e77de314841503c49c71b96bab38c854dfb7c3156fa5a30c81`.
Les diagnostics transitoire et stationnaire compressible ont été exécutés sur
Kali. Sept cas sur douze passent toutes les portes numériques de débit ; aucun
cas ne passe la validation complète car l'énergie reste indisponible.

| Cas | débit puits kg/s | masse % | plateau % | résidu p | porte débit |
| --- | ---: | ---: | ---: | ---: | :---: |
| 2V grossier admission | 0,197748 | 2,71e-9 | 1,12e-8 | 2,37e-8 | oui |
| 2V moyen admission | 0,200790 | 1,80e-8 | 4,08e-8 | 1,81e-7 | oui |
| 2V fin admission | 0,199051 | 5,33e-7 | 5,50e-10 | 3,95e-6 | **non** |
| 2V grossier échappement | 0,076038 | 1,16e-6 | 1,03e-9 | 3,52e-7 | oui |
| 2V moyen échappement | 0,077791 | 9,19e-8 | 4,33e-10 | 1,14e-7 | oui |
| 2V fin échappement | 0,078683 | 4,48e-7 | 4,99e-10 | 4,19e-7 | oui |
| 4V grossier admission | 0,236292 | 7,24e-6 | 2,39e-7 | 9,13e-6 | **non** |
| 4V moyen admission | 0,241484 | 3,33e-5 | 6,28e-5 | 1,25e-5 | **non** |
| 4V fin admission | 0,242474 | 3,35e-6 | 9,86e-7 | 1,58e-6 | **non** |
| 4V grossier échappement | 0,082220 | 4,98e-7 | 3,68e-9 | 1,88e-7 | **non** |
| 4V moyen échappement | 0,082504 | 2,18e-7 | 6,26e-10 | 1,67e-7 | oui |
| 4V fin échappement | 0,083916 | 3,21e-8 | 4,29e-9 | 1,59e-7 | oui |

Tous les déséquilibres massiques et plateaux sont sous 1 %. Les admissions 2V
fine et 4V moyen/fin échouent sur le résidu de pression. L'admission 4V
grossière échoue aussi sur ce résidu. Les deux cas 4V grossiers sont refusés par
l'écart de volume OpenFOAM/F48 d'environ 1,504 %, supérieur à la porte de 1 %.

![Débits sur trois grilles](../twins/reference-917-engine/evidence/f50-cfd-recovery/917-f50-incompressible-grid-comparison.png)

![Portes numériques](../twins/reference-917-engine/evidence/f50-cfd-recovery/917-f50-incompressible-numerical-gates.png)

## Convergence sur trois grilles

Pour chaque couple variante/écran, la taille effective est
`h = N_cells^(-1/3)`. Avec `1=fine`, `2=medium`, `3=coarse`, l'ordre observé est
obtenu par itération de la formulation à ratios inégaux :

\[
p=\frac{1}{\ln r_{21}}\left|\ln\left|\frac{\epsilon_{32}}{\epsilon_{21}}\right|
+\ln\left(\frac{r_{21}^{p}-s}{r_{32}^{p}-s}\right)\right|
\]

où `s = sign(epsilon32/epsilon21)`. Le GCI avec facteur de sécurité `Fs=1,25`
est :

\[
GCI_{21}=\frac{1{,}25\,|\phi_1-\phi_2|/|\phi_1|}{r_{21}^{p}-1}
\]

La porte demande une évolution monotone, `0,5 <= p <= 10`,
`GCI21 <= 5 %` et un rapport asymptotique entre 0,9 et 1,1. Une grille dont la
porte de volume ou de solveur échoue rend le GCI indisponible ; aucune valeur
n'est réparée ni écartée pour améliorer artificiellement la convergence.

Une seule des quatre séries ouvre cette porte : l'échappement 2V, avec
`p=2,239`, `GCI fine/moyen=0,831 %` et rapport asymptotique `1,011`. Le GCI
admission 2V est indisponible à cause du résidu de la grille fine. Les deux GCI
4V sont indisponibles puisque toutes leurs grilles n'ont pas une porte débit
verte.

Les écarts bruts 4V–2V sont de `+6,06 %` sur la grille moyenne échappement et
`+6,65 %` sur la grille fine échappement. Ils ne constituent pas une
revendication de performance : le GCI 4V, l'énergie et l'accord avec une seconde
formulation convergée manquent encore. La même interdiction s'applique aux
écarts bruts d'admission.

Les valeurs complètes sont publiées dans
[`f50-cfd-recovery-report.json`](../twins/reference-917-engine/evidence/f50-cfd-recovery/f50-cfd-recovery-report.json)
et le tableau machine dans
[`917-f50-incompressible-cases.csv`](../twins/reference-917-engine/evidence/f50-cfd-recovery/917-f50-incompressible-cases.csv).

## Accord F49/F50

Le rapport calcule, à titre informatif seulement, l'écart brut lorsque F49
contient le cas correspondant. F49 n'a aucun cas convergé et ne contient pas les
grilles fines. La porte d'accord interméthode ne peut donc pas être évaluée et
reste rouge. Il serait incorrect de comparer une valeur F49 transitoire arrêtée
en cours d'évolution à un plateau stationnaire et de l'appeler validation.

## Reproduction

Les maillages F48 restent hors dépôt conformément à leur politique. Sur le
calculateur autorisé qui les contient :

```sh
python3 twins/reference-917-engine/source/build_cfd_cases_f50_incompressible.py \
  --project-root . \
  --domain-root "$F48_DOMAIN_ROOT" \
  --output "$F50_WORK_ROOT" \
  --iterations 6000

python3 twins/reference-917-engine/source/run_cfd_cases_f50_incompressible.py \
  --project-root . \
  --work-root "$F50_WORK_ROOT" \
  --levels coarse medium fine \
  --variants 2V 4V \
  --screens intake exhaust
```

Le second appel est séquentiel. Les douze identifiants de cas peuvent être
lancés en processus séparés avec un seul niveau, une seule variante et un seul
écran par processus, car leurs répertoires sont disjoints. Il ne faut jamais
lancer deux processus sur le même identifiant. Les rapports d'exécution sont ensuite passés à
`publish_cfd_recovery_f50.py`. La publication vérifie douze identifiants uniques,
les drapeaux d'immuabilité géométrique et l'autorité runtime avant de calculer
les GCI.

Le contrôle autonome du lot public est :

```sh
make 917-f50-cfd-recovery-check
```

## Calculateur et coût de la campagne

La campagne sélectionnée a utilisé un seul calculateur éphémère vérifié :
`32` cœurs CPU effectifs, `128565 MB` de RAM et une NVIDIA RTX PRO 6000
Blackwell de `97887 MB`. L'image `linux/amd64` était épinglée au digest
`sha256:897ee887e0d442d871ac7980730d3a4d7ae59fff4aff17e4ff5809cb735fd331`.
La fenêtre d'exécution observée, depuis le marqueur runtime prêt jusqu'à la
vérification de destruction, est restée inférieure à une heure. Au tarif
affiché de `2,0072888889 USD/h`, le coût conservateur retenu est donc
`<= 2,01 USD` pour le calculateur, hors trafic réseau. Ce chiffre est une borne
technique calculée, pas une facture fournisseur. Après récupération et
vérification SHA-256 des douze rapports et des journaux bruts, la location a
été détruite et l'inventaire actif vérifié vide. Aucun identifiant d'instance,
hôte SSH ou chemin privé n'est publié.

## Portes explicitement fermées

- énergie `<= 1 %` : indisponible sur le contrôle incompressible et en échec sur
  les formulations compressibles ;
- CHT : aucun domaine solide final ni condition thermique corrélée ;
- AATE/moteur : aucun cycle mobile, piston, loi de soupape ni combustion ;
- performance 4V : aucune revendication tant que GCI et accord interméthode ne
sont pas tous verts ;
- impression, démarrage et montage : non autorisés.
