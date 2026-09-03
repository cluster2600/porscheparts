# Preuves F39 B-Rep scan-only

Ce dossier publie uniquement la reconstruction analytique F39, ses rapports et
ses images. Le scan source et les STL/MSH dérivés ne sont pas versionnés.

Fichiers :

- `f39-brep-scan-only-head.step` : maître analytique OCCT, SHA-256
  `562a274fb22b9b957a47b0d51020ad1807a2733c3e6b8a4eddb526b9c8a0c71a` ;
- `f39-brep-build-report.json` : réimport STEP et maillage volumique ;
- `f39-brep-validation-report.json` : topologie, flood-fill, épaisseur et écart
  échantillonné au scan ;
- `f39-brep-exterior.png` : vue extérieure ;
- `f39-brep-section.png` : coupe calculée en X = -18 mm ;
- `f39-brep-scan-overlay.png` : comparaison visuelle, sans géométrie de scan
  distribuée.

Verdict : le STEP est réimportable et maillable, et aucun volume fermé n'est
détecté aux trois résolutions testées. Les portes d'épaisseur globale et de
qualité minimale du maillage échouent. Ajustement OEM, impression métal et
démarrage moteur restent interdits.
