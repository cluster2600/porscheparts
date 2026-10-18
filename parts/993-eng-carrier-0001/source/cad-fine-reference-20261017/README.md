# Référence CAD fine — capsule documentaire

Cette capsule conserve les sources et reçus **réellement exécutés** de la
référence OCP, indépendamment de la mesure globale CGAL encore séparée.
Les sept documents d'origine sont copiés à l'octet près ; leurs chemins et
empreintes figurent dans `copy-provenance.json`. Le NPZ est identifié par SHA
et taille dans `reference-identity.json`, sans duplication du fichier.

Le STEP retenu est `de0e55a3…`. Le runtime existant est OCP 7.9.3.1 / Python 3.10.11,
avec NumPy 2.0.2. L'appel OCP direct demande une déflexion absolue 0,01 mm,
angle 0,10 rad, sans parallélisme. Le critère 0,01 mm est celui de
`gmsh-criteria.json:37` ; l'angle vient du source CAD exécuté, ligne 36.
Le plan original contient les 1 350 empreintes de sources/inputs/runtime ; aucun de
ces fichiers runtime ni aucune archive n'est copié ici.

Résultat conservé : 68 744 sommets float64, 137 572 triangles int64, 240 faces CAD
entièrement triangulées, une composante par arêtes, fermeture/orientation
cohérentes et volume orienté exact positif. Les triangles d'aire exacte nulle
sont au nombre de 0. L'extraction et le roundtrip NPZ conservent les octets
float64/int64, sans passage par STL32 ni soudure par tolérance.
L'auto-intersection n'a pas été contrôlée par ce producteur.

Le vrai enfant a retourné 0 ; 8,746832 s murales pour l'appelant, 7,890711 s pour
l'enfant, pic RSS 560 988 160 octets. Le reçu atteste les entrées et fichiers
épinglés inchangés. Ces chiffres décrivent ce run ; ils ne prédisent pas le
coût d'une mesure de distance globale.

Le NPZ `c2aad5a8…` est une référence triangulée additionnelle. La déflexion
demandée n'est pas une borne globale démontrée du BREP. Aucun résultat CGAL,
seuil franchi ou admission globale n'est inclus dans cette capsule.

## Vérification documentaire hors environnement CAD

```sh
python3 -B /ABSOLUTE/PATH/TO/THIS/CAPSULE/verify_capsule.py
```

Ce contrôle stdlib vérifie les fichiers locaux et les liaisons entre reçus.
Il n'importe aucun runtime CAD et ne relance aucun calcul. Le manifeste est
relatif à la capsule. Son SHA est fourni avec la capsule afin de le vérifier
indépendamment.

`source/plan.json` est le **plan historique byte-identique**, avec ses chemins
producteur et sa sortie déjà occupée. Les fichiers `source/` documentent
l'exécution ; ils ne sont pas un nouveau lanceur portable autorisé.
Une future reproduction demanderait un nouveau plan explicite, les entrées
externes de mêmes SHA et le runtime correspondant, en conservant ces reçus.

La proposition d'image est dans `comparison-image-proposal.md`. Aucun rendu
de résultat absent n'est produit. OCCT reste sous LGPL-2.1 avec exception
OCCT : [source officielle 7.9.3](https://github.com/Open-Cascade-SAS/OCCT/blob/V7_9_3/src/BRepMesh/BRepMesh_IncrementalMesh.hxx).
