# Système horizontal 935 — préparation de la référence

Étape du 3 octobre 2026 : deux scans préparés et passés par PicoGK, exigences
d'interfaces définies, recherche dimensionnelle poursuivie, puis
[base exécutable du jumeau système](SYSTEM_TWIN.md) : registre complet des
fonctions, graphe OpenUSD, six modèles réduits et comparaison aux mesures.
La référence
fonctionnelle, les améliorations et le jumeau calibré restent à construire.

## Contrat indépendant avant reconstruction

Le [contrat](interface-contract.json) décrit **17 interfaces** : rotor/moyeu,
arbres, courroies, transmission, appuis, support, moteur, carter, guides,
lubrification, accouplement et alternateur. Il décrit les chemins d'efforts
à vérifier et les preuves nécessaires. Les axes, trous, faces, tolérances,
échelles et la variante moteur cible sont inconnus. Aucune cote plausible
ne les remplace. L'emplacement de l'accouplement sur le spécimen doit être
identifié ; la fiche fournisseur ne suffit pas à l'assigner.

Voir le [dossier documentaire](../../docs/research/935-horizontal-cooling/DIMENSIONS_AND_DETAILS.md)
pour distinguer fiche FIA de base, références Porsche 993 et reproductions
935. Aucun de ces champs commerciaux n'est une calibration de nos scans.

## Traitement des scans exécuté

La préparation réutilise le [programme existant](../993-engine-cooling-fan-system-f0/source/prepare_private_scan.py) :
transformation rigide PCA, matrice inverse conservée, ordre des sommets
préservé, retrait des seuls triangles d'aire exactement nulle. La PCA fournit
des vues pratiques et ne définit ni un axe fonctionnel ni une mise en position
rotor/support. Le dos du rotor n'a pas été réaligné ou comblé.

| Résultat | Rotor | Entraînement/support |
|---|---:|---:|
| Sommets conservés | 624 492 | 1 256 836 |
| Triangles après préparation | 1 240 439 | 2 484 656 |
| Triangles d'aire nulle retirés | 26 | 0 |
| Arêtes de bord après préparation et après PicoGK | 8 657 | 29 476 |
| Contours de bord après préparation | 58 | 200 |
| Composantes de surface | 2 | 1 |
| Cercles de bord passant le filtre diagnostique | 0 | 0 |

[inspect_private_interfaces.py](source/inspect_private_interfaces.py) examine
les contours de bord, ajuste un plan/cercle et exige une couverture angulaire
suffisante. Les seuils sont des filtres diagnostiques, pas des tolérances
d'usinage. Les contours correspondent aussi à des défauts de couverture :
ce filtre ne détecte pas tous les alésages internes à une surface continue.
Il ne segmente pas toutes les pièces mécaniques. Aucun datum mesuré n'est
établi par ce résultat négatif.

## PicoGK réellement exécuté

