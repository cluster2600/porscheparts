# Validation

Le calcul principal termine en 226.279 s; la reconstruction indépendante en
214.614 s. Ces durées locales ne sont pas des benchmarks CFD. Le parcours
principal a recouvert une partie de l'exécution des tests du dépôt.

Les 527744 enregistrements de faces et leurs 2100224 bornes individuelles sont
relus avec inclusion des bornes indépendantes. Toutes les classifications
positives revendiquées sont confirmées. Les 3328 indécisions sur l'enveloppe
sont conservées; les 509184 contrôles locaux sont positifs. Les 6144 cellules
sont relues pour les deux applications de gardes. Neuf références analytiques
par programme, treize manifestes et 309 entrées de payload vérifiés.

La borne inférieure minimale parmi les enregistrements positifs employés pour
la couverture est environ 0.8545777791134115, au-dessus du seuil source 0.8.
Ce nombre est une borne conservative, pas une valeur ponctuelle de planéité.
Les minima exacts et leurs domaines/rangs figurent dans summary.json.
L'independent-readback conserve aussi son minimum incluant les faces indécises
sur l'enveloppe : il ne doit pas être présenté comme le minimum des certificats
positifs locaux. Les résumés sont des relectures structurelles.

Tests turbo : 108 réussis, un ignoré, 15.308 s.
`PATH=work/bionic-tools/bin:$PATH make check` : 3920 tests en 209.516 s,
172 ignorés, deux échecs flottants WE43/fan_stator et trois erreurs
rtree/networkx hors turbo. Les cinq labels sont exactement ceux de PR244,
comparaison enregistrée dans test-comparison.json. Codes turbo 0 et make 2.

Une vérification de compilation seule du lecteur, pendant sa préparation,
a détecté une nouvelle ligne manquante; elle a été corrigée avant sa première
exécution. preparation-attempts.json conserve cet incident sans résultat
scientifique. Les deux évaluateurs terminent sans assertion refusée. Aucune
installation, ancien parcours relancé, création de conteneur ou calcul natif.
Le volume bionic-native-source-20261012 est présent et préservé.

Les expressions mathématiques conditionnelles WM_DP sont couvertes, pas les
arrondis d'une exécution, les conversions d'entrée/sortie ou l'admission native.
Aucun ratio choisi, candidat, dictionnaire, solveur, débit, puissance ou
calibration validé. Toutes les boîtes et les indécisions antérieures demeurent.
