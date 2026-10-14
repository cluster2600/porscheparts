# Localisation de l'anomalie et contre-essai de frontière MRF

La PR #164 est fusionnée sur `main` au commit `5c4eb85d8859df71c892a50e9a5839513c3c7ffe`. Les neuf actifs de l'archive 010 publiée correspondent aux tailles et SHA-256 locaux, voir `../airflow-completed-20261012/remote-verification.json`.

## Résultat local vérifiable

Les deux extractions indépendantes retrouvent la cellule froide au même centre : **(31,129482 ; 7,260121 ; 4,643917) mm**. Elle touche trois faces du stator et son centre est à environ 31,965 mm de l'axe, près de la limite MRF de 32 mm. Ses dimensions sont environ 0,298 × 0,299 × 0,299 mm.

| Champ natif dans cette cellule | Démarrage 010 à 19,4966 µs | Reprise 014 à l'itération locale 100 |
|---|---:|---:|
| Température | 136,170 K | 4,21148 K |
| Pression | 70 517,1 Pa | 8 105,97 Pa |
| Vitesse absolue | 1 381,53 m/s | 2 425,04 m/s |

Les minima de pression du domaine se trouvent ailleurs : **178,42 Pa** à l'itération 100 de 014. Le gaz parfait et cette solution non convergée ne permettent aucune conclusion physique de performance. La référence 014 a été arrêtée volontairement après sauvegarde des champs à 100 ; elle n'a pas terminé ses 600 itérations. Le reçu d'arrêt est conservé avec le cas.

`locate_cold_cell.py` relit les champs ASCII natifs, identifie la cellule, retrouve ses faces via `owner`/`neighbour`, puis ses coordonnées et contacts de paroi. Les rapports épinglent les fichiers consommés et le source. Le rapport 010 concerne `work/bionic-airflow-20261012/baseline-transient-010`. Le rapport 014 concerne `work/bionic-airflow-20261012/baseline-parallel-014/processor1`, cellule locale 495869. Les percentiles du rapport 014 portent uniquement sur ce rang MPI.

## Portée de la comparaison série / MPI

La référence respecte rtol = 1e-5 et atol = 1e-10 sur les premiers 14 échantillons de p_min, T_min, débit de sortie et couple axial total. Les petites composantes transverses du moment ne respectent pas ce seuil (écarts relatifs jusqu'à environ 0,98 %).

La candidate ne respecte pas ce seuil strict sur toutes les grandeurs sélectionnées : l'écart relatif de T_min atteint environ 1,5e-4 dans le court historique comparé. Les rapports conservent valeurs, seuils et écarts. **Aucune équivalence de tous les champs ni indépendance à la décomposition n'est établie.** Les témoins série 013 ont été arrêtés explicitement ; leurs champs et journaux restent conservés.

## Hypothèse testée par 015

`cfd/mrf_interface_countertrial.py` copie les entrées vérifiées de 008 et applique les mêmes équations transitoires, conditions aux limites et démarrage à froid que 010. Seul le rayon de la sélection MRF passe de 32 à 38 mm ; le solveur tourne sur quatre rangs MPI. Le régime reste 100 000 tr/min et le rapport de pression imposé reste 1,2.

`topoSet` reconstruit la zone. Le préparateur vérifie que les points, faces, propriétaires et voisins n'ont pas changé et relit la topologie : tous les propriétaires du rotor doivent rester dans la zone, tous les ports hors zone. Il réutilise le contrôle d'arrêt sur p/T non positives et la limite de deux heures. Un test provoque une mutation native de géométrie pour vérifier son rejet.

**Critères d'interprétation, définis avant le résultat :** comparer les historiques sur les mêmes 20 µs, localiser à nouveau le minimum de température et la vitesse associée, puis contrôler les flux physiques. Une amélioration de ces anomalies établira seulement une sensibilité numérique à l'interface, pas un gain de débit ou de puissance du turbo. Un code natif nul ne vaut pas convergence.

Le contrôle canonique du maillage reste non satisfait. Les parois en escalier, les couches limites absentes, l'indépendance au maillage et les conditions non mesurées bloquent toujours une qualification de performance et un jumeau numérique calibré.
