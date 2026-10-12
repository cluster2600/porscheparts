# Observer les résidus natifs sans modifier le solveur — 054/055

Cette phase utilise le paramètre natif `log 2` du solveur de pression GAMG.
Aucune instrumentation C++, équation, tolérance, condition aux limites ou
pièce du turbo n'est modifiée. Le contrôle court 054 conserve exactement
les cinq champs finaux de 052 ; 055 conserve exactement ceux de 044 sur les 200 pas. Les historiques
d’extrema et les 800 résumés de pression sont également identiques.

## Provenance et protocole

Les cinq fichiers sources examinés sont extraits de l'archive officielle
v2406 déjà conservée dans la release native-binary. Leurs SHA-256 sont
vérifiés contre les membres exacts de l'archive dans `source-references.json`.
La casse du dossier natif est `solvers`, pas `Solvers` : les chemins hôtes
macOS ne servent pas à établir l'identité des membres de l'archive.

`lduMatrixSolver.C` lit le paramètre `log`. `GAMGSolverSolve.C` imprime
le facteur de normalisation avant chaque résolution et les résidus à chaque
cycle. Le résidu normalisé est la somme des valeurs absolues du résidu
algébrique sur la grille fine divisée par ce facteur. Les produits publiés
reconstituent donc cette somme L1 à la précision du journal, pas un maximum
par cellule ou une mesure indépendante d'erreur physique. Les nombres sont
publiés comme valeurs algébriques ; aucune unité de débit n'est revendiquée.

054 reprend les entrées exactes de 052 sur deux pas, à 0,2 µs. 055 reprend
celles de 044 sur 200 pas, à 20 µs. Pour chaque paire, seule l'insertion de
`log 2;` dans `system/fvSolution` pour p est autorisée ; pFinal en hérite.
Les deux utilisent le binaire original et l'image runtime immuable. Ils
sont bornés à un CPU, 2 Gio et respectivement 180 et 900 secondes, sans réseau.
Les anciens cas ne sont pas relancés. Aucun seuil n'est changé.

## Lecture et limites

Le lecteur distingue les résumés GAMG de grille fine des résolutions du
niveau grossier. Il exige une séquence complète de cycles, un facteur par
résolution, les bons pas et les mêmes résumés finaux que le témoin original.
Un exemple vérifie le produit attendu et l'exclusion des lignes grossières ;
un cycle manquant est refusé. Les champs natifs sont relus, avec les labels
owner ET neighbour pour compter les cellules ; tous les payloads et reçus
sont vérifiés avant comparaison.

Le diagnostic `solverInfo` n'est pas activé : son stockage initialisé après
la première itération et son résidu INITIAL sont distincts de ces résumés
finaux. Aucun résidu initial n'est présenté comme un résidu final.

Les témoins restent synthétiques, avec les coupes fixes de 044. Ils ne
qualifient ni le maillage réel ni la stabilité de perturbations. Aucun débit
maximal, gain de puissance ou jumeau numérique calibré n'est validé.

## Résultats achevés

054 termine en 6,545 s et 055 en 473,630 s, codes natifs zéro, sans OOM.
Les champs p/T/U/rho ont 12 480 cellules ; phi contient 25 936 faces internes.
Tous les fichiers finaux, y compris leurs frontières, sont identiques à
leurs témoins respectifs. Le binaire original est relu par SHA-256 dans
les deux nouveaux cas. Le lanceur de 044 possède un autre emballage de
commande : aucune identité intégrale des commandes 044/055 n'est annoncée.
L'image, les ressources CPU/mémoire et les entrées physiques sont identiques.

| Instant | Vitesse maximale, m/s | Maximum des résidus finaux normalisés | Maximum des produits L1 finaux | Maximum du facteur |
|---|---:|---:|---:|---:|
| 0,1 µs | 2,953e-12 | 0,3393 | 9,641e-18 | 4,478e-17 |
| 10,6 µs, premier dépassement de vitesse | 1,058e-8 | 8,584e-4 | 7,698e-18 | 9,481e-15 |
| 20 µs | 4,503e-5 | 8,812e-5 | 3,907e-15 | 4,719e-11 |

Chaque ligne prend les maxima des quatre résolutions du pas ; les colonnes
ne correspondent pas nécessairement à la même résolution. Les 800 tuples
facteur/résidu/produit sont conservés dans `native-full-readback.json`, et
les 200 pas dans `pressure-history.csv`. Les 647 plafonds de 1 000 itérations
sont les mêmes que dans 044. Les trois seuils de repos restent dépassés :
erreur p 0,0028541403 Pa, erreur T 1,9837315e-6 K, Umax 4,5028331e-5 m/s.

Le facteur varie de 2,841e-17 à 4,719e-11 et le produit L1 final de
7,438e-18 à 3,907e-15. Une diminution du résidu normalisé ne suffit donc
pas à établir une amélioration du résidu algébrique absolu. Ces observations
ne prouvent ni une erreur d'arrondi comme cause unique, ni une résolution
suffisante de chaque équation, ni la stabilité des perturbations. Le rejet
044 est reproduit, pas corrigé. Aucun seuil ni limite d'itérations n'est
assoupli à partir de ces valeurs.

La suite doit distinguer la stabilité de l'opérateur tournant avec les
coupes synthétiques de l'admission du vrai maillage. Ces diagnostics
existants rendent inutile une instrumentation C++ pour cette seule mesure.
Une mesure locale du résidu ou une attribution causale demanderait un
contrôle distinct, avec vérification de neutralité.

[Archive native 054/055](https://github.com/cluster2600/porscheparts/releases/tag/bionic-turbo-native-residual-log-2026-10-12) : 95 fichiers, 21 549 595 octets, SHA-256
`0664545d2df97cc8800f621ca1b06469a94d72a3f1d84e3b635e3760db823531`.
Tous les payloads sont relus localement ; les cinq actifs distants sont
contrôlés par tailles et digests GitHub, sans second téléchargement intégral.
