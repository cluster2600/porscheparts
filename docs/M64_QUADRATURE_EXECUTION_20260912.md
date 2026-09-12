# M64 — deux coupons LPBF exécutés et contre-vérifiés

**Résultat :** la variation de quadrature ne supprime pas le plafond numérique
de 3 300 K. Deux calculs thermiques natifs ont terminé sur Kali en **67,140 s**,
nettoyage compris. Aucun nouveau coût Vast. Ce coupon n'est ni la culasse
entière ni une simulation de fonctionnement moteur.

[Reçu public chiffré et empreintes](../twins/m64-cylinder-head/evidence/quadrature-native-and-mesh-bridge-20260912.json).
Les [préparatifs](M64_JOBS_234_20260912.md) restent un historique distinct.

## Expérience effectivement réalisée

Même maillage de 57 600 cellules, AlSi10Mg témoin, laser de 380 W,
pas fixe de 25 ns, fenêtre de 40 µs, soit 1 600 pas par cas. Seule différence
entre les entrées : quadrature `nPoints=(10,10,10)` puis `(20,20,20)`.
Énergie incidente commune : 0,0152 J. Ni limiteur, ni matériau, ni pression,
ni vitesse, ni maillage n'ont été ajustés pour obtenir un succès.

| Grandeur intégrée ou observée | q10 | q20 |
|---|---:|---:|
| Énergie laser absorbée | 8,923918 mJ | 8,929018 mJ |
| Énergie sensible stockée | 9,526165 mJ | 9,601713 mJ |
| Énergie latente stockée | 1,045571 mJ | 1,059072 mJ |
| Diffusion entrante aux frontières | 2,523533 mJ | 2,523533 mJ |
| Énergie retirée par le limiteur | 0,875733 mJ | 0,791783 mJ |
| Limiteur / énergie absorbée | 9,8133 % | 8,8675 % |
| Première atteinte du seuil de censure à 3 299 K | 10,500 µs | 10,625 µs |
| Température maximale, limitée | ≈3 300 K | ≈3 300 K |

Écart relatif à q20 : **0,0571155 %** sur l'énergie laser absorbée, mais
**10,6026 %** sur le puits artificiel du limiteur. La différence maximale des
températures appariées est 33,9288 K ; elle porte sur des séries censurées.
Deux niveaux ne suffisent pas à établir un ordre de convergence. La faible
variation de l'énergie totale ne prouve pas la convergence locale du flux.

Le bilan vérifié est
`sensible + latent - diffusion entrante - laser + advection sortante + limiteur`.
L'advection est nulle dans cette expérience thermique seule. Les résidus
intégrés sont respectivement 1,6753×10⁻⁸ J et 1,5973×10⁻⁸ J.
Un petit résidu comptable ne prouve pas la validité du modèle physique.

Le [lecteur 40 µs](../twins/m64-cylinder-head/source/compare_f58_quadrature_40us.py)
reparse les six termes en Decimal à 80 chiffres. Une relecture indépendante
a recalculé les intégrales depuis les deux logs et contrôlé leurs SHA.
C'est un contre-calcul du bilan, **pas un second solveur physique**.
Le lecteur conserve son statut « sorties natives non vérifiées » : il
n'exécute rien lui-même. Les preuves de sorties natives sont dans le reçu
distinct, relié aux mêmes empreintes de journaux.

## Exécution reproductible et limites

Sources versionnées : [superviseur](../twins/m64-cylinder-head/source/f58-quadrature/run_quadrature.py),
[worker](../twins/m64-cylinder-head/source/f58-quadrature/quadrature_worker.py).
Le paquet privé contient ces deux scripts, `manifest.json`,
`preparation-report.json`, `q10/` et `q20/`. Il doit être neuf sous
`/var/tmp/m64-f58-quad.<suffixe>`. Le manifeste épingle scripts, six fichiers
backend, 91 sources régulières et 67 alias `lnInclude` strictement internes.
Les dictionnaires privés proviennent du préparateur déjà versionné.

```sh
python3 /var/tmp/m64-f58-quad.SUFFIX/run_quadrature.py \
  --packet /var/tmp/m64-f58-quad.SUFFIX \
  --manifest-sha256 SHA256_DU_MANIFESTE_REEL --execute
```

