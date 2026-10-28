# Contrôle des expositions de supports

Ce contrôle complète `process-slicing-20261016/audit_scanpaths.py`, qui vérifie
les trajectoires de **pièce**. Il lit tous les vrais vecteurs de **supports**,
les NPZ de feuilles/dents et les six admissions du même processus. Un cache de
pièce terminé n'est pas un processus de supports terminé.

Depuis la racine du dépôt, avec le runtime PySLM de couverture :

```sh
work/part-workflow/runtimes/pyslm-coverage-011/env/bin/python \
  parts/993-eng-carrier-0001/source/process-scanpath-audit-20261016/test_support_scanpaths.py

work/part-workflow/runtimes/pyslm-coverage-011/env/bin/python \
  parts/993-eng-carrier-0001/source/process-scanpath-audit-20261016/audit_support_scanpaths.py \
  PROCESS_OUTPUT PROCESS_OUTPUT/support-scanpath-audit \
  --source-stl work/part-workflow/run-001/surface/carrier-remeshed.stl \
  --part-cache work/carrier-process-20261016/part-layer-cache-001
```

Le dossier de sortie doit être nouveau. Le code de retour vaut zéro uniquement
pour un reçu `assessment.json` accepté. Aucun mode d'échantillonnage ne peut
produire une admission complète.

Les critères restent explicites :

- Chaque tableau est fini, de type float64, sans segment nul ni doublon exact,
  et contient toutes les coupes attendues, sans segment supplémentaire.
- Chaque triangle retenu appartient à un groupe `face_range/order/type` lié au
  matériau WKB et à son reçu de contact. Les grilles couvrent exactement ce
  matériau. La reproduction du remappage figé des peaux établit l'identité entre
  leur matériau paramétrique, leurs cartes par morceaux et leurs triangles.
- L'auditeur coupe ensuite les **vrais triangles NPZ** par une formule
  barycentrique rationnelle indépendante du sectionneur. Une section de triangle
  est convexe : son segment entier est ainsi certifié. Les IEEE d'entrée sont
  interprétés exactement ; aucune distance de proximité ne soude des feuilles.
- Les endpoints rationnels sont encodés par arrondi float64 au plus proche, pair
  en cas d'égalité. Leur erreur exacte est bornée par une demi-ULP. Un endpoint
  encodé peut nécessairement sortir d'une feuille sans épaisseur lorsque la
  coordonnée rationnelle n'est pas dyadique. Ce verdict strict reste affiché ;
  le certificat de section et d'encodage est distinct. Les collisions entre
  deux représentations float64 identiques gardent leurs deux identités
  rationnelles.
- Les traces de contact sont aussi l'intersection rationnelle entière entre
  le matériau et les interfaces brutes. Les trous sont conservés. Un simple
  contact ponctuel n'est pas un intervalle d'ancrage. Les anciennes
  intersections GEOS peuvent servir de diagnostics ; leurs points arrondis ne
  doivent pas être utilisés comme preuve de confinement exact.
- Les graphes des sections rationnelles et des vecteurs float64 effectivement
  exposés doivent tous deux passer. Une arête intralayer est une intersection
  exacte de trajectoires. Une liaison entre couches exige une intersection XY
  dans deux couches **consécutives**. Chaque composante de couche doit déjà
  rejoindre un ancrage inférieur ; une jonction apparue plus tard ne sauve pas
  une feuille qui a commencé à flotter.
- Chaque composante finale rejoint aussi un contact supérieur réellement exposé
  dans la section de pièce. Le même morceau de trajectoire doit rencontrer la
  bande de contact et une longueur positive dans la pièce. La pénétration
  verticale de 0,2 mm est le paramètre du générateur, sans extension XY.
  L'ancrage plaque est limité à la première couche et au vrai carré de 500 mm,
  avec une interface inférieure à Z=0.

Les domaines de pièce sont comparés aux tableaux du cache complet via
`CachedLayers`. Le STL source, la pose exacte et le magasin d'enveloppes avec
ses audits natifs sont vérifiés. Les sources, reçus, NPZ et CSV doivent garder
leurs SHA avant et après le passage.

`exact_support_section.support_section(surface,z,face_z_bounds)` est le hook de
génération séparé du CORE4184. Il calcule les arêtes partagées en rationnels,
arrondit correctement et n'emploie pas `tol.merge`. Le lanceur peut affecter
`core.support_section = hook.support_section` sur son module chargé, puis figer
le hook dans ses extensions. Le fichier CORE et le cache de pièce sont
inchangés. `exact_contacts.round_contact_traces(material,interfaces)` fournit
le pendant pour les métadonnées de contact.

Le reçu accepté doit porter `complete_build_audited=true`,
`support_scanpaths_audited=true`, `geometric_confinement_passed=true` et
`exposure_connectivity_passed=true`, et référencer exactement le SHA de
`PROCESS_OUTPUT/report.json`. Il porte sur les lignes d'exposition et les
contacts entre couches. Aucun diamètre de spot ni ordre d'exposition à
l'intérieur d'une couche n'est supposé.

Les témoins et les profils sont référencés dans `results.json`. L'exécution
complète sur les supports corrigés du carrier reste une étape distincte.
