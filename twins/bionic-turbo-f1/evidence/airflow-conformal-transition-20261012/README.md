# Raccord conforme sur une couronne synthétique — 057 à 059

Le raccord en trois prismes par secteur passe l'admission native dans 058.
Il remplace les faces coplanaires distinctes du raccord grossier/fin 056
par des cellules conformes. Ce nouveau domaine ne reproduit pas les parois
038/056 et ne contient aucune pièce, pale ou entrée/sortie du turbo.

La section est homothétique : R(z) = 32 mm + 0,4 (z − 6 mm), entre z = 6
et 7 mm, dix intervalles. Les trois rayons sont 63/64 R, R et 33/32 R ;
128 secteurs côté intérieur et interface, 256 côté extérieur. Ces nombres
définissent un témoin synthétique, pas des dimensions certifiées du passage
rotor/stator. Le secteur tournant contient seulement les 1 280 hexaèdres
intérieurs. Les 3 840 prismes de transition sont dans la zone fixe : ce
contrôle ne qualifie donc pas des prismes adaptés autour des pales en MRF.

Le premier montage 057 termine avec code 134, sans OOM, avant tout
maillage final. Le dictionnaire déclarait les fermetures triangulaires
alors que la topologie des blocs attendait encore des quadrilatères avec
un sommet répété. 058 corrige uniquement cette déclaration dans une nouvelle
source et un nouveau cas. blockMesh produit ensuite les prismes et élimine
les faces réduites. L'échec initial est conservé, jamais remplacé.

058 contient 5 632 points, 15 872 faces et 5 120 cellules, une région
fluide. Il passe checkMesh -allTopology -allGeometry : déterminant minimal
0,007600852357723562, non-orthogonalité maximale 22,2105°, aucune concavité.
Les seuils natifs sont inchangés. L'exécution prend 1,748 s, code zéro.

Le lecteur indépendant apparie tous les sommets construits aux points
natifs à 8,717e-18 m près, retrouve exactement les 4 864 faces de frontière
et les 1 280 quadrilatères MRF, et vérifie l'annulation de toutes les arêtes
orientées par cellule. Tous les volumes sont positifs. Le volume natif
3,086839304608924e-7 m³ concorde avec l'intégrale analytique entre les deux
polygones homothétiques, 3,086839304608921e-7 m³.

La planéité maximale des faces vaut 1,121e-17 m. La normale géométrique de
rotation de l'interface est au plus 2,8635e-12 m/s ; le bilan maximal de
flux de repère par cellule vaut 3,7269e-20 m³/s. Ce ne sont pas des débits
d'air. Les diagnostics géométriques ne prouvent ni le repos ni la
stabilité d'une perturbation.

059 reprend le maillage 058 et les équations, pas de 0,1 µs, tolérances,
conditions initiales et murs fixes du témoin 026. Un patch empty de zéro
face, créé par blockMesh, est explicitement déclaré dans p/T/U. Aucun
patch réel n'est changé. Les critères antérieurs restent 0,001 Pa,
1e-6 K et 1e-8 m/s. Le contrôle couvre 200 pas, 20 µs, en local et avec
une limite de 1 200 s. Le calcul termine en 181,148 s, code zéro sans OOM. Les 200 pas
respectent les critères : erreur p maximale 6,1118e-10 Pa, T 9,9476e-12 K,
vitesse maximale sur tout l’historique 4,1727e-12 m/s. Les champs natifs
p/T/U des 5 120 cellules sont relus, finis et hachés ; le maximum du seul
champ U final vaut 4,1694e-12 m/s. Courant maximal 0,0213419.

Les 800 résolutions de pression atteignent le plafond de 1 000 itérations.
Le repos est respecté, mais la convergence linéaire n’est pas qualifiée.
Aucune modification de solveur ou de tolérance ne masque cette limite.

Aucune indépendance au maillage ou au temps, stabilité de perturbation,
performance du turbo ni calibration physique n'est établie. Le raccord
reste à certifier dans les bornes du vrai passage, avec ses parois,
fermetures, coquilles et séparation roue–écrou inchangées.

[Archive native](https://github.com/cluster2600/porscheparts/releases/tag/bionic-turbo-conformal-transition-2026-10-12) : 75 fichiers, 1464945 octets ; SHA-256 `b0704cae64157f57287416f2be4f09a914d04382439a0aef850171ab1f1c9937`. Tous les payloads ont été relus localement. Les tailles et empreintes des cinq actifs distants sont vérifiées séparément, sans second téléchargement intégral.
