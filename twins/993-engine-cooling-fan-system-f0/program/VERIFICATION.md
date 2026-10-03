# Vérification de la publication

[Programme](../README.md) · [Reçu de vérification](../results/program-20261003/verification.json)

`make check` termine avec **code 0** sur la branche isolée, Python 3.12.11,
NumPy 2.2.6 et Matplotlib 3.10.8 comme les versions de dépendances CI.
La suite principale exécute **3 367 tests**, avec **193 sauts optionnels** ;
les contrôles complémentaires du Makefile passent également, dont l'audit LPBF
Docker historique et le contrôle du programme ventilateur.

Le premier essai confiné avait des erreurs de permissions Git temporaire et de
sockets loopback. Le deuxième a détecté une assertion existante sur le début de
la cible `check` : le contrôle ventilateur a été déplacé à la fin de ses
prérequis, sans changer l'assertion historique. Le troisième termine normalement.
Les journaux complets restent locaux et privés ; leur hash est enregistré.

Les quatre tests synthétiques du scan et de sa préparation réversible passent
séparément sans saut, après le complément de préparation. Les intégrales et
résidus natifs des deux CFD ont été recalculés ; ils confirment les critères
rejetés. La composition OpenUSD a été générée deux fois avec rapports et hashes
identiques, sans utiliser le scan. Les liens relatifs/ancres et `git diff --check`
passent. Les archives publiées n'incluent pas de scan, maillage du scan,
justificatif d'achat ni identifiant privé d'hôte ; leurs métadonnées d'utilisateur
ont été retirées.

La CI GitHub doit encore être vérifiée sur la PR brouillon. Aucun résultat
logiciel ci-dessus ne ferme les barrières physiques du plan de validation.
