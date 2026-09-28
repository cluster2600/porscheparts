# Validation logicielle préliminaire — 28 septembre 2026

Les contrôles logiciels décrits ici passent. **La qualification GPU et Vast reste
à effectuer** : ce dossier ne prouve ni une station opérationnelle, ni la
fabricabilité ou la qualification physique d'une pièce.

Le [statut du déploiement](deployment-status.json) consigne l'échec constaté :
l'image finale est construite sur Kali2, mais les deux essais de publication
GHCR ont été refusés au stade `PUSH`. Le lecteur OpenBao GHCR a été utilisé pour
une écriture alors que sa portée observée ne la permet pas. La voie historique
de publication utilise GitHub Actions, qui fournit au job son `GITHUB_TOKEN`
éphémère avec la permission `packages: write`.

La publication de l'image existante, sans reconstruction, est en préparation
avec un workflow distinct et un runner éphémère sur Kali2, pilotés par le wrapper
GitHub OpenBao déjà approuvé. Cette voie ne suppose pas un nouveau jeton GHCR ;
son enregistrement, son exécution et le digest publié restent à vérifier.
L'inventaire Vast est vide, aucune location ni dépense de qualification n'a
été engagée. Le digest de configuration local ne doit pas être présenté comme
un digest de manifeste publié. La vérification anonyme du registre reste
obligatoire avant toute location.

L'[image construite et les témoins CPU](build/README.md) sont documentés à part,
avec les sources C#, le document FreeCAD éditable, les STEP/STL, l'assemblage USD
et les journaux d'exécution extraits de l'image.

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

À joindre après la qualification réelle : digest de l'image et accès anonyme
observé, ressources attribuées et préflight Vulkan/NVENC, témoin PicoGK natif,
réponse Qwen et outil OpenClaw depuis Kali2, manipulation et sauvegarde USD puis
reconnexion WebRTC, rapport des 30 minutes simultanées, compteurs de transfert
et reçus de la garde de coût. La simulation thermomécanique calibrée et la
qualification physique restent hors du périmètre de cette première installation.
