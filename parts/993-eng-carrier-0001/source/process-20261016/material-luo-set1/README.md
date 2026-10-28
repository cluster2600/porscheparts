# Sensibilité mécanique RT — données publiques Luo, jeu de procédé1

Ce lot contient quatre courbes individuelles mesurées, leurs conversions pré-striction et les tables de plasticité dérivées. La première courbe à utiliser pour le diagnostic convenu est `flat-set-1-plastic.inp`, choisie indépendamment de la réponse du carrier. Les trois autres spécimens bornent la dispersion observée de ce seul jeu ; quatre essais ne définissent pas une contrainte admissible.

Données originales : Luo,Yin,Simpson,Beese, [Data in Brief46(2023)108911](https://doi.org/10.1016/j.dib.2023.108911), [Zenodo6587905, version10-16-2023](https://zenodo.org/records/6587905), licence **CC BY4.0**. Attribution, lien de licence et transformations sont conservés dans `DATA_LICENSE.json`. Les archives originales ne sont pas ajoutées au dépôt.

Procédé : ProX DMP320, poudre LaserForm Ti Gr23(A) Ti6Al4V ELI,275W/800mm/s,couche60µm,hatch82µm, traction suivant l'axe de construction Z. Traitement : détente670°C5h puis refroidissement four sous argon12h. Ce lot constitue une sensibilité à température ambiante pour ce matériau et cet état ; il n'identifie pas la loi réelle du Grade5 du carrier. Le coefficient de Poisson n'est pas fourni par cette source : toute valeur utilisée reste une hypothèse distincte.

| Spécimen | E publié (MPa) | Rp0,2 publié (MPa) | Points plastique | Domaine εp du modèle | σvraie initiale → finale (MPa) |
| --- | ---: | ---: | ---: | ---: | ---: |
| Flat1 | 106000 | 946 | 248 | 0–0,046980426 | 956,878–1073,556 |
| Flat2 | 110000 | 942 | 255 | 0–0,046609583 | 952,630–1082,480 |
| Round1 | 118787 | 927 | 277 | 0–0,049013623 | 936,794–1082,219 |
| Round2 | 110000 | 956 | 191 | 0–0,047629591 | 966,909–1094,936 |

Pour la déformation homogène pré-striction : σvraie=σeng(1+eeng), εvraie=ln(1+eeng), εplast,brute=εvraie−σvraie/Epublié. Le modèle prend le Rp0,2 mesuré comme seuil initial et déplace son origine plastique à ce point. Cette convention enlève environ0,24–0,26% de déformation plastique déjà présente au point de preuve ; ce n'est pas une mesure de limite de proportionnalité. Les CSV conservent la conversion brute, sans cette translation et sans lissage, pour permettre de revoir cette décision.

Le bruit de contrainte est traité par régression isotone PAVA sur tous les points retenus après ce seuil et avant le maximum de contrainte engineering. Ajustement maximal0,611MPa pour les quatre essais,0,431MPa pour Flat1. Aucun point d'écrouissage n'est reconstruit depuis le seul couple Rp/Rm. La table est destinée à un modèle J2 isotrope de sensibilité ; elle n'inclut pas d'endommagement ni de loi de rupture. Un solveur peut extrapoler après la dernière entrée : rejeter l'interprétation du diagnostic si sa PEEQ maximale dépasse le domaine correspondant ci-dessus.

Reproduction depuis les trois téléchargements publics épinglés, avec Python et les dépendances `../materials/requirements.txt` :

```sh
python3 ../materials/fetch_luo_sources.py /path/to/new/source-data
python3 ../materials/extract_luo_rt.py /path/to/new/source-data /path/to/new/derived-data
```

Les SHA256, données de procédé, conventions, nombre de points et écart du lissage sont dans `provenance.json`. L'extracteur portable a reproduit exactement les huit fichiers numériques CSV/INP de ce lot.
