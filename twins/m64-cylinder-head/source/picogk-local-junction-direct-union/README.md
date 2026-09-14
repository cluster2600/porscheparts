# Témoin local — union directe, état rejeté

Cette variante conserve les sources et résultats de la première formulation.
Elle construit `A ∪ (C ∩ R)`, avec `C = fermeture(A)` et un rayon exploratoire
de 1 unité. L'identité avec `A ∪ ((C \ A) ∩ R)` vaut pour tous les ensembles,
sans supposer `C ⊇ A`. Elle n'implique pas que leurs champs discrets, ni leurs
maillages extraits, soient identiques. L'ajout `(C \ A) ∩ R` est conservé comme
diagnostic : il ne participe plus à la construction du candidat.

Seul le témoin synthétique de deux cylindres étagés a été exécuté au pas 0,2,
sur Kali, avec 2 CPU / 4 Gio et une limite de 300 s. Ni culasse privée,
ni second pas 0,1, ni nouveau B-Rep n'ont été traités.

## Résultat conservé

Le calcul natif a terminé en 4,737 s ; pic mémoire processus : 179 163 136
octets. Sur 1 157 625 nœuds natifs comparables, les compteurs de changement
d'occupation hors ROI, aux protections, de perte du gaz initial et de contact
de l'ajout avec le bord du masque sont tous nuls, pour `<0` et `<=0`.
Les nœuds modifiés sont respectivement 1 944 et 828. Ce sont des résultats
de grille, pas une preuve d'invariance d'une surface continue.

L'audit des valeurs du champ détecte **72 changements hors ROI**, de maximum
brut **0,0012884736061096191 unité de longueur native**. Aucun changement de
valeur n'est détecté aux protections échantillonnées. L'invariance du champ
hors ROI n'est donc pas établie, malgré les signes inchangés.

| Maillage brut | Triangles | Aire exactement nulle | Arêtes d'incidence > 2 |
|---|---:|---:|---:|
| Avant | 89 708 | 0 | 0 |
| Après | 90 028 | 16 | 16 |
| Ajout diagnostique | 4 464 | 8 | 8 |

**Le témoin reste rejeté avant toute culasse.** L'auditeur réindexe uniquement
les coordonnées exactement identiques, conserve toutes les faces et désactive
explicitement la réparation lors de la recherche de composantes
(`repair=False`). Ces composantes ne sont pas interprétées comme des cavités.
Aucune arête d'incidence un ne permet ici de conclure à des trous physiques.
Le résidu entre différence des volumes triangulaires globaux et volume de
l'ajout diagnostique est **3,618739229847031 unité³**, non expliqué. Les trois
isosurfaces sont discrétisées séparément ; ce résidu reste visible et n'est
pas utilisé comme preuve de conservation.

## Erratum obligatoire pour lire le reçu

Le [fichier d'erratum](interpretation-erratum.json) est lié aux empreintes
exactes du programme exécuté et de ses reçus, qui ne sont pas réécrits.
Les champs nommés `native_voxel_units` et les conversions `times_h` du reçu
initial sont mal libellés. Dans ce runtime, `RenderImplicit` reçoit les
coordonnées monde via `vecToMM`, stocke les distances du callback sans division
par le pas, puis `GetZSlice` copie les valeurs directement. L'ABI C et le mode
C# `SignedDistance` n'ajoutent aucune conversion. **Il ne faut pas multiplier
le delta par 0,2.** Pour ce témoin synthétique, ces longueurs sont les unités
monde nommées MM par PicoGK ; cela ne certifie pas l'échelle du scan privé.
Ce delta de champ n'est pas une borne de déplacement de la surface.

Une autre correction concerne l'explication du runtime : les booléens
appellent `RebuildGrid`, mais la version épinglée retourne immédiatement
aux lignes 773–776. Elle n'exécute donc pas sa reconstruction. Cette dernière
ne peut pas être présentée comme la cause démontrée des défauts observés.
Les [sources exactes et lignes contrôlées](interpretation-erratum.json)
permettent de vérifier ces deux corrections.

## Champs et reproductibilité

Six champs natifs sont enregistrés dans `native-fields.vdb` : `original_A`,
`closing_C`, `ROI_R`, `C_intersect_R`, `direct_candidate`, `diagnostic_added`.
La relecture vérifie les noms, le nombre, l'échelle de métadonnées et l'accès
à des champs non vides. **L'identité des valeurs avant/après sérialisation
n'a pas été contrôlée.**

`Program.cs` est figé dans sa version exécutée pour assurer la provenance ;
ses anciennes étiquettes d'unités exigent l'erratum. `criteria.json` contient
les gardes préenregistrés, `audit_mesh.py` l'audit brut, et
`tests/test_picogk_direct_union_junction.py` les tests de contrat et d'identité
ensembliste. Un exit 0 natif signifie uniquement réussite des gardes
d'occupation, avec SDF et maillage encore à examiner. L'audit indépendant
a retourné 3 (`rejected_raw_mesh_screen`).

Ce témoin ne prouve ni raccord G1, ni performance fluidique/thermique,
ni imprimabilité. Toute extraction nettoyée éventuelle doit rester un
contre-essai séparé, sans effacer le rejet du maillage brut.
