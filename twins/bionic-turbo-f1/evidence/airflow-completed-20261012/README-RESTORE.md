# Archives complètes des calculs transitoires 010

427 fichiers natifs, toutes les sauvegardes de champs et tous les historiques des deux calculs terminés. Résultats diagnostiques non stationnaires et non qualifiants.

L'archive de 4 827 880 716 octets est divisée en cinq segments. Vérifier chaque SHA-256 avec `split-receipt.json`, puis concaténer dans l'ordre :

```sh
cat airflow-completed-010.tar.gz.part0[1-5] > airflow-completed-010.tar.gz
shasum -a 256 airflow-completed-010.tar.gz
mkdir restored
cd restored
tar -xzf ../airflow-completed-010.tar.gz
```

SHA-256 attendu de l'archive : `dda2205a4e20348cbaf045f147cde486b833d28b800cef5626654a47122f3f06`.

Le manifeste liste les empreintes individuelles. Tous les contenus uniques de l'archive ont été relus ; les cibles des liens physiques et la concaténation ont été vérifiées. Les doublons utilisent des liens physiques : copier indépendamment avant toute modification. Ne pas écraser les essais historiques.

Le débit est encore inversé à la sortie à 20 µs. Le code natif nul ne démontre pas une convergence stationnaire ni un gain de performances. Les reprises ultérieures 011–013 ne font pas partie de cette archive.
