# Audit des volumes solides disponibles — 7 septembre 2026

## Verdict

Deux volumes tétraédriques de la géométrie de référence réelle existent, mais
**aucun des deux n'est qualifié pour valider la thermique ou la résistance de la
culasse**. Aucun volume trouvé dans les candidats F53/F54 inspectés n'est issu
directement du STEP F53 exact `700baea…`. Un maillage volumique n'est donc pas
manquant au sens informatique ; ce sont sa qualité, son rattachement démontré à
la CAO retenue et ses frontières physiques qui restent insuffisants.

Il ne s'agit pas des anciens calculs sur disque ou sur un tutoriel thermique.
Les fichiers audités sont les maillages privés de la reconstruction 4V, avec
leurs milliers de surfaces. Leur filiation au scan ne certifie pas les
interfaces M64 ni l'échelle absolue.

## Contrôles réellement exécutés sur Kali

L'outil [audit_solid_mesh.py](../../twins/m64-cylinder-head/audit_solid_mesh.py) lit
uniquement le MSH adressé par SHA-256, sous Gmsh **4.12.1**. Il recalcule les
volumes signés par `det(b-a, c-a, d-a)/6`, contrôle la connectivité de la frontière
des tétraèdres contre tous les triangles de surface stockés, recherche les faces
partagées par plus de deux tétraèdres et inventorie les groupes physiques.
Les empreintes MSH sont revérifiées après l'audit.

Exécution par candidat : conteneur sans réseau, limite 2 CPU / 4 Gio, délai
maximum 300 secondes, géométrie montée en lecture seule. Aucun remaillage,
changement de CAO, solveur physique ou dépense Vast. Les deux audits ont abouti
avec le code **2 attendu : échec du seuil de qualité du projet**.

| Contrôle | F53 optimisé | F54 fusion de faces coplanaires/co-surfaciques |
|---|---:|---:|
| Tétraèdres linéaires | 1 906 364 | 1 894 579 |
| Nœuds | 369 536 | 367 329 |
| Entités volumiques | 1 | 1 |
| Entités surfaciques | 4 929 | 4 454 |
| Tétraèdres inversés / de volume nul | 0 / 0 | 0 / 0 |
| Minimum minSICN | 0,00002480245 | 0,00000181255 |
| Tétraèdres de minSICN < 0,1 | **1 048** | **1 050** |
| Triangles frontières = triangles stockés | 253 078 = 253 078 | 252 416 = 252 416 |
| Triangles manquants / supplémentaires / dupliqués | 0 / 0 / 0 | 0 / 0 / 0 |
| Faces internes non-manifold détectées | 0 | 0 |
| Groupes physiques de surface / volume | **0 / 0** | **0 / 0** |

Le `minSICN` est la qualité signée par conditionnement inverse décrite par
[Gmsh](https://gmsh.info/doc/texinfo/gmsh.html#index-gmsh_002fmodel_002fmesh_002fgetElementQualities).
Le seuil **0,1 est le seuil existant du projet**, pas une norme générale ni une
preuve de convergence. L'absence d'inversion ne neutralise pas les très mauvais
éléments. L'accord exact des triangles porte sur la **connectivité discrète**,
pas sur la distance à la surface CAO, l'absence de recouvrement géométrique des
cellules ou la résolution des gradients physiques.

Rapports expurgés :
[F53](../../twins/m64-cylinder-head/evidence/f53-solid-mesh-audit-20260907.json),
[F54](../../twins/m64-cylinder-head/evidence/f54-solid-mesh-audit-20260907.json).
Aucun maillage, nœud ou coordonnée n'est publié.

## Filiation : ne pas confondre le numéro F53 et le STEP F53

Les empreintes des fichiers et leurs rapports de construction ont été relus
sur Kali. La chaîne observée est :

| Candidat | Géométrie réellement passée au mailleur | Chaîne de preuve |
|---|---|---|
| F53 optimisé `4f3dff…` | BREP natif F50 `10ff1a…` | BREP → MSH F50 `d1e8dc…` → optimisation intérieure F53 ; son rapport déclare les nœuds frontières inchangés à chaque étape |
| F54 `b68dc3…` | STEP F54 `825169…` | STEP F53 `700baea…` → fusion des mêmes domaines, 4 929 → 4 454 faces → MSH F54 |

Le champ ancien `native_BREP_sha256` du rapport de maillage F54 porte en réalité
l'empreinte du **STEP** F54, ce que confirme le fichier source. Il ne faut pas
déduire son format du nom de ce champ. Les anciens paramètres suffixés `_mm`
restent des conventions du candidat, pas une certification métrologique.

La reconstruction des p-curves F53 conserve presque les intégrales et l'emprise
3D ; la fusion F54 aussi. Ces écarts faibles ne constituent cependant ni une
identité des fichiers, ni une correspondance vérifiée des numéros de faces, ni
une preuve locale de conformité du maillage au STEP retenu.

Un contrôle supplémentaire de volume sur le STEP exact, avec
`BRepGProp.VolumeProperties_s` / OCP 7.9.3.1 sans recours à la triangulation,
donne **1 246 030,353585284 unités de scan³**. Les sommes des volumes des
tétraèdres valent respectivement **1 246 526,705216762** et
**1 246 539,5537188756**, soit **+0,039835 %** et **+0,040866 %**. Ces agrégats ne
définissent aucun seuil d'acceptation et ne détectent pas tous les écarts locaux.
La méthode d'intégration est documentée par
[Open CASCADE](https://occt3d.com/dev/doc/refman/html/class_b_rep_g_prop.html).

Les empreintes complètes et celles des rapports privés sont conservées dans
[le relevé de provenance](../../twins/m64-cylinder-head/evidence/solid-mesh-provenance-20260907.json).

## Frontières et prochain maillage réellement utilisable

Les **4 929 entités Gmsh de F53 ne sont pas une preuve** de correspondance avec
les 4 929 faces OCCT du STEP exact. Aucune association vérifiée n'est présente
dans le MSH et aucun groupe physique n'y nomme chambre, conduits, contacts ou
refroidissement. Les propositions de provenance des faces établies dans
[l'audit thermique](M64_THERMAL_FACE_PROPOSALS.md) ne sont ni des CL validées, ni
des étiquettes transférables par simple numéro d'entité.

Le meilleur candidat de **diagnostic** est F53 optimisé : minimum de qualité
moins mauvais, moins d'éléments sous le seuil et pas de fusion supplémentaire
des faces. Il n'est pas promu en maillage de calcul accepté.

La prochaine étape de production du maillage doit donc :

1. Figer l'empreinte de la CAO corrigée retenue et résoudre les ambiguïtés des
   contacts/frontières. Si les raccords changent, invalider les anciennes
   correspondances ; ne pas recycler silencieusement les groupes de F53.
2. Mailler ce solide précis, avec une correspondance explicite CAO → surfaces
   maillées, puis conserver des groupes physiques distincts. Vérifier à nouveau
   les écarts locaux à la CAO, les zones minces et la fermeture discrète.
3. Faire passer les contrôles de qualité et les études de convergence avant
   l'emploi des charges et des propriétés matériau à chaud. L'échelle, les
   interfaces M64 et les conditions de fonctionnement restent des entrées à
   justifier, pas des corrections que le maillage peut inventer.

Tests unitaires : **12 réussis** (tétraèdre analytique, inversion, dégénérescence,
connectivité invalide, frontière complète/incomplète/dupliquée/non-manifold,
face interne, qualité non finie et distinction positivité/seuil de qualité).
Cet audit n'exécute ni CHT, ni contraintes, ni fatigue, ni qualification LPBF.
