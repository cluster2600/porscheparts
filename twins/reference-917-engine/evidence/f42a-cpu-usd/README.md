# F42a — conversion CPU des six STEP F41

Le 3 septembre 2026, le lot F42a a été exécuté sur un worker privé
`linux/amd64`, sans GPU et sans réseau dans le conteneur. Il a utilisé l'image
publique immuable :

`ghcr.io/cluster2600/3dprinting993-simready-workflow@sha256:3d841cc578ca2da04f021e92bfbffabe53052aa49ba9c12ae2971526cd692e84`

L'archive F41 liée par SHA-256 a été filtrée par l'allowlist de quinze fichiers.
Aucun scan brut, STL ou 3MF n'a été importé dans le lot.

## Résultat vérifié

- six STEP ont été convertis en six USD : bielle, vilebrequin, paire de paliers,
  piston, axe de piston et segment ;
- les six USD totalisent `167044` octets ;
- chaque USD a un `defaultPrim`, au moins un mesh, `upAxis=Z` et
  `metersPerUnit=0.001` ;
- les bornes ont respecté les tolérances du contrat F42a ;
- aucun rigid body, collider ou joint n'a été ajouté ;
- le convertisseur a conservé un nom de `defaultPrim` issu de son fichier
  temporaire : ces USD ne sont donc ni canoniques ni publiables tels quels ;
- 132 familles sur les 138 prévues restent bloquées ;
- aucune instance payante n'a été lancée pour cette conversion.

Les SHA-256 et tailles de chaque USD figurent dans [`summary.json`](summary.json).
Le rapport d'exécution privé porte le SHA-256
`5d9e2a4d6c7c387f8926896de80a84b18c9927f09c3af01b8eff16f3354dafa7`.

## Limites fermées

Les USD, STEP, archive source et journaux restent hors du dépôt. Les six
géométries sont des graines paramétriques de recherche et leur namespace doit
être normalisé avant le lot RTX : elles ne sont ni
dimensionnellement corrélées à un moteur réel, ni SimReady, ni assemblées, ni
qualifiées pour l'impression 3D. Aucun matériau, PhysX, fluide, combustion,
fatigue, refroidissement ou validation à 1 600 ch n'a été exécuté.

Le lot suivant est volontairement séparé et exige un runtime RTX qualifié. Il
doit commencer par l'affectation de propriétés sourcées, les collisions et un
aperçu OVRTX, sans ouvrir les portes de fabrication ou de démarrage.
