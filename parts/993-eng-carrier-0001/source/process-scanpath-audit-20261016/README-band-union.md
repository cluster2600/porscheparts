# Confinement dans la bande verticale intentionnelle

Sur une grille réelle de la région gauche, l’overlay GEOS de la bande ne contient
pas exactement son propre domaine libre D. Le même témoin rationnel refuse D et
le matériau R inchangé. Le test conserve ce refus ; aucune tolérance ne le masque.

`exact_band_union.py` contrôle directement R dans l’union des mêmes convexes
élémentaires que `vertical_contact_band`, avant leur overlay. Les coordonnées
IEEE des balayages verticaux de ±0,2 mm restent identiques. Le découpage à Z ≥ 0
se fait sur les fractions exactes, sans nouvel encodage du matériau.

La triangulation n’est pas supposée correcte : la somme exacte des chaînes de
triangles orientés positivement doit égaler la frontière complète du Polygon,
trous compris. Par les nombres d’enroulement, ces triangles partitionnent alors
le domaine sans manque ni recouvrement positif. Chaque triangle du matériau est
soit contenu dans un convexe attesté, soit partitionné par les droites des
primitives candidates avec le helper exact existant. La fermeture de cette union
finie couvre aussi toutes les frontières.

Le cas réel passe en 1,561 s : 102 triangles de matériau, 95 primitives et
12 partitions collectives. Les polygones, leurs SHA et le reçu sont conservés
dans `band-union-evidence/`. Les cinq tests couvrent aussi une ouverture véritable,
du matériau hors bande, du matériau sous le plateau et des triangulations
incomplètes ou dupliquées. La preuve a été relue indépendamment.

Cette preuve porte sur le matériau inchangé dans **l’union intentionnelle** ;
elle ne déclare pas que l’ancien Polygon GEOS le contient. Elle ne constitue
ni une admission des sept régions ni un audit des trajectoires exposées.

```sh
AM_PYTHON -B -m unittest discover -s tests -p test_carrier_exact_band_union.py -v
```
