# Runtime PySLM à domaines contrôlés

Ce dossier conserve le générateur et l'installation utilisés par le cache des
1 034 couches de la pièce. Les versions et les quatre modules PySLM corrigés
sont liés par empreinte dans [upstream.json](upstream.json). L'installateur
refuse un répertoire existant, contrôle le patch et les fichiers installés,
vérifie les dépendances et découpe un témoin de 20 × 10 mm.

Installation sur macOS arm64 avec Python 3.11 :

```sh
python3.11 parts/993-eng-carrier-0001/source/process-coverage-20261016/setup_pyslm.py \
  work/part-workflow/runtimes/pyslm-new
```

Le [reçu de réinstallation indépendante](../process-slicing-20261016/pyslm-reinstall-validation.json)
confirme le runtime réellement reproduit. Le [cache des couches](../process-cache-20261016/README.md)
utilise ce générateur figé ; les corrections de peaux et de contacts restent
dans `process-skins-20261016` pour préserver ses empreintes.

Le générateur seul ne constitue pas une préparation complète admise : la
génération historique des supports du carrier a été refusée. Les contrôles
supplémentaires de toutes les régions, des peaux, des grilles, des contacts,
des collisions et des trajectoires restent nécessaires. Aucune traduction
vers un fichier de fabrication propre à une machine n'est exécutée ici.

PySLM est conservé à la révision
`8fa03f1eb98b1fbc8e617eb3119d669f356a2f0b`, sous LGPL-2.1, avec sa
[licence](LICENSE.pyslm), son patch et la liste verrouillée des dépendances.
Le runtime historique de `process-20261016` reste séparé.
