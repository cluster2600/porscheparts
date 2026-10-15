# Piste native de subdivision radiale — non exécutée

L'inspection de blockMeshDict 063 vérifie 6 784 blocs hexaédriques fixes dont la
première arête est radiale, et 20 352 blocs prismatiques tournants. Tous utilisent
(1 1 1). Une nouvelle version pourrait étudier (2 1 1) uniquement dans les blocs
fixes, via blockMesh existant, afin de fournir une face radiale interne après
isolement du sous-domaine. Aucun dictionnaire n'a été changé, aucun cas préparé.

Cette piste doit prouver que les quadrilatères du raccord restent identiques,
que les subdivisions des fermetures couvrent exactement les faces parentes,
que toutes les faces sont partagées correctement et que les volumes, la zone et
la frontière sont conservés. Le domaine complet ET le sous-domaine isolé doivent
passer les contrôles natifs ; aucune admission n'est déduite de la seule lecture
du dictionnaire. Le témoin peut ensuite tester la protection sélective, avant
une quelconque projection des surfaces physiques ou protection du raffinement.
Les refus 071/072 et le déplacement MRF de 074 restent conservés.
