# Criblage PicoGK F0 du piston

Le balayage du 8 septembre 2026 a réellement généré six variantes avec
PicoGK 2.3.0 / `picogk.26.2` dans l'image native amd64 identifiée dans
`picogk-optimization-screen.json`. Il minimise la masse et emploie des rapports
géométriques de galerie comme proxies thermohydrauliques, sous une marge de
plaque ambiante provisoire de `1,50`.

Aucun dessin n'est sélectionné. Toutes les variantes échouent la marge cible ;
l'audit trimesh trouve aussi des arêtes non-manifold dans chaque STL brut.
Les maillages volumineux restent hors Git et n'ont pas été réparés. Leurs
empreintes sont conservées dans les rapports afin de rendre l'exécution
auditable sans faire passer un mesh PicoGK pour un master BREP.

- `picogk-optimization-screen.json` : paramètres, résultats, empreintes et
  décision multiobjectif ;
- `picogk-output-integrity.json` : audit indépendant des sorties STL ;
- `../../source/run_picogk_optimization_screen.cs` : générateur reproductible ;
- `../../source/verify_picogk_optimization_outputs.py` : contrôle non destructif.

Ces preuves n'autorisent ni fabrication, ni simulation LPBF aval, ni montage,
ni fonctionnement moteur.
