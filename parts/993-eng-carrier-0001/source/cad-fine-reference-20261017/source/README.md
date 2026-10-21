# Préparation d'une référence CAD triangulée fine

Ce dossier est une préparation non exécutée. Il ne modifie ni le STEP retenu,
ni le STL443b, ni les sources ou les calculs actifs. Le futur résultat serait
une référence **mesh↔mesh additionnelle**, sans borne BREP globale démontrée.

Le plan identifie le STEP `de0e55a3…` du run-001 et le runtime geometry/OCP
7.9.3.1 déjà installé. L'appel direct est
`BRepMesh_IncrementalMesh(shape, .01, False, .10, False)` : mode absolu,
angle conservé, calcul séquentiel. `STEPControl_Reader` transfère le STEP à
neuf dans l'unité système millimètre ; aucun maillage ancien n'est réutilisé.

Le choix **0,01 mm** provient uniquement du critère numérique existant
`parts/993-eng-carrier-0001/source/remesh-20261016/gmsh-criteria.json`,
ligne **37**, champ `maximum_mesh_interface_deviation_mm`. Le fichier porte
aussi des identités historiques d'autres exports : elles ne sont pas
présentées comme celles du STEP actuel. L'angle **0,10 rad** est repris du
source CAD réellement exécuté, `run-001/cad/source-snapshot.py`, ligne **36**.
Les deux sources sont épinglées. Aucun ratio ni subdivision arbitraire n'est
ajouté. Le mode relatif de `build123d.export_stl` est ainsi évité.

## Sortie prévue et gardes

`reference-mesh.npz` contiendrait `vertices` float64, `faces` int64 et
`CAD_face_ids` int64. Les coordonnées sont celles des nœuds OCP transformés
dans le repère monde ; aucune sortie STL ni conversion float32 n'intervient.
Un aller-retour NPZ doit conserver exactement les octets/dtypes/formes.

Chaque face CAD doit avoir des nœuds et triangles en double précision ; aucun
triangle ni face n'est omis. Les indices OCP sont validés avant conversion
1-based→0-based. L'ordre est inversé seulement pour `TopAbs_REVERSED` ; les
orientations internes/externes non prises en charge sont refusées. Le reçu
garde les ranges de toutes les faces CAD et leurs déflexions diagnostiques.

Seuls des XYZ aux **bits float64 identiques** partagent un indice. Aucune
tolérance de soudure n'est utilisée, même aux coutures CAD. Des coutures OCP
non identiques peuvent donc causer un refus, conservé comme tel. Les contrôles
sur les coordonnées dyadiques exactes refusent les triangles nuls, bords
ouverts, arêtes non manifold ou orientations incohérentes ; une composante
par arêtes et un volume orienté strictement positif sont requis. Le test
d'auto-intersection n'est pas effectué ici et reste explicitement `false`.
Ces gardes ne constituent pas un audit complet de la surface BREP.

## Exécution future bornée, non autorisée par cette préparation

`run.py` est l'appelant propriétaire de son unique enfant : plafond global
300 s, enfant au plus 260 s CPU/murales, réserve de nettoyage 30 s, un thread,
nice10. L'enfant reçoit seulement le runtime CAD existant et le plan gelé.
Le timeout termine uniquement son groupe de processus nouvellement créé et
récolte le vrai code retour. Les fichiers d'entrée, sources et fichiers du
runtime épinglés sont revérifiés avant/après. Le pic RSS est mesuré ; aucun
plafond RAM matériel n'est affirmé. Le budget est une borne d'essai, sans ETA
prédite depuis l'ancien maillage relatif.

La commande à examiner avant tout GO est :

```sh
python3 -B /ABSOLUTE/PATH/TO/THIS/FOLDER/run.py
```

Les selfchecks stdlib sont seuls exécutables pendant cette préparation :

```sh
python3 -B /ABSOLUTE/PATH/TO/THIS/FOLDER/selfcheck.py
```

Ils n'importent ni OCP, ni NumPy, ni build123d et ne lancent aucun processus
CAD. Ils vérifient notamment orientation, fermeture, aire nulle exacte,
composantes, IEEE voisins, double précision et indices incomplets.

Même après un éventuel succès, `.01 mm` resterait une **déflexion demandée**,
pas une borne globale symétrique BREP↔référence. Le futur calcul CGAL sera
préparé séparément et devra conserver sa propre erreur additive absolue.

Sources primaires : [OCCT 7.9.3 meshing](https://github.com/Open-Cascade-SAS/OCCT/blob/V7_9_3/src/BRepMesh/BRepMesh_IncrementalMesh.hxx),
[lecture STEP](https://github.com/Open-Cascade-SAS/OCCT/blob/V7_9_3/src/STEPControl/STEPControl_Reader.hxx),
[triangulation double](https://github.com/Open-Cascade-SAS/OCCT/blob/V7_9_3/src/Poly/Poly_Triangulation.hxx).
OCCT est distribué sous LGPL-2.1 avec exception OCCT ; ces sources sont citées,
aucun environnement ni binaire n'est copié dans ce dossier.
