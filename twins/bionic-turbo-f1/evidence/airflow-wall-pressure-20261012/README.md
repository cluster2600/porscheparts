# Pression de paroi : contrôle isolé 051 rejeté

Le témoin 044 dérivait du maillage local 043 admis, avec des coupes
synthétiques fixes et une pression `zeroGradient` sur les murs. La fonction
native [constrainPressure v2406](https://gitlab.com/openfoam/core/openfoam/-/raw/OpenFOAM-v2406/src/finiteVolume/cfdTools/general/constrainPressure/constrainPressure.C)
ajuste les gradients des conditions compatibles avec `updateableSnGrad`
pour faire correspondre le flux à la vitesse prescrite, en tenant compte
du repère MRF. La condition native
[fixedFluxPressure](https://gitlab.com/openfoam/core/openfoam/-/raw/OpenFOAM-v2406/src/finiteVolume/fields/fvPatchFields/derived/fixedFluxPressure/fixedFluxPressureFvPatchScalarField.H)
implémente ce mécanisme. Les sources officielles consultées sont référencées
avec leurs empreintes ; aucun code natif n'est modifié.

051 remplace uniquement `walls {type zeroGradient;}` dans `0/p` par
`walls {type fixedFluxPressure; value uniform 101325;}`. Les maillages,
conditions de vitesse et température, rotation, équations, schémas,
tolérances, pas de temps et critères restent identiques. Le comparateur
indépendant vérifie toutes les empreintes des entrées et la substitution
exacte ; il refuse toute autre différence. Les 12 480 cellules et les
320 quadrilatères MRF sont conservés. Le turbo réel n'est pas modifié.

## Résultat natif

checkMesh donne Mesh OK avec les diagnostics de 043 conservés : 417 faces
au-dessus de 70° de non-orthogonalité, maximum 70,8352°. Le calcul termine
200 pas de 0,1 µs jusqu'à 20 µs en 375,283 s, code zéro et sans OOM.
Le conteneur est conservé. Cette fin native ne vaut pas acceptation.

| Mesure sur l'historique | 044 zeroGradient | 051 fixedFluxPressure | Seuil conservé |
|---|---:|---:|---:|
| Écart maximal de pression, Pa | 0,0028541403 | 0,0023936101 | 0,001 |
| Écart maximal de température, K | 1,9837315e-6 | 1,6637543e-6 | 1e-6 |
| Vitesse maximale, m/s | 4,5028331e-5 | 3,7743604e-5 | 1e-8 |

**051 échoue aux trois critères.** Son premier dépassement du seuil de
vitesse est écrit à 10,8 µs, contre 10,6 µs pour 044. Les écarts sont
plus faibles mais restent inacceptables ; cela ne qualifie ni une correction
ni une stabilité de perturbations. Aucun gain physique n'est démontré.
Le Courant maximal reste voisin de 2,059932393. La pression atteint 650 fois
sa limite de 1 000 itérations, contre 647 pour 044 : aucune convergence
linéaire qualifiée. Les résidus imprimés ne sont pas une mesure indépendante
du résidu absolu de la matrice.

Le lecteur vérifie tous les payloads natifs et relit p/T/U sur les 12 480
cellules : valeurs finies, vitesse finale maximale identique au maximum
historique. Il recalcule aussi la géométrie MRF : normale de rotation
maximale 1,65448e-11 m/s, planéité 5,726e-18 m. Ces valeurs géométriques ne
sont pas des débits d'air. La comparaison réutilise les critères originaux
et leurs historiques vérifiés, sans modifier les preuves 044.

## Portée et suite

La compatibilité de pression de paroi est une piste fondée sur le code
natif, mais son changement isolé n'a pas supprimé la dérive du témoin.
Le contrôle périodique 048 reste un autre problème aux limites ; il ne
rend pas ce contrôle à murs fixes acceptable. Aucune prescription de
pression nouvelle n'est appliquée au turbo complet.

Avant de multiplier les calculs, examiner les flux et les opérateurs aux
parois fixes incluses dans MRF, avec bilan absolu/relatif explicitement
vérifié et résidus matriciels distingués des résidus normalisés imprimés.
Ne pas déduire de ce rejet une exclusion générale des murs fixes du repère,
un besoin de changer les pièces, ni un ajustement de tolérance. Le maillage
réel 033 reste rejeté ; sa correction de séparation roue–écrou doit rester
préservée. Aucun débit maximal, gain de puissance ou jumeau calibré validé.

## Conservation

[Archive native 051](https://github.com/cluster2600/porscheparts/releases/tag/bionic-turbo-wall-pressure-2026-10-12) :
35 fichiers, 1 350 993 octets, SHA-256
`5e150c0e733872e08146848fcd82a8ce01a1f51e7d26a1dad0031c7acd50127b`.
Tous les payloads sont relus localement. Les reçus, historiques et champs
sont conservés, y compris le rejet. La vérification distante des cinq actifs
compare tailles et SHA-256 GitHub ; elle ne prétend pas à un second
téléchargement intégral.
