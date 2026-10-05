# D3 : superviseur exact préparé et testé, sans exécution native

[Accueil de l'étude](README.md) · [Diagnostic et protocole initial D3](D3_ESTABLISHMENT_DIAGNOSTIC.md) · [Dernier résultat natif D2](D2_COMPLETION_EXECUTION.md)

Le superviseur est préparé pour deux redémarrages séquentiels du même checkpoint
natif 1020 : `control015` avec relaxation de pression 0,15, puis `candidate005`
avec 0,05. Chaque branche comporte exactement vingt itérations SIMPLE,
1021–1040, sur les quatre partitions originales du maillage de 680 596 cellules.
Les itérations SIMPLE ne représentent pas vingt pas de temps physiques.
Le maillage, les conditions, les autres paramètres et les critères initiaux
restent identiques. L'état actuel est **préparé et testé hors solveur** : aucun
solveur, conteneur ou résultat natif 1040 n'a été créé pour cette préparation.
Aucune ressource n'est réservée par ce travail.

## Capsule exécutable et contrôles indépendants

La [capsule figée](parameters/D3-supervisor-reviewed-capsule/capsule-manifest.json)
contient treize sources originales ou déjà vérifiées, les configurations et les
empreintes des entrées privées. Les champs natifs restent privés. Son SHA256,
qui doit être fourni au lanceur depuis une référence revue indépendante, est :

```text
e72db463f7f2feaec1ba7d53cfc2472b493e0ca9b89fe1ff01289246d094213f
```

Le [contrôle réel des copies](results/runtime/D3-supervisor-input-copy-audit.json)
a vérifié les 179 fichiers d'entrée préparés, les 64 copies des fichiers MPI
1020 et les deux ensembles de huit fichiers série 1020. Les seuls écarts entre
les répertoires de travail des deux branches concernent `system/fvSolution`.
Les protocoles dérivés conservent les critères initiaux et exigent vingt mesures
natives consécutives 1021–1040. Ce contrôle bloque toute création de processus ;
il ne constitue pas une exécution OpenFOAM.

Les [19 tests du superviseur](results/runtime/D3-supervisor-offline-tests.json)
vérifient notamment le refus d'un support ou solveur déjà actif, les limites
réelles du conteneur avant l'ouverture du gate, l'absence de relance après une
branche partielle, l'archivage des preuves et le nettoyage du seul conteneur
possédé. Les fixtures de champs sont synthétiques, les appels Docker et solveur
sont simulés. Le test réel de timeout porte sur un petit processus Python
possédé. Les imports et aides CLI de la capsule sont aussi exécutés réellement.
Ces tests qualifient les contrôles logiciels, pas leur fonctionnement avec un
nouveau solveur natif ni la physique du ventilateur.

## Budget et admission au lancement

Un seul délai global de **360 s** couvre les deux branches, la préparation,
les reconstructions, l'analyse, la préservation et la libération. Chaque phase
reste bornée par sa part et par la réserve nécessaire aux phases suivantes :

| Phase | Maximum, s |
|---|---:|
| Préparation et admission | 30 |
| Solveur témoin 0,15 | 90 |
| Solveur candidat 0,05 | 90 |
| Deux reconstructions, budget partagé | 40 |
| Analyse | 45 |
| Préservation et vérification d'archive | 60 |
| Libération | 5 |

Le plafond est de quatre CPU, avec quatre cœurs physiques distincts vérifiés,
5 GiB de RAM et swap cumulés, réseau absent et sources montées en lecture seule.
L'image Foundation OpenFOAM 13 est celle déjà disponible, référencée par digest ;
aucun téléchargement, installation ou nouvel accès n'est prévu. L'admission
exige au moins 7 GiB de mémoire disponible et une réserve CPU vérifiée au moment
du lancement. Une référence explicite de coordination **après libération du
travail support** est obligatoire. Cette référence ne contourne pas les gates
qui refusent un calcul concurrent.

Le contrôle en lecture seule de Kali1 n'a pas permis l'accès Docker avec le
compte existant ; aucun exécutable `foamRun` n'a été trouvé dans son PATH.
Ce runtime n'est donc pas admis pour ce superviseur sans résoudre la
compatibilité dans un périmètre nouvellement coordonné. Aucun accès privilégié
ni modification de sécurité n'a été tenté. Kali2 reste la cible existante à
coordonner avec le propriétaire du travail support et des autres calculs.

## Reproduction

Les vérifications locales ne lancent aucun solveur :

```sh
python3 models/horizontal-fan-reconstruction/source/test_d3_supervisor.py
python3 models/horizontal-fan-reconstruction/source/verify_d3_supervisor.py
make fan-program-check
```

Le [lanceur figé](parameters/D3-supervisor-reviewed-capsule/source/launch_d3.py)
est réservé au runtime Linux amd64 compatible, après coordination explicite.
Les chemins ci-dessous désignent les copies privées déjà vérifiées ; le
répertoire de sortie doit être nouveau. Il s'agit de la commande future,
**non exécutée dans cette préparation** :

```sh
python3 -B "$D3_CAPSULE/source/launch_d3.py" \
  "$D3_PREPARED" "$D3_PREVIOUS" "$D3_SELECTIONS" "$D3_CAPSULE" "$D3_OUTPUT" \
  --capsule-sha256 e72db463f7f2feaec1ba7d53cfc2472b493e0ca9b89fe1ff01289246d094213f \
  --coordinated-release "$D3_CONFIRMED_RESOURCE_RELEASE"
```

La capsule peut être préparée à nouveau avec le
[builder](source/build_d3_capsule.py) et contrôlée avec
[l'audit indépendant](source/audit_d3_input_copy.py). L'empreinte d'une nouvelle
capsule doit être revue à nouveau ; les preuves précédentes ne s'y appliquent
pas automatiquement. Les sources figées et les artefacts historiques ne sont
pas réécrits.

## Interprétation et preuves requises

Une variance de pression moindre sous relaxation 0,05 pourrait refléter un
établissement numérique plus lent. L'analyse exige les dix contrôles numériques
initiaux et les sept contrôles additionnels de stationnarité pour **les deux**
branches. Elle compare aussi les champs locaux 1020→1040, le reflux et la
fenêtre native précédente. Aucun seuil n'est assoupli ; une admission déclarée
dans un rapport ne peut pas remplacer les contrôles eux-mêmes.

Même une paire admise ne démontrerait ni une instationnarité physique, ni
l'indépendance du domaine, ni une amélioration d'airflow ou du refroidissement
installé. Un timeout ou une branche partielle entraîne préservation et arrêt,
sans extension ni relance automatique. La nouvelle exécution native, son
archive vérifiée et son reçu de libération restent les preuves manquantes.
