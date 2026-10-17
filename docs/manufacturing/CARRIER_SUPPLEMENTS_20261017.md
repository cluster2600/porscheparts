# Suppléments du calcul et de sa reproduction

Le [guide 7](../../scripts/build_carrier_workshop_guide_v7.py) ajoute au guide 6
le cycle mécanique à **32 états**. Il vérifie d’abord le rattachement historique
à 16 états et conserve les six admissions de supports du guide 6. Il rattache
ensuite les résultats au même maillage et au même deck de charges, vérifie les
reçus du solveur et des audits, puis recalcule la comparaison des états JSON.

Les seuils restent ENER = 0,001 et Piola = 0,0001. Le refus ENER historique
à 16 états reste visible. La loi est la référence publiée Grade 23 ELI ; le
résidu calculé n’a pas de seuil d’acceptation défini. La
[capsule des preuves](../../parts/993-eng-carrier-0001/source/design-20261016/constitutive-refinement-20261017/README.md)
et ses 44 fichiers sont copiés avec leur manifeste dans le dossier du passage.

Sur une nouvelle exécution dont les sept régions et le processus ont été admis :

```sh
python scripts/build_carrier_workshop_guide_v7.py /chemin/du/passage
```

Le module ne relance ni solveur ni audit des fichiers DAT. Son rattachement a
été rejoué sur des copies exactes des entrées du modèle actuel. Le packaging
du guide complet attend encore les résultats des sept régions.

Le [runner 3](../../scripts/run_part_workflow_v3.py) conserve le contrat du
runner 2 et accepte un budget déclaré de 1 à 86 400 secondes **par étape**.
Les étapes restent séquentielles ; ce plafond n’est pas une durée totale.
Les recettes existantes gardent leurs budgets. La recette suivante doit
déclarer explicitement les budgets nécessaires aux longues générations.
Le nettoyage sur dépassement reste celui du runner 2 ; le superviseur des
diagnostics constitue un mécanisme distinct.

Les tests ciblés couvrent les identités et les sorties du runner, les bornes
des budgets et les refus du supplément mécanique : données modifiées,
calendrier incomplet, seuils altérés, erreurs du solveur ou des audits et
copies modifiées après rendu. La [galerie](../../parts/993-eng-carrier-0001/source/progress-figures-20261016/index.html)
conserve les images du modèle et des calculs.

La [recette locale de la région 008](../../manufacturing/workflows/993-carrier-source008-v7-001.json)
relance uniquement sa génération V7 depuis les entrées conservées, avec un
budget de 57 600 secondes et les captures de chaque section terminée. Ses
47 empreintes et son identité de runtime ont été vérifiées avant lancement.
Elle reste distincte de la recette complète : son exécution est en cours,
et aucun résultat des sept régions n’est déduit du seul rejeu local illustré.

La [capsule des restaurations logicielles](../../parts/993-eng-carrier-0001/source/software-archive-restoration-20261017/README.md)
conserve les trois expériences réelles CalculiX, PyMesh et CGAL b4e8, les
appelants exécutés, les petits résultats natifs et un vérificateur sans
runtime natif. Elle précise les dépendances déjà installées et distingue
l’archive expérimentale de la procédure CGAL stable 6.1.3.

La [capsule d'encodage des points couverts](../../parts/993-eng-carrier-0001/source/process-point-encoding-20261017/README.md)
conserve le contrôle réel des **17 384 événements** de la grande zone 000 sur
les 1 034 hauteurs : tous possèdent un témoin encodé non nul du même groupe.
Le helper et ses treize tests sont utilisables sans runtime AM ; un
vérificateur relit les preuves compressées et recalcule cellules d'arrondi et
inclusions rationnelles. La géométrie originale reste intacte. L'intégration
au découpeur et le recalcul des contacts et des graphes restent séparés de
ce contrôle ; aucune admission globale n'est donnée par cette capsule.
