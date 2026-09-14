# Culasse 917 conceptuelle 2V/4V — F29

## Résultat

F29 produit quatre solides paramétriques fermés : deux architectures de culasse
(2 et 4 soupapes) appliquées aux enveloppes atmosphérique 5,0 l et turbo
5,374 l. Chaque STEP a été rouvert dans OCCT et vérifié comme un solide unique,
valide, manifold et fermé.

Ce résultat est une étude de concept à partir d'une feuille blanche. Il ne
reproduit pas une culasse Porsche mesurée, ne prouve aucun ajustement sur un
moteur 917 et n'autorise ni impression métal, ni montage, ni démarrage moteur.

| Scénario | Architecture en tête | Aire effective moyenne 4V vs 2V | Masse totale estimée des soupapes | Contrainte de plaque 4V vs 2V | Indicateur thermique 4V vs 2V |
| --- | --- | ---: | ---: | ---: | ---: |
| 5,0 l atmosphérique | 4V | +19,60 % | +21,22 % | +10,35 % | +4,78 % |
| 5,374 l turbo | 4V | +19,60 % | +18,55 % | +10,39 % | +4,78 % |

La branche 4V est donc le concept prioritaire pour la prochaine itération CFD/FEA.
La 2V reste le témoin de référence : elle est plus simple, comporte moins
d'ouvertures et obtient de meilleurs indicateurs thermiques et structuraux dans
ce modèle simplifié.

## Géométries produites

Les maîtres neutres STEP sont les livrables modifiables. Les STL sont uniquement
des dérivés de visualisation et de maillage :

- `work/917-clean-sheet-head-f29/cad/type_912_5_0_na_2v.step`
- `work/917-clean-sheet-head-f29/cad/type_912_5_0_na_4v.step`
- `work/917-clean-sheet-head-f29/cad/917_30_1973_turbo_5374_2v.step`
- `work/917-clean-sheet-head-f29/cad/917_30_1973_turbo_5374_4v.step`

L'instantané publié avec ses rapports, STEP, STL et figures se trouve dans
`twins/reference-917-engine/evidence/f29/`. Les chemins `work/` ci-dessus restent
les sorties reproductibles locales et ne sont pas suivis par Git.

L'image CAO utilisée est verrouillée par digest :
`ghcr.io/cluster2600/3dprinting993-cad-author-f28@sha256:18dbfa559306a31c909480695acf0e89a9bc904c83d280065c1d9d29036fec57`.

## Modèles mathématiques exécutés

- Débit relatif : aire de rideau et aire de gorge, coefficient de décharge et
  débit d'orifice à perte de charge constante. Ce n'est pas un rendement
  volumétrique moteur.
- Résistance : plaque circulaire mince sous pression, corrigée par une pénalité
  d'ouvertures et de ponts de sièges. Ce n'est pas une FEA 3D.
- Thermique : conduction 1D à travers le deck avec flux imposé. Ce n'est pas un
  calcul conjugué air/métal/gaz.
- Distribution : mouvement sinusoïdal de soupape, effort gaz/inertie et modèle
  masse-ressort. Ce n'est pas la loi de came réelle et ne détecte ni surge, ni
  rebond, ni impact de siège.

Les pressions, flux thermiques, coefficients de décharge et conductivités sont
des hypothèses de sensibilité. Ils ne proviennent pas d'une corrélation banc.

## Choix matière et distribution

Le criblage retient provisoirement :

- culasse : AlF357 en LPBF, devant AlSi10Mg pour la limite élastique et
  l'allongement à température ambiante dans les conditions fournisseur citées ;
- soupape d'admission : Ti-6Al-4V forgé ou usiné, acheté, non imprimé ;
- soupape d'échappement : INCONEL 751 acheté, non imprimé ;
- ressort : acier silicium-chrome trempé à l'huile, nitruré et grenaillé en
  plusieurs étapes, acheté, non imprimé.

Le choix AlF357 reste bloqué tant que les courbes à chaud, fatigue
thermomécanique, orientation LPBF, traitement thermique, porosité, étanchéité,
usinage et contrôle non destructif ne sont pas qualifiés. Références :
[EOS AlF357](https://store.eos.info/products/eos-aluminum-alf357),
[EOS AlSi10Mg](https://store.eos.info/products/eos-aluminum-alsi10mg),
[Special Metals INCONEL 751](https://www.specialmetals.com/documents/technical-bulletins/inconel/inconel-alloy-751.pdf) et
[SAE 2009-32-0082](https://saemobilus.sae.org/papers/development-high-fatigue-strength-valve-spring-using-control-white-layer-nitriding-2009-32-0082).

## Omniverse et PhysicsNeMo

Le préflight officiel CAD-to-SimReady est bloqué sur le Mac arm64 actuel :
OpenUSD Python, Asset Validator, `usd-convert-cad`, SimReady Foundation, les
Content Agents et les services matériau/physique/OVRTX ne sont pas disponibles.
Aucun USD n'a donc été créé et aucun essai Omniverse/PhysX n'est revendiqué.

Une exécution distante a ensuite été tentée sur Vast.ai avec une RTX PRO 6000
WS de 97 887 Mo et l'image SimReady verrouillée par digest. L'instance est
restée en état `loading` et n'a exposé ni SSH authentifié, ni marqueur
`/workspace/READY` pendant les 1 200 s autorisées. Aucun STEP n'a été transféré,
aucun préflight distant n'a été exécuté et le bilan reste donc à zéro USD, zéro
image et zéro validation SimReady. L'instance a été détruite avec récupération
explicitement levée puisqu'aucun artefact distant n'existait. Les rapports
`instance-ready.json` et `destroy-report.json` sont référencés avec leur SHA-256
dans le handoff F29.

Omniverse sert ici à composer, inspecter et visualiser les résultats. PhysX
n'est pas un solveur de contrainte thermomécanique de culasse. Les champs de
résistance et de performance devront venir de solveurs CFD/FEA de référence,
puis être affichés dans Omniverse. PhysicsNeMo pourra ensuite apprendre un
substitut DoMINO, Transolver, FIGConvUNet ou MeshGraphNet seulement après
constitution et corrélation d'un jeu de simulations.

Le handoff est défini dans
`twins/reference-917-engine/omniverse-handoff-f29.json`. Les preuves locales
sont consolidées dans `work/917-clean-sheet-head-f29/report.json` et
l'instantané publié dans
`twins/reference-917-engine/evidence/f29/validation-report.json`.

Les deux figures publiées sont des aperçus techniques reproductibles : une
planche issue directement des quatre STL et un graphique des variations 4V par
rapport au 2V. Elles ne sont ni des rendus Omniverse ni des résultats CFD/FEA.

## Reproduction

```bash
make 917-clean-sheet-head-f29
make 917-clean-sheet-head-f29-check
make 917-clean-sheet-head-f29-figures
```

Le second objectif exige un rapport de préflight Omniverse F29 existant. Un
préflight bloqué est un résultat recevable ; il doit rester bloquant et ne doit
jamais être transformé en succès simulé.
