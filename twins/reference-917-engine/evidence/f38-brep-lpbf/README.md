# F38 — B-Rep hybride conforme au scan et audit LPBF

Ce dossier remplace l'ancienne direction parallélépipédique. L'extérieur F38
reprend exactement la connectivité du maillage F37 et applique un décalage
normal de `0,45 mm`. Il ne contient ni boîte externe ni empilement synthétique
d'ailettes. L'échelle reste conditionnelle à `1 unité du scan = 1 mm`.

## Hiérarchie géométrique

- Le maître de surface est local :
  `local-only://917-head-f38-scan-offset-master.stl`, SHA-256
  `d51129380f33d5613b6e8cf8cc5e01f05d4fcd9f22f5e98682c8d05b86f0e032`.
  Il contient 857 330 triangles et conserve la morphologie fine du scan.
- Le STEP local `local-only://917-head-f38-faceted-proxy.step` est un B-Rep OCCT facetté à 7 000 faces.
  Il repasse bien par OCCT/build123d comme un solide unique valide, mais Gmsh
  échoue sur une intersection PLC segment/facette. Ce proxy n'est donc pas un
  domaine CAE ni une CAO de production.
- Le STL local `local-only://917-head-f38-faceted-proxy.stl` est uniquement le maillage allégé associé.
- Les volumes gaz/chambre quatre soupapes et huile restent les noyaux F36/F37
  référencés par empreinte dans le rapport. La coupe les montre, mais ne prouve
  pas l'ajustement dimensionnel.

Les deux proxies sont identifiés par empreinte dans le rapport mais **ne sont
pas versionnés**, car leur géométrie dérive directement du scan et aucune
licence de republication réutilisable n'est établie.

## Résultats bloquants

| Contrôle | Résultat | Exigence | Porte |
|---|---:|---:|---|
| Épaisseur, minimum échantillonné | 0,00497 mm | ≥ 1,5 mm | échec |
| Épaisseur, percentile 1 % | 0,1113 mm | ≥ 1,5 mm | échec |
| Cavités voxel 2,0 / 1,5 / 1,0 mm | 0 / 37,125 / 106 mm³ | zéro convergé | échec |
| Surfaces à supporter, orientation X 45° | 10,3707 % | < 0,5 % | échec |
| Maillage volumique Gmsh du STEP | intersection PLC | succès | échec |

Les contrôles d'épaisseur sont échantillonnés, non exhaustifs et ne remplacent
pas une tomographie. Le contrôle de surplomb n'est pas une simulation thermique
de procédé LPBF.

## Images

- `917-head-f38-exterior.png` : extérieur ombré, sans arêtes de proxy visibles.
- `917-head-f38-scan-overlay.png` : comparaison F37/F38, écart construit de
  0,45 mm.
- `917-head-f38-section.png` : grande coupe avec noyaux gaz et huile.

## Verdict

**Impression métal et démarrage moteur interdits.** Il faut encore corriger les
parois minces, ouvrir ou supprimer les volumes piégés, reconstruire les surfaces
fonctionnelles analytiques, produire un solide volumiquement maillable, qualifier
le matériau par coupons à chaud et corréler les calculs aux contrôles physiques.
