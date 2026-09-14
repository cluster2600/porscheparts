# Raccord local PicoGK — témoin avant toute culasse

Ce module teste une **fermeture morphologique locale** de rayon exploratoire
1 unité, via `voxFillet(1)` (offset +1 puis −1). Il ne crée ni congé B-Rep
exact, ni preuve G1, ni corps M64, ni validation thermique ou de fabrication.
Le masque conserve le volume de gaz initial et n'autorise qu'un ajout local.
Il ne suffit pas à établir la protection : les occupations sont comparées
après tous les booléens. Correction de lecture du runtime : `RebuildGrid` est
appelée mais désactivée par un `return` inconditionnel dans la révision
épinglée ; aucune reconstruction effective ne doit lui être attribuée.

`criteria.json` fixe les écrans avant exécution : zéro changement hors ROI et
aux interfaces protégées, zéro perte du gaz initial et zéro contact de l'ajout
avec le bord du masque, pour les deux conventions `<0` et `<=0`. Le contrôle
porte sur tous les nœuds de la grille native englobante, pas sur une surface
continue entre ces nœuds. La comparaison de résolutions 0,2/0,1 serait un écran
de stabilité, pas une preuve de convergence asymptotique.

## Résultat du 8 septembre 2026

Le témoin constitué de deux cylindres coaxiaux étagés a été exécuté à 0,2,
sur le runtime x86 épinglé, 2 CPU / 4 Gio et timeout 300 s. Il a terminé en
6,233 s avec un pic processus de 129 445 888 octets. Sur 1 157 625 nœuds,
828 passent de l'extérieur au gaz ; les quatre compteurs de protection
restent nuls pour les deux conventions de zéro.

**Le lot est néanmoins arrêté au témoin**, avant 0,1 et avant la géométrie
privée. Le contre-contrôle des STL bruts trouve 496 triangles d'aire exactement
nulle dans le candidat et 8 dans l'ajout ; ces maillages ne sont pas des
2-variétés fermées. Il n'y a pas d'arête d'incidence un, mais des incidences
supérieures à deux : cela ne prouve donc pas la présence de trous physiques.
Les nombreuses composantes contenant ces triangles dégénérés ne sont pas
interprétées comme des cavités. Aucun triangle n'est supprimé par l'auditeur.

Le résidu entre différence des volumes globaux et volume de l'ajout booléen
est 0,860474131 unité³, non expliqué. Les volumes sont intégrés depuis les
triangles orientés, non repris de `CalculateProperties` qui remaille le champ.
Les STL et les reçus sont préservés ; les champs intermédiaires de cette passe
n'ont pas été sérialisés en VDB. Une reprise exigerait une nouvelle exécution
tracée, pas une prétendue réutilisation de champs inexistants.

## Fichiers et exécution

- `Program.cs` accepte uniquement `--witness` tant que ce garde est en échec.
- `criteria.json` : critères et source de la future admission, non utilisée.
- `audit_mesh.py` : indexe uniquement les coordonnées de sommets exactement
  identiques puis contrôle les triangles originaux, sans arrondi ou réparation.
- `tests/test_picogk_local_junction.py` : contrats préenregistrés et régression
  de l'auditeur avec un triangle nul et une orientation inversée.

Dans l'image existante (pas de téléchargement ni nouvelle location) :

```sh
dotnet build LocalJunction.csproj -c Release -o bin \
  -p:UpstreamRoot=/upstream -p:GeneratePackageOnBuild=false --ignore-failed-sources
timeout --signal=TERM --kill-after=10 300 \
  dotnet bin/LocalJunction.dll --witness criteria.json NOUVEAU_DOSSIER 0.2
```

Le réseau était désactivé. La compilation a réussi avec un avertissement
NU1900 : la consultation des vulnérabilités NuGet était indisponible, pas les
packages déjà présents. Un exit 0 natif signifie uniquement que les compteurs
d'occupation passent. L'audit indépendant retourne 3 et bloque la suite.

## Compléments indépendants sans écraser les reçus initiaux

`audit_surface_topology.py` contrôle la connexité par toutes les incidences,
les liens de sommets et la collinéarité par arithmétique dyadique entière,
sans réparation. Les trois STL forment chacun une seule composante ; le
candidat reste rejeté avec 552 liens invalides. Les anciens nombres de groupes
issus de `Trimesh.split` ne sont pas un inventaire de cavités.

`exact_zero_countertrial.py` retire seulement les produits vectoriels float64
nuls dans une copie en mémoire, sans écrire de STL. Il reste 340 arêtes
non-manifold sur le candidat : ce contre-essai est lui aussi rejeté.

Le libellé historique `raw_native_SDF_units="voxel_units_sign_only"` est
incorrect. Pour ce témoin, `GetZSlice` recopie les valeurs dans les unités
géométriques du callback, sans conversion. Les compteurs de signes restent
valides ; aucun résultat de distance continue n'était établi par ce reçu.
Le programme et ses reçus d'exécution restent inchangés pour traçabilité.

Références épinglées : [PicoGK, opération de fermeture](https://github.com/leap71/PicoGK/blob/0e6cf6b6f4993ec16dbcd72d8f27f26b999980f3/Base/Voxels.cs#L613-L643)
et [kernel, booléens, slices et reconstruction désactivée](https://github.com/leap71/PicoGKRuntime/blob/0f26321c18ed878a7820ef769c38fd5d49d39242/Source/PicoGKVdbVoxels.h).
