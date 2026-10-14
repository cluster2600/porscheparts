# Vérification

- `read_castellation_v2.py` relit tous les payloads et copies préalables de 089–091, ainsi que 086. Il reconstruit la parenté, les chaînes orientées, volumes, raccord, niveaux, diagnostics et seize instantanés natifs. Le premier lecteur et son traceback sont conservés : il tentait de convertir `constant` en nombre. La v2 sépare explicitement le maillage initial des étiquettes numériques.
- `read_target_v2.py` décode le STL sauvegardé, retrouve les coordonnées exactes de 086, compare tous les triangles orientés par région, contrôle les arêtes et la convexité projetée, recalcule la borne entre facettisations et leurs volumes. Sa v1 est conservée : elle incluait à tort le manifeste dans la comparaison des entrées du solveur natif. La v2 exclut explicitement cette métadonnée et confirme une seule accolade ajoutée dans le dictionnaire.
- Aucun natif rejoué pour corriger ces lecteurs. Tous les refus, dictionnaires et journaux sont archivés. Code zéro de 091 ne vaut pas admission : `Failed 1 mesh checks.` dans chacun des seize contrôles.
- Tests turbo : 109 exécutés, 108 réussis et un ignoré, 15,644 s.
- `PATH=work/bionic-tools/bin:$PATH make check` : 3 896 tests en 211,695 s, 172 ignorés ; deux échecs flottants WE43/fan_stator et trois erreurs de dépendances rtree/networkx hors turbo déjà connus. Le contrôle global local n'est pas vert.
- Publication : trois actifs de lecture préalable publiés avant préparation, puis archive complète et cinq actifs de livraison ajoutés. Tailles et SHA-256 GitHub comparés aux fichiers locaux ; tous les payloads du tar relus localement. Aucun second téléchargement distant intégral revendiqué.

Les conditions de maillage, d'admission, de repos, de convergence, de performance et de calibration physique restent distinctes. Aucun changement des surfaces physiques, des équations ni des seuils.
