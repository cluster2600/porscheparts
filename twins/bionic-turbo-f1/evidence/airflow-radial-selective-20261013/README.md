# Projection sélective du sous-domaine radial — 080 et 081

081 conserve exactement le raccord et les deux fermetures tout en projetant une
autre paroi vers une cible synthétique connue. Le maillage est admis avant et
après projection. Aucun rotor ni port physique n'est présent, aucune surface ou
connexion du vrai turbo n'est modifiée, aucun solveur d'écoulement n'est lancé.

## Préparation et admission

Le parent 079 est le sous-domaine fixe à deux cellules radiales admis dans la
phase précédente. Les cartes et faces natives 078/079 sont relues avec toutes
leurs empreintes. Le raccord contient 6 912 points ; les 512 faces de fermeture
contiennent 768 points. Leur union de 7 424 points est gelée. Les 6 656 points
extérieurs restants sont déplacés radialement vers l'intérieur d'un huitième de
la largeur existante, au maximum 0,056605625 mm. Les 6 656 points internes et
les fermetures ne sont pas perturbés. Ce déplacement est uniquement synthétique.

La cible STL contient exactement les 28 160 triangles provenant des quadrilatères
de frontière originaux 079. Les faces natives restent quadrilatérales. Toutes
les entrées sont copiées AVANT exécution. Les entrées préparées de 080 et 081
sont identiques ; seule l'opération native ajoute snappy dans 081. Les paramètres
sont exactement ceux de 075, notamment nSmoothPatch=0 et nSolveIter=0 pour le
lissage du MAILLAGE, sans changement d'un solveur d'écoulement. Castellation,
raffinement et couches sont désactivés ; aucun seuil de qualité n'est assoupli.

080 passe le contrôle préalable en 2,263 s, code zéro sans OOM : 13 568 cellules,
20 736 points, 47 744 faces, une région fluide. Déterminant minimum
0,07945697154 ; non-orthogonalité maximale 23,21723 degrés. L'admission est
vérifiée avant de préparer/exécuter la projection suivante.

081 termine projection et checkMesh en 3,568 s, code zéro sans OOM : Mesh OK,
déterminant minimum 0,11865095799, non-orthogonalité maximale 23,08987 degrés,
aucune concavité ni petit déterminant signalé. Points, faces, owner/neighbour,
zones et métadonnées sont relus. La topologie et le rôle wall sont conservés ;
le groupe natif optionnel `inGroups 1(wall)` est explicitement vérifié.

## Conservation et déplacement mesurés

Tous les 7 424 points du raccord et des fermetures ont EXACTEMENT leurs coordonnées
originales décodées. Les 6 656 points internes sont aussi inchangés. Les 6 784
quadrilatères du raccord et les 512 faces des fermetures sont donc conservés,
sans projection implicite sur un autre plan aux extrémités.

Les 6 656 points extérieurs se déplacent tous : de 0,031702134 à
0,055450663 mm par rapport à l'entrée perturbée. La normale géométrique maximale
de rotation du raccord est 2,28795e−12 m/s et sa planéité 1,06252e−17 m ; ce
n'est pas une vitesse physique de l'air. Le domaine est entièrement fixe.

La planéité maximale de toutes les faces devient 1,35450e−6 m ; toutes les
cellules ont un volume positif. Volume 081 : 2,333381635788176e−6 m³, contre
2,042896235642941e−6 m³ dans 080 et 2,334076530416437e−6 m³ dans 079. La
frontière extérieure et le volume ne sont donc pas restitués exactement.

## Distance à la cible : points et surfaces distincts

Le lecteur final de distance utilise une projection sur le plan du triangle avec
coordonnées barycentriques, ou le minimum sur ses trois segments bornés. Des
cas analytiques à quatre échelles et douze recherches exhaustives sans élagage
vérifient la formule et la recherche. Toutes les boîtes des triangles cibles
sont examinées avant l'élagage conservatif des candidats.

