# Forme native du congé R1 — coupe comparative

Planche de revue en `work/` uniquement. Elle compare le STEP de référence et le BREP natif du prototype C1-002 à **X = 81,6750002098722 mm**, abscisse du pic EF initial indiqué par la racine. Les deux vues YZ partagent exactement leurs axes en millimètres et leur fenêtre. L’encart montre la position du zoom dans la coupe complète de référence.

La forme après est issue de `candidate-native.brep` SHA `a42e6942722957076410d4a89b24f9bd0f11677dfa8319103d6733a0db8a1cf9`, pas du STEP réexporté. Le reçu natif C1-002 `403d77960c019c367bec96adee0078f519fda98623b2468e2c5d33fee3219b25` conserve son statut **refused**, causé par le contrôle de retrait de matière au rechargement STEP. Il constate séparément un booléen natif ancien−nouveau vide et un ajout natif de **35,534438081499616 mm³**. La légende « prototype CAO, échange STEP en contrôle » reste visible. Aucune admission de fabrication ou de résistance n’est déduite de cette figure.

Le R1 est le rayon de la construction 3D native. Aucun cercle R1 n’est redessiné à la place de la coupe. `BRepAlgoAPI_Section` calcule chaque section avec `Approximation(False)`. Les courbes natives sont ensuite échantillonnées par `GCPnts_QuasiUniformDeflection` à 0,001 mm pour le dessin seulement ; cette valeur n’est pas un nouveau critère d’admission. Les coordonnées XYZ réellement évaluées et les types de courbes sont conservés dans `data-001/section-data.json`, avec un SHA de leurs bits binary64 et les sources. Aucun point n’est déplacé vers le plan ni lissé par le renderer.

## Exécutions réelles

- Sept tests stdlib PASS ; aucun import CAD ou Matplotlib pendant les tests.
- Extraction : superviseur 4d18 inchangé, budget 180 s, alarme 150 s, CPU 140–160 s, nice 10, OSD/BLAS 1, zéro pool. RC réel 0, 8,2305185 s ; groupe fermé et toutes les sources inchangées.
- Coupe avant : **24 arêtes, 699 points** ; coupe après : **25 arêtes, 1 700 points**. Écart X maximal observé : **2,842170943040401×10⁻¹⁴ mm**, vérifié contre la tolérance native des arêtes. Tous les points round-trip JSON conservent leur SHA binary64.
- Rendu exécuté depuis `/`, via le runtime Matplotlib de la planche21, sous 4d18/120 s ; RC réel 0, 2,1562467 s, groupe fermé. PNG, SVG et PDF conservés dans `render-001/`. PNG et page1 du PDF inspectés ici ; revue racine attendue avant toute galerie.

Le source, les plans exacts, les argv, stdout/stderr et les deux reçus de supervision sont conservés. Le source et les entrées n’ont pas changé pendant ces exécutions. Les tableaux des coupes complètes sont soumis au dessin ; le zoom est uniquement un cadrage des axes, explicitement indiqué dans les reçus.

## Rejeu portable du dessin

Depuis `/`, avec un **nouveau** chemin de sortie inexistant :

```sh
/Library/Frameworks/Python.framework/Versions/3.10/bin/python3.10 -B \
  /CHEMIN/REPO/work/carrier-fillet-section-figure-001/figure.py render \
  /CHEMIN/REPO/work/carrier-fillet-section-figure-001/data-001/section-data.json \
  DATA_SHA256 /CHEMIN/REPO/work/carrier-fillet-section-figure-001/render-fresh
```

Le SHA exact des données et les trois SHA des formats figurent dans `terminal-collection.json`. Les plans `export-launch-plan.json` et `render-launch-plan.json` gardent les commandes bornées réellement exécutées. Aucune galerie, capsule publiée ou géométrie d’origine n’a été modifiée.
