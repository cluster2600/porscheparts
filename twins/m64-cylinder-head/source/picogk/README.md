# PicoGK — qualification géométrique du corps existant

Cette application utilise le noyau LEAP 71 fixé dans
`containers/m64-leap71/sources.lock`. Elle traite une copie triangulée du corps
privé à quatre logements, **sans modifier le STEP maître ni lui appliquer un
nouveau recalage**. L'échelle reste l'hypothèse 1 unité du scan = 1 mm ; les
interfaces moteur ne deviennent pas des cotes M64 mesurées.

## Lot reproductible

1. `export_master.py` : importer le STEP exact par son SHA256, contrôler son
   état et trianguler avec une déflexion absolue déclarée ; conserver les
   fichiers et rapports dérivés dans le répertoire privé, hors Git/Docker.
2. `/opt/m64/HeadVoxels.dll INPUT_STL NOUVEAU_REPERTOIRE RESOLUTION_MM` :
   importer sans transformation, voxeliser puis exporter le maillage. Lancer
   trois processus indépendants à 0,6 / 0,3 / 0,15 mm et limiter chaque durée.
3. `compare_meshes.py` : comparer ces trois sorties au même maître triangulé,
   vérifier la topologie, le volume, les boîtes et les distances échantillonnées
   dans les deux sens. Effectuer le repérage échantillonné des zones fines et
   sauvegarder séparément chaque résolution. Produire la vue comparative et
   une section dans une étape distincte du gros audit.

Le contre-contrôle Python nécessite `numpy`, `scipy`, `trimesh`, `rtree`,
`matplotlib` et `networkx` (construction des contours de coupe). Son
environnement Python est isolé dans `/opt/geometry-qa` de l'image PicoGK de
recherche ; les versions réellement utilisées accompagnent le reçu d'audit.
Le témoin de l'image utilise uniquement des formes synthétiques, hors réseau.
Le rendu Matplotlib peut
présenter des défauts de tri de profondeur sur les faces coplanaires : une
vue opaque VTK permet de les distinguer de défauts géométriques.

L'import-export PicoGK remaille les surfaces : les maillages résultants ne
remplacent **pas** le maître B-Rep des interfaces et des portées usinées.
Une faible erreur volumique globale ne suffit pas à qualifier ces interfaces.

## Audit reprenable et mémoire

`compare_meshes.py --output NOUVEAU_DOSSIER --query-chunk-size 32` crée un
contexte lié aux SHA des entrées, reçus et sources, aux versions Python et
bibliothèques, ainsi qu'aux paramètres. Il exécute le maître puis chacune des
trois résolutions dans un processus neuf. Chaque résultat complet est écrit
atomiquement en JSON privé avant le suivant ; temps et pic RSS sont conservés.

Après interruption, la même commande avec `--resume` réutilise seulement les
checkpoints intègres dont tout le contexte correspond. Une modification de
maillage, code, versions, seed ou taille de lot interdit la reprise du même
dossier. Les sorties anciennes sans contexte ne sont pas promues en checkpoints.
Le repli de classification intérieur/extérieur est explicitement seedé et
les ambiguïtés persistantes sont rejetées et comptées, non résolues au hasard.

Les lots bornent les requêtes de proximité et de rayons, **pas** la taille du
maillage ou de son index spatial. Sur le maillage à 13,7 millions de triangles,
lancer **sans `--render`**, avec limites mémoire/temps externes et supervision
du groupe de processus. Après arrêt brutal du parent, vérifier l'absence de
worker orphelin avant reprise : le verrou du répertoire seul ne le démontre pas.
Le rendu Matplotlib ne possède pas de checkpoint distinct et ne doit pas
conditionner la sauvegarde du calcul fin.

Les tests couvrent panne après première résolution, reprise, corruption,
contexte changé, verrou concurrent et invariance des requêtes, y compris une
branche de parité incohérente forcée. Ils ne qualifient pas la pièce.

## Coques orientées et contre-test du STEP

`audit_roundtrip_shells.py` relit un candidat lié explicitement à son SHA,
au maître et au reçu de voxelisation. Il conserve toutes les coques, compte
leurs triangles et intègre leurs volumes signés ; la somme est comparée au
volume du maillage entier. Une petite coque négative n'est ni supprimée selon
sa taille, ni interprétée automatiquement comme porosité physique.

`audit_shell_against_step.py extract` localise une coque choisie et enregistre
ses triangles exacts **en privé**. Son mode `occt` utilise ces triangles comme
un opérande fermé distinct, orienté positivement pour le diagnostic, puis
calcule région moins STEP et région intersectée avec STEP. Il contrôle la
validité et le bilan volumique aux tolérances OCCT déclarées, avec valeur
floue supplémentaire nulle. Il n'inverse jamais le maillage source.
Les témoins couvrent régions intérieures, extérieures et traversantes.

Le [reçu de reprise](../../evidence/picogk-roundtrip-checkpoint-audit-20260907.json)
conserve l'audit complet, les défauts et le contre-test de la micro-coque à
0,3. Les coques de 0,15 ne sont pas assimilées à ce résultat. La
[propagation des vides](../picogk-connectivity/README.md) est un contrôle
distinct : connexité de surface et connectivité d'un volume ne sont pas
équivalentes. Aucune de ces commandes ne répare ni n'autorise la fabrication.

## Diagnostic morphologique distinct

Le programme construit aussi une ouverture morphologique de rayon 0,75 mm
(érosion puis dilatation), intersectée avec le volume initial. La différence
`opening-sensitive-features.stl` montre les détails sensibles à cette opération.
Elle inclut aussi des angles et des arêtes : **ce n'est pas une mesure des
parois inférieures à 1,5 mm**, ni un calcul de support LPBF, ni une proposition
de suppression de matière. Le diagnostic reste séparé du maillage aller-retour.

Les cordes normales échantillonnées du contre-contrôle Python ne donnent pas
non plus une borne continue d'épaisseur minimale. Les résultats orientent la
reconstruction locale ultérieure ; aucun lissage global, nouvelle enveloppe,
galerie d'huile ou surface fonctionnelle n'est imposé sans zone autorisée.

## Livraison et limites

Le reçu de chaque exécution lie l'entrée et les sorties par SHA256, indique la
résolution, les temps et la mémoire du processus, et garde les autorisations
de fabrication fausses. Un échec écrit `FAILED.json` ; un ancien dossier de
sortie n'est jamais écrasé. Une exécution réussie ne constitue ni CFD/CHT, ni
calcul de résistance, ni simulation d'impression de cette culasse.

L'image publiable ne contient que le logiciel et des témoins synthétiques.
Le STEP, son STL, les variantes dérivées et les vues restent privés. La
publication d'un digest, son téléchargement anonyme exact, le smoke x86 et
les contrôles SSH sont requis avant la location ; la durée et le coût sont
bornés par le manifeste et un garde externe de destruction.
