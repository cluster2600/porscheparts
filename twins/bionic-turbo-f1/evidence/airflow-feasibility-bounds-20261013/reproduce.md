# Reproduction

Restaurer séparément les archives parentes indiquées dans dependencies.json sous work/, puis les fichiers de cette archive dans un NOUVEAU répertoire de travail. Garder les sources et preuves publiées immuables. Les chemins des dépendances restent ceux des archives restaurées ; aucun gros maillage n'est dupliqué ici.

Dans la racine du dépôt, lancer la copie de bounds.py, test_arithmetic.py, verify_bounds.py puis summarize_ranges.py avec le Python du projet. bounds.py refait un encadrement de boîtes, jamais un maillage natif. Il vérifie tous les payloads des trois manifestes parents avant calcul. verify_bounds.py peut aussi relire directement le certificat restauré sans refaire le premier encadrement.

Le résultat scientifique est certificate.json et ses bornes rationnelles ; les nombres décimaux de présentation n'en sont pas les entrées. Les sorties du programme sont relatives au dossier de sa copie. Ne pas l'exécuter directement dans le dossier evidence/ épinglé et ne pas écraser un résultat archivé.
