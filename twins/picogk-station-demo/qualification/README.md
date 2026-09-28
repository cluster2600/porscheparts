# Qualification de la station — 28 septembre 2026

L'image est **publiée et vérifiée anonymement** ; l'instance Vast **53246885**
est louée. Le préflight GPU, les témoins CPU, la réponse Qwen, l'appel d'outil
OpenClaw, le rendu OVRTX sur GPU 3 et l'édition/sauvegarde/reconnexion
Omniverse via le relais SSH passent. La vidéo est également reçue sur Kali2. Le premier essai simultané a échoué sur le seuil de mémoire
GPU ; l'API Qwen est de nouveau vérifiée après fixation explicite de sa limite
à 0,90 ; un nouvel appel d’outil OpenClaw passe également. Le deuxième essai
a été interrompu pour diagnostiquer l’absence de réponse dans le dashboard
utilisateur, qui a confirmé la reprise des réponses. Le [troisième essai de trente minutes](runtime/soak/README.md)
**passe**, de 21:25:42 à 21:55:42 UTC : 120 requêtes Qwen, 53 chaînes complètes,
aucun OOM ni redémarrage. Les 1 219 fichiers attendus sont identiques entre
Vast et la copie persistante de Kali2. Ces résultats ne prouvent aucune
qualification physique de pièce.

