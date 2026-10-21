# Encodages ponctuels couverts — grande zone 000

Les **17 384 événements** du recensement original ont tous un témoin encodé
non nul dans le même groupe, le même NPZ et la même couche. Le contrôle réel
termine les **1 034 hauteurs** en 361,672 s ; le superviseur collecte le code
réel 0 et le groupe fermé en 362,088 s. Les 24 fichiers liés restent inchangés.
Root a ensuite recalculé les 17 384 cellules d'arrondi et vérifié de nouveau
les témoins rationnels, les identités et les totaux des 198 faces concernées.

Le maillage original `c351989c…`, ses sommets, ses faces et ses attributs de
scan restent intacts. Les 87 groupes concernés font partie de la partition
authentique des 337 groupes. La recherche emploie les boîtes exactes des
triangles sources, puis les coupes rationnelles des candidats : 2 111 987
recoupes de candidats, sans grille ni marge géométrique.

## Règle et helper

`closed_encoded_point_coverage_v1.py` reçoit des coupes Q **déjà liées par
l'appelant** au NPZ, à sa partition complète, aux attributs et au calendrier.
Il conserve toutes les coupes exactes. Si deux extrémités s'arrondissent au
même point P, il vérifie la cellule convexe d'arrondi au plus proche pair et
exige un vecteur encodé non nul du même propriétaire contenant P exactement.
Sinon il refuse. Un autre point nul ne sert jamais de témoin.

Le résultat distingue les coupes rationnelles complètes, les encodages non
nuls et les sources de ces seuls encodages. Les faces réduites à un point ne
transmettent aucune ancre à leur témoin. Les contacts et les graphes doivent
être recalculés séparément sur les deux représentations.

La fonction du helper est identique par AST à l'original testé `59523be9…` ;
seuls les chemins vers les deux autorités copiées dans `reference/` changent.
Ces autorités sont conservées à l'octet. Leurs anciens points d'entrée ne sont
pas des commandes de reproduction de cette capsule.

## Vérifier la capsule

Avec Python 3.10, sans dépendance ni runtime AM :

```sh
python3 -B CHEMIN/process-point-encoding-20261017/selfcheck.py
python3 -B CHEMIN/process-point-encoding-20261017/verify.py
```

Les treize tests couvrent notamment la couverture fermée, les mauvaises
identités, le refus des points isolés, les coupes Q distinctes partageant un
encodage et la provenance non nulle. Le vérificateur relit les empreintes et
les 17 384 preuves compressées sans perte ; il recalcule leurs cellules et
leurs inclusions exactes. Il ne recalcule pas les 25 951 937 coupes non nulles
du recensement original ni l'appartenance des coupes témoins aux triangles.
Cette dernière vérification a été exécutée par le diagnostic lié aux NPZ.

Les reçus et les sources historiques du diagnostic sont sous `evidence/`.
Ils conservent leurs chemins d'exécution originaux. Le fichier JSONL de
29 400 326 octets est compressé sans perte ; son empreinte décompressée reste
`7a354547e45f637e3287b5afb9f5d5aacf3225a8ded791aa69e1505b878ca9be`.

Cette capsule prépare la nouvelle règle. Elle n'est pas encore intégrée à la
factory des sept zones et ne donne aucune admission de contacts, de graphes
d'exposition ou de préparation globale. Les contrôles stricts historiques
restent inchangés. La [planche explicative](../progress-figures-20261016/encoded-point-coverage-20261017/README.md)
conserve son diagnostic antérieur, limité à la peau 13 et à ses 703 événements.
