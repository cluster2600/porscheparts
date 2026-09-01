# Contrats F1 de segmentation et de simulation moteur

Ce dossier transforme les géométries de référence en un registre vérifiable de
composants, interfaces, matériaux candidats et cas de charge. Il ne contient ni
scan, ni maillage dérivé, ni USD. Ces artefacts restent sous `raw-scans/` et
`work/`, hors Git, conformément à l'instruction du propriétaire.

## État obtenu

Le raffinement géométrique du moteur 917 affecte chaque face à au plus un
voisinage d'ouverture. Sur le maillage local de 599 999 triangles, 118 938
triangles sont distribués entre douze voisinages et 481 061 restent dans le
corps non classifié, soit zéro recouvrement par construction. Ces régions sont
des voisinages visibles, pas encore des cylindres manufacturables.

Pour la culasse 935, la séparation par connexité conserve neuf composants
externes de plus de 250 triangles. Les étiquettes `stud_or_long_fastener` et
`small_external_hardware` sont seulement des candidats de faible confiance à
confirmer visuellement.

## Exécution reproductible

```bash
make engine-contracts
make engine-contracts-check
```

Le calcul utilise l'image immuable :
`ghcr.io/cluster2600/3dprinting993-mesh-cfd@sha256:a1db60cbf61bbcca52c171e50cab01ed0b6ec860b227e7c5fc50f7b809659b4f`.

## Matériaux candidats

Le Ti-6Al-4V LPBF EOS est retenu uniquement comme candidat pour une soupape
d'admission. Les données thermiques TIMET sont celles d'un produit corroyé et
servent de référence provisoire, jamais d'équivalent LPBF. L'INCONEL 751 en
barre vieillie est retenu comme référence candidate pour l'échappement. Aucun
de ces jeux n'est affecté automatiquement aux scans 917 ou 935, dont les
alliages restent inconnus.

Sources primaires : [EOS Ti64 Grade 5](https://store.eos.info/de/products/eos-titanium-ti64-grade-5),
[TIMETAL 6-4](https://www.timet.com/documents/datasheets/alpha-and-beta-alloys/timetal-6-4.pdf) et
[INCONEL alloy 751](https://www.specialmetals.com/documents/technical-bulletins/inconel/inconel-alloy-751.pdf).

## Matrice de préparation

| Cas | Géométrie | Matière | Conditions | État |
|---|---|---|---|---|
| soupape 993 thermique | proxy incomplet | candidate | manquantes | bloqué |
| distribution 993 dynamique | proxy incomplet | candidate | profil de came et ressort manquants | bloqué |
| conduit 935 à froid | deux domaines locaux | culasse inconnue | port, levée et pressions manquants | bloqué |
| refroidissement externe 917 | maillage `checkMesh` en échec | composants inconnus | débit et charge thermique manquants | bloqué |

PhysicsNeMo reste désactivé. Il ne pourra servir que de surrogate après une
solution de référence validée, une étude d'indépendance au maillage et une
validation sur un jeu tenu à l'écart. Les propriétés USD/Omniverse ne seront
assignées qu'après validation sémantique, métrique et matière des composants.

## Proxies d'organes moteur

`make engine-components` génère localement cinq masters STEP et leurs STL
`display-only` : piston 993 Turbo, bielle PAUTER, arbre à cames d'implantation,
K16 gauche et K16 droit. Les paramètres et leur niveau de preuve sont dans
`engine-components-f1.json` : une valeur déclarée et une hypothèse de forme ne
sont jamais fusionnées en une cote prétendument mesurée.

- piston : diamètre 100 mm = alésage moteur nominal, pas diamètre de piston ;
- bielle : entraxe, alésages, largeurs et masse déclarés ; contour extérieur hypothétique ;
- arbre à cames : topologie d'implantation uniquement, profil et calage non mesurés ;
- K16 : encombrement et masses fournisseur, diamètres de roues catalogue du côté droit ; carters et surfaces aérodynamiques hypothétiques.
