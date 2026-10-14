# Archives de relance CFD du turbo — 12 octobre 2026

Archive diagnostique non qualifiante. Elle contient tous les fichiers locaux retenus des essais stationnaires 008 rejetés, les sorties complètes des essais transitoires 009 échoués (entrée rhoFinal absente), et les entrées immuables des relances 010. Les sorties 010 en cours ne sont pas incluses.

Vérifier le SHA-256 de `airflow-restart.tar.gz` avec `archive-receipt.json`, puis extraire dans un dossier vide :

```sh
mkdir restored
cd restored
tar -xzf ../airflow-restart.tar.gz
```

`file-manifest.json` donne taille et empreinte de chaque fichier. L'archive utilise des liens physiques pour les doublons : copier les fichiers indépendamment avant toute modification ou nouvelle simulation. Ne pas modifier les cas historiques. Le code correspondant à 010 est dans le commit Git 915616a0 ; le code initial 009 est conservé dans son sous-dossier provenance.

Les reçus `running` de 008 sont périmés. Les tables natives contiennent des températures absolues négatives ; aucun résultat de performance n'est accepté. Pour les relances 010, consulter l'état exact du conteneur nommé dans `launch-transient.json` et le futur `native-exit.json`. Un lancement ne démontre ni convergence, ni meilleur débit, ni puissance maximale.
