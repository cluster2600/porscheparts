# F42 — audit B-Rep privé de la culasse 917/935

## Verdict

Le STEP F41 lu localement n'est **ni réparé, ni déclaré imprimable**. Il est
réimportable comme un solide OCCT unique et `BRepCheck_Analyzer` le considère
valide, mais ces deux constats ne suffisent pas : le contrôle préparatoire aux
opérations booléennes trouve 247 défauts et l'écran d'épaisseur exact conserve
des zones très inférieures à la cible conditionnelle de 1,5 mm.

Le verrou F42 interdit toute ovalisation, dilatation ou reconstruction globale
de l'enveloppe issue du scan. Une réparation automatique `ShapeFix`, une couture
globale ou un offset n'est donc pas défendable sans localisation face par face
et preuve que la peau externe ne bouge pas. Aucun STEP F42 n'a été produit.

## Entrée privée et unités

- entrée : `917-head-lpbf-candidate-f41.step`, 16 838 933 octets ;
- SHA-256 : `b3110e5d6d102c7af865b4f5a8067281ed4b9452e331eb68433e4119d36c609a` ;
- politique : fichier privé local, jamais copié dans Git ;
- unité : le millimètre reste une convention du projet, pas une échelle OEM
  certifiée ;
- ajustement Porsche 917 : non certifié.

## Contrôles OCCT exacts

| Contrôle | Résultat F42 |
|---|---:|
| Solides / coques | 1 / 1 |
| Faces / arêtes / sommets uniques | 320 / 940 / 613 |
| Arêtes deux-faces / coutures / dégénérées | 906 / 31 / 3 |
| Arêtes libres / non-manifold | 0 / 0 |
| `BRepCheck_Analyzer`, méthode exacte | valide, 0 statut d'erreur |
| Volume | 1 086 299,458 unités³ |
| Surface | 178 755,423 unités² |
| Encombrement | 119,114 × 206,100 × 82,000 unités |
| Tolérance maximale arête/sommet | 0,000985 unité |

Les trois arêtes d'une longueur inférieure à `1e-5` sont des arêtes dégénérées
de pôles reconnues par OCCT ; elles ne sont pas comptées comme des arêtes libres.

Le second diagnostic, `BOPAlgo_ArgumentAnalyzer`, est plus sévère et pertinent
avant une nouvelle soustraction ou fusion :

- 9 faces signalées `BOPAlgo_SelfIntersect` ;
- 238 couples arête/face signalés `BOPAlgo_InvalidCurveOnSurface` ;
- défauts distribués sur la chambre, les surfaces internes et plusieurs niveaux
  d'ailettes, donc non assimilables à un défaut local unique.

Le fait que `BRepCheck` passe et que l'analyse booléenne échoue n'est pas une
contradiction : le premier accepte la représentation topologique courante ; le
second vérifie si ses courbes paramétriques et faces sont sûres pour de nouvelles
opérations géométriques.

Un second consommateur, Gmsh 4.12.1 avec import OpenCASCADE, a reçu le même STEP
par montage en lecture seule. Il n'a pas achevé le maillage 3D : après environ
10 minutes de reprises de maillage surfacique, le journal contenait 88 événements
« elements remain invalid » sur 25 surfaces distinctes. Le total cumulé de 3 488
éléments rapportés additionne plusieurs passes et ne représente donc pas 3 488
éléments uniques. Le calcul a été arrêté sans fichier `.msh`; cela confirme que
le STEP n'est pas CAE-ready malgré le `BRepCheck` positif.

## Épaisseur sans faux impacts de tessellation

La triangulation OCCT de 229 209 triangles sert uniquement à choisir des
centroïdes UV. Pour chaque échantillon, le point et la normale sont recalculés
sur la surface B-Rep, puis la corde est obtenue avec
`IntCurvesFace_ShapeIntersector` sur les faces exactes. Les intersections exactes
coïncidentes à `1e-5` unité sont fusionnées. Une couture entre deux triangles ne
peut donc plus produire seule une épaisseur quasi nulle.

Résultat déterministe (`seed=42`) :

- 640 cordes demandées et résolues, au moins une sur chacune des 320 faces ;
- minimum : 0,097251 unité ;
- p01 / p05 / médiane : 0,382384 / 0,810556 / 21,492815 unités ;
- 54 échantillons sous 1,5 unité ;
- fraction surfacique pondérée résolue sous 1,5 : 9,4298 %.

Cette méthode neutralise la couture de tessellation qui dégradait l'ancien écran
facetté, mais elle reste un **échantillonnage de cordes normales**. Ce n'est ni
une recherche continue du minimum global, ni une épaisseur par axe médian, ni
une tomographie. Le seuil de 1,5 mm échoue même avec cette méthode exacte.

## Décision de réparation

Aucune réparation n'est exécutée. Une correction acceptable devra :

1. rattacher chaque défaut aux opérations booléennes qui ont généré la face ou
   la p-courbe ;
2. corriger seulement ces sous-formes, en distinguant surfaces internes et peau
   externe ;
3. démontrer un déplacement nul de l'enveloppe extérieure par comparaison
   surfacique dense ;
4. répéter l'audit exact, le maillage volumique et l'écran d'épaisseur ;
5. conserver fermées les portes dimensionnelles, matériau à chaud, fatigue
   thermomécanique, CT/CND et banc corrélé.

## Artefacts et reproduction

Le rapport complet local contient les coordonnées des défauts et reste hors
Git :

`work/917-f42-brep-audit/917-head-f42-private-brep-audit.json`

Le dépôt ne reçoit que le
[résumé public lié par hash](../twins/reference-917-engine/evidence/f42-brep-audit/917-head-f42-brep-audit-summary.json),
et le [rendu diagnostique extérieur/demi-coupe](../twins/reference-917-engine/evidence/f42-brep-audit/917-head-f42-brep-audit.png),
sans STEP, sans maillage et sans coordonnées échantillonnées dans le JSON.

```bash
python twins/reference-917-engine/source/audit_brep_f42.py \
  --input /chemin/prive/917-head-lpbf-candidate-f41.step \
  --output work/917-f42-brep-audit/917-head-f42-private-brep-audit.json \
  --expected-sha256 b3110e5d6d102c7af865b4f5a8067281ed4b9452e331eb68433e4119d36c609a \
  --samples 640

python twins/reference-917-engine/source/publish_brep_audit_f42.py \
  --local-report work/917-f42-brep-audit/917-head-f42-private-brep-audit.json \
  --gmsh-log work/917-f42-brep-audit/gmsh.log \
  --image twins/reference-917-engine/evidence/f42-brep-audit/917-head-f42-brep-audit.png \
  --output twins/reference-917-engine/evidence/f42-brep-audit/917-head-f42-brep-audit-summary.json

make 917-f42-brep-audit-test
```

Les tests autonomes utilisent un parallélépipède OCCT synthétique : ils
vérifient volume/topologie et prouvent que les cordes exactes restent égales aux
dimensions analytiques malgré les coutures de la triangulation. Ils vérifient
également que le code F42 ne contient aucun écrivain STEP ni guérison automatique.

## Portes laissées fermées

F42 ne prouve ni l'épaisseur globale, ni l'échelle absolue, ni l'ajustement 917,
ni la matière à chaud, ni la fatigue, ni le procédé LPBF, ni le contrôle CT/CND,
ni la tenue au banc. La fabrication et le démarrage moteur restent interdits.
