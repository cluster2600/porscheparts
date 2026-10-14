# Validation

- Primaire : 42462720 paires couvertes, dont 59462 intersections rationnelles
  exactes; 21 références, 11,891 s, code 0.
- Reconstruction indépendante : gabarits hex réduits, autre algorithme
  d'intersection, même parcours exhaustif et mêmes 59462 ensembles, 21
  références, 57,147 s, code 0. Aucun epsilon géométrique.
- Recollement : liens latéraux, domaines, 119808 bornes positives PR241 héritées,
  frontière de la chaîne tétraédrique égale aux 17920 triangles extérieurs,
  1,707 s, code 0. Ce contrôle ne rejoue pas les anciens encadrements.
- Hypothèses de preuve : reçus, empreintes et domaines liés à `proof.md`;
  contrôle structurel réussi, pas un prouveur automatique.
- Turbo : 109 tests, 108 réussis, un ignoré, 15,425 s, code 0.
- `PATH=work/bionic-tools/bin:$PATH make check` : 3911 tests en 214,315 s,
  172 ignorés, deux échecs et trois erreurs, code 2. Les cinq labels sont
  exactement ceux de PR241 (`validation.json`) : écarts flottants WE43/fan_stator
  et dépendances rtree/networkx hors turbo. Ils ne sont pas corrigés ici.

Aucune assertion scientifique refusée dans cette phase. Aucun paquet installé,
ancien parcours relancé, ratio ponctuel, nouveau maillage, conteneur ou solveur.
Docker observé sans calcul actif au précontrôle; aucun conteneur ou volume modifié.
Les preuves exactes concernent les expressions rationnelles et la représentation
partagée. CI, fusion, qualité native, repos et performance sont des étapes
séparées. Les traces locales de tests sont archivées.
