# D1 préparé, aucun solveur lancé

Ce lot attend la libération explicite de Kali2 par la coordination. Le pilote
Ti conserve sa fenêtre ; aucun solveur, conteneur ou copie de maillage D1 n'a
été lancé. Les petits dictionnaires V2/900 ont été lus en lecture seule et
recoupés avec l'archive native privée : huit fichiers, 8027 octets. Les champs
et le maillage restent sur leur ressource d'origine.

## Comparaison figée avant calcul

Le [manifeste de la paire préparée](parameters/D1-prepared-pair-manifest.json)
lie les neuf fichiers du checkpoint 900, treize fichiers constants, les
configurations préparées et les sources. Les deux branches sont :

| Branche | GAMG relTol pression | Tolérance absolue | Relaxation p | Itérations |
| --- | ---: | ---: | ---: | --- |
| control | 0,01 | 10⁻⁸ | 0,15 | 901–960 |
| absolute | 0 | 10⁻⁸ | 0,15 | 901–960 |

Modèle, conditions physiques, CAD, maillage, autres tolérances et critères
originaux sont inchangés. Le futur exécuteur copie le même état 900, vérifie les
empreintes des copies, décompose une seule fois et copie la même partition
initiale MPI dans les deux branches avant le premier solveur. Les cas sont
séquentiels. Il ne relance aucun cas en échec.

Les checkpoints ont un intervalle 60 et les trois fonctions de débit/force un
intervalle 1. La fenêtre d'admission exige vingt mesures à 941–960. Le rapport
prospectif exige aussi toutes les soixante mesures pour ses trois fenêtres :
901–920, 921–940, 941–960. Les résidus p/U/turbulence, masse, stabilité débit/couple,
direction et champs complets finis restent exigés avec les seuils originaux.
Le compte attendu de cellules 453496 est lié au résumé des champs natifs 900.

Chaque fenêtre rapporte moyenne, écart type, min/max et CV si la moyenne est
non nulle : Qin/Qout, couple total, résidu initial et résidu final linéaire p,
continuité globale. La différence des moyennes finales entre branches et leurs
CV sont descriptifs. Ces variations d'itérations stationnaires ne sont pas un
bruit physique, des observations indépendantes, un intervalle de confiance ou
une fréquence rotor. Aucun seuil de significativité n'est ajusté après calcul.
Un diagnostic nouvellement admis ne restitue jamais les mesures historiques
fines manquantes et ne rétablit pas rétroactivement l'admission R0 fine.

## Exécution future bornée

Le lanceur est [launch_d1_pair.py](source/launch_d1_pair.py), avec
[exécuteur isolé](source/run_d1_in_container.py). Il utilise seulement l'image
Foundation 13 déjà disponible et figée, sans réseau ni téléchargement :
4 CPU, cpuset 0/2/4/5, 5 GiB RAM et mémoire+swap, tâches à nice 10. Il exige
6 GiB disponibles à l'admission et refuse un autre conteneur de cette image.
Le plafond global est 600 s, préparation/copies incluses ; la charge du
conteneur est plafonnée à 580 s, chaque MPI à 270 s, sans prolongation. Le
lanceur réserve du temps pour arrêter seulement son conteneur nommé en cas
de timeout, puis conserve les logs et receipts. Aucun service tiers n'est touché.
Estimation : 4–6 min ; plafond : 10 min. L'exécution native de ces nouveaux
helpers n'est pas encore vérifiée : cette vérification attend la fenêtre.

Après libération et transfert de la capsule locale de préparation, la commande
sur Kali2 sera de la forme suivante. Ce bloc documente la future exécution ;
il n'a pas été exécuté.

```sh
python D1_CAPSULE/source/launch_d1_pair.py NATIVE_V2_900_CASE D1_CAPSULE NEW_D1_OUTPUT --coordinated-release COORDINATOR_RELEASE_REFERENCE
```

Pour reproduire seulement la préparation locale, sans solveur ni maillage :

```sh
python source/prepare_d1_configurations.py NATIVE_SMALL_CONFIG SOURCE_IDENTITY_JSON NEW_CONFIG_OUTPUT
```

## Sous-systèmes visibles, dimensions en attente

Le [contrat qualitatif](parameters/qualitative-subsystem-contract.json) distingue
quatre sous-systèmes à documenter avant toute reconstruction fonctionnelle :
plénum installé, train poulies/courroie avant, support nervuré et enveloppe
centrale relevée. Les paramètres et interfaces sont tous inconnus (`null`).
La vidéo confirme seulement une implantation générale ; elle ne mesure aucun
diamètre, ratio, axe de fixation, matériau ou tolérance. R0 reste un rotor,
un carter et une transmission analytique ; son propre modèle ne fournit pas
les mesures manquantes des nouveaux sous-systèmes. Aucune nouvelle géométrie
dimensionnée ni preuve de montage n'est générée.

La [publication exacte fournie par le parent](https://www.instagram.com/patrickmotorsports/reel/DeC4x04yjNP/)
revendique un ensemble « 935 3.5L Flat Fan MoTeC EFI » et une boîte-pont 993 à 6 rapports ;
cela n'identifie pas la base moteur comme 993, ni l'équivalence du ventilateur.
Les images tierces restent privées. La recherche publique du moteur n'est
pas dupliquée ici.
