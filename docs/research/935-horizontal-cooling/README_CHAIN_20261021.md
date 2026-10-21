# 935 — reprise par la chaîne logicielle du README

Cette reprise suit la [chaîne du README](../../../README.md#software-chain-qwen-and-picogk)
sur le rotor issu des scans, avec sa [pointe 03 corrigée](TIP_CORRECTION_20261013.md).
Le lot examine la sensibilité de la mécanique à la sélection des nœuds fixés
dans l'alésage. Il conserve la géométrie, les profils acquis et les réparations.
Il ne définit aucun nouvel appui physique.

Le checkout principal contenait d'autres travaux et un ancien README. Le
worktree dédié a repris `origin/main` à `e3cd41df`. La mise à jour a d'abord
échoué faute d'espace ; le checkout a été rétabli après vérification et
suppression de copies locales déjà archivées sur GitHub privé. Les scans,
paramètres et résultats nécessaires au lot restent disponibles.

## Identité, interfaces et hypothèses

Le README renvoie aussi aux [reconstructions analytiques R0/V2/S1](../../../models/horizontal-fan-reconstruction/README.en.md)
et à leur chaîne CAD/CFD. Leurs géométries et conditions ont leur identité
propre. Les résultats CFD ou les modes de V2 ne caractérisent pas le rotor
scanné corrigé. Le présent calcul ne lance pas leur superviseur D3 et ne
modifie pas leurs sources figées.

L'[entrée système 935](../../../twins/935-horizontal-cooling-system/README.md)
et le [contrat des 17 interfaces](../../../twins/935-horizontal-cooling-system-f0/interface-contract.json)
conservent les lacunes de définition. Le chemin d'effort étudié va du rotor
vers le moyeu puis l'arbre et ses appuis. Les cotes d'ajustement, surfaces de
portée, retenue axiale, précharge, rigidité d'appui et variante exacte ne sont
pas mesurées. Aucun de ces champs inconnus n'est complété par le calcul.

Le scénario conserve 6 000 tr/min, AlSi10Mg élastique à E = 70 GPa,
ν = 0,33 et ρ = 2,67 g/cm³, sans qualification de procédé, orientation ni
température. Seule la force centrifuge est appliquée. L'hypothèse d'échelle
reste 1 mm par unité source ; les précisions déclarées dans les noms des
scans ne constituent pas cette calibration.

## Position du lot dans la chaîne

| Étape du README | Exécution et frontière de preuve |
|---|---|
| Catalogue, exigences et interfaces | Réutilisation des identités et lacunes documentées ; aucune nouvelle cote physique admise |
| Qwen puis contrôle indépendant | Assistance facultative ; aucune nouvelle inférence ni exécution de code proposé par un modèle |
| Recettes C# / PicoGK | Rotor natif conservé ; empreinte et moments volumétriques revérifiés, contrôles topologiques antérieurs référencés |
| Gmsh / préparation | Maillages existants conservés ; modification de la seule liste `BORE`, sans changer nœuds, éléments, matériau ou charges |
| CalculiX / revue numérique | Calculs locaux Linux aarch64 sur le Mac, puis couverture complète des résultats et bilans de forces/moments |
| OpenFOAM | Aucun nouveau calcul ; les anciennes valeurs CFD ne sont pas transférées au rotor corrigé |
| OpenUSD / Omniverse | Inspection visuelle séparée ; aucun nouveau résultat SimReady ou jumeau physique qualifié |
| PhysicsNeMo et fabrication | Pas d'entraînement à partir de calculs refusés ; aucune préparation machine ou libération de fabrication |

Cette utilisation des maîtres existants suit le [contrat du workflow](../../architecture/engineering-workflow.md).
La présence d'un outil n'impose pas son exécution à chaque lot. Les sources
PicoGK et les programmes de calcul précédemment figés restent inchangés.

## Expérience : isoler la sélection de l'appui

Le calcul précédent choisissait les nœuds tels que
`abs(sqrt(x²+y²) - R_bore) < h`, où `h` est le pas du maillage. La condition
de fixation variait donc avec la discrétisation, en plus de la géométrie
voxelisée. Une expérience à demi-largeur radiale constante de 1,5 mm
supposé découple ces deux paramètres. Une seconde valeur de 0,6 mm au pas
fin mesure la sensibilité. Ces valeurs sont des bandes de sélection
numériques, pas des jeux, portées de roulement ou tolérances d'usinage.

Le [préparateur](../../../twins/935-horizontal-cooling-system-f0/source/prepare_bore_sensitivity.py)
vérifie les empreintes du parent, du rotor et de la grille, puis remplace
uniquement le bloc `*NSET,NSET=BORE`. Il vérifie la couverture des nœuds et
conserve exactement le texte hors de ce bloc. Le reçu retient la plage
radiale effectivement sélectionnée, le nombre de nœuds fixés et les
empreintes avant/après. Le parent n'est pas modifié.

Au pas de 1,35 mm, la bande de 1,5 mm produit exactement le même deck que
le cas antérieur : son résultat est réutilisé avec son empreinte. Deux
calculs supplémentaires seulement sont nécessaires au pas de 1,2 mm.
Chaque nouveau solveur est limité à 240 s, avec un budget global de 900 s
incluant la revue ; les cas restent séquentiels. Aucun calcul Kali, aucune
location Vast, aucun téléchargement d'image ni modification de service tiers.

## Reproduction et contrôles

Le [reçu structuré](readme-chain-20261021.json) conserve les empreintes et
les contrôles. Les entrées, decks et sorties restent dans l'[archive privée](https://github.com/cluster2600/porscheparts-935-private/releases/tag/readme-chain-20261021).

| Pas supposé, mm | Demi-largeur radiale, mm | Nœuds fixés | Déplacement max., mm | Écart au parent de même pas |
|---|---:|---:|---:|---:|
| 1,35 | 1,50 | 3 848 | 0,603618 | 0 %, deck identique réutilisé |
| 1,20 | 1,20, référence | 4 264 | 0,759834 | référence |
| 1,20 | 1,50 | 4 920 | 0,759617 | −0,0285 % |
| 1,20 | 0,60 | 2 952 | 0,760114 | +0,0369 % |

Les deux nouveaux calculs terminent en 139,3 et 146,5 s de temps solveur.
Les bilans indépendants de forces et moments passent ; la plus grande
erreur relative des trois cas est inférieure à 3 × 10⁻⁹. Les contraintes
maximales du maillage fin restent proches de 197,46 MPa et le P95 des pics
hors r = 25 mm proche de 34,54 MPa. Ces contraintes ne sont pas des limites
admissibles de la pièce.

À demi-largeur constante de 1,5 mm, l'écart de déplacement entre les deux
maillages fins reste **25,84 %**. La variation de bande n'explique donc pas
la non-convergence de cette campagne. Ce résultat n'affirme pas que les
appuis réels sont sans influence : ils ne sont pas représentés par un modèle
de contact ou de roulement mesuré.

La suite numérique est un témoin indépendant de flexion puis une comparaison
de formulations d'éléments sur géométrie identique, avec un appui numérique
fixé. Les surfaces acquises ne seront pas épaissies pour forcer le passage
d'un critère. La métrologie du montage et la qualification matière restent
des travaux distincts nécessaires à la validation du système.

Les cas, entrées et résultats détaillés restent privés sous
`work/935-readme-chain-20261021/`. Le cas d'entrée du préparateur fixe le
répertoire parent, les trois empreintes `receipt.json`, `case.json` et
`rotor.inp`, le chemin du rotor, la demi-largeur et le statut d'hypothèse.

```sh
python prepare_bore_sensitivity.py CASE.json work/NEW-prepared
timeout --signal=TERM --kill-after=10s 240s bash run_candidate_fea.sh \
  work/NEW-prepared/rotor.inp DECK_SHA256 work/NEW-solved
cp work/NEW-solved/ccx.log work/NEW-solved/log.rotor
python assess_mac_fea.py work/NEW-prepared work/NEW-solved work/NEW-assessed
```

Le lancement du solveur utilise Linux natif dans le conteneur local existant.
L'audit est celui de la campagne précédente : déplacements de tous les
nœuds, huit points d'intégration par C3D8, réactions de tous les nœuds fixés,
bilans indépendants, contraintes maximales et P95 hors r = 25 mm. Le script
de revue exige que l'alias de log soit identique au journal original.
Les tests ciblés vérifient la modification limitée au bloc d'appui, la
sélection, la conservation du texte et les refus des entrées invalides.

La [documentation CalculiX, section 6.2](https://www.dhondt.de/ccx_2.15.pdf)
signale la raideur excessive possible du C3D8 pleinement intégré en flexion.
Cette limitation est une piste de diagnostic, pas une cause démontrée par
le présent lot. Un témoin indépendant de flexion et une comparaison de
formulations doivent précéder toute conclusion sur ce mécanisme.

Les résultats restent des études sous hypothèses. Les critères numériques
ne remplacent ni la métrologie, ni la caractérisation des appuis et matériaux,
ni les essais de rotation contenus et la revue mécanique professionnelle.
