# Vérification de la publication

[Programme](../README.md) · [Reçu de vérification](../results/program-20261003/verification.json)

`make check` termine avec **code 0** sur la branche isolée, Python 3.12.11,
NumPy 2.2.6 et Matplotlib 3.10.8 comme les versions de dépendances CI.
La suite principale exécute **3 369 tests**, avec **193 sauts optionnels** ;
les contrôles complémentaires du Makefile passent également, dont l'audit LPBF
Docker historique et le contrôle du programme ventilateur.

Le premier essai confiné avait des erreurs de permissions Git temporaire et de
sockets loopback. Le deuxième a détecté une assertion existante sur le début de
la cible `check` : le contrôle ventilateur a été déplacé à la fin de ses
prérequis, sans changer l'assertion historique. Le troisième termine normalement ; le quatrième reprend tous les contrôles après ajout de l’inspection des contours.
Les journaux complets restent locaux et privés ; leur hash est enregistré.

Les cinq tests synthétiques du scan, des contours et de sa préparation réversible passent
séparément sans saut, après le complément de préparation. Les intégrales et
résidus natifs des deux CFD ont été recalculés ; ils confirment les critères
rejetés. La composition OpenUSD a été générée deux fois avec rapports et hashes
identiques, sans utiliser le scan. Les liens relatifs/ancres et `git diff --check`
passent. Les archives publiées n'incluent pas de scan, maillage du scan,
justificatif d'achat ni identifiant privé d'hôte ; leurs métadonnées d'utilisateur
ont été retirées.

La [première CI GitHub](https://github.com/cluster2600/porscheparts/actions/runs/37110927353)
est verte sur le commit `0ddd2238` de la [PR brouillon 118](https://github.com/cluster2600/porscheparts/pull/118).
Le complément d'inspection des contours suit dans cette même PR ; son contrôle
GitHub est vérifié séparément après publication. Aucun résultat
logiciel ci-dessus ne ferme les barrières physiques du plan de validation.
