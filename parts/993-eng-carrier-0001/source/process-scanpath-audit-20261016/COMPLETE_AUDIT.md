# Reçu complet obligatoire

Le lanceur final utilise `audit_complete_supports.py`. Les six fichiers initiaux
restent figés ; ce wrapper ajoute la preuve qu'aucun groupe matériel entier ne
disparaît entre les plans de tranchage.

```sh
work/part-workflow/runtimes/pyslm-coverage-011/env/bin/python \
  parts/993-eng-carrier-0001/source/process-scanpath-audit-20261016/audit_complete_supports.py \
  PROCESS_OUTPUT PROCESS_OUTPUT/support-scanpath-audit \
  --source-stl work/part-workflow/run-001/surface/carrier-remeshed.stl \
  --part-cache work/carrier-process-20261016/part-layer-cache-001
```

Le wrapper exécute obligatoirement l'audit complet initial dans `scanpaths/`.
Il recherche ensuite, pour chaque groupe de faces, au moins une vraie exposition
enregistrée égale à l'encodage correctement arrondi de sa coupe rationnelle.
Le témoin contient l'identifiant du groupe, la face source, la couche, Z et le
vecteur. Une feuille entièrement située entre deux plans est refusée.

Cette seconde recherche utilise des témoins de couche après le contrôle
obligatoire de **toutes** les couches. Elle ne peut pas remplacer cet audit
complet. Son cache de lecture est borné à huit couches et ne recalcule aucune
hachure de pièce.

Le reçu final `assessment.json` lie par SHA le même `process/report.json`,
`scanpaths/assessment.json` et `group-exposure-coverage.json`. Les deux sous-reçus
doivent être acceptés. Les cinq flags initiaux sont conservés et
`every_material_group_exposed=true` est obligatoire. Le sous-reçu de couverture
porte aussi `layers_audited`, `complete_build_audited` et le SHA du processus ;
la provenance du passage complet y est indiquée.

Vérification ciblée : `python test_complete_supports.py` (trois témoins,
dont la feuille située entre deux plans). L'exécution complète sur le carrier
attend encore le processus final avec ses supports corrigés.
