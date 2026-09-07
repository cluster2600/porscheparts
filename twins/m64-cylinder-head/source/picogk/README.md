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
   produire la vue comparative et une section.

Le contre-contrôle Python nécessite `numpy`, `scipy`, `trimesh`, `rtree`,
`matplotlib` et `networkx` (construction des contours de coupe). Son
environnement est distinct du conteneur PicoGK .NET ; les versions réellement
utilisées doivent accompagner le reçu d'audit. Le rendu Matplotlib peut
présenter des défauts de tri de profondeur sur les faces coplanaires : une
vue opaque VTK permet de les distinguer de défauts géométriques.

L'import-export PicoGK remaille les surfaces : les maillages résultants ne
remplacent **pas** le maître B-Rep des interfaces et des portées usinées.
Une faible erreur volumique globale ne suffit pas à qualifier ces interfaces.

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
