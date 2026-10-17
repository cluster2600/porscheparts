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

La [planche du calcul de retrait imposé sur la pièce entière](../../parts/993-eng-carrier-0001/source/progress-figures-20261016/wholepart-release-20261017/README.md)
conserve les quatre champs de déplacement natifs, leur lecture en double
précision et les contrôles analytiques. L'ancien seuil de gradient de 10⁻⁷
reste inchangé. Le cas uniforme donne une erreur de 1,24×10⁻¹⁴ ; le champ
quadratique et le bridage provisoire donnent 58,090 µm après libération.
Cette étude de sensibilité mécanique ne remplace pas la simulation du procédé.
Le PNG a été relu ; les trois formats ont été reproduits depuis une copie séparée.
La [capsule du cas natif complet](../../parts/993-eng-carrier-0001/source/design-20261016/wholepart-native64-20261017/README.md)
conserve les entrées, les quatre états, les sources exactes et les vrais reçus.
Ses commandes restaurent les fichiers comprimés et rejouent leur analyse avec
Python et NumPy, sans relancer le solveur.

La [planche du raffinement local](../../parts/993-eng-carrier-0001/source/progress-figures-20261016/local-refinement-20261017/README.md)
compare les arêtes réelles avant et après dans deux zones fixes. Le maillage
résultant contient **160 964 nœuds et 86 544 éléments T10** ; les 3 218 facettes
protégées et les ensembles d'appuis sont conservés. La
[capsule des deux calculs élastiques](../../parts/993-eng-carrier-0001/source/design-20261016/local-refinement-20261017/README.md)
fournit le maillage, les entrées du solveur, les champs complets et les commandes
de restauration et de réanalyse. Les deux bilans énergétiques passent leur
seuil inchangé de 10⁻⁴ ; la réanalyse depuis un autre répertoire reproduit
les quatre rapports complets à l'octet.

Les pics calculés atteignent **1 108 MPa sur appuis rigides et 3 337 MPa sous
K1000**, soit des hausses de 79,4 % et 99,1 % par rapport au maillage EF7.
Ils migrent vers la jonction capot–nervure. Ce résultat oriente la correction
de la forme ; il ne constitue pas une convergence des contraintes. Les dessins
du maillage et les résultats mécaniques restent rattachés au même STEP de
référence, distinct de toute nouvelle géométrie de congé.

La [coupe comparative du congé R1](../../parts/993-eng-carrier-0001/source/progress-figures-20261016/native-fillet-20261017/README.md)
montre le raccord construit dans le BREP natif, aux mêmes coordonnées avant et
après. Ses points CAO extraits et les trois exports sont conservés ; le rejeu
autonome reproduit leur dessin. Le prototype conserve son contrôle d'échange
STEP refusé et n'hérite pas des calculs mécaniques de la géométrie précédente.

La [planche du nouveau remaillage](../../parts/993-eng-carrier-0001/source/progress-figures-20261016/surface-remesh-20261017/README.md)
compare les deux STL complets du même BREP C1. Gmsh 4.15.2 produit **638 174
triangles**, avec **zéro aiguille** au critère inchangé de 0,001. Le
[contrôle libigl réellement clos](../../parts/993-eng-carrier-0001/source/progress-figures-20261016/surface-remesh-audit-20261017.json)
confirme zéro bord ouvert, non-manifold, incohérence d'orientation, dégénéré
ou intersection, une composante positive et les alésages et appuis conservés
dans leurs tolérances. Les 3 072 sondes STL→BREP et les 8 621 points BREP→STL
donnent des maxima de **0,018234 et 0,047388 mm**, sous le seuil de 0,06 mm.
Ces distances restent échantillonnées. Le
[rejeu autonome du dessin](../../parts/993-eng-carrier-0001/source/progress-figures-20261016/surface-remesh-root-publication-20261017.json)
reproduit les PNG, SVG et PDF à l'octet ; les vrais reçus sont conservés.

Le maître BREP C1 passe aussi le Cut natif strict de conservation de matière.
Son nouveau maillage global de calcul comprend **166 794 nœuds et 89 788
éléments T10**, avec un minimum de Jacobien de **0,00828553** et aucun élément
non positif. Les six groupes nodaux sont mesurés sur ce maillage ; leurs
listes diffèrent de l'ancien EF7. Le contrôle d'import compare désormais les
volumes calculés par la même intégration, au seuil inchangé de 10⁻⁸ ; le
volume adaptatif reste la référence pour la masse et le volume EF.
La masse CAO reste proche de **1,26237 kg**, sous le plafond de **1,30 kg**.
Les nouveaux cas rigide et K1000 du congé sont préparés séparément ; les
contraintes et le raffinement local de l'ancienne CAO ne sont pas transférés.
