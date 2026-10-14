# Référence 015 : contre-essai MRF de 38 mm terminé

Les 786 fichiers natifs sont conservés : champs de tous les rangs MPI, dernière reconstruction, entrées, journaux et reçu terminal. Le calcul termine à 20,0239 µs, mais ne valide aucun régime établi ni gain de performances.

Archive compressée : 2 701 650 759 octets. SHA-256 : `5dc38526dce22f7431c9bad64eec28922935cfa73c9121ec09cab4d0b4d16596`. Les trois segments ont été relus et leur concaténation vérifiée.

```sh
cat airflow-baseline-interface-015.tar.gz.part01 airflow-baseline-interface-015.tar.gz.part02 airflow-baseline-interface-015.tar.gz.part03 > airflow-baseline-interface-015.tar.gz
shasum -a 256 airflow-baseline-interface-015.tar.gz
```

Extraire dans un dossier neuf. Le TAR utilise des liens physiques pour dédupliquer les contenus identiques : copier indépendamment avant modification. Le manifeste fournit les chemins, tailles et empreintes de chaque fichier. L'audit figure dans `twins/bionic-turbo-f1/evidence/airflow-frame-equilibrium-20261012/baseline-interface-015-audit.json`.