Le [statut du déploiement](deployment-status.json), la
[preuve de publication](publication.json) et les
[preuves d'exécution sur Vast](runtime/README.md) précisent chaque état observé.
Le manifeste publié est :

```text
ghcr.io/cluster2600/3dprinting993-picogk-m64@sha256:540d9d4af34a73f91114f2d3dd4f4ad847eee42037c26efaf1caadb5b155e871
```

La publication a réutilisé l'image construite, sans reconstruction, via GitHub
Actions et un runner JIT sur Kali2. Le run `36471929525` a réussi ; le runner
correspondant a été automatiquement retiré. Les refus antérieurs de publication
directe et le refus budgétaire antérieur à toute création restent conservés dans
le statut comme historique ; ils ne décrivent plus l'état actuel.

La location porte sur l'offre **49181720**, machine **44690**. Le manifeste
initial réservait **26,99 USD** et fixait une échéance au 29 septembre à
00:12:16 UTC. À **21:36:31 UTC**, l'utilisateur a explicitement demandé de
conserver Vast allumée après ajout de crédit : la [garde destructive a été retirée](runtime/keep-running.json),
le manifeste historique est conservé et aucune destruction n'a été appelée.
La station fonctionne désormais **sans échéance automatique**, au tarif observé
de **6,237037 USD/h**, soit environ **149,69 USD/jour hors transferts**.
La facture réelle reste inconnue. La [synchronisation permanente vers Kali2](runtime/sync-persistent.json)
est active, sans suppression ni suivi de liens ; sa dernière copie relevée
réussit à 21:42:55 UTC.

Le rendu OVRTX a nécessité un correctif explicite des permissions du cache
sur l'instance. La [couche finale persistante](runtime/image-hotfix-persistent/final-image.json)
le reprend avec les correctifs Qwen/client/relais et passe le témoin CPU en
4,157 s ; sa publication reste à effectuer. Le digest initial ci-dessus ne contient pas
encore ces correctifs. Les échecs UDP observés depuis Mac et Kali2 ne
permettent pas d'attribuer la cause au fournisseur, car les deux machines
peuvent partager le même accès Internet.

Kali1 est également disponible pour du [calcul PicoGK CPU borné](runtime/kali1-cpu/summary.json).
Le lancement depuis Kali2 et la collecte automatique sont prouvés avec
`kali1-picogk` : deux CPU, 2 Gio, priorité réduite et cinq minutes maximum,
sans installation système ni redémarrage du gateway. La liaison passe par le
tunnel du contrôleur Mac, qui doit rester disponible.

L'[image construite et les témoins CPU initiaux](build/README.md) sont documentés
à part, avec les sources C#, le document FreeCAD éditable, les STEP/STL,
l'assemblage USD et les journaux extraits de l'image.

Le [dernier reçu `make check`](runtime/make-check-delivery.json) consigne le code
**0** sur le contrôleur macOS : **3 230 tests principaux**, 148 ignorés et
**572 documents Markdown sans lien cassé**. Les cinq tests du correctif Git 2.53
ajouté pendant ce contrôle ont ensuite été relancés avec succès ; les nouvelles
preuves documentaires sont contrôlées séparément. La [preuve GitHub sur Kali2](runtime/github-access/proof.json)
confirme lecture native et `push --dry-run` sur les deux dépôts autorisés, sans
modification distante. L’historique ci-dessous conserve le premier contrôle
complet et ses conditions d’exécution.

## Historique du premier contrôle logiciel

`make check` s'est terminé avec le code **0** sur Kali2, dans une copie isolée de
3 898 fichiers du worktree, du 28 septembre 2026 à 18:49:46 UTC jusqu'à
18:57:39 UTC (472,58 s). Aucun fichier de cette copie n'a changé pendant le
contrôle. Les nouveaux fichiers ont été ajoutés à l'index de cette copie avant
l'exécution afin d'inclure leurs liens documentaires.

| Contrôle | Résultat constaté |
|---|---|
| Suite principale | 3 213 tests ; 140 ignorés explicitement ; aucune erreur |
| Ensemble des 32 suites invoquées par `make check` | 3 490 invocations, avec répétitions ; 141 ignorées |
| Liens Markdown de la copie contrôlée | 567 documents ; aucun lien cassé |
| Contrôle natif LPBF F37 | Image `mesh-cfd` épinglée par le Makefile ; exécution sans réseau |

Les copies des résultats sont [summary.json](summary.json) et
[result.json](result.json). Le journal intégral est conservé localement sous
`work/station-linux-check-r8kj70sz/make-check.log`, hors Git. Son SHA-256 est :

```text
5db7a308778d76816b8a6787acb2dd0f263f0645c3ac634b3e0538977dfa4d51
```

L'exécution utilise Python 3.14.7, un environnement virtuel dédié avec les
paquets système, `PYTHONNOUSERSITE=1`, `umask 022` et un `TMPDIR` dédié. Aucun
paquet global n'a été installé. Ces paramètres évitent les bindings OCP
incomplets du site utilisateur et le `/tmp` plein de l'hôte. Les essais
préliminaires avaient aussi révélé des fixtures sensibles à l'umask ; la suite
GHCR ciblée (17 tests) puis le contrôle complet passent sous `022`.

Les tests ignorés concernent principalement les runtimes facultatifs
OCP/CadQuery, OpenUSD et Trimesh, ainsi que des preuves locales volontairement
absentes de Git. Leur absence ne vaut pas validation de ces fonctionnalités.

Après l'ajout de `soak.py` et `qualify_image.py`, les **29 tests ciblés station**
passent sans test ignoré. Les quatre nouveaux tests du registre utilisent des
réponses simulées : manifeste et configuration conformes, sommes de couches,
rejet des empreintes divergentes, ports supplémentaires et tailles invalides.
`soak.py --self-check` passe également ; il vérifie ses parseurs sans exécuter
la qualification de 30 minutes. Ces ajouts sont postérieurs à la copie Linux
ci-dessus et ne sont donc pas couverts par son résultat `make check`.

Les preuves de publication, préflight GPU, témoins CPU, réponse Qwen, outil
OpenClaw, rendu OVRTX, manipulation/sauvegarde USD et reconnexion WebRTC
sur Vast et le rapport des trente minutes simultanées sont désormais liés
ci-dessus. La facture réelle et le bilan final des transferts restent inconnus ;
la garde destructive a été retirée à la demande de l’utilisateur. La simulation
thermomécanique calibrée et la qualification physique restent hors du périmètre
de cette première installation.
