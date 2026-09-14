# F54 — attribution CAO des faibles épaisseurs et simplification locale

## Vérification des rayons sur les faces CAO

`verify_wall_rays_occt_f54.py` confronte les 42 sondes faibles du contrôle
par rayon sur le STL 4V aux faces rognées du STEP F53 corrigé. Le hash du
STEP et celui des sondes sont contrôlés. Le segment entre intersections
est retenu seulement si son milieu est intérieur au solide et si l'entrée
est à moins de 0,05 unité du scan de la sonde.

Résultat : 37 trajets internes sous 1,5 unité du scan, cinq sondes non
résolues. Parmi les 37, 32 relient des faces partageant une arête. Cela
localise des zones d'arête/raccord, sans démontrer qu'elles sont acceptables
ni qu'il s'agit de faux positifs. Les cinq autres sondes concernent quatre
paires distinctes de surfaces BSpline non adjacentes, avec des trajets
compris entre 0,753 et 1,428 unité du scan. Le contrôle n'est pas exhaustif.

Un test natif sur un solide synthétique d'épaisseur unitaire récupère
exactement cette épaisseur, reconnaît les faces opposées non adjacentes
et refuse un rayon dirigé vers l'extérieur. Ce test valide ces chemins
du logiciel, pas les caractéristiques mécaniques de la culasse.

## Essai de modification des huit faces

`offset_local_wall_faces_f54.py` sélectionne les huit faces à partir du
rapport d'attribution lié au STEP exact. Sur une copie privée, il demande
un décalage sortant de 0,5 unité du scan uniquement sur ces faces BSpline.
Le premier essai OCCT échoue avec `BRepOffset_MixedConnectivity`. Aucun
STEP modifié n'est obtenu ; aucune paroi n'est déclarée corrigée. Un second
mode utilisant les raccords par intersection est essayé séparément.

Le second mode termine sur la même erreur `BRepOffset_MixedConnectivity`.
Les deux tentatives sont refusées. Une reconstruction des raccords locaux
est nécessaire avant de pouvoir retenir une modification des parois.

## Simplification pour le maillage

`unify_same_domain_f54.py` utilise `ShapeUpgrade_UnifySameDomain` en mode
entrée protégée, tolérance linéaire `1e-7`, sans concaténation des splines.
Sur la 4V, le nombre de faces passe de 4 929 à 4 454, celui des arêtes de
10 222 à 9 403. Après export/réimport, BRepCheck est valide et aucun défaut
de courbe paramétrique n'est détecté. Le solide reste fermé et manifold.

STEP candidat : `825169c8c361b59176921796ed3e5b3ccd7b6f600c4baabf04e628bfee5d8e7a`.
Variation relative de volume : `-1,51e-9` ; variation maximale des bornes :
`4,27e-14` unité du scan. Ces métriques ne remplacent pas une carte de
déviation. Audit BOP complet et nouveau maillage volumique sont lancés
séparément. Le candidat ne remplace pas le maître validé tant que ces
contrôles et la comparaison des surfaces restent incomplets.

Le maillage volumique termine avec 1 894 579 tétraèdres, aucun élément
inversé, mais **1 050 éléments sous `minSICN=0,1`** et un minimum
`1,81e-6`. Le nombre est légèrement inférieur aux 1 086 de F50, mais le
minimum est plus faible. La génération réussie ne satisfait donc pas le
critère strict : maillage refusé, aucune amélioration suffisante revendiquée.

L'audit BOP complet du STEP simplifié termine ensuite sans défaut signalé,
avec BRepCheck valide. Ce succès d'intégrité ne change pas le refus du
maillage ni l'absence de correction des épaisseurs.

Tous les fichiers géométriques et indices de faces restent privés. Aucun
de ces essais n'autorise une fabrication, un montage ou un démarrage.
