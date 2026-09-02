# Preuves F31 — calcul EF du deck de culasse 2V/4V

Ce dossier publie les résultats synthétiques de 36 résolutions CalculiX sur les
quatre concepts F29. La géométrie solveur est un deck défeaturé reconstruit à
partir des paramètres de conception ; ce n'est pas une culasse Porsche 917
mesurée ni une géométrie de fabrication.

## Contenu

- `report.json` : maillages, cas de charge, résultats, convergence, bilans et
  empreintes des fichiers de travail ;
- `publication.json` : empreintes SHA-256 des preuves publiées ;
- `figures/reference-fea-2v-4v.png` : comparaison P95/déplacement ;
- `figures/mesh-convergence.png` : indépendance au maillage.
- `omniverse/preflight.*` : préflight CAD-to-SimReady bloqué avant conversion.

![Comparaison EF 2V/4V](figures/reference-fea-2v-4v.png)

![Convergence](figures/mesh-convergence.png)

Les fichiers lourds Gmsh/CalculiX restent sous `work/` et se régénèrent par la
chaîne documentée. Aucun maximum de contrainte aux appuis n'est utilisé comme
contrainte admissible. Toutes les autorisations de fabrication et de démarrage
moteur restent à `false`.

Le préflight Omniverse est une preuve de blocage, pas une conversion : les
services Content Agents n'étaient pas prêts et aucun USD n'a été créé.

La méthode et l'interprétation sont détaillées dans
[la documentation F31](../../../../docs/917_HEAD_REFERENCE_CAE_F31.md).
