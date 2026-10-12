# Préparer un diagnostic natif sans changer les équations — 052/053

Un diagnostic des résidus absolus nécessite de vérifier d'abord qu'une
recompilation locale du solveur intact reproduit le binaire de référence.
Sur le contrôle court décrit ici, **les cinq champs finaux p, T, U, rho et
phi sont identiques octet pour octet**. Aucun solveur instrumenté n'est
encore utilisé. Ce résultat logiciel ne qualifie pas le repos du turbo.

## Sources et environnement

Le runtime original reste l'image OpenCFD v2406 épinglée utilisée depuis
les témoins précédents. Ses métadonnées donnent api2406, patch0, build
`_be01ca78-20240625`. L'archive officielle
[OpenFOAM-v2406](https://dl.openfoam.com/source/v2406/) contient
52 374 726 octets, SHA-256
`8d1450fb89eec1e7cecc55c3bb7bc486ccbf63d069379d1d5d7518fa16a4686a`.
Son identifiant exporté est `_630d60de3b-20240620`.

La [comparaison officielle des révisions](https://gitlab.com/openfoam/core/openfoam/-/compare/630d60de3bb6c1646fcd4e0da39332332ca14a2d..be01ca78882c0bb2b9cd15c22d1b0e5e517735b3)
renvoie zéro fichier différent et aucun timeout. La seconde révision est
une fusion dont la première est un parent. Cela établit une correspondance
des sources, pas une identité des binaires compilés.

Une image locale séparée ajoute g++ et make au runtime épinglé. Elle ne
remplace pas l'image originale. La compilation utilise GCC13.3.0, C++14,
double précision et labels32 bits, avec les options wmake originales.
Les bibliothèques OpenFOAM du runtime original sont utilisées à l'édition
de liens. Aucun fichier d'équation n'est modifié.

Le premier montage de sources sur macOS est rejeté : `Time.H` et `time.h`,
ainsi que `string.H` et `string.h`, y désignent le même fichier. Les en-têtes
échouent à la compilation. Un volume Docker Linux neuf permet la distinction
requise. Les 27 092 fichiers réguliers de l'archive sont ensuite comparés
par SHA-256 à ceux du volume compilé : tous sont inchangés.

Les essais intermédiaires restent conservés : chargement bashrc sous
`set -e`, mauvais chemin de binaire, compilation sur le montage insensible
à la casse, chemin erroné dans le lanceur Linux, puis recherche de
bibliothèques au mauvais emplacement. La version6 ajoute le chemin des
bibliothèques natives via l'option wmake `FOAM_EXTRA_LDFLAGS`. Elle termine
avec code zéro. Aucun de ces échecs n'a lancé d'écoulement. Le volume,
les images et les conteneurs restent disponibles, sans suppression.

## Comparaison appariée

Les deux cas neufs dérivent des entrées exactes de 044. Le pas reste
1e-7 s ; seuls la durée et l'intervalle d'écriture sont raccourcis de manière
identique : deux pas, champ final à **2e-7 s**, soit 0,2 µs. Les équations,
conditions aux limites, maillage et tolérances sont inchangés. Cette fenêtre
courte ne remplace pas le contrôle de repos de 20 µs et n'annule pas le rejet
044. Aucune tolérance numérique n'est introduite pour la comparaison logicielle.

052 exécute le binaire original ; 053 le binaire recompilé monté en lecture
seule. Les deux utilisent la même image runtime originale, un CPU, 2 Gio,
réseau désactivé, timeout180 s. Les entrées sont identiques par empreinte et
les commandes ne diffèrent que par l'exécutable, le nom du conteneur et le
chemin du cas. checkMesh est relancé comme admission native avant chaque
exécution ; les diagnostics existants du maillage sont conservés.

| Contrôle | 052 original | 053 recompilé |
|---|---:|---:|
| Code de fin natif | 0 | 0 |
| Durée murale, s | 5,594 | 5,585 |
| Pas terminés | 2 | 2 |
| OOM | non | non |
| Champs finaux | p/T/U/rho/phi | p/T/U/rho/phi |

Le SHA du binaire original vaut
`85e40da38fc4fd0ba24ef1560f659390684f334677554ebfb0ac2d0f41ba3467` ;
celui du recompilé vaut
`08e208f562e59c5faf74c4075ef90330728d548080497c3f635eeb9a72c03e00`.
Le lecteur confirme néanmoins l'identité octet pour octet des cinq fichiers
finaux, y compris leurs valeurs de frontière. Il relit aussi leurs valeurs
internes finies : 12 480 cellules pour p/T/U/rho et 25 936 faces intérieures
pour phi. Les reçus et tous les payloads sont hachés et vérifiés.

Le premier lecteur refusait ces champs parce qu'il ne comptait que le plus
grand label propriétaire : le dernier label existe seulement parmi les
voisins. Son refus est conservé. La version2 compte les deux ensembles,
contrôle les effectifs attendus, accepte un témoin scalaire connu et refuse
un vecteur tronqué. Elle ne change aucun champ ni critère.

## Portée et reproduction

Les sources officielles complètes, le binaire recompilé, les recettes,
manifestes, journaux, refus et les deux cas natifs sont conservés dans
l'archive référencée par `archive-receipt.json` et `file-manifest.json`.
Le runtime original est épinglé ; rejouer le binaire archivé reproduit le
contrôle sans installer le compilateur. La recette apt de compilation n'est
pas un verrouillage intégral de tous les paquets : l'identifiant de l'image,
les versions observées et le binaire obtenu sont conservés. Une nouvelle
compilation exige donc une nouvelle comparaison de parité.

La prochaine étape est une copie de source distincte pour observer les
résidus absolus avant/après résolution, après examen des effets de
`fvMatrix::residual()`. Les champs de ce futur binaire devront à leur tour
être comparés au solveur non modifié. Cette instrumentation n'est pas encore
réalisée ici. Aucun résidu matriciel absolu ni stabilité de perturbation
n'est qualifié. Le maillage réel reste rejeté ; aucun débit maximal, gain
de puissance ou jumeau numérique calibré n'est validé.

[Archive native et compilation](https://github.com/cluster2600/porscheparts/releases/tag/bionic-turbo-native-binary-2026-10-12) :
134 fichiers, 54 591 667 octets, SHA-256
`87d6f62fde69d4fcbad7bf1defb09e61009191f05e02be1d3f9c29e8687a7558`.
Tous les payloads sont relus localement. Les cinq actifs GitHub sont
vérifiés par tailles et SHA-256 distants, sans revendiquer un second
téléchargement intégral. Les volumes et conteneurs locaux sont conservés.
