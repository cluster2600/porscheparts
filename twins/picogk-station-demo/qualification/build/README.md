# Image construite et témoins CPU — 28 septembre 2026

Ces fichiers proviennent de l'image assemblée sur **Kali2**, avant toute
qualification sur GPU Vast. Ils prouvent le fonctionnement logiciel décrit
ci-dessous ; ils n'autorisent aucune fabrication métal.

L'image locale finale porte le tag
`ghcr.io/cluster2600/3dprinting993-picogk-station:station-20260928-ef4b546991d6`
et l'identifiant de configuration
`sha256:4893cbb406c8b88ec9dcaec201ebfbe42f68902e1987c5d65a2f556ee390a603`.
Cet identifiant local **n'est pas un digest de manifeste du registre** et ne
prouve pas la publication. [final-image.json](final-image.json) consigne la
taille annoncée de 36 938 062 301 octets, les empreintes des couches, les seuls
ports déclarés `22/tcp` et `47998/udp`, et la licence globale `NOASSERTION`.
Les licences de chaque composant restent applicables ; la
[notice NVIDIA](NVIDIA-NOTICE.txt) accompagne le runtime.

La normalisation a retiré le port hérité `8000/tcp` sans modifier les couches.
Le [journal](normalize-disk.log) vérifie cette égalité. Une dernière opération
de métadonnées a corrigé uniquement le champ de licence, toujours sans nouvelle
couche. Le normaliseur utilise une archive temporaire sur disque, hors `/tmp`,
et demande une réserve de trois fois la taille annoncée de l'image.

| Contrôle CPU | Résultat observé |
|---|---|
| PicoGK 2.3.0, runtime natif ABI 26.2 et .NET 9.0.317 | Volume, offset et aller-retour STL passent ; témoin natif de 3 660 triangles, erreur relative de volume 0,00596707 |
| Géométrie Python | Boîte fermée, volume, distances intérieur/extérieur, rayon et composantes passent |
| build123d | Export STEP puis réimport ; volume témoin 6 000 mm³ |
| FreeCAD 1.0.2 | Import natif et volume de boîte passent |
| CalculiX et Gmsh | Exécutables présents ; aucun calcul physique validé ici |
| OVRTX 0.3.0.312915 | Installation/import vérifiés ; rendu GPU non testé |
| Compte `station-worker` | Connexion SSH par clé, UID/GID 10002, puis démonstrateur exécuté avec succès |

Les journaux [CPU](qualified-cpu-v2.log) et
[SSH du compte de travail](worker-ssh-check.log) sont conservés. Les versions
Python résolues sont dans [geometry-resolved.txt](geometry-resolved.txt) ;
les références PicoGK et l'empreinte native figurent dans
[sources.lock](sources.lock) et [native-library.sha256](native-library.sha256).

Le démonstrateur produit un témoin en forme de support et deux coupons à partir
de [Program.cs](csharp-source/Program.cs) avec son
[projet C#](csharp-source/StationDemo.csproj). La taille de voxel est 0,25 mm.
Les volumes ci-dessous sont des valeurs numériques du modèle voxelisé,
sans mesure physique ni preuve dimensionnelle d'une pièce fabriquée.

| Géométrie | Triangles | Volume calculé (mm³) |
|---|---:|---:|
| [Support témoin](station-demo-cpu/geometry/bracket-witness.stl) | 54 496 | 1 743,2296 |
| [Coupon fin](station-demo-cpu/geometry/coupon-thin.stl) | 8 348 | 154,33018 |
| [Coupon épais](station-demo-cpu/geometry/coupon-thick.stl) | 19 964 | 677,1537 |

L'[assemblage USD](station-demo-cpu/station-assembly.usda) est conservé avec
les rapports géométriques, métriques de couches et cartes de procédé. Les trois
surfaces sont fermées et entrent dans l'enveloppe nominale de la machine de
référence EOS M 290 selon le contrôle logiciel. L'orientation reste candidate ;
les supports, le passage du recoater, la corrélation du procédé et les coupons
physiques restent non validés. Les rapports maintiennent explicitement
`metal_print_authorized=false`.

Un témoin **CAO paramétrique distinct** est également livré : cylindre FreeCAD
`Part::Cylinder`, rayon 3 mm et hauteur 20 mm. Son
[document éditable](cad-coupon/cad-coupon.FCStd), son
[STEP](cad-coupon/cad-coupon.step) et sa
[source Python](cad-coupon/source.py) sont conservés. La construction a vérifié
la réouverture du document, les paramètres natifs et le volume `180π` mm³ dans
le document et le STEP, avec une tolérance numérique de `1e-6` mm³. Ce témoin
ne constitue pas une reconstruction CAO exacte des trois maillages PicoGK.

[completed.json](station-demo-cpu/completed.json) déclare
`software_pipeline_completed`, vérifie 21 artefacts et maintient
`manufacturing_authorized=false` et `physical_coupon_tested=false`.
Les empreintes de ces 21 artefacts et de la source C# ont été revérifiées après
rapatriement. [SHA256SUMS](SHA256SUMS) couvre les 35 fichiers rapatriés : environ
8 Mo au total, aucun fichier de plus de 10 Mo. La revue limitée à ces artefacts
n'a trouvé aucun motif de clé privée ou de jeton ; les champs d'auteur et de
société du document FreeCAD sont vides. Aucun cache ni archive d'image n'est
inclus.

Restent à prouver sur la station attribuée : ressources réellement disponibles,
Vulkan/NVENC, requête Qwen et outil OpenClaw, rendu OVRTX sur GPU 3, interaction
et reconnexion Kit sur GPU 2, puis coexistence pendant 30 minutes. La présence
de ces fichiers ne constitue pas cette qualification.