Deux CPU, 4 Gio de mémoire, aucun swap, réseau coupé, utilisateur non root,
racine en lecture seule, capacités supprimées. Maximum 600 s dont 30 s de
nettoyage ; 250 s par cas. `checkMesh` et les deux solveurs terminent avec
code zéro ; OOM faux ; 1 600 bilans ordonnés par cas ; toutes les entrées
restent identiques ; conteneur exact vérifié absent après suppression.

Les sorties natives étaient dans un tmpfs de 1 Gio, compris dans les 4 Gio.
**Les champs temporaires ont été supprimés avec le conteneur** ; seuls leurs
SHA, les logs bruts et reçus ont été conservés. Les champs nécessiteraient une
nouvelle exécution pour être consultés. Les écrivains de résultats sont bornés
à 260 Mio au total ; le dossier hôte n'est pas protégé par un quota disque
noyau. Aucun réessai automatique.

Un premier prévol a été refusé sans création de conteneur : six fichiers
`Make/files` et `Make/options` de sous-bibliothèques manquaient à l'inventaire.
Aucune source n'avait changé. Leur inventaire a été complété avant une
nouvelle tentative explicite dans un autre dossier ; l'échec est conservé.

Vérification logicielle : 33 tests ciblés quadrature passent, dont neuf du
nouveau superviseur. `make check` complet termine avec code zéro ; les tests
natifs optionnels dont les runtimes sont absents restent signalés ignorés.
Ce contrôle du dépôt ne remplace pas les preuves natives exposées ci-dessus.

## Géométrie : progression indépendante du coupon

Un prototype privé a classé 716 383 tétraèdres parmi 784 675 cellules.
Parmi les sommets incidents aux défauts `lowD`, 47 sont potentiellement
mobiles sous les contraintes retenues, dans 129 tétraèdres concernés.
La première région de 1 000 tétraèdres contient 305 points, dont 251 fixes,
54 libres et trois libres incidents à des défauts ciblés. Elle a été refusée
pour 18 arêtes orientées de coque non conformes. Ces 18 occurrences ne sont
pas nécessairement 18 arêtes géométriques distinctes.

Cinq tests synthétiques du pont passent ; aucune importation native MFEM,
écriture inverse polyMesh, optimisation de points ou qualification de la
culasse n'en découle. Le maître et son contour sont inchangés.

Une tentative complémentaire de fermeture par tétraèdres adjacents a retrouvé
trois étoiles d'arêtes disjointes, avec cellules non tétraèdriques à l'interface.
Aucun chemin composé seulement de tétraèdres n'a relié ces composantes.
La région reste à 1 000 cellules, sans ajout ni déplacement ; aucun export
MFEM réel admis. Il faut revoir la sélection locale ou un adaptateur mixte,
pas louer un GPU pour cette région refusée.

## Suite et LLM

La suite LPBF doit séparer l'erreur de distribution spatiale de source,
les conditions thermiques imposées et la validité du domaine matériau à
haute température. Ne pas simplement relever le plafond. Un coupon limité
ne constitue pas un jeu de vérité pour entraîner PhysicsNeMo.

L'[étude Neural Concept](M64_NEURAL_CONCEPT_20260912.md) retient apprentissage
actif, interfaces fixes et recalcul des finalistes ; aucun entraînement lancé.

L'image existante `ghcr.io/cluster2600/qwen38-flash-next-vast` au digest
`6b3b1790dd3140c27a5b5f85181dccef06c8d96c02f3003bb3c9b267b8758e34`
est accessible ; son manifeste `linux/amd64` a été revérifié. Le modèle
`orcarouter/Qwen3.8-Flash-Next-Uncensored-NVFP4` reste gated (`auto`) lors du
contrôle public, révision `c1209bda15a6bbc4c68b585e93d40c0d85f50306`.
Les lanceurs installés examinés sur Mac/Kali n'ont pas établi de chemin
OpenBao approuvé pour cet accès Hugging Face. Aucun secret récupéré, aucune
image reconstruite et aucune machine LLM louée. Le budget utilisateur reste
38 USD ; une image publiée n'est pas un endpoint prêt à servir.

**Fabrication et démarrage moteur non autorisés.** Matériau/procédé à qualifier,
interfaces M64, domaine complet et corrélation physique restent nécessaires.
