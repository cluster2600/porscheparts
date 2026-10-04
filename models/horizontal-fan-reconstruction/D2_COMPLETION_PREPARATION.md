# D2 : préparer les vingt itérations manquantes

**Préparation vérifiée, aucun solveur lancé, aucune ressource réservée.** Le lot
[D2 initial](D2_EXECUTION.md) reste clos et ses résultats restent inchangés.
Le témoin a terminé 961–1020 ; seule la branche prolongée est concernée par
cette proposition. L'objectif est de terminer la comparaison tronquée par son
budget à **1020**, sans prolongation automatique pour obtenir une admission.

## État natif réellement disponible

L'[audit privé des checkpoints](results/runtime/D2-restart-checkpoint-audit.json),
effectué le 4 octobre 2026 à 20:46:51 UTC sans solveur ni reconstruction,
vérifie **980 et 1000 complets sur les quatre partitions**. Chaque partition
contient `p`, `U`, `k`, `omega`, `nut`, `phi`, `Uf` et `uniform/time`. Les champs
volumiques couvrent 680 596 cellules, avec 122 709 / 167 115 / 208 232 / 182 540
cellules par rang. Les cardinalités des champs de faces sont contrôlées contre
le maillage natif ; les valeurs sont finies. Les quatre index et temps sauvés
à 1000 concordent, `deltaT = deltaT0 = 1`.

Le checkpoint choisi est **1000**, le dernier complet : 32 fichiers natifs,
152 261 842 octets. La racine sérielle contient seulement 960 ; il n'existe
aucun checkpoint 1001 ou 1020. Le début incomplet d'itération1001 dans l'ancien
log ne constitue pas un état reprenable. La reprise parallèle utilisera les
champs1000 existants, jamais un état reconstruit à partir des intégrales.

Le [préparateur](source/prepare_d2_restart1000.py) a effectivement créé une
copie privée séparée du maillage, des configs et des quatre partitions1000.
La [preuve de préparation](results/runtime/D2-restart-preparation-receipt.json)
contrôle les SHA et tailles avant et après copie. Le code final portable a
préparé cette copie en **0,580 s** ; une copie provisoire antérieure a également
été conservée. Aucun solveur, `reconstructPar`, `decomposePar` ou conteneur n'a
été exécuté pour cette préparation. Les fichiers natifs du lot clos sont
préservés. Le marqueur `1000/uniform/time` à la racine de la copie sert uniquement
au helper de résumé ; il n'est pas présenté comme des champs sériels complets.

## Reprise fixe proposée

Le [protocole de complétion](parameters/D2-restart1000-protocol.json) impose
**une branche, quatre rangs, exactement 1001–1020**, un seul appel au solveur.
Le témoin complet est réutilisé en lecture seule. Pas de nouveau maillage,
de partitionnement, de géométrie, de zone MRF, de régime, de condition limite,
de schéma ou de seuil. La sortie reste prolongée de 275 mm en cinquante couches,
avec le même cœur de 453 496 cellules et les mêmes sélections communes.

Le [controlDict préparé](parameters/D2-restart1000-controlDict) est identique
octet pour octet au contrôle natif effectivement exécuté, sauf `startFrom
startTime` et `startTime 1000`. `endTime 1020`, `deltaT 1`, sauvegarde tous les
20 pas, `purgeWrite 0` et mesures à chaque itération sont conservés. Le contrôle
statique reconstruit ces deux substitutions et retrouve le SHA du fichier
natif original. L'efficacité de la reprise reste à vérifier lors d'une future
exécution : premier pas1001, vingt pas complets consécutifs, terminaison `End`,
tables natives finies et checkpoint1020 complet sont obligatoires.

Préparation reproductible, avec les chemins privés fournis explicitement :

```sh
python3 source/prepare_d2_restart1000.py \
  "$D2_NATIVE_EXTENDED" "$D2_NATIVE_CHECKPOINT_AUDIT" \
  parameters/D2-restart1000-protocol.json \
  parameters/D2-restart1000-controlDict "$D2_PRIVATE_PREPARED_CASE"
```

Cette commande copie et vérifie les fichiers ; elle ne lance aucun calcul.
Les seules commandes numériques prévues, **à superviser dans le runtime
existant isolé après coordination explicite**, sont :

```sh
mpirun --bind-to none --use-hwthread-cpus -np 4 foamRun -parallel
reconstructPar -time 1000,1020
```

