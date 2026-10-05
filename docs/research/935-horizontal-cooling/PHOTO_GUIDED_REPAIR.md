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

## Fermeture Poisson rejetée après revue visuelle

La méthode historique a produit `run-009`. Cette sortie est fermée au sens
topologique mais sa revue multi-vues a révélé des ponts artificiels entre les
pales, le moyeu et la face arrière. Elle est donc **rejetée comme référence
visuelle** ; son volume et ses comptes de maillage ne doivent pas être repris.
Elle reste privée uniquement comme trace de la tentative.

La suite retenue est le [proxy visuel PicoGK](PICOGK_ROTOR_VISUAL_PROXY.md),
qui reconstruit explicitement le disque, le moyeu et les dix pales observées,
sans faire passer les surfaces absentes pour mesurées.

## Méthode historique et trace privée

Le programme [photo_guided_surface_repair.py](../../../twins/935-horizontal-cooling-system-f0/source/photo_guided_surface_repair.py)
contrôle l'empreinte SHA-256 de l'OBJ préparé, réduit la surface pour le
calcul, estime les normales et applique une reconstruction Screened Poisson.
Il réexporte dans un nouveau dossier privé `work/`, puis contrôle la fermeture
topologique après soudure des sommets STL. Les petits fragments créés par le
reconstructeur sous 0,1 % des triangles sont retirés et consignés.

L'exécution `run-009` a conservé deux composantes substantielles et retiré 16
triangles de poussière générée. Ces résultats techniques ne compensent pas
l'écart visible avec le rotor. Le contrôle MeshLab de cette sortie ne détecte
ni face auto-intersectée, ni face d'arête non-manifold, ni sommet non-manifold
mais il ne détecte pas une topologie mécaniquement ou visuellement inventée.

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
