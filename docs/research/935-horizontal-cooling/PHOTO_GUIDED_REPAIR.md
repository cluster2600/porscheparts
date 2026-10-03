# Réparation visuelle des surfaces du rotor 935

Exécution privée du 3 octobre 2026. Le scan préparé du rotor avait 8 657
arêtes de bord réparties en 58 contours. Une fermeture automatique brutale
aurait créé des plaques planes à travers les pales et le moyeu. La réparation
ci-dessous produit donc une **référence visuelle fermée**, distincte du modèle
fonctionnel et des calculs mécaniques.

## Références visuelles

Trois photographies/pages publiques ont servi à contrôler la topologie
extérieure attendue : roue horizontale à pales radiales courbes, moyeu central
et volume général du flat fan. Elles ne sont ni téléchargées ni incluses dans
le dépôt.

- [Design911, roue et entonnoir de reproduction 935](https://www.design911.co.uk/p/fan-housing-with-fan-blades-porsche-935/)
- [AASE Sales, ensemble flat fan 935/962](https://www.aasesales.com/products/noloc-j128-24000r-110746)
- [Jim Torres Racing, ensemble de reproduction](https://jimtorresracing.com/for-sale/reproduction-flat-fan)

Ces sources documentent une silhouette et des composants commerciaux. Elles ne
calibrent pas une caméra, ne donnent aucune profondeur de pales ou épaisseur
du spécimen, et ne démontrent pas l'identité de sa variante.

## Méthode et résultat

Le programme [photo_guided_surface_repair.py](../../../twins/935-horizontal-cooling-system-f0/source/photo_guided_surface_repair.py)
contrôle l'empreinte SHA-256 de l'OBJ préparé, réduit la surface pour le
calcul, estime les normales et applique une reconstruction Screened Poisson.
Il réexporte dans un nouveau dossier privé `work/`, puis contrôle la fermeture
topologique après soudure des sommets STL. Les petits fragments créés par le
reconstructeur sous 0,1 % des triangles sont retirés et consignés.

L'exécution `run-009` a conservé deux composantes substantielles, retiré 16
triangles de poussière générée et donné une surface de 72 879 sommets et
145 794 triangles. Elle est étanche et son orientation est cohérente. Le
volume de 1 173 660,4 unités source cubiques est seulement une propriété de
cette fermeture visuelle : l'unité de l'OBJ est inconnue et ce volume ne doit
être converti ni en masse ni en dimension.
Le contrôle MeshLab de cette sortie ne détecte ni face auto-intersectée,
ni face d'arête non-manifold, ni sommet non-manifold.

La géométrie, son aperçu et le reçu d'exécution restent privés dans
`work/935-photo-guided-repair-20261003/run-009/`. Les scans, leurs coordonnées
et les images sources restent hors Git.

## Ce que la réparation ne résout pas

Le résultat ne fournit ni axe fonctionnel, ni moyeu/arbre, ni épaisseur locale
fiable, ni jeu rotor/carter, ni support, ni entraînement, ni datums. Il est
donc `solver_ready: false` et ne peut pas porter un poids, un régime, une
contrainte, un débit ou une décision d'impression. La prochaine reconstruction
fonctionnelle enregistrera les surfaces réparées comme hypothèses et les
remplacera par des relevés indépendants des portées, trous, épaisseurs et face
arrière.
