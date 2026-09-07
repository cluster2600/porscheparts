# F43 — reconstruction locale par contours du scan

Ce dossier publie uniquement une synthèse chiffrée et deux rendus de la
reconstruction. Le scan, les profils de coupe, le STEP, le STL et les maillages
Gmsh restent privés et non versionnés. Leurs empreintes SHA-256 lient les
contrôles publics aux fichiers locaux.

Le candidat F43 est une **base B-Rep externe uniquement**. Le corps et les
ailettes suivent des contours irréguliers dérivés du stock scan-conforme; aucune
ellipse, aucun ovale et aucune boîte globale ne génèrent l'enveloppe. Trois
sections localement pathologiques ont été retirées et le contour supérieur a
été reconstruit depuis son voisin immédiat. Ces modifications sont explicites
dans le rapport.

Résultat actuel : BRepCheck, monobloc/manifold, p-courbes et BOPAlgo passent.
Le maillage tétraédrique 3D termine sans élément inversé, mais 378 éléments sur
654 729 restent sous `minSICN = 0,1`. La déviation latérale P95 au stock dépasse
également le seuil documentaire. Les chambres, conduits, sièges, guides,
galeries et interfaces ne sont pas présents. Le verdict est donc fermé : ni
CAE strict, ni impression, ni montage, ni démarrage ne sont autorisés.

Fichiers publiés :

- `f43-scan-contour-patch-report.json` : métriques et verdict fail-closed;
- `917-head-f43-scan-contour-4views.png` : quatre vues ombrées;
- `917-head-f43-scan-contour-section.png` : coupe de la seule peau externe.
