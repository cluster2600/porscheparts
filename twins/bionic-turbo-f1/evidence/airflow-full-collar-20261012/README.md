# Couronne complète positionnée par la preuve 062 — 063/064

063 construit une couronne à partir du profil 030 et des ratios géométriquement
vérifiés en 062, de z=-3,75 à 33 mm. Toutes les ruptures de pente sont conservées.
Les subdivisions affines limitent le pas axial à 0,8 mm, comme le fond 030. Le
stencil natif 060 est réutilisé, sans projection ni raffinement snappy.

Ce domaine ne représente pas le turbo complet : rotor et ports sont absents.
Les parois latérales et la fermeture avant sont des troncatures synthétiques
situées dans le fluide CFD. Les 512 faces arrière sont exactement à −3,75 mm,
couvertes par les anneaux de stator des deux surfaces sources. Le lecteur v2
vérifie explicitement la convexité avant d'exclure l'origine et de borner
chaque face par ses arêtes ; la première version est conservée.

Le maillage natif termine en 25,647 s, code zéro sans OOM, et passe Mesh OK :
27 136 cellules, 20 352 prismes tournants, 6 784 hexaèdres fixes, 27 648 points, 
81 920 faces et 6 784 quadrilatères MRF. Une région fluide, aucune concavité,
aucun petit déterminant ; minimum 0,038085656, non-orthogonalité maximale
47,817352 degrés. Les sources et le conteneur sont conservés.

La lecture indépendante vérifie tous les points contre 062, les parois,
l'interface, les types de cellules par zone, les chaînes d'arêtes fermées
et les volumes positifs. Volume 4,611377236219329e-6 m³ concordant avec
l'intégrale analytique par segments ; planéité maximale 1,44199e-17 m.
Normale géométrique de rotation MRF maximale 2,28795e-12 m/s et bilan
maximal par cellule tournante 1,49078e-19 m³/s. Ce ne sont pas des débits d'air.

064 reprend les équations, conditions initiales, pas 1e-7 s et critères de 061
pour 200 pas sur 20 µs. Le comparateur prouve que seuls six fichiers polyMesh
changent : toutes les entrées hors maillage et les critères sont identiques.
Les nouveaux rayons, la longueur et les parois empêchent d'interpréter ceci
comme une comparaison de performance à géométrie constante.

Le raccord au cœur adapté autour des pales, la séparation roue–écrou 033 et
les couches de paroi restent à construire et vérifier. Aucune performance
physique, indépendance au maillage, stabilité de perturbation ni calibration
n'est accordée par le seul maillage de cette couronne.

064 termine nativement avec code zéro, sans OOM, en 1 168,593 s, avant la
limite de 1 200 s. Les 200 pas atteignent 20 µs. Les seuils de repos sont
respectés : erreur maximale de pression 1,29512e-9 Pa, de température
1,23919e-11 K et vitesse maximale historique 2,94572e-12 m/s. Le maximum
du champ final de vitesse est 2,94512e-12 m/s ; Courant maximal 0,0859544.
Les 800 résolutions de pression atteignent 1 000 itérations : aucune
convergence linéaire n'est qualifiée.

Les champs p/T/U/rho sont relus sur les 27 136 cellules et phi sur les
60 544 faces internes. Tous sont finis, p/T/rho strictement positifs ;
tous les payloads natifs et entrées sont relus et hachés. phi est un flux
massique relatif au repère, pas un débit physique du turbo. Cette réussite
au repos ne démontre ni stabilité aux perturbations ni performance forcée.

L'[archive 063/064](https://github.com/cluster2600/porscheparts/releases/tag/bionic-turbo-full-collar-2026-10-12)
conserve 74 fichiers, 4 968 828 octets, SHA-256
`669b8820869e85d37926bdd643dc65aa73685557aff4a7a536ce0cedf13f4921`.
Tous les payloads sont relus localement. Les cinq actifs distants sont
vérifiés par tailles et SHA-256 GitHub, sans second téléchargement intégral.
Les deux conteneurs terminés restent conservés.