Pour les 6 656 points mobiles, la distance maximale à la surface cible passe de
55,449066 µm avant projection à 1,752582 nm après projection. Elle diminue pour
chaque point examiné. La distance maximale à l'ANCIEN SOMMET reste 22,433753 µm :
les points peuvent glisser sur la cible, ces deux distances ne sont pas égales.

Une preuve séparée apparie explicitement les triangles (v0,v1,v2) et (v0,v2,v3)
de chaque quadrilatère source/final. Pour les mêmes coordonnées barycentriques,
l'inégalité triangulaire borne l'écart par le plus grand déplacement des sommets.
Elle fournit une borne symétrique de Hausdorff de **22,433753 µm** entre ces deux
surfaces triangulées, pas la distance de Hausdorff mesurée. La triangulation sert
uniquement à cette analyse, sans modifier les faces natives. Cette preuve remplace
l'argument antérieur de convexité des quadrilatères parents du lecteur v2 : on
ne revendique pas une borne pour n'importe quelle autre facettisation.

## Refus de lecteurs conservés

Le premier lecteur de topologie compare trop strictement le texte du patch et
s'arrête sur l'ajout natif de `inGroups 1(wall)`. Sa v2 vérifie le type, le compte,
l'adresse et cet unique groupe autorisé, sans modifier le maillage.

Le premier lecteur de distance utilisant trimesh 5.1.1 donne une borne impossible.
Sur la face native 40607, inchangée, il attribue 133,905549 µm de distance à un
sommet appartenant au triangle. Une représentation en millimètres du même cas
et la formule indépendante retrouvent zéro à l'arrondi près. La dépendance à
l'échelle est reproduite, source installée et licence MIT archivées. Les sorties
v1 restent REJETÉES. Aucun seuil de maillage ou solveur n'est changé. Les distances
ponctuelles finales proviennent uniquement du lecteur v2 indépendant. Le premier
script du témoin de bibliothèque avait aussi une erreur d'indexation d'un tuple ;
traceback conservé, v2 matérialise les labels comme tableau. Aucun natif rejoué.

## Portée

C'est un contrôle de projection sélective avec raccord et fermetures conservés,
sur un sous-domaine synthétique admis. La restitution exacte de la paroi, la
protection pendant le raffinement, le raccord après traitement, les couches et
l'intégration des pièces physiques restent distincts. Aucun repos, convergence,
stabilité ou gain de débit/puissance du turbo n'est validé par 080/081.

## Archive

[Entrées, sorties, journaux et lecteurs](https://github.com/cluster2600/porscheparts/releases/tag/bionic-turbo-radial-selective-2026-10-13). Les cinq actifs sont vérifiés par tailles et digests GitHub ; tous les payloads du tar sont relus localement. Aucun second téléchargement intégral distant n’est revendiqué.

```json
{
  "files": 123,
  "archive_bytes": 4299186,
  "archive_sha256": "00734a1ad31e03aedde8d1a84275aa31d300bc174f9cac0302a7ca225847f2f4",
  "manifest_sha256": "1749fafb0f2cb14a902b2a015f90919f2bc08831f25e98924a08ad61cdda1e89",
  "all_payloads_verified": true,
  "performance_ranking_authorized": false,
  "scopes": [
    {
      "case": "work/bionic-airflow-20261012/radial-selective-initial-080",
      "scope": "all_native_inputs_mesh_logs_histories_fields_and_receipts",
      "performance_accepted": false
    },
    {
      "case": "work/bionic-airflow-20261012/radial-selective-snap-081",
      "scope": "all_native_inputs_mesh_logs_histories_fields_and_receipts",
      "performance_accepted": false
    },
    {
      "case": "work/bionic-radial-selective-20261013",
      "scope": "selective_projection_native_admission_independent_distance_and_surface_bounds",
      "performance_accepted": false
    }
  ]
}
```