[ScanReview](source/picogk-scan-review/Program.cs) utilise une instance
`Library` sans viewer. Le noyau local est **PicoGK Core 26.2.0**, build natif
`2026-06-05 21:50:16`. Les empreintes des bibliothèques C# et native sont
conservées dans le résumé. La source locale du
[projet LEAP 71](https://github.com/leap71/PicoGK) est au commit
`0e6cf6b6f4993ec16dbcd72d8f27f26b999980f3` ; ce repère ne constitue pas
une attestation de construction des binaires réutilisés.

Le témoin synthétique annulaire, de dimensions choisies et connues en mm,
teste les opérations voxel, le volume et trois sondes intérieur/extérieur.
À 0,5 mm/voxel, l'écart de volume à la formule analytique est **0,0556 %**.
C'est une vérification du runtime sur ce témoin, sans validation d'un
ventilateur ni garantie générale de convergence géométrique.

Les deux OBJ préparés ont ensuite été chargés comme `PicoGK.Mesh`, sans
voxelisation. Tous les indices de triangles ont été relus dans le noyau avant
export ; le nouvel audit des OBJ exportés conserve les comptes de bord,
sans nouvelle aire nulle, arête non-manifold ou incohérence d'orientation.
PicoGK stocke les positions en float32 : l'écart maximal de chaque scan est
mesuré dans son reçu privé, en unités source inconnues. Il ne peut pas être
interprété en mm ou confronté à une tolérance fonctionnelle à ce stade.
Les intersections de surfaces ne sont pas qualifiées par cet audit.

## Reproduction locale

Les sorties doivent être dans un nouveau dossier privé, hors Git ou sous
`work/` ignoré. Les fichiers d'entrée ne sont pas modifiés. NumPy, SciPy et
Matplotlib sont nécessaires au diagnostic Python ; .NET 9 et une installation
PicoGK officielle déjà qualifiée sont nécessaires au programme C#.

```sh
python3 twins/993-engine-cooling-fan-system-f0/source/prepare_private_scan.py PRIVATE.obj work/NEW/prepared --expected-sha256 RAW_SHA256
python3 twins/935-horizontal-cooling-system-f0/source/inspect_private_interfaces.py work/NEW/prepared/pose-normalized-open-scan.obj work/NEW/inspection --expected-sha256 PREPARED_SHA256
dotnet build twins/935-horizontal-cooling-system-f0/source/picogk-scan-review/ScanReview.csproj -p:PicoGKAssembly=/PRIVATE/PicoGK.dll -p:BaseIntermediateOutputPath=/PRIVATE/obj/ -o /PRIVATE/bin
# Installer les bibliotheques natives officielles compatibles a cote du binaire.
dotnet /PRIVATE/bin/ScanReview.dll witness work/NEW/witness
dotnet /PRIVATE/bin/ScanReview.dll mesh work/NEW/prepared/pose-normalized-open-scan.obj PREPARED_SHA256 work/NEW/picogk
```

Le [reçu public limité](../../docs/research/935-horizontal-cooling/preparation-summary.json)
conserve les empreintes des entrées/exports/outils et les comptes.
Les coordonnées, transformations, géométries et paramètres dérivés restent
dans les rapports privés. Huit tests synthétiques Python couvrent les cercles
inclinés, arcs incomplets, anneaux non plans, dégénérescences, bords pincés,
surfaces distinctes et protections des entrées/sorties. Six cas CLI natifs
ont vérifié export ouvert, rejet de valeurs non finies/indices invalides/
records inconnus, contrôle SHA et refus d'écrasement.

## Réparation visuelle du rotor

La fermeture Screened Poisson produite par
[photo_guided_surface_repair.py](source/photo_guided_surface_repair.py) est
rejetée après revue multi-vues : sa fermeture topologique invente des volumes
au moyeu et entre les pales. Elle est gardée privée comme tentative, jamais
comme référence, interface ou maillage de calcul.

Le programme
[picogk-rotor-visual-proxy](source/picogk-rotor-visual-proxy/Program.cs)
produit à la place une topologie visuelle explicite avec un disque, un moyeu
et dix pales courbes. PicoGK l'aligne sur l'enveloppe PCA du scan, sans
convertir l'unité source en millimètres ni déduire une interface. La
[documentation du proxy](../../docs/research/935-horizontal-cooling/PICOGK_ROTOR_VISUAL_PROXY.md)
enregistre son audit et ses limites.

## Prochaine preuve à obtenir

Il faut identifier la variante, établir l'échelle sur deux cotes indépendantes
et vérifier les interfaces du contrat pour reconstruire une référence
fonctionnelle. Les intérieurs de la transmission et les guides manquants
requièrent aussi des documents ou inspections adaptés. Les calculs de masse,
inertie, contraintes, entraînement, débit/pression et refroidissement du
spécimen utiliseront ces entrées qualifiées ; aucune caractéristique réelle
ou amélioration chiffrée n'est annoncée à partir du seul passage dans PicoGK.
