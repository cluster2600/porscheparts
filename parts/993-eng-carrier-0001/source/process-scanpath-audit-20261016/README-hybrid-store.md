# Audit complet avec magasin mixte

`audit_complete_supports_hybrid.py` conserve la boucle d'audit de toutes les
couches, les intersections rationnelles avec les sections réelles de pièce et
la preuve d'exposition de chaque groupe matériel. Il ajoute le chargement du
magasin à cinq enveloppes historiques et deux enveloppes de prismes natifs.
Les anciens fichiers d'audit ne sont pas modifiés.

```sh
AM_PYTHON -B parts/993-eng-carrier-0001/source/process-scanpath-audit-20261016/audit_complete_supports_hybrid.py \
  PROCESS OUTPUT/support-scanpath-audit \
  --source-stl work/part-workflow/run-001/surface/carrier-remeshed.stl \
  --part-cache PART_CACHE
```

`AM_PYTHON` désigne le runtime de préparation épinglé. `PROCESS` doit être le
process complet réellement exécuté, avec ses six admissions et tous ses NPZ de
couches. Le dossier de sortie doit être nouveau. Aucun magasin partiel ou
diagnostic ne remplace ce process.

L'adaptateur charge une copie privée de chaque ancien auditeur. Il intercepte
uniquement le chargement nommé `support_audit_envelopes` à l'adresse exacte
`PROCESS/source/admitted_regions.py`, vérifie son empreinte, puis remplace son
constructeur par le lecteur v2 du même instantané. Les autres chargements et
l'objet partagé `importlib` restent inchangés. Les six sources épinglées du
magasin sont exigées dans `report.json.outputs_sha256`, vérifiées avant et après
l'audit, puis copiées dans les preuves de l'audit. Un import frère provenant
d'un autre instantané est refusé.

Le résumé final et `scanpaths/assessment.json` portent tous deux
`hybrid_envelope_store_verified=true` et
`rational_part_contact_intersections=true`. Le résumé conserve les empreintes
directes de `scanpaths/assessment.json` et `group-exposure-coverage.json` ; la
preuve séparée des groupes conserve son contrat antérieur. Une seule instance
du magasin doit avoir été effectivement chargée et vérifiée avant d'émettre le
nouveau marqueur.

Les neuf tests nouveaux couvrent l'ancien lecteur refusé, l'injection privée,
les imports inchangés, les identités absentes ou modifiées, le mauvais
instantané, les paramètres changés, l'absence de vrai chargement et les deux
marqueurs obligatoires. Avec les dix témoins rationnels précédents : **19 tests
passés**. Le prévol réel relit les sept régions et les deux cas natifs du
magasin déplacé ; les neuf faces gauches sans parent prouvé restent inconnues.
Ce prévol ne tranche aucune couche et ne constitue pas l'audit complet de la
préparation LPBF. Les identités et cette limite sont conservées dans
[`hybrid-store-results.json`](hybrid-store-results.json).
