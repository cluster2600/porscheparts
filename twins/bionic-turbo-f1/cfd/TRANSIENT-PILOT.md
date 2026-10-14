# Relance transitoire diagnostique du 12 octobre 2026

Les deux essais stationnaires 008 sont rejetés : leurs historiques natifs
contiennent une température absolue négative (référence : −9,296 K à
l'itération 21 ; volute F1 : −9,553 K à l'itération 16). Les conteneurs
ont disparu et le lanceur hôte n'a pas finalisé ses reçus `running`.
Ces reçus historiques restent conservés tels quels ; ils ne prouvent pas
qu'un calcul tourne encore. La cause exacte de leur disparition n'est pas
établie. Les historiques suffisent à rejeter les résultats physiques.

Le nouvel essai 010 utilise `rhoPimpleFoam`, Euler en temps, une convection
amont conservative, deux corrections externes PIMPLE et un pas adaptatif
limité à Co = 0,3 et 0,1 µs. Il vise uniquement les 20 premières µs du
démarrage. Cette durée très courte ne permet ni convergence stationnaire,
ni comparaison de débit/puissance, ni qualification d'un jumeau numérique.

Les maillages, conditions aux limites, propriétés de l'air et rotation
MRF à 100 000 tr/min sont copiés et vérifiés par empreinte depuis 008.
Les frontières restent en escalier, sans couches de paroi ; l'autorisation
de classement des performances reste explicitement fausse. La nouvelle
discrétisation traite le démarrage instable ; ce changement ne démontre pas
à lui seul la cause physique ou numérique précise des échecs stationnaires.
Aucune température ni pression n'est écrêtée pour rendre un résultat acceptable.

Le lancement Docker est détaché. Le solveur écrit directement son journal
dans le dossier local. Un surveillant dans le même conteneur arrête le
solveur sur erreur native ou minimum p/T non positif/non fini. `timeout`
limite l'exécution à deux heures ; `native-exit.json` enregistre la sortie.
Les conteneurs arrêtés sont conservés pour permettre l'inspection Docker,
notamment en cas de manque de mémoire ou d'arrêt extérieur. Une coupure
de Docker peut empêcher l'écriture du reçu terminal : vérifier alors
`docker inspect`, sans interpréter `launch-transient.json` comme un statut vivant.

```sh
python twins/bionic-turbo-f1/cfd/transient_pilot.py prepare OLD_RUNTIME_008 NEW_CASE
python twins/bionic-turbo-f1/cfd/transient_pilot.py launch NEW_CASE
# Le nom exact du conteneur figure dans NEW_CASE/launch-transient.json.
docker inspect CONTAINER --format '{{json .State}}'
cat NEW_CASE/native-exit.json
tail -40 NEW_CASE/log.transient-rhoPimpleFoam
```

Un code natif nul avec `End` signifie seulement que l'exécution s'est
terminée. Il faut encore auditer les historiques, les bilans et les champs ;
ce pilote ne satisfait pas le contrôle canonique du maillage.

L'essai transitoire 009 a détecté une entrée `rhoFinal` manquante lors de
la seconde correction PIMPLE. Les deux sorties natives et leurs reçus
d'échec sont conservés. L'essai 010 ajoute cette entrée au solveur diagonal
de densité ; un test empêche sa régression. Le source exact de 009 est
conservé dans son dossier `provenance`.

La réparation de l'empreinte `Runner.cs` attendue par l'étude des supports
moteur était déjà dans `origin/main` (`f9a44898`) ; l'intégration de `main`
la réutilise, sans réécrire cette étude ni ses preuves.

Références OpenCFD : [solveur rhoPimpleFoam](https://doc.openfoam.com/2312/tools/processing/solvers/rtm/compressible/rhoPimpleFoam/)
et [schémas numériques](https://www.openfoam.com/documentation/user-guide/6-solving/6.2-numerical-schemes).
