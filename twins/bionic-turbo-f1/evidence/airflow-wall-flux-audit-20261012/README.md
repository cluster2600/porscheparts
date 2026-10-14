# Audit des flux aux murs et localisation de la dérive

Cette phase reproduit et publie les deux lectures exploratoires annoncées
après #191. Aucun nouveau maillage ou solveur n'est lancé. Les entrées,
champs, journaux et reçus des cas terminés 044 et 051 sont inchangés ;
chaque lecteur vérifie toutes les empreintes du reçu avant son analyse.
Les deux relances des lecteurs reproduisent exactement leurs JSON initiaux.

## Flux relatif et reconstruction dans le repère fixe

Les 928 faces du patch `walls` sont relues avec leurs propriétaires ;
464 appartiennent à des cellules MRF. Les centres et vecteurs aires sont
calculés par la formule polygonale native déjà testée. La vitesse de
rotation, son axe et son origine viennent du dictionnaire natif. Le code
refuse un autre axe, une autre origine ou l'absence de `nonRotatingPatches
(walls)`. Les dimensions des champs rho et phi sont vérifiées. Le lecteur
de listes scalaires contient un contrôle positif et refuse une liste tronquée.

La [conversion native v2406](https://gitlab.com/openfoam/core/openfoam/-/raw/OpenFOAM-v2406/src/finiteVolume/cfdTools/general/MRF/MRFZoneTemplates.C)
traite aussi les faces de parois non tournantes dont le propriétaire est
MRF. Pour ces faces, le diagnostic reconstruit :

`phi_fixed_diagnostic = phi_relative + rho_final * ((omega × Cf) · Sf)`.

Le terme de rotation est nul pour les propriétaires hors zone. Ce calcul
n'assimile pas le flux relatif à de l'air traversant physiquement la paroi.

| Diagnostic sur toutes les faces murs | 044 | 051 |
|---|---:|---:|
| Maximum absolu de phi relatif, kg/s | 4,041015765e-6 | 4,041015765e-6 |
| Somme des valeurs absolues de phi relatif, kg/s | 3,233274422e-4 | 3,233274421e-4 |
| Maximum absolu reconstruit avec rho final, kg/s | 4,235164736e-21 | 3,388131789e-21 |
| Somme absolue reconstruite avec rho final, kg/s | 8,759305020e-20 | 9,276789211e-20 |

La compensation est voisine de la précision d'écriture dans les deux cas.
Elle ne démontre pas que les flux étaient corrects à chaque assemblage :
[rhoPimpleFoam v2406](https://gitlab.com/openfoam/core/openfoam/-/raw/OpenFOAM-v2406/applications/solvers/compressible/rhoPimpleFoam/rhoPimpleFoam.C)
écrit rho après les corrections de pression et sa mise à jour thermodynamique.
La densité utilisée par la matrice n'est pas enregistrée séparément ici.
Le diagnostic ne mesure donc ni le résidu matriciel absolu, ni un défaut de
masse temporel complet. Les URL et SHA des sources consultées sont conservés ;
aucun code natif n'est modifié.

## Localisation indépendante du maximum de vitesse

Le second lecteur relit U final, recherche son maximum de norme, puis
retrouve les faces frontières de cette cellule via owner/neighbour. Il ne
réutilise pas une position dessinée ou un label supposé.

Dans les deux cas, le maximum est dans la cellule **9366**, adjacente à la
face frontière **26601**. Les quatre sommets sont sauvegardés dans le JSON :
leurs coordonnées y valent exactement zéro et leurs z vont de 6,75 à
6,8 mm. C'est la coupe angulaire synthétique du secteur, pas une paroi du
turbo réel. Les vitesses maximales restent 4,5028331e-5 m/s (044) et
3,7743604e-5 m/s (051), donc les deux rejets au repos restent inchangés.

Cette coïncidence localise le symptôme sans prouver une cause unique.
Elle ne justifie ni de retirer des parois physiques, ni d'exclure tout le
stator de MRF. Le témoin périodique 048 conserve un autre problème aux limites.

## Conservation et prochaine vérification

Les petits scripts et rapports sont conservés directement dans Git. Aucun
nouveau gros payload n'est créé : les champs lus restent dans les archives
[044](https://github.com/cluster2600/porscheparts/releases/tag/bionic-turbo-directed-sector-2026-10-12)
et [051](https://github.com/cluster2600/porscheparts/releases/tag/bionic-turbo-wall-pressure-2026-10-12),
avec leurs inventaires et empreintes publiés. Les reçus précis des deux cas
sont identifiés dans chaque rapport. Les preuves épinglées antérieures
restent intactes.

Avant de changer une recette, il faut distinguer le flux au stade de la
correction de pression, le résidu absolu de la matrice et les résidus
normalisés imprimés. Cette phase ne les mesure pas. Ne pas lancer un
balayage de tolérances ou de pas sur la base de ces seuls diagnostics.
Le maillage réel 033 reste rejeté : préserver sa correction roue–écrou et
traiter sa qualité, la tangence MRF et le bilan par cellule. Aucun débit
maximal, gain de puissance ou jumeau numérique calibré n'est validé.

Le lecteur `read_wall_flux_v2.py` corrige uniquement la formulation de portée
du rapport exploratoire : la densité d'assemblage n'est pas enregistrée
séparément, on ne démontre pas qu'elle diffère de rho final. Les valeurs
calculées sont strictement identiques ; le premier lecteur et son rapport
restent conservés.
