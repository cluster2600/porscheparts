# F42.2 — exécutions AdditiveFOAM mesurées

Ce dossier publie deux exécutions complètes et indépendantes au niveau hôte du
même plan F42 : `27` cas nominaux et `6` cas supplémentaires de convergence.
Les résultats sont extraits des champs VTK volumiques et des moniteurs de bain
du solveur. Les manifestes de provenance retirent les chemins privés, les
identifiants Vast et la géométrie dérivée du scan.

La comparaison inter-hôtes mesure la reproductibilité du runtime et des
résultats numériques. Elle **n'est pas** une deuxième méthode physique, une
carte matière fournisseur, une simulation de distorsion de la culasse entière
ou une qualification de machine LPBF.

Les deux exécutions ont terminé `33/33` cas, sans saturation à `3 300 K`, avec
`3/3` comparaisons de convergence passées. Les `33/33` couples inter-hôtes sont
dans les tolérances ; l'écart absolu maximal observé sur T99 est
`3,0517578125e-5 K`.

Les fichiers `results-host-*.json` contiennent les `33` mesures et les tests de
convergence. Les fichiers `provenance-host-*.json` lient les journaux de solveur
par SHA-256 sans publier leurs chemins. Les images sont des visualisations de
ces nombres. Le manifeste de publication lie tous les artefacts publics.

Le volume liquide extrait des VTK finaux peut être nul parce que ces états sont
écrits après refroidissement. Les dimensions de bain proviennent du moniteur
thermique en ligne ; ces deux observations ne doivent pas être confondues.

Toutes les portes de fabrication, de coupon physique, de fichier machine et de
démarrage moteur restent fermées. Aucun fichier de ce dossier n'autorise une
impression métal.
