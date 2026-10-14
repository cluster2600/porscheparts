# Frontière plongée et couverture volumique de l'éventail partagé

Sur l'enveloppe fermée des **153 boîtes** PR239, u=q_m source, les côtés fixes
et les fermetures PR240 forment une surface 3D plongée. La preuve `proof.md`
établit son indice un, puis la couverture exacte du volume fermé et le
non-recouvrement des **intérieurs** des tétraèdres/cellules de la représentation
PR241. Aucun ratio ponctuel, subdivision, candidat, dictionnaire ou natif.

## Contrôles nouveaux

Les 2304 faces latérales donnent 9216 triangles sans aplanir les quads. Les
42462720 paires sont couvertes par séparation stricte rationnelle des boîtes
englobantes (42403258) ou intersection exacte (59462). Les intersections
restantes sont exactement les simplexes partagés : 13312 arêtes, 43520 sommets,
2630 ensembles vides. Les 512 contacts d'arêtes par fermeture retrouvent
exactement les quatre boucles fixes PR240.

`check_embedding.py` utilise sections par plans et découpage coplanaire;
`verify_embedding.py` reconstruit les gabarits hex réduits et utilise
arêtes/triangles, barycentriques et déterminants. Il régénère le filtrage
exhaustif, relit toutes les paires candidates et exige l'égalité des ensembles
intersectés. Chaque lecteur contrôle 21 références analytiques à trois échelles.
Les deux lectures passent sans assertion refusée, en 11,891 s et 57,147 s.
Ces durées ne sont pas des benchmarks CFD.

`verify_gluing.py` contrôle les liens latéraux (chemins au bord, cycles ailleurs),
les deux composantes de 3072/6144 triangles et leurs 1024 arêtes de bord. Il
relit les **119808 bornes positives héritées** PR241 et annule les 479232 faces
orientées des tétraèdres exactement vers les 17920 triangles extérieurs. Il
ne recalcule pas les anciennes bornes polynomiales. Onze manifestes ancrés
au commit PR241 `c11b7bd5ae58049ccd4901627146c63666a50401`, 258 entrées.

## Déduction et portée

La couverture annulaire des fermetures PR240 est héritée dans son domaine.
Les côtés plongés ne rencontrent les plans extrêmes que sur leurs bords. Le
recollement donne une surface fermée connexe orientable. La dualité d'Alexander
justifie les deux composantes du complément, sans supposer une sphère. Le bord
de la chaîne tétraédrique est cette surface avec multiplicité un; les
orientations tétraédriques positives imposent une multiplicité intérieure un.
Les intérieurs sont donc disjoints et la couverture fermée suit par densité.
Tous les bords du domaine paramétrique sont conservés.

`check_proof_inputs.py` lie les reçus et leurs domaines à la preuve écrite;
c'est un contrôle structurel des hypothèses, **pas** un prouveur de théorèmes
ni une seconde reconstruction géométrique. La référence topologique et ses
numérotations selon l'édition sont précisées dans `source-references.json`.
Le livre reste local; son contenu n'est pas redistribué dans cette archive.

La conclusion ne catalogue pas tous les contacts internes de dimension
inférieure entre cellules non incidentes. L'égalité de volume signé native
PR241 reste mathématique; aucun premier moment ou centre natif n'est remplacé.
Les 113 boîtes passantes aux prédicats variables nécessaires ne sont toujours
pas admises en natif. Les deux boîtes aux déterminants indécis restent présentes.
Ni arrondis OpenFOAM, branches ROOTVSMALL/VSMALL, qualité native, repos, couches
physiques ou CFD qualifiés. Aucun débit, puissance ou calibration validé.

## Conservation et validation

`triangles.json` et `pairs.jsonl.gz` complets sont dans l'archive, pas dupliqués
dans Git. Sources, journaux, reçus et domaine sont conservés. Les preuves et
parcours PR238–241 ne sont pas relancés. Les tests locaux sont détaillés dans
`validation.md`; publication distante et inventaire via `archive-receipt.json`,
`file-manifest.json` et `remote-assets.json` dans la copie Git.
