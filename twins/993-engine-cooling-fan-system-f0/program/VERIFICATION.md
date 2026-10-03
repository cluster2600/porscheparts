# Vérification de la publication

[Programme](../README.md) · [Reçu de vérification](../results/program-20261003/verification.json) · [CI de la PR](https://github.com/cluster2600/porscheparts/pull/118/checks)

`make check` termine avec **code 0** après l’intégration complète des recherches,
avec Python 3.12.11, NumPy 2.2.6 et Matplotlib 3.10.8. La suite principale
exécute **3 375 tests**, avec **193 sauts optionnels**. Tous les contrôles
complémentaires du Makefile passent, dont l’audit LPBF Docker historique et le
contrôle des références, hashes et barrières de validation du programme.
Les journaux complets restent privés ; le SHA-256 du dernier journal est dans
le reçu. Les tests utilisant Git temporaire, loopback ou Docker ont été exécutés
avec les permissions locales nécessaires.

Les **cinq tests scan/préparation/contours** et les **six tests recherche** passent
séparément sans saut. Les vingt textes originaux de recherche sont contrôlés
par SHA-256 ; leurs références et l’index de 140 fiches sources / 130 groupes
d’URL sont vérifiés. Une exception Git limitée à la ligne finale d’un CSV
préserve ses octets originaux. Les contrôles stricts de liens/ancres passent
sur **687 fichiers Markdown**, ainsi que `git diff --check`.

Les intégrales et résidus natifs des deux CFD ont été recalculés et confirment
les critères rejetés. La composition OpenUSD a été générée deux fois avec
rapports et hashes identiques, sans utiliser le scan. Les fichiers récupérés
du transfert CFD interrompu ont été confrontés au manifeste distant : les
32 partitions finales du contrôle sont présentes, pas les champs complets du
candidat. Le détail est dans l’[état d’exécution](EXECUTION_20261003.md).

Les archives publiques n’incluent ni scan, dérivé du scan, justificatif d’achat,
identifiant privé d’hôte ni données de facturation. Les métadonnées d’utilisateur
des archives solveur publiées ont été retirées. Les originaux et dérivés privés
ainsi que les rapports de récupération sont conservés sur le Mac.

Les CI des commits [0ddd2238](https://github.com/cluster2600/porscheparts/actions/runs/37110927353)
et [ebd13b93](https://github.com/cluster2600/porscheparts/actions/runs/37111701807)
sont vertes. Les [checks de la PR brouillon 118](https://github.com/cluster2600/porscheparts/pull/118/checks)
affichent le commit contrôlé pour chaque nouveau complément. Un contrôle logiciel
réussi ne ferme aucune barrière physique du plan de validation.