Ces deux commandes ne constituent pas un lanceur autonome autorisé. Le lanceur
historique `launch_d2.py` prépare et rejoue une paire ; il ne convient donc pas
à cette reprise unique. Avant une exécution, le superviseur de ce lot doit
appliquer le plafond global ci-dessous, conserver les preuves et arrêter
uniquement son propre processus/conteneur. Il doit utiliser une **nouvelle
date limite**, jamais la date limite expirée du lot720 s. Aucune installation,
image téléchargée, location ou modification de service n'est nécessaire.

## Coût observé et budget proposé

Le log natif de la branche prolongée donne `ExecutionTime = 81,138094 s` à
980 puis `155,099948 s` à 1000 : **73,961854 s pour vingt itérations**,
soit environ 3,70 s/itération. Les `ClockTime` arrondis donnent **75 s**.
Cette mesure inclut la sauvegarde1000. Le maximum d'incrément de cette fenêtre
est 4,869 s. Le déséquilibre des partitions est conservé ; aucune estimation
linéaire basée seulement sur le nombre de cellules ne remplace cette mesure.

| Étape future | Estimation / preuve | Plafond proposé |
|---|---|---:|
| Admission fraîche, identité et copie isolée | Copie finale mesurée 0,580 s ; audit complet précédent 10,174 s | 30 s |
| Vingt itérations1001–1020 | 75–80 s estimés avec redémarrage, dernier20 mesuré75 s | 110 s |
| Reconstruction1000 et1020 | Témoin : trois checkpoints reconstruits en11,480 s ; estimation prolongée15–25 s | 25 s |
| Résumé, fenêtres, champs et comparaison | Estimation, aucune mesure de ce futur lot | 30 s |
| Archivage, vérification et libération | Archivage/vérification final précédent6,389 s ; réserve accrue pour ce lot | 45 s |
| **Ensemble, sans remise à zéro** | **120–180 s nominaux estimés** | **240 s** |

Ce budget est **proposé, non démarré** : 4 CPU maximum, RAM+swap5 GiB, réseau
absent, niceness10, même image Foundation13 déjà disponible. Charge, RAM et
coordination doivent être vérifiées immédiatement avant lancement. Aucune
réservation implicite n'est maintenue pendant cette préparation. Le budget ne
garantit ni la convergence, ni le temps d'archivage ; un dépassement conserve
l'état partiel et termine le lot sans nouvel essai.

## Analyse et règle d'arrêt

Les [critères originaux](parameters/D2-executed-configurations/protocol.json)
sont recopiés sans modification dans le protocole proposé. La fenêtre finale
doit contenir vingt mesures consécutives1001–1020. Elle est comparée à la
fenêtre native981–1000 ; RMS du cœur, p99/max locaux et reflux sont évalués
sur les véritables checkpoints1000 et1020. Pression commune : dispersion
≤2 Pa, différence entre moyennes des deux fenêtres ≤2 Pa et RMS pression du
cœur ≤1 Pa. Maximum du résidu initial p ≤10⁻⁴ ; les autres seuils numériques,
de vitesse et de stabilité restent également obligatoires.

Le précédent échec de stationnarité de pression reste documenté. **Même avec
vingt itérations supplémentaires complètes, une pression non stationnaire
rejette l'admission.** La comparaison physique des domaines reste inconclusive
si l'un des prérequis numériques ou de stationnarité échoue. Le lot s'arrête
à1020 dans tous les cas ; aucun seuil n'est assoupli, aucune continuation1040
n'est prévue. Une éventuelle admission ne qualifierait ni les champs locaux,
ni une indépendance générale du domaine, ni le refroidissement installé.

Conserver séparément l'ancien log natif40 pas complets plus début1001, le
nouveau log20 pas et leurs tables. Une vue d'analyse composée, si nécessaire,
doit être identifiée comme dérivée : retirer seulement le bloc1001 incomplet
de l'ancienne vue, contrôler l'égalité des mesures au checkpoint1000 avant
déduplication et conserver les SHA des deux sources. Ne jamais présenter cette
vue comme un log natif unique. Les futurs champs et maillages restent privés ;
seuls scripts originaux, paramètres et rapports expurgés sont publiables.

Vérification sans solveur : `make fan-program-check`. Cinq nouveaux tests
refusent notamment champ surfacique absent, pression non finie, temps mélangés,
pas supplémentaires et rejeu du témoin. Les résultats D2 initiaux, leur capsule,
leurs archives et les validations antérieures restent inchangés.
